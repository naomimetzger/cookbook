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
The behind lines are placed from the cut-out: their bottom sits a little below the top of the head, so
hair overlaps the letters and the face stays clear. Text stays inside the Instagram safe zone.
Phone photos (HEIC, sideways), iPhone HDR video and any frame rate are handled (media.py).
No shadows, no outlines. Every output gets a .settings.txt next to it.
"""
import argparse, os, shutil, subprocess, sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import find_font as _find_font, make_masks  # noqa: E402
from media import (COLOR_TAGS, RGB_TO_YUV, AUDIO_MAP, frame_rate, is_image, load_image,  # noqa: E402
                   prepare_video, safe_output, temp_dir)

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
# Instagram safe zone at 1080x1920: below the top 250 px, above the bottom 380 px, 120 px clear each side.
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 250 / 1920, 380 / 1920, 120 / 1080
COVER_MAX_WIDTH = 0.96   # covers can use the full width, with a hair of margin
TUCK = 0.35              # how far the letters' bottom goes below the top of the head, in cap heights...
TUCK_MAX_HEAD = 0.25     # ...but never more than this much of the head's width (keeps it above the eyes)


def find_font(kind, override=None):
    return _find_font(FONTS[kind], override)


def widest(path, lines):
    """The line that's widest when drawn (not the one with the most letters)."""
    ref = ImageFont.truetype(path, 100)
    return max(lines, key=lambda t: ref.getbbox(t)[2] - ref.getbbox(t)[0])


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


def head_top(mask):
    """(y of the top of the head, head width) from a cut-out mask, or None if there's no person."""
    m = mask.point(lambda v: 255 if v > 127 else 0)
    W, H = m.size
    if m.histogram()[255] < 0.002 * W * H:
        return None
    small = m.resize((max(1, W // 4), max(1, H // 4)), Image.BOX).point(lambda v: 255 if v > 127 else 0)
    w, h = small.size
    top = None
    for y in range(h):  # first row with more than a few stray hairs in it
        if small.crop((0, y, w, y + 1)).histogram()[255] >= max(2, 0.01 * w):
            top = y
            break
    if top is None:
        return None
    width = 0
    for y in range(top, min(h, top + int(0.06 * h) + 1)):
        b = small.crop((0, y, w, y + 1)).getbbox()
        if b:
            width = max(width, b[2] - b[0])
    return top * 4, width * 4


def max_width(frac, W, args):
    """Fit the text to the frame: a clip keeps inside the safe zone, a cover can use the full width."""
    limit = (1 - 2 * SAFE_SIDE) if args.clip else COVER_MAX_WIDTH
    return min(frac * args.scale, limit) * W


def layout(args, W, H, head):
    """Returns [(text, font, x, top, colour, behind)] with tops on the actual letter edges.
    head: (top y, width) of the person's head from the cut-out."""
    items = []
    # the top/bottom safe zone is for tall (9:16) frames; a wide or square frame sits in the middle on Instagram
    tall = H >= 1.6 * W
    safe_top, safe_bottom = (SAFE_TOP * H, (1 - SAFE_BOTTOM) * H) if tall else (0.02 * H, 0.98 * H)
    if args.style in ("caps", "bootzy"):
        path = find_font("bootzy", args.font)
        behind = [t.upper() for t in args.behind]
        front = [t.upper() for t in args.front]
        bottom = None
        if behind:
            fb = fit_font(path, widest(path, behind), max_width(BOOTZY["behind_width"], W, args))
            capb = cap_height(fb, "H")
            n, pitch = len(behind), BOOTZY["pitch"]
            # the last line's bottom sits a little below the top of the head, so the hair overlaps it
            bottom = head[0] + min(TUCK * capb, TUCK_MAX_HEAD * head[1]) + args.shift * H
            if bottom > safe_bottom:
                print("Note: the head is low in the frame, so the text can't tuck behind it inside the safe zone.")
                bottom = safe_bottom
            room = bottom - safe_top
            if (n - 1) * capb * pitch + capb > room:  # not enough room above the head: smaller text
                cap_fit = room / ((n - 1) * pitch + 1)
                size = max(8, int(fb.size * cap_fit / capb))
                while size > 8 and cap_height(ImageFont.truetype(path, size), "H") > cap_fit:
                    size -= 1
                fb = ImageFont.truetype(path, size)
                capb = cap_height(fb, "H")
                print("Note: the head is high in the frame, so the behind text is smaller to stay in the safe zone.")
            y = bottom - capb - (n - 1) * capb * pitch
            for t in behind:
                items.append((t, fb, None, y, colour(args.behind_colour), True))
                y += capb * pitch
        if front:
            ff = fit_font(path, widest(path, front), max_width(BOOTZY["front_width"], W, args))
            capf = cap_height(ff, "H")
            y = (args.front_top if args.front_top is not None else BOOTZY["front_top"]) * H
            if bottom is not None and y < bottom + 0.3 * capf:
                print("Note: the front lines touch the behind lines (the head is low in the frame). "
                      "Try --front-top, or leave out --front.")
            for t in front:
                items.append((t, ff, None, y, colour(args.front_colour), False))
                y += capf * BOOTZY["pitch"]
            if y - capf * (BOOTZY["pitch"] - 1) > (safe_bottom if args.clip else H):
                print("Note: the front lines run past the bottom of the safe zone. Try --front-top or --scale.")
    else:
        path = find_font("satoshi", args.font)
        lines = [(t.lower(), True) for t in args.behind] + [(t.lower(), False) for t in args.front]
        f = fit_font(path, widest(path, [t for t, _ in lines]), max_width(LOWER["width"], W, args))
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


def no_person(where):
    raise SystemExit(f"No person found in {where}, so there's no head to tuck the text behind. "
                     "Pick a frame where the person is clearly in shot, or use --point X Y to pick them.")


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
    ap.add_argument("--allow-download", action="store_true",
                    help="let rembg download its one-time cut-out model (about 176 MB). Ask first.")
    a = ap.parse_args()
    if not a.behind and not a.front:
        raise SystemExit("Give at least one line with --behind or --front.")
    safe_output(a.output)
    if not os.path.exists(a.input):
        raise SystemExit(f"File not found: {a.input}")
    still = a.at is not None or is_image(a.input)
    a.clip = not still
    if a.clip and (a.start is None or a.end is None):
        raise SystemExit("For a clip give --from and --to (or --at for a still).")
    tmp = temp_dir("textbehind_")
    try:
        frames, masks = os.path.join(tmp, "f"), os.path.join(tmp, "m")
        os.makedirs(frames)
        src = a.input if is_image(a.input) else prepare_video(a.input, tmp)
        if still:
            if is_image(a.input):
                load_image(a.input).save(os.path.join(frames, "0001.png"))
            else:
                run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.at), "-i", src, "-map", "0:v:0", "-frames:v", "1",
                     os.path.join(frames, "0001.png")])
            make_masks(frames, masks, a.point, a.allow_download)
            fr = Image.open(os.path.join(frames, "0001.png")).convert("RGB")
            m = Image.open(os.path.join(masks, "0001.png")).convert("L").resize(fr.size)
            head = head_top(m)
            if head is None:
                no_person("this frame")
            items = layout(a, *fr.size, head)
            compose(fr, m, items).save(a.output)
        else:
            fps = frame_rate(src)
            W = 540 if a.rough else 1080
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-to", str(a.end), "-i", src, "-map", "0:v:0",
                 "-vf", f"scale={W}:-2,fps={fps}", os.path.join(frames, "%05d.png")])
            make_masks(frames, masks, a.point, a.allow_download)
            names = sorted(os.listdir(frames))
            if not names:
                raise SystemExit(f"No frames between {a.start} and {a.end} s. Check the times.")
            first = Image.open(os.path.join(frames, names[0]))
            mask_of = lambda n: Image.open(os.path.join(masks, os.path.splitext(n)[0] + ".png")).convert("L")
            # the head's usual position across the clip (every 6th frame), so the text sits still
            heads = [h for h in (head_top(mask_of(n).resize(first.size)) for n in names[::6]) if h]
            if not heads:
                no_person("this clip")
            heads.sort()
            items = layout(a, *first.size, heads[len(heads) // 2])
            on = a.on or [0.0] * len(items)
            if len(on) != len(items):
                raise SystemExit(f"--on needs {len(items)} times (one per line), got {len(on)}.")
            out = os.path.join(tmp, "o")
            os.makedirs(out)
            empty = 0
            for i, n in enumerate(names):
                t = i / fps
                fr = Image.open(os.path.join(frames, n)).convert("RGB")
                m = mask_of(n).resize(fr.size)
                empty += m.getbbox() is None
                compose(fr, m, items, [t >= x for x in on]).save(os.path.join(out, n))
                os.remove(os.path.join(frames, n))  # keep temp space small
            if empty:
                print(f"Note: no person found on {empty} of {len(names)} frames; the text shows over everything there.")
            run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(out, "%05d.png"),
                 "-ss", str(a.start), "-to", str(a.end), "-i", src, "-map", "0:v:0", "-map", f"1:{AUDIO_MAP}",
                 "-vf", RGB_TO_YUV, "-c:v", "libx264", "-crf", "23" if a.rough else "17", *COLOR_TAGS,
                 "-threads", "2", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", a.output])
        with open(os.path.splitext(a.output)[0] + ".settings.txt", "w", encoding="utf-8") as s:
            s.write(" ".join(sys.argv) + "\n")
        print("wrote", a.output)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
