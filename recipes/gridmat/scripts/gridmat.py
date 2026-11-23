#!/usr/bin/env python3
"""Grid mat recipe (/gridmat): a plain cutting-mat style grid background (fine lines, stronger lines
every 5, a ruler edge) in a chosen colour, with the user's clip or photo on top as a card.

  python3 gridmat.py MEDIA OUTPUT [options]

  --mat green      green (default), blue, pink, cream, black, or a hex colour
  --size 0.62      card height as a share of the frame height (keeps the clip's shape)
  --radius 0.03    card corner roundness (0 = square)    --shadow 0.35  soft shadow under the card
  --angle 0        tilt the whole mat a little (degrees, e.g. 8) for a desk-photo feel
  --ruler          numbered ruler edge along the top and left
  --frame auto     16:9 or 9:16 (auto = same way round as the media)
  --dur 4 (photo) / --start 0 / --length / --still / --rough

Works on Mac, Windows and Linux. Needs ffmpeg and Pillow.
"""
import json, os, re, shlex, shutil, subprocess, sys, platform

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from media import (load_image, prepare_video, safe_output, temp_dir, frame_rate, is_image,  # noqa: E402
                   COLOR_TAGS, RGB_TO_YUV, AUDIO_MAP)



def fps_text(f):
    """media.frame_rate() as ffmpeg wants it: exact fractions for the NTSC rates (23.976 -> 24000/1001)."""
    return {23.976: "24000/1001", 29.97: "30000/1001", 59.94: "60000/1001"}.get(f, f"{f:g}")


def even(n):
    n = int(round(n)); return n - (n % 2)


def ready(path, tmp):
    """A photo becomes an upright PNG (HEIC and phone rotation handled); a video gets normal colour."""
    if is_image(path):
        out = os.path.join(tmp, "photo.png")
        load_image(path).save(out)
        return out
    return prepare_video(path, tmp)


def display_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    w, h, rot = s["width"], s["height"], 0
    for d in s.get("side_data_list", []):
        if "rotation" in d:
            rot = int(d["rotation"] or 0)
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          path], capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def has_audio(path):
    if is_image(path):
        return False
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                                "stream=index", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout.strip())


def colour(c):
    c = c.strip()
    return "0x" + c.lstrip("#") if re.fullmatch(r"#?[0-9a-fA-F]{6}", c) else c


HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CHOICES = {
    "bold": [("/System/Library/Fonts/HelveticaNeue.ttc", 1), ("C:/Windows/Fonts/arialbd.ttf", 0),
             ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)],
    "condensed": [("/System/Library/Fonts/HelveticaNeue.ttc", 9), ("C:/Windows/Fonts/impact.ttf", 0),
                  ("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", 0)],
    "serif": [("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", 0), ("C:/Windows/Fonts/georgiab.ttf", 0),
              ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 0)],
}


def find_font(name):
    if os.path.exists(name):
        return name, 0
    for path, idx in FONT_CHOICES.get(name, []) + FONT_CHOICES["bold"]:
        if os.path.exists(path):
            return path, idx
    raise SystemExit(f"No bold font found on this {platform.system()} computer; pass --font path/to/font.ttf")


def source_args(path, seek, dur):
    """ffmpeg input args for an image (looped for dur seconds) or a video (from seek)."""
    if is_image(path):
        return ["-loop", "1", "-framerate", "30", "-t", f"{dur:.3f}", "-i", path]
    return ["-ss", f"{seek:.3f}", "-t", f"{dur:.3f}", "-i", path]


def push_chain(W, H, push, dur, cx=0.5, cy=0.5):
    """Slow eased push-in: scale up a little over the clip, crop the frame around (cx, cy)."""
    if push <= 0:
        return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    z = f"(1+{push}*(1-pow(1-min(t/{dur:.3f}\\,1)\\,2)))"
    return (f"scale={2 * W}:{2 * H}:force_original_aspect_ratio=increase,crop={2 * W}:{2 * H},"
            f"scale=w='trunc({2 * W}*{z}/2)*2':h='trunc({2 * H}*{z}/2)*2':eval=frame:flags=bicubic,"
            f"crop={2 * W}:{2 * H}:x='(iw-{2 * W})*{cx}':y='(ih-{2 * H})*{cy}',scale={W}:{H}")


def finish(a, cmd, out, audio_from, length, info, fps="30"):
    """Add audio + encoder (or still frame) options, run, write settings."""
    if a.still is not None:
        cmd += ["-frames:v", "1", out]
    else:
        if audio_from is not None:
            cmd += ["-map", f"{audio_from}:{AUDIO_MAP}", "-c:a", "aac", "-b:a", "192k"]
        crf, preset = ("28", "veryfast") if a.rough else ("18", "medium")
        cmd += ["-t", f"{length:.3f}", "-r", fps, "-c:v", "libx264", "-crf", crf, "-preset", preset,
                "-pix_fmt", "yuv420p", *COLOR_TAGS, "-threads", "2", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    with open(out + ".settings.txt", "w", encoding="utf-8") as f:
        f.write(info + "\n" + " ".join(shlex.quote(c) for c in cmd) + "\n")
    print(f"Done: {out} ({info})")


MATS = {"green": "#11866A", "blue": "#2B5FD9", "pink": "#E58FB2", "cream": "#EFE7D6", "black": "#1E1E1E"}


def mat_image(W, H, colour, angle, ruler):
    from PIL import Image, ImageDraw, ImageFont
    base = MATS.get(colour, colour)
    light = colour in ("cream",)
    line = (0, 0, 0, 34) if light else (255, 255, 255, 38)
    strong = (0, 0, 0, 70) if light else (255, 255, 255, 85)
    pad = int(max(W, H) * 0.3)
    big = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), base)
    d = ImageDraw.Draw(big)
    step = max(8, int(min(W, H) / 22))
    lw = max(2, step // 22)
    for i, x in enumerate(range(0, big.width, step)):
        d.line([(x, 0), (x, big.height)], fill=strong if i % 5 == 0 else line, width=lw * (2 if i % 5 == 0 else 1))
    for i, y in enumerate(range(0, big.height, step)):
        d.line([(0, y), (big.width, y)], fill=strong if i % 5 == 0 else line, width=lw * (2 if i % 5 == 0 else 1))
    if ruler:
        rp, ri = find_font("bold")
        f = ImageFont.truetype(rp, max(8, step // 3), index=ri)
        for i, x in enumerate(range(pad, big.width - pad, step * 5)):
            d.text((x + 4, pad + 4), str(i * 5), font=f, fill=strong)
        for i, y in enumerate(range(pad, big.height - pad, step * 5)):
            d.text((pad + 4, y + 4), str(i * 5), font=f, fill=strong)
    if angle:
        big = big.rotate(angle, resample=Image.BICUBIC, fillcolor=base)
    return big.crop((pad, pad, pad + W, pad + H)).convert("RGB")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("media"); p.add_argument("output")
    p.add_argument("--mat", default="green"); p.add_argument("--size", type=float, default=0.62)
    p.add_argument("--radius", type=float, default=0.03); p.add_argument("--shadow", type=float, default=0.35)
    p.add_argument("--angle", type=float, default=0); p.add_argument("--ruler", action="store_true")
    p.add_argument("--frame", default="auto", choices=["auto", "16:9", "9:16"])
    p.add_argument("--dur", type=float, default=4.0); p.add_argument("--start", type=float, default=0)
    p.add_argument("--length", type=float); p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true")
    a = p.parse_args()
    safe_output(a.output)                       # never overwrite: refuse before doing any work
    tmp = temp_dir("gridmat_")
    try:
        make(a, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def make(a, tmp):
    from PIL import Image, ImageDraw, ImageFilter
    a.media = ready(a.media, tmp)
    fps = 30 if is_image(a.media) else frame_rate(a.media)   # keep the source frame rate (photos: 30)
    rate = fps_text(fps)
    iw, ih = display_size(a.media)
    fr = a.frame if a.frame != "auto" else ("9:16" if ih > iw else "16:9")
    W, H = (1920, 1080) if fr == "16:9" else (1080, 1920)
    if a.rough:
        W, H = W // 2, H // 2
    ch = even(H * a.size); cw = even(ch * iw / ih)
    if cw > W * 0.86:
        cw = even(W * 0.86); ch = even(cw * ih / iw)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    r = int(min(cw, ch) * a.radius)
    page = mat_image(W * 2, H * 2, a.mat, a.angle, a.ruler).resize((W, H), Image.LANCZOS).convert("RGBA")
    if a.shadow > 0:
        sh = Image.new("L", (W, H), 0)
        off = int(ch * 0.02)
        ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + off, x0 + cw, y0 + ch + off], radius=r, fill=int(255 * a.shadow))
        sh = sh.filter(ImageFilter.GaussianBlur(max(2, int(ch * 0.035))))
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 255)); dark.putalpha(sh)
        page = Image.alpha_composite(page, dark)
    pf = os.path.join(tmp, "mat.png"); page.save(pf)
    m = Image.new("L", (cw * 4, ch * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cw * 4 - 1, ch * 4 - 1], radius=r * 4, fill=255)
    mf = os.path.join(tmp, "mask.png"); m.resize((cw, ch), Image.LANCZOS).save(mf)
    seek = a.still if a.still is not None else a.start
    length = (a.length or max(0.1, duration(a.media) - seek)) if not is_image(a.media) else (a.length or a.dur)
    cmd = ["ffmpeg", "-n", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", pf]
    cmd += source_args(a.media, 0 if is_image(a.media) else seek, length + 0.1)
    cmd += ["-loop", "1", "-i", mf]
    lines = [f"[1:v:0]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},setsar=1,fps={rate},format=rgba[v]",
             f"[2:v]format=gray[m];[v][m]alphamerge[c];[0:v]fps={rate},format=rgba[pg];[pg][c]overlay={x0}:{y0}:shortest=1:format=rgb,{RGB_TO_YUV}[out]"]
    cmd += ["-filter_complex", ";".join(lines), "-map", "[out]"]
    finish(a, cmd, a.output, 1 if has_audio(a.media) else None, length,
           f"{W}x{H}, {rate} fps, mat {a.mat}, card {cw}x{ch} at {x0},{y0}, radius {r}px, shadow {a.shadow}, angle {a.angle}, ruler {a.ruler}",
           rate)


if __name__ == "__main__":
    main()
