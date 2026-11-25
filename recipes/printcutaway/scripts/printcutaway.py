#!/usr/bin/env python3
"""Paper collage cutaway made from the speaker's own footage: a halftone cut-out moving at 12 poses a second
(so lips still follow the words) on grid paper, a pen ring drawing round the head, and big words on the beat.

  printcutaway.py VIDEO bet_v1.mp4 --from 40.67 --to 42.085 --word "BET ON@0.76" --word "YOURSELF@0.95" --rough
  printcutaway.py VIDEO bet_v1.png --from 40.67 --to 42.085 --word ... --still 1.2      (one frame of that scene)

Word times are seconds from --from. The last word gets the key colour (red).
"""
import argparse, math, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video  # noqa: E402

POSES = 12
PAPER, GRID, SHADOW = (239, 238, 229), (219, 221, 216), (150, 148, 140)
PERSON_H = 1150 / 1920     # the print fills this much of the page, standing on the bottom edge
PUSH = 0.035
WORD_SIZES = {1: [200], 2: [140, 200], 3: [110, 110, 170]}
WORD_BASE = {1: [560], 2: [445, 615], 3: [360, 480, 635]}


def halftone(gray, cell):
    g = np.asarray(gray.filter(ImageFilter.GaussianBlur(cell / 3)), dtype=np.float32) / 255
    dark = np.clip((1 - g - 0.08) * 1.25, 0, 1)
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]].astype(np.float32)
    u, v = (xx + yy) / math.sqrt(2), (xx - yy) / math.sqrt(2)
    cu, cv = (u % cell) - cell / 2, (v % cell) - cell / 2
    ink = np.sqrt(cu * cu + cv * cv) < cell * 0.72 * np.sqrt(dark)
    return Image.fromarray(np.where(ink, 22, 238).astype(np.uint8))


def ring_points(box, frac):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    for k in range(0, int(380 * frac) + 1, 4):
        a, s = math.radians(k - 100), 1 + 0.025 * math.sin(k / 37) + 0.012 * k / 360
        pts.append((cx + rx * s * math.cos(a), cy + ry * s * math.sin(a)))
    return pts


class Scene:
    def __init__(self, a, frames, masks, size, words):
        self.W, self.H = W, H = size
        self.s = s = min(W / 1080, H / 1920)
        boxes = [m.point(lambda p: 255 if p > 128 else 0).getbbox() for m in masks]
        # one box round the person across EVERY pose, so the top of the head is never cut off
        self.box = box = (min(b[0] for b in boxes), max(0, min(b[1] for b in boxes) - round(24 * s)),
                          max(b[2] for b in boxes), max(b[3] for b in boxes))
        scale = min(PERSON_H * H / (box[3] - box[1]), W / (box[2] - box[0]))
        self.pw, self.ph = round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale)
        self.px, self.py = (W - self.pw) // 2, H - self.ph
        g0 = np.asarray(frames[0].convert("L").crop(box), dtype=np.float32)
        inside = np.asarray(masks[0].crop(box)) > 128
        lo, hi = np.percentile(g0[inside], 1), np.percentile(g0[inside], 99.5)  # one set of levels, so no flicker
        self.prints = []
        heads = []
        for fr, m in zip(frames, masks):
            g = np.asarray(fr.convert("L").crop(box), dtype=np.float32)
            g = np.clip((g - lo) / max(hi - lo, 1), 0, 1) ** 0.55 * 255
            p = halftone(Image.fromarray(g.astype(np.uint8)), max(3.0, 8 * s)).convert("RGB")
            m = m.crop(box).resize((self.pw, self.ph), Image.LANCZOS)
            self.prints.append((p.resize((self.pw, self.ph), Image.LANCZOS), m))
            solid = np.asarray(m) > 128
            rows = np.where(solid.any(1))[0]
            cols = np.where(solid[rows[0]:rows[0] + max(2, round(0.12 * self.ph))].any(0))[0]
            heads.append((cols[0] + cols[-1]) / 2)
        cx = self.px + float(np.median(heads))  # the ring is drawn on the page, so it stays still
        wide = W > H  # in a wide shot the head is far more of the cut-out
        half = (0.26 if wide else 0.15) * self.ph * a.ring_size
        low = self.py + (0.70 if wide else 0.36) * self.ph
        self.ring = None if a.no_ring else (cx - half, self.py - 40 * s, cx + half, low)
        self.ring_colour = video.colour(a.ring_colour)

        self.paper = Image.new("RGB", size, PAPER)
        d, step = ImageDraw.Draw(self.paper), max(8, round(66 * s))
        for x in range(0, W, step):
            d.line([(x, 0), (x, H)], fill=GRID, width=1)
        for y in range(0, H, step):
            d.line([(0, y), (W, y)], fill=GRID, width=1)

        self.words = []
        if words:
            path, n = video.find_font("display", a.font), len(words)
            for i, (text, t) in enumerate(words):
                f = video.fit_text(text, path, WORD_SIZES[n][i] * s, W * 840 / 1080)
                layer = Image.new("RGBA", size)
                col = video.colour(a.key_colour if i == n - 1 else a.word_colour)
                video.draw_centred(layer, text, f, W / 2, round(WORD_BASE[n][i] * H / 1920), col + (255,))
                self.words.append((t, layer))

    def render(self, t, dur):
        W, H, s = self.W, self.H, self.s
        k = min(int(t * POSES + 1e-6), len(self.prints) - 1)
        p, m = self.prints[k]
        sh = Image.new("L", (W, H), 0)
        sh.paste(m, (self.px + round(10 * s), self.py + round(12 * s)))
        sh = sh.filter(ImageFilter.GaussianBlur(14 * s))
        c = Image.composite(Image.new("RGB", (W, H), SHADOW), self.paper, sh.point(lambda v: int(v * 0.45)))
        c.paste(p, (self.px, self.py), m)
        if self.ring:
            pts = ring_points(self.ring, min(1.0, (k + 1) / 4))  # draws on over 4 poses
            ImageDraw.Draw(c).line(pts, fill=self.ring_colour, width=max(2, round(7 * s)), joint="curve")
        for on, layer in self.words:
            if t + 1e-6 >= on:
                c.paste(layer, (0, 0), layer)
        z = 1 + PUSH * t / dur
        cw, ch = W / z, H / z
        x, y = (W - cw) / 2, (H - ch) * 0.45
        return c.resize((W, H), Image.LANCZOS, box=(x, y, x + cw, y + ch))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--from", dest="start", type=float)
    ap.add_argument("--to", dest="end", type=float)
    ap.add_argument("--still", type=float, help="just one frame, this many seconds into the scene")
    ap.add_argument("--word", action="append", default=[], help="TEXT@SECONDS, up to 3 lines")
    ap.add_argument("--font")
    ap.add_argument("--word-colour", default="ink")
    ap.add_argument("--key-colour", default="red")
    ap.add_argument("--ring-colour", default="blue")
    ap.add_argument("--ring-size", type=float, default=1.0)
    ap.add_argument("--no-ring", action="store_true")
    ap.add_argument("--crop")
    ap.add_argument("--point", nargs=2, type=float, default=[0.5, 0.55])
    ap.add_argument("--rough", action="store_true")
    ap.add_argument("--allow-download", action="store_true", help="Windows/Linux: allow the one-time cut-out model download (ask first)")
    a = ap.parse_args()
    if len(a.word) > 3:
        raise SystemExit("Up to 3 lines of words, or it stops reading in one glance.")
    words = [video.split_time(w) for w in a.word]
    photo = video.is_image(a.input)
    still = photo or a.still is not None
    out = video.new_output(a.output, still)
    with video.workspace("printcutaway") as tmp:
        if photo:
            fr = video.load_still(a.input, crop=a.crop, rough=a.rough)
            mask = video.read_mask(video.person_masks([fr], tmp, a.point, a.allow_download)[0], fr.size)
            scene = Scene(a, [fr], [mask], fr.size, [(t, 0.0) for t, _ in words])
            scene.prints *= 4  # a photo has one pose: show the ring finished
            scene.render(3 / POSES, 1.0).save(out)
        else:
            if a.start is None or a.end is None:
                raise SystemExit("Give the line as --from and --to (add --still SECONDS for one frame).")
            info = video.probe(a.input)
            crop = video.parse_crop(a.crop, info.w, info.h)
            full = video.work_size(info.w, info.h, crop)  # the dots need full size, rough only shrinks the result
            size = video.work_size(info.w, info.h, crop, a.rough)
            start, n = video.clip_range(info, a.start, a.end)
            fps, dur = float(info.fps), n / float(info.fps)
            late = [t for _, t in words if not 0 <= t < dur]
            if late:
                raise SystemExit(f"Word times are seconds from --from, inside 0-{dur:.2f}.")
            count = math.ceil(dur * POSES - 1e-6)
            need = {min(n - 1, math.ceil(k * fps / POSES - 1e-6)): k for k in range(count)}
            frames = [fr for i, fr in enumerate(video.read_frames(info, full, start, n, crop=crop)) if i in need]
            masks = [video.read_mask(p, full) for p in video.person_masks(frames, tmp, a.point, a.allow_download)]
            scene = Scene(a, frames, masks, full, words)
            if still:
                im = scene.render(min(max(a.still, 0), dur - 1 / fps), dur)
                im.resize(size, Image.LANCZOS).save(out)
            else:
                with video.Writer(out, size, info.fps, n, info, start, a.rough) as w:
                    for i in range(n):
                        w.add(scene.render(i / fps, dur).resize(size, Image.LANCZOS))
    video.write_settings(out)


if __name__ == "__main__":
    main()
