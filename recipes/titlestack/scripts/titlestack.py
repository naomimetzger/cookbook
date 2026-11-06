#!/usr/bin/env python3
"""Title stack recipe (/titlestack): a three-line intro title with a big contrast in size and font.
A small plain word, then a huge hand-drawn coloured word, then a small plain word tucked to the
right, e.g.  the / FLASH CUT / transition. The words appear one at a time.

  python3 titlestack.py OUTPUT --top the --big "FLASH CUT" --bottom transition [options]

  --over FILE      put the title over a video or image (default: a plain paper-coloured page)
  --card FILE      a clip or photo in a rounded card under the title, exactly as wide as the big word
  --card-shape 9:16  a tall vertical card, centred under the title (default: as wide as the big word)
  --card-start 0   where the card clip starts (seconds); its sound plays (--mute-card to silence it)      --card-radius 0.04  corner roundness
  --bg #F6F0E3     page colour when there's no --over (cream paper by default)
  --frame 9:16     9:16 (default) or 16:9 (ignored with --over: follows that file)
  --color #9B111E  colour of the big word (deep red)          --ink #111111   colour of the small words
  --big-font pixel pixel (blocky pixel lettering, default), hand (hand-drawn marker), bold, condensed,
                   serif, or a .ttf/.otf file
  --small-font rounded   rounded (default), bold, serif, or a .ttf/.otf file
  --slant 0.18     lean the big word forward like brush lettering (0 = upright)
  --y 0.3          where the title sits, 0 = top, 1 = bottom
  --every 0.35     seconds between the three words appearing (0 = all at once)
  --dur 2.5        length (or the length of --over minus --start)
  --still 1.5 / --rough / --start 0

Works on Mac, Windows and Linux (fonts fall back to the closest one on each computer).
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
    "hand": [("/System/Library/Fonts/MarkerFelt.ttc", 1), ("C:/Windows/Fonts/segoepr.ttf", 0),
             ("C:/Windows/Fonts/Inkfree.ttf", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf", 0)],
    "rounded": [("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", 0), ("C:/Windows/Fonts/arialbd.ttf", 0),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)],
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


def text_img(text, font, color, slant=0.0):
    from PIL import Image, ImageDraw
    l, t, r, b = font.getbbox(text)
    pad = int(font.size * 0.1)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    img = Image.new("RGBA", (w + int(abs(slant) * h), h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l + int(abs(slant) * h), pad - t), text, font=font, fill=color)
    if slant:
        img = img.transform(img.size, Image.AFFINE, (1, slant, 0, 0, 1, 0), resample=Image.BICUBIC)
    return img.crop(img.getbbox())


def pixel_img(text, path, idx, color, max_w, max_h):
    """Real pixel lettering: draw the word tiny with no smoothing, then blow it up with hard edges."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(path, 16, index=idx)
    l, t, r, b = f.getbbox(text)
    small = Image.new("L", (r - l + 2, b - t + 2), 0)
    dr = ImageDraw.Draw(small); dr.fontmode = "1"                 # no anti-aliasing = square pixels
    dr.text((1 - l, 1 - t), text, font=f, fill=255)
    small = small.crop(small.getbbox())
    scale = max(1, int(min(max_w / small.width, max_h / small.height)))   # whole-number blow-up
    mask = small.resize((small.width * scale, small.height * scale), Image.NEAREST)
    img = Image.new("RGBA", mask.size, color); img.putalpha(mask)
    return img


def main():
    import argparse
    from PIL import Image, ImageFont
    p = argparse.ArgumentParser()
    p.add_argument("output"); p.add_argument("--top", default=""); p.add_argument("--big", required=True)
    p.add_argument("--bottom", default=""); p.add_argument("--over"); p.add_argument("--bg", default="#F6F0E3")
    p.add_argument("--frame", default="9:16", choices=["9:16", "16:9"])
    p.add_argument("--color", default="#9B111E"); p.add_argument("--ink", default="#111111")
    p.add_argument("--big-font", default="pixel"); p.add_argument("--small-font", default="rounded")
    p.add_argument("--slant", type=float, default=0.18); p.add_argument("--y", type=float, default=0.3)
    p.add_argument("--every", type=float, default=0.35); p.add_argument("--dur", type=float, default=2.5)
    p.add_argument("--card"); p.add_argument("--card-start", type=float, default=0.0)
    p.add_argument("--card-shape", help="card shape, e.g. 9:16 for a vertical clip (a tall card, centred); default: as wide as the big word")
    p.add_argument("--card-radius", type=float, default=0.04); p.add_argument("--mute-card", action="store_true")
    p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true")
    p.add_argument("--start", type=float, default=0); p.add_argument("--length", type=float)
    a = p.parse_args()
    if a.over:
        iw, ih = display_size(a.over)
        W, H = (1080, 1920) if ih > iw else (1920, 1080)
    else:
        W, H = (1080, 1920) if a.frame == "9:16" else (1920, 1080)
    if a.rough:
        W, H = W // 2, H // 2
    length = a.length or (a.dur if not a.over or is_image(a.over) else max(0.1, duration(a.over) - a.start))
    # big word: as wide as 84% of the frame, but never taller than 13% (tall) / 24% (wide) of it
    bp, bi = find_font("bold" if a.big_font == "pixel" else a.big_font)
    sp, si = find_font(a.small_font)
    if a.big_font == "pixel":
        pp, pi = find_font("bold")
        big = pixel_img(a.big, pp, pi, a.color, W * 0.84, H * (0.13 if H > W else 0.24))
    else:
        fs = int(H * 0.2)
        for _ in range(12):
            big = text_img(a.big, ImageFont.truetype(bp, fs, index=bi), a.color, a.slant)
            if big.width <= W * 0.84 and big.height <= H * (0.13 if H > W else 0.24):
                break
            fs = int(fs * min(W * 0.84 / big.width, H * (0.13 if H > W else 0.24) / big.height, 0.97))
    small_fs = max(10, int(big.height * 0.42))
    sf = ImageFont.truetype(sp, small_fs, index=si)
    top = text_img(a.top, sf, a.ink) if a.top else None
    bot = text_img(a.bottom, sf, a.ink) if a.bottom else None
    # measured layout: equal gaps, "top" lines up with the big word's left edge at its top,
    # "bottom" lines up with the big word's right edge at its foot (exact even with the lean)
    gap = int(big.height * 0.12)
    band = max(1, big.height // 4)
    tl = big.crop((0, 0, big.width, band)).getbbox() or (0, 0, big.width, band)
    br = big.crop((0, big.height - band, big.width, big.height)).getbbox() or (0, 0, big.width, band)
    card = None
    if a.card:
        cw_ = int(big.width)
        if is_image(a.card):
            ci = Image.open(a.card); c_ar = ci.width / ci.height
        else:
            ciw, cih = display_size(a.card); c_ar = ciw / cih
        ch_ = int(min(cw_ / c_ar, H * (0.42 if H > W else 0.5)))
        if a.card_shape:                                       # e.g. 9:16 for a vertical clip: a tall card, centred
            sw, sh_ = (float(v) for v in a.card_shape.split(":"))
            ch_ = int(H * (0.64 if H > W else 0.6)); cw_ = int(ch_ * sw / sh_)
            if cw_ > big.width:
                cw_ = int(big.width); ch_ = int(cw_ * sh_ / sw)
        cw_ -= cw_ % 2; ch_ -= ch_ % 2
        card = (cw_, ch_)
    block_h = (top.height + gap if top else 0) + big.height + (gap + bot.height if bot else 0)
    if card:
        block_h += gap * 3 + card[1]
    y0 = int((H - block_h) * a.y)
    bx = (W - big.width) // 2
    layers, y = [], y0
    if top:
        layers.append((top, bx + tl[0], y)); y += top.height + gap
    layers.append((big, bx, y)); y += big.height + gap
    if bot:
        layers.append((bot, bx + br[2] - bot.width, y)); y += bot.height
    card_xy = (((W - card[0]) // 2 if a.card_shape else bx), y + gap * 3) if card else None
    tmp = tempfile.mkdtemp(prefix="titlestack_")
    files = []
    for k, (im, x, yy) in enumerate(layers):
        full = Image.new("RGBA", (W, H), (0, 0, 0, 0)); full.alpha_composite(im, (x, yy))
        f = os.path.join(tmp, f"w{k}.png"); full.save(f); files.append(f)
    seek = a.still if a.still is not None else a.start
    off = seek if a.still is not None else 0.0
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if a.over:
        cmd += source_args(a.over, 0 if is_image(a.over) else seek, length + 0.1)
        base = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30[b0]"
    else:
        cmd += ["-f", "lavfi", "-i", f"color=c={colour(a.bg)}:s={W}x{H}:r=30:d={length + 0.1:.3f}"]
        base = "[0:v]setsar=1[b0]"
    for f in files:
        cmd += ["-loop", "1", "-i", f]
    lines = [base]
    ci_idx = None
    if card:
        from PIL import ImageDraw
        cmask = os.path.join(tmp, "cmask.png")
        m = Image.new("L", (card[0] * 4, card[1] * 4), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, card[0] * 4 - 1, card[1] * 4 - 1], radius=int(card[0] * a.card_radius * 4), fill=255)
        m.resize(card, Image.LANCZOS).save(cmask)
        ci_idx = len(files) + 1
        cmd += (["-loop", "1", "-i", a.card] if is_image(a.card) else ["-ss", str(a.card_start), "-i", a.card])
        cmd += ["-loop", "1", "-i", cmask]
        lines.append(f"[{ci_idx}:v]scale={card[0]}:{card[1]}:force_original_aspect_ratio=increase,crop={card[0]}:{card[1]},"
                     f"setsar=1,fps=30,format=rgba[cv];[{ci_idx + 1}:v]format=gray[cm];[cv][cm]alphamerge[cc];"
                     f"[b0][cc]overlay={card_xy[0]}:{card_xy[1]}:eof_action=pass[b0c]")
        lines[0] = lines[0]
        base_label = "b0c"
    else:
        base_label = "b0"
    for k in range(len(files)):
        t = k * a.every - off
        src_lbl = base_label if k == 0 else f"b{k}"
        lines.append(f"[{src_lbl}][{k + 1}:v]overlay=enable='gte(t\\,{t:.3f})':shortest=1[b{k + 1}]")
    lines.append(f"[b{len(files)}]format=yuv420p[out]")
    cmd += ["-filter_complex", ";".join(lines), "-map", "[out]"]
    audio_in = None
    if a.over and has_audio(a.over):
        audio_in = 0
    elif card and not is_image(a.card) and has_audio(a.card) and not a.mute_card:
        audio_in = ci_idx                                     # the rounded card clip's own sound
    finish(a, cmd, a.output, audio_in, length,
           f"{W}x{H}, '{a.top}' / '{a.big}' / '{a.bottom}', big font {a.big_font} {a.color}, small {a.small_font}, every {a.every}s")


if __name__ == "__main__":
    main()
