#!/usr/bin/env python3
"""Photo behind head: proof photos pop in behind the speaker's head on the words that need them
(e.g. title photos on "and then i won, won again"), one per beat, each replacing the
last with a hard cut. The Mac cuts the person out so the photo sits behind the head. No shadow.

  photobehind.py VIDEO OUT.mp4 --from 7.6 --to 13.6 --photo champs1.png@0.40 --photo champs2.png@1.20 \
      --photo champs3.png@2.00 --end 3.0 --rough

Photo times are seconds from --from. The last photo stays until --end (seconds from --from) or the
clip end. Writes OUT.mp4 (just that piece, with its sound), OUT.cues.json (camera hits for /sfxhits)
and OUT.settings.txt.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutout import make_masks  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Measured from finished reels (9:16): card height 27% of the frame, top at 20%,
# centred over the head, at most 50% of the width, slightly rounded corners.
CARD_H, CARD_TOP, CARD_MAXW, RADIUS = 0.27, 0.20, 0.50, 0.022


def head_centre_x(mask):
    """x of the top of the person (their head), from the cut-out mask."""
    m = mask.point(lambda v: 255 if v > 127 else 0)
    bbox = m.getbbox()
    if not bbox:
        return mask.width / 2
    top = bbox[1]
    band = m.crop((0, top, m.width, min(m.height, top + int(0.12 * m.height))))
    xs = [x for x in range(band.width) if band.crop((x, 0, x + 1, band.height)).getbbox()]
    return (xs[0] + xs[-1]) / 2 if xs else mask.width / 2


def card(photo_path, W, H, scale):
    ph = Image.open(photo_path).convert("RGB")
    h = int(CARD_H * H * scale)
    w = int(ph.width * h / ph.height)
    if w > CARD_MAXW * W * scale:  # wide photo: limit the width, crop the sides
        w = int(CARD_MAXW * W * scale)
        sw = int(ph.height * w / h)
        ph = ph.crop(((ph.width - sw) // 2, 0, (ph.width - sw) // 2 + sw, ph.height))
    ph = ph.resize((w, h), Image.LANCZOS)
    r = max(2, int(RADIUS * W))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    ph.putalpha(m)
    return ph


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--from", dest="start", type=float, required=True)
    ap.add_argument("--to", dest="end_clip", type=float, required=True)
    ap.add_argument("--photo", action="append", required=True, help="PATH@SECONDS (from --from), in order")
    ap.add_argument("--end", type=float, help="when the last photo goes, seconds from --from")
    ap.add_argument("--scale", type=float, default=1.0, help="photo size multiplier")
    ap.add_argument("--top", type=float, default=CARD_TOP, help="card top as a fraction of height")
    ap.add_argument("--point", nargs=2, type=float, default=[0.5, 0.4], help="a point on the person, 0-1")
    ap.add_argument("--rough", action="store_true", help="half size, quick")
    a = ap.parse_args()
    if os.path.exists(a.output):
        raise SystemExit(f"{a.output} exists. Never overwrite: use the next version number.")
    photos = []
    for p in a.photo:
        path, _, t = p.rpartition("@")
        if not os.path.exists(path):
            raise SystemExit(f"Photo not found: {path}")
        photos.append((path, float(t)))
    photos.sort(key=lambda x: x[1])
    dur = a.end_clip - a.start
    end = a.end if a.end is not None else dur
    tmp = tempfile.mkdtemp(prefix="photobehind_")
    try:
        frames, masks, out = (os.path.join(tmp, d) for d in "fmo")
        for d in (frames, masks, out):
            os.makedirs(d)
        W = 540 if a.rough else 1080
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.start), "-to", str(a.end_clip), "-i", a.input,
                        "-vf", f"scale={W}:-2,fps=30", os.path.join(frames, "%05d.png")], check=True)
        names = sorted(os.listdir(frames))
        first = Image.open(os.path.join(frames, names[0]))
        W, H = first.size
        cards = [card(p, W, H, a.scale) for p, _ in photos]
        # only lift the frames that show a photo
        lit = os.path.join(tmp, "lit")
        os.makedirs(lit)
        for i, n in enumerate(names):
            t = i / 30.0
            if photos[0][1] <= t < end:
                os.link(os.path.join(frames, n), os.path.join(lit, n))
        make_masks(lit, masks, a.point)
        cx = None
        for i, n in enumerate(names):
            t = i / 30.0
            fr = Image.open(os.path.join(frames, n)).convert("RGB")
            idx = max([k for k, (_, pt) in enumerate(photos) if pt <= t], default=None)
            mp = os.path.join(masks, os.path.splitext(n)[0] + ".png")
            if idx is not None and t < end and os.path.exists(mp):
                m = Image.open(mp).convert("L").resize(fr.size)
                if cx is None:  # lock the position on the first photo frame, so the card doesn't wander
                    cx = head_centre_x(m)
                c = cards[idx]
                x = int(min(max(cx - c.width / 2, 0.06 * W), W - 0.06 * W - c.width))
                o = fr.convert("RGBA")
                o.alpha_composite(c, (x, int(a.top * H)))
                subj = fr.convert("RGBA")
                subj.putalpha(m.filter(ImageFilter.GaussianBlur(0.8)))
                o.alpha_composite(subj)
                fr = o.convert("RGB")
            fr.save(os.path.join(out, n))
            os.remove(os.path.join(frames, n))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(out, "%05d.png"),
                        "-ss", str(a.start), "-to", str(a.end_clip), "-i", a.input, "-map", "0:v", "-map", "1:a?",
                        "-c:v", "libx264", "-crf", "23" if a.rough else "17", "-pix_fmt", "yuv420p", "-threads", "2",
                        "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", a.output], check=True)
        base = os.path.splitext(a.output)[0]
        with open(base + ".cues.json", "w") as f:
            json.dump([{"type": "camera", "t": round(t, 3)} for _, t in photos], f, indent=1)
        with open(base + ".settings.txt", "w") as f:
            f.write(" ".join(sys.argv) + "\n")
        print("wrote", a.output, "and", base + ".cues.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
