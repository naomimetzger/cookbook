#!/usr/bin/env python3
"""Clips on white recipe (/clipsonwhite): 1 to 4 phone clips (or photos) appear one at a time, side
by side in a neat row on a white page, with equal gaps. Each clip starts playing when it appears.

  python3 clipsonwhite.py OUTPUT CLIP1 [CLIP2 CLIP3 CLIP4] [options]

  CLIP@12.5        start that clip at 12.5 seconds
  CLIP@12.5-15     use only 12.5-15s of that clip (its best bit); it leaves when that ends (never freezes)
  --every 0.5      seconds between each clip appearing (or --at 0 0.4 1.2 for exact times)
  --height 0.6     clip height as a share of the frame height
  --gap 0.02       gap between clips as a share of the frame width (all gaps equal)
  --y 0.5          where the row sits, 0 = top, 1 = bottom (0.5 = centred)
  --bg paper       page: paper (soft off-white with fine grain, default) or a colour
  --radius 0.07    rounded corners (share of clip width, 0 = square)   --shadow 0.25  soft shadow (0 = none)          --frame 16:9   16:9 or 9:16
  --audio 1        which clip's sound to keep (0 = silent)
  --exit 0         0 (default) = the whole row cuts away at once, abruptly, at the end.
                   Above 0 = clips leave one by one, last in first out, this many seconds apart.
  --still 1.0 / --rough / --length 4

Works on Mac, Windows and Linux. Needs ffmpeg.
"""
import json, os, re, shlex, subprocess, sys, tempfile, platform


def even(n):
    n = int(round(n)); return n - (n % 2)


def is_image(p):
    return p.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic"))


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


def finish(a, cmd, out, audio_from, length, info):
    """Add audio + encoder (or still frame) options, run, write settings."""
    if a.still is not None:
        cmd += ["-frames:v", "1", out]
    else:
        if audio_from is not None:
            cmd += ["-map", f"{audio_from}:a:0?", "-c:a", "aac", "-b:a", "192k"]
        crf, preset = ("28", "veryfast") if a.rough else ("18", "medium")
        cmd += ["-t", f"{length:.3f}", "-r", "30", "-c:v", "libx264", "-crf", crf, "-preset", preset,
                "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    with open(out + ".settings.txt", "w") as f:
        f.write(info + "\n" + " ".join(shlex.quote(c) for c in cmd) + "\n")
    print(f"Done: {out} ({info})")


def parse_clip(c):
    """'clip.mp4@12.5' starts at 12.5s; 'clip.mp4@12.5-15' uses only 12.5-15s (its best bit),
    then holds the last frame."""
    if "@" in c and not os.path.exists(c):
        f, t = c.rsplit("@", 1)
        try:
            if "-" in t:
                a_, b_ = t.split("-", 1)
                return f, float(a_), float(b_)
            return f, float(t), None
        except ValueError:
            pass
    return c, 0.0, None


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("output"); p.add_argument("clips", nargs="+")
    p.add_argument("--every", type=float, default=0.5); p.add_argument("--at", type=float, nargs="+")
    p.add_argument("--height", type=float, default=0.6); p.add_argument("--gap", type=float, default=0.05)
    p.add_argument("--y", type=float, default=0.5); p.add_argument("--bg", default="paper")
    p.add_argument("--radius", type=float, default=0.07); p.add_argument("--shadow", type=float, default=0.25)
    p.add_argument("--exit", type=float, default=0.0)
    p.add_argument("--equal", action="store_true", help="size the clips so every gap and every margin (left, right, top, bottom) is exactly the same")
    p.add_argument("--frame", default="16:9", choices=["16:9", "9:16"]); p.add_argument("--audio", type=int, default=1)
    p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true"); p.add_argument("--length", type=float)
    a = p.parse_args()
    clips = [parse_clip(c) for c in a.clips]
    n = len(clips)
    if not 1 <= n <= 4:
        raise SystemExit(f"/clipsonwhite takes 1 to 4 clips; got {n}.")
    W, H = (1920, 1080) if a.frame == "16:9" else (1080, 1920)
    if a.rough:
        W, H = W // 2, H // 2
    g = even(W * a.gap)
    ch = even(H * a.height); cw = even(ch * 9 / 16)
    if n * cw + (n - 1) * g > W * 0.92:                     # too wide: shrink to fit
        cw = even((W * 0.92 - (n - 1) * g) / n); ch = even(cw * 16 / 9)
    if a.equal:   # solve n*w + (n+1)*g = W and h + 2*g = H with w = h*9/16, so all gaps and margins match
        g = round((W - n * H * 9 / 16) / ((n + 1) - n * 9 / 8))
        ch = even(H - 2 * g); cw = even(ch * 9 / 16)
        g = (W - n * cw) // (n + 1)
    row = n * cw + (n - 1) * g
    x0 = (W - row) // 2
    y = int((H - ch) * a.y) if not a.equal else (H - ch) // 2
    times = a.at if a.at else [i * a.every for i in range(n)]
    vids = [(f, t0, t1) for f, t0, t1 in clips if not is_image(f)]
    length = a.length or (min((t1 or duration(f)) - t0 for f, t0, t1 in vids) if vids else 4.0)
    if a.exit <= 0:   # hard cut: end before any clip runs out of its best bit, so none leaves early
        times_ = a.at if a.at else [i * a.every for i in range(n)]
        ends = [ti + (t1 - t0) for (f, t0, t1), ti in zip(clips, times_) if t1]
        if ends:
            length = min(a.length, min(ends)) if a.length else min(ends)
    seek = a.still if a.still is not None else 0.0
    from PIL import Image, ImageDraw, ImageFilter
    tmp = tempfile.mkdtemp(prefix="clipsonwhite_")
    # page: plain colour, or "paper" = soft off-white with fine grain
    if a.bg == "paper":
        page = Image.blend(Image.new("L", (W, H), 244), Image.effect_noise((W, H), 22), 0.05).convert("RGB")
    else:
        page = Image.new("RGB", (W, H), colour(a.bg).replace("0x", "#") if colour(a.bg).startswith("0x") else a.bg)
    pf = os.path.join(tmp, "page.png"); page.save(pf)
    r = int(cw * a.radius)
    mk = Image.new("L", (cw * 4, ch * 4), 0)
    ImageDraw.Draw(mk).rounded_rectangle([0, 0, cw * 4 - 1, ch * 4 - 1], radius=r * 4, fill=255)
    mf = os.path.join(tmp, "mask.png"); mk.resize((cw, ch), Image.LANCZOS).save(mf)
    pad = int(ch * 0.12)
    shf = None
    if a.shadow > 0:
        sh = Image.new("L", (cw + 2 * pad, ch + 2 * pad), 0)
        ImageDraw.Draw(sh).rounded_rectangle([pad, pad + int(ch * 0.02), pad + cw, pad + ch + int(ch * 0.02)], radius=r,
                                             fill=int(255 * a.shadow))
        sh = sh.filter(ImageFilter.GaussianBlur(max(2, int(ch * 0.04))))
        img = Image.new("RGBA", sh.size, (0, 0, 0, 255)); img.putalpha(sh)
        shf = os.path.join(tmp, "shadow.png"); img.save(shf)
    lines = [f"[{n}:v]fps=30,format=rgba[c0]"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for i, ((f, t0, t1), ti) in enumerate(zip(clips, times)):
        played = max(0.0, seek - ti)                          # how far this clip has played at the still
        use = (t1 - t0) if t1 else length + 0.2
        played = min(played, max(0.0, use - 0.05))
        cmd += source_args(f, t0 + played, max(0.05, use - played))
    cmd += ["-loop", "1", "-t", f"{length + 0.2:.3f}", "-i", pf, "-loop", "1", "-i", mf]
    if shf:
        cmd += ["-loop", "1", "-i", shf]
    mi, si = n + 1, n + 2
    lines.append(f"[{mi}:v]format=gray,split={n}" + "".join(f"[m{i}]" for i in range(n)))
    if shf:
        lines.append(f"[{si}:v]format=rgba,split={n}" + "".join(f"[s{i}]" for i in range(n)))
    for i, ((f, t0, t1), ti) in enumerate(zip(clips, times)):
        x = x0 + i * (cw + g)
        lines.append(f"[{i}:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},setsar=1,fps=30,format=rgba,"
                     f"setpts=PTS-STARTPTS+{max(0.0, ti - seek):.3f}/TB[v{i}];[v{i}][m{i}]alphamerge[r{i}]")
        out = length - a.exit * (i + 1) if a.exit > 0 else length + 1
        if t1:                                                # leave when its best bit ends, never freeze
            out = min(out, ti + (t1 - t0))
        en = f"enable='between(t\\,{max(0.0, ti - seek):.3f}\\,{out - seek:.3f})'"
        src = f"c{i}"
        if shf:
            lines.append(f"[{src}][s{i}]overlay={x - pad}:{y - pad}:{en}[d{i}]"); src = f"d{i}"
        lines.append(f"[{src}][r{i}]overlay={x}:{y}:{en}:eof_action=pass[c{i + 1}]")
    lines.append(f"[c{n}]format=yuv420p[out]")
    cmd += ["-filter_complex", ";".join(lines), "-map", "[out]"]
    au = None
    if 1 <= a.audio <= n and has_audio(clips[a.audio - 1][0]):
        au = a.audio - 1
    finish(a, cmd, a.output, au, length,
           f"{W}x{H}, {n} clips {cw}x{ch}, gap {g}px, row from x={x0}, y={y}, appear at {times}")


if __name__ == "__main__":
    main()
