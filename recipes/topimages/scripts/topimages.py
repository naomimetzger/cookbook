#!/usr/bin/env python3
"""Images across the top, the speaker cut out in front of them, and a two-line title over the body.

  topimages.py VIDEO cover_v1.png --at 38.6 --image left.jpg --image right.png --title "THE ART OF" "BETTING ON YOURSELF"
  topimages.py VIDEO hook_v1.mp4 --from 37.71 --to 40.67 --image left.jpg --image right.png --title ... --rough

--crop X,Y,W,H frames the speaker closer (pixels of the upright video). Each --image can take its own
--fit (cover = fill the tile, top = whole picture at the top with its edge colour below) and --anchor X,Y.
"""
import argparse, os, sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video  # noqa: E402

BAND = 860 / 1920          # the images end at the speaker's eye line
TITLE = [(48, 0.08), (66, 0.04)]  # size and letter spacing of the small and big line, at 1080 wide
BASE = [1268 / 1920, 1350 / 1920]
BASE_WIDE = [0.85, 0.92]  # wide shots: the chin sits lower, so the title does too


def edge_colour(im):
    strip = [im.crop((0, 0, 3, im.height)), im.crop((im.width - 3, 0, im.width, im.height))]
    px = sorted((s.getpixel((x, y)) for s in strip for x in range(s.width) for y in range(s.height)), key=sum)
    return px[len(px) // 2]


def tile(im, w, h, fit, anchor):
    if fit == "top":
        out = Image.new("RGB", (w, h), edge_colour(im))
        s = min(w / im.width, h / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        out.paste(im, ((w - im.width) // 2, 0))
        return out
    s = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * s)), max(h, round(im.height * s))), Image.LANCZOS)
    x, y = round((im.width - w) * anchor[0]), round((im.height - h) * anchor[1])
    return im.crop((x, y, x + w, y + h))


def build_layers(a, W, H):
    band_h, n = round(a.band * H), len(a.image)
    band = Image.new("RGB", (W, band_h))
    for i, path in enumerate(a.image):
        x0, x1 = round(i * W / n), round((i + 1) * W / n)
        fit = a.fit[i] if i < len(a.fit) else "cover"
        try:
            anchor = tuple(float(v) for v in a.anchor[i].split(",")) if i < len(a.anchor) else (0.5, 0.5)
        except ValueError:
            raise SystemExit("--anchor is X,Y from 0 to 1, e.g. 0.85,0")
        band.paste(tile(video.load_image(path), x1 - x0, band_h, fit, anchor), (x0, 0))
    title = Image.new("RGBA", (W, H))
    if a.title:
        path, s = video.find_font("mono", a.font), min(W / 1080, H / 1920) * a.text_scale
        bases = BASE_WIDE if W > H else BASE
        rows = list(zip(a.title, TITLE, bases)) if len(a.title) == 2 else [(a.title[0], TITLE[1], bases[1])]
        for text, (size, track), base in rows:
            f = video.fit_text(text, path, size * s, W * 840 / 1080, track, a.weight)
            video.draw_centred(title, text, f, W / 2, round(base * H), video.colour(a.colour) + (255,), track)
    return band, title


def compose(frame, mask, band, title):
    out = frame.copy()
    out.paste(band, (0, 0))
    out.paste(frame, (0, 0), mask)
    out.paste(title, (0, 0), title)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--at", type=float, help="still or cover: which moment")
    ap.add_argument("--from", dest="start", type=float)
    ap.add_argument("--to", dest="end", type=float)
    ap.add_argument("--image", action="append", required=True, help="1 to 3 times, left to right")
    ap.add_argument("--fit", action="append", default=[], choices=["cover", "top"], help="one per image, same order")
    ap.add_argument("--anchor", action="append", default=[], help="X,Y 0-1 per image: which part to keep")
    ap.add_argument("--band", type=float, default=BAND, help="where the images end, fraction of height")
    ap.add_argument("--title", nargs="+", default=[], help="one line, or a small line and a big line")
    ap.add_argument("--font")
    ap.add_argument("--weight", default="Regular")
    ap.add_argument("--colour", default="white")
    ap.add_argument("--text-scale", type=float, default=1.0)
    ap.add_argument("--crop", help="X,Y,W,H of the upright input")
    ap.add_argument("--point", nargs=2, type=float, default=[0.5, 0.55], help="a point on the person, 0-1")
    ap.add_argument("--rough", action="store_true")
    ap.add_argument("--allow-download", action="store_true", help="Windows/Linux: allow the one-time cut-out model download (ask first)")
    a = ap.parse_args()
    if len(a.image) > 3 or len(a.title) > 2:
        raise SystemExit("Up to 3 images and 2 title lines.")
    if not 0.1 <= a.band <= 0.9:
        raise SystemExit("--band is a fraction of the height, e.g. 0.448")
    still = a.at is not None or video.is_image(a.input)
    out = video.new_output(a.output, still)
    with video.workspace("topimages") as tmp:
        if still:
            fr = video.load_still(a.input, a.at, a.crop, a.rough)
            band, title = build_layers(a, *fr.size)
            m = video.person_masks([fr], tmp, a.point, a.allow_download)[0]
            compose(fr, video.read_mask(m, fr.size, 1.2 * fr.width / 1080), band, title).save(out)
        else:
            info = video.probe(a.input)
            crop = video.parse_crop(a.crop, info.w, info.h)
            size = video.work_size(info.w, info.h, crop, a.rough)
            start, n = video.clip_range(info, a.start, a.end)
            band, title = build_layers(a, *size)
            masks = video.person_masks(video.read_frames(info, size, start, n, crop=crop), tmp, a.point, a.allow_download)
            with video.Writer(out, size, info.fps, n, info, start, a.rough) as w:
                for fr, m in zip(video.read_frames(info, size, start, n, crop=crop), masks):
                    w.add(compose(fr, video.read_mask(m, size, 1.2 * size[0] / 1080), band, title))
    video.write_settings(out)


if __name__ == "__main__":
    main()
