#!/usr/bin/env python3
"""Text behind head: a big title tucked behind the speaker's head (the Mac's subject cut-out goes
on top of the words), with optional lines in front over the body. For covers and hook titles.

Cover / still (one frame):
  textbehind.py VIDEO_OR_IMAGE OUT.png --at 30.0 --behind "11 TITLES" --front "1 YEAR" "SPONSORED"
Hook clip (text stays behind the head on every frame, each line lands on its own time):
  textbehind.py VIDEO OUT.mp4 --from 0 --to 4.1 --behind "11 BRITISH TITLES" --front "1 YEAR SPONSORED" --on 0 1.19 --rough

Styles:
  caps       (default) bold caps (your font with --font, e.g. Bootzy); behind lines in pink, front lines in white.
  lowercase  bold white lowercase (e.g. Satoshi Bold), stacked above the head (nothing tucked unless you pass --behind).
No shadows, no outlines. Every output gets a .settings.txt next to it.
"""
import argparse, os, shutil, subprocess, sys, tempfile

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import find_font as _find_font, make_masks  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
COLOURS = {"pink": (233, 172, 163), "white": (255, 255, 255), "yellow": (255, 225, 74), "black": (17, 17, 17)}


def colour(c):
    """A name (pink, white, yellow, black) or a hex code like #E9ACA3."""
    if c in COLOURS:
        return COLOURS[c]
    c = c.lstrip("#")
    if len(c) != 6:
        raise SystemExit(f"Colour {c!r}: use pink, white, yellow, black or a hex code like #E9ACA3")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
FONTS = {  # your own font with --font; otherwise these if installed, then a bold system font
    "bootzy": ["~/Library/Fonts/BootzyTM.ttf"],
    "satoshi": ["~/Library/Fonts/Satoshi-Bold.otf", "C:/Windows/Fonts/Satoshi-Bold.otf"],
}
# Layout measured from a finished 9:16 cover (1080x1920), as fractions of width/height.
BOOTZY = dict(behind_width=0.943, behind_top=0.2625, front_width=0.885, front_top=0.6526, pitch=1.5)
LOWER = dict(width=0.764, top=0.108, pitch=0.93)


def find_font(kind, override=None):
    return _find_font(FONTS[kind], override)


def fit_font(path, text, width):
    lo, hi = 8, 2000
    while lo < hi:  # biggest size whose ink fits the width
        mid = (lo + hi + 1) // 2
        b = ImageFont.truetype(path, mid).getbbox(text)
        if b[2] - b[0] <= width:
            lo = mid
        else:
            hi = mid - 1
    return ImageFont.truetype(path, lo)


def cap_height(font, text):
    b = font.getbbox(text)
    return b[3] - b[1]


def layout(args, W, H):
    """Returns [(text, font, x, top, colour, behind)] with tops on the actual letter edges."""
    items = []
    if args.style in ("caps", "bootzy"):
        path = find_font("bootzy", args.font)
        behind = [t.upper() for t in args.behind]
        front = [t.upper() for t in args.front]
        if behind:
            fb = fit_font(path, max(behind, key=len), BOOTZY["behind_width"] * W * args.scale)
            capb = cap_height(fb, "H")
            y = BOOTZY["behind_top"] * H + args.shift * H
            for t in behind:
                items.append((t, fb, None, y, colour(args.behind_colour), True))
                y += capb * BOOTZY["pitch"]
        if front:
            ff = fit_font(path, max(front, key=lambda s: ImageFont.truetype(path, 100).getlength(s)),
                          BOOTZY["front_width"] * W * args.scale)
            capf = cap_height(ff, "H")
            y = (args.front_top if args.front_top is not None else BOOTZY["front_top"]) * H
            for t in front:
                items.append((t, ff, None, y, colour(args.front_colour), False))
                y += capf * BOOTZY["pitch"]
    else:
        path = find_font("satoshi", args.font)
        lines = [(t.lower(), True) for t in args.behind] + [(t.lower(), False) for t in args.front]
        ref = ImageFont.truetype(path, 100)
        f = fit_font(path, max((t for t, _ in lines), key=ref.getlength), LOWER["width"] * W * args.scale)
        pitch = f.size * LOWER["pitch"]
        y = LOWER["top"] * H + args.shift * H
        for t, b in lines:
            items.append((t, f, None, y, colour(args.front_colour), b))
            y += pitch
    return items


def draw(items, size, which):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for t, f, x, top, col, behind in items:
        if behind != which:
            continue
        b = f.getbbox(t)
        xx = (size[0] - (b[2] - b[0])) / 2 - b[0] if x is None else x
        capb = f.getbbox("H" if t.isupper() else "x")
        # align the top of the capitals (or x-height for lowercase ascenders) on the measured line
        d.text((xx, top - (capb[1] if t.isupper() else f.getbbox("h")[1])), t, font=f, fill=col + (255,))
    return layer


def compose(frame, mask, items, visible=None):
    """visible: list of booleans per item (for timed lines)."""
    its = [it for i, it in enumerate(items) if visible is None or visible[i]]
    out = frame.convert("RGBA")
    out.alpha_composite(draw(its, frame.size, True))
    subj = frame.convert("RGBA")
    subj.putalpha(mask.filter(ImageFilter.GaussianBlur(0.8)))
    out.alpha_composite(subj)
    out.alpha_composite(draw(its, frame.size, False))
    return out.convert("RGB")


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--at", type=float, help="still/cover: the time of the frame to use")
    ap.add_argument("--from", dest="start", type=float, help="clip: start time")
    ap.add_argument("--to", dest="end", type=float, help="clip: end time")
    ap.add_argument("--behind", nargs="*", default=[], help="lines tucked behind the head")
    ap.add_argument("--front", nargs="*", default=[], help="lines in front (over the body)")
    ap.add_argument("--on", nargs="*", type=float, help="clip: when each line lands, seconds from clip start (behind lines first, then front)")
    ap.add_argument("--style", choices=["caps", "bootzy", "lowercase"], default="caps", help="caps (bold caps, two colours) or lowercase (stacked)")
    ap.add_argument("--behind-colour", default="pink", help="pink, white, yellow, black or #hex")
    ap.add_argument("--front-colour", default="white", help="pink, white, yellow, black or #hex")
    ap.add_argument("--front-top", type=float, help="front lines' top as a fraction of height (default 0.65)")
    ap.add_argument("--scale", type=float, default=1.0, help="text size multiplier (keep inside the safe zone)")
    ap.add_argument("--shift", type=float, default=0.0, help="move the behind lines up (-) or down (+), fraction of height")
    ap.add_argument("--point", nargs=2, type=float, default=[0.5, 0.4], help="a point on the person, 0-1 from top-left")
    ap.add_argument("--font", help="font file override")
    ap.add_argument("--rough", action="store_true", help="clip: half size, quick")
    a = ap.parse_args()
    if not a.behind and not a.front:
        raise SystemExit("Give at least one line with --behind or --front.")
    if os.path.exists(a.output):
        raise SystemExit(f"{a.output} exists. Never overwrite: use the next version number.")
    tmp = tempfile.mkdtemp(prefix="textbehind_")
    try:
        frames, masks = os.path.join(tmp, "f"), os.path.join(tmp, "m")
        os.makedirs(frames)
        is_image = a.input.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".heic"))
        if a.at is not None or is_image:
            if is_image:
                Image.open(a.input).convert("RGB").save(os.path.join(frames, "0001.png"))
            else:
                run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.at), "-i", a.input, "-frames:v", "1",
                     os.path.join(frames, "0001.png")])
            make_masks(frames, masks, a.point)
            fr = Image.open(os.path.join(frames, "0001.png")).convert("RGB")
            m = Image.open(os.path.join(masks, "0001.png")).convert("L").resize(fr.size)
            items = layout(a, *fr.size)
            compose(fr, m, items).save(a.output)
        else:
            if a.start is None or a.end is None:
                raise SystemExit("For a clip give --from and --to (or --at for a still).")
            W = 540 if a.rough else 1080
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", a.input,
                 "-vf", f"scale={W}:-2,fps=30", os.path.join(frames, "%05d.png")])
            make_masks(frames, masks, a.point)
            names = sorted(os.listdir(frames))
            first = Image.open(os.path.join(frames, names[0]))
            items = layout(a, *first.size)
            on = a.on or [0.0] * len(items)
            if len(on) != len(items):
                raise SystemExit(f"--on needs {len(items)} times (one per line), got {len(on)}.")
            out = os.path.join(tmp, "o")
            os.makedirs(out)
            for i, n in enumerate(names):
                t = i / 30.0
                fr = Image.open(os.path.join(frames, n)).convert("RGB")
                m = Image.open(os.path.join(masks, os.path.splitext(n)[0] + ".png")).convert("L").resize(fr.size)
                compose(fr, m, items, [t >= x for x in on]).save(os.path.join(out, n))
                os.remove(os.path.join(frames, n))  # keep temp space small
            run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(out, "%05d.png"),
                 "-ss", str(a.start), "-to", str(a.end), "-i", a.input, "-map", "0:v", "-map", "1:a?",
                 "-c:v", "libx264", "-crf", "23" if a.rough else "17", "-pix_fmt", "yuv420p", "-threads", "2",
                 "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", a.output])
        with open(os.path.splitext(a.output)[0] + ".settings.txt", "w") as s:
            s.write(" ".join(sys.argv) + "\n")
        print("wrote", a.output)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
