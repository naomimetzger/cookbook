#!/usr/bin/env python3
"""Big words recipe (/bigwords): huge words fill the frame, up to 3 at a time, each appearing
the moment it's spoken. Equal margins all round and between lines.

Wide frame, 3 words ("hi I'm Naomi"):  HI ........ I'M   (top line, first word left, second right)
                                        NAOMI            (bottom line, filling the width)
Phone frame: one word per line, stacked, up to 3 lines.

  python3 bigwords.py INPUT OUTPUT [options]

  --same-size       every word the same size (no stretching)
  --top 0.08        all the words on one line along the top (keeps the face clear)
  --font helvetica   helvetica (condensed black, default), helvetica-bold, impact, din, avenir,
                     or a path to any .ttf/.otf font file. Works on Mac, Windows and Linux: each
                     style falls back to the closest font that computer has.
  --max-words 3      most words on screen at once (1-3)
  --margin 0.04      outside margin and gap between lines, as a share of the frame width
  --color white      text colour (name or hex)
  --case upper       upper (default) or as-is
  --hold 0.35        seconds the last word of a screen stays after it's spoken
  --words FILE       use a word-timing JSON instead of transcribing (fix spellings in it and rerun)
  --still 2.0        one PNG frame at 2.0s (fast preview)
  --rough            fast low-quality video (half size)
  --start 0 / --length 3   only make part of the video

Transcription uses faster-whisper (free, offline once its model is downloaded; ask the user
before the first download, then pass --allow-download).
The word timings are saved next to OUTPUT as <OUTPUT>.words.json so they can be corrected.
"""
import argparse, json, os, re, shlex, shutil, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

import platform, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Each style lists fonts to try, in order, on Mac, Windows and Linux (plus any font in ../fonts).
FONT_CHOICES = {
    "helvetica": [("/System/Library/Fonts/HelveticaNeue.ttc", 9), ("C:/Windows/Fonts/impact.ttf", 0),
                  ("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", 0)],
    "helvetica-bold": [("/System/Library/Fonts/HelveticaNeue.ttc", 4), ("C:/Windows/Fonts/ARIALNB.TTF", 0),
                       ("/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf", 0)],
    "impact": [("/System/Library/Fonts/Supplemental/Impact.ttf", 0), ("C:/Windows/Fonts/impact.ttf", 0),
               ("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf", 0)],
    "din": [("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", 0), ("C:/Windows/Fonts/bahnschrift.ttf", 0)],
    "avenir": [("/System/Library/Fonts/Avenir Next Condensed.ttc", 8), ("C:/Windows/Fonts/bahnschrift.ttf", 0)],
}
# last resort on any computer: whatever bold condensed font we can find
FALLBACKS = [("C:/Windows/Fonts/impact.ttf", 0), ("/System/Library/Fonts/Supplemental/Impact.ttf", 0),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", 0),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0)]


def find_font(name):
    """Return (path, index) for a style name or a font file, on any computer."""
    if os.path.exists(name):
        return name, 0
    bundled = os.path.join(HERE, "..", "fonts")
    if os.path.isdir(bundled):  # open-licence fonts shipped with the recipe, e.g. fonts/anton.ttf
        for f in sorted(os.listdir(bundled)):
            if f.lower().startswith(name.lower()) and f.lower().endswith((".ttf", ".otf")):
                return os.path.join(bundled, f), 0
    for path, idx in FONT_CHOICES.get(name, []) + FALLBACKS:
        if os.path.exists(path):
            return path, idx
    raise SystemExit(f"No bold font found for '{name}' on this {platform.system()} computer. "
                     "Pass --font with the path to any .ttf or .otf file.")


def even(n):
    n = int(round(n)); return n - (n % 2)


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
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                                "stream=index", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout.strip())


# ---------- words ----------

def transcribe(path, start, length, tmp, allow_download=False):
    """Word timings (seconds on the original clock) with the local faster-whisper model."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Speech-to-text isn't installed. Ask the user, then run: "
                         f"{sys.executable} -m pip install faster-whisper")
    wav = os.path.join(tmp, "a.wav")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(start)] + (["-t", str(length)] if length else [])
    subprocess.run(cmd + ["-i", path, "-ac", "1", "-ar", "16000", wav], check=True)
    model = None
    for name in ("base.en", "base", "tiny.en"):
        try:
            model = WhisperModel(name, device="cpu", compute_type="int8", local_files_only=not allow_download)
            break
        except Exception:
            continue
    if model is None:
        raise SystemExit("No speech model on this computer yet. Ask the user, then rerun with "
                         "--allow-download (downloads the 'base.en' model once, about 150 MB).")
    segs, _ = model.transcribe(wav, word_timestamps=True, vad_filter=True)
    words = []
    for s in segs:
        for w in s.words or []:
            words.append({"word": w.word.strip(), "start": round(w.start + start, 3), "end": round(w.end + start, 3)})
    return words


def clean(w, case):
    w = re.sub(r"[^\w'*&%$#@!?.,-]", "", w).strip(".,!?-")
    return w.upper() if case == "upper" else w


def group_words(words, max_words, pause=0.35):
    """Up to max_words per screen; a new screen after a pause or the end of a sentence."""
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        ends_sentence = re.search(r"[.!?]$", w["raw"]) is not None
        gap = (nxt["start"] - w["end"]) if nxt else 9
        if len(cur) >= max_words or ends_sentence or gap > pause or nxt is None:
            groups.append(cur); cur = []
    return groups


# ---------- layout ----------

def word_img(text, font, color):
    """Tight white image of one word at the font's size."""
    l, t, r, b = font.getbbox(text)
    img = Image.new("RGBA", (r - l + 2, b - t + 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((1 - l, 1 - t), text, font=font, fill=color)
    return img


def layout(group_texts, W, H, font, margin, color, tall, top=None, fixed_h=None, fixed_sx=1.0):
    """Return [(img, x, y)] per word: every word in a line shares one height; lines share one height.
    top = a share of the height: all the words sit on ONE line along the top, starting that far down (keeps the face clear).
    fixed_h = one letter height for every screen (--same-size): no stretching, so every word is the same size."""
    m = int(W * margin)
    n = len(group_texts)
    if top is not None:
        lines = [group_texts]; slots = 1
    elif tall:
        lines = [[w] for w in group_texts]
        slots = 3
    else:
        lines = [group_texts[:2], group_texts[2:]] if n == 3 else [group_texts]
        slots = 2
    box_h = (H - (slots + 1) * m) // slots
    if top is not None:
        box_h = int(H * 0.12)
    box_w = W - 2 * m
    imgs = [[word_img(w, font, color) for w in line] for line in lines]
    # one shared text height for the whole screen; squeeze or stretch widths within limits
    placed = []
    total_h = len(lines) * box_h + (len(lines) - 1) * m
    y0 = (H - total_h) // 2 if top is None else int(H * top)
    for li, line in enumerate(imgs):
        h = fixed_h or box_h
        nat = [im.width * h / im.height for im in line]          # natural widths at this height
        gaps = m * (len(line) - 1)
        sx = (box_w - gaps) / sum(nat)                          # width scale to fill the line
        sx = max(0.45, min(sx, 1.35))                           # keep letters believable
        if fixed_h:
            sx = fixed_sx                                        # same size and same letter width on every screen
        widths = [w * sx for w in nat]
        if sum(widths) + gaps > box_w:                          # still too wide: shrink the height too
            k = box_w / (sum(widths) + gaps)
            widths = [w * k for w in widths]; h = int(h * k)
        y = y0 + li * (box_h + m) + ((box_h - h) // 2 if top is None else 0)
        if fixed_h and len(line) > 1:                            # same size: words sit side by side, centred
            xs, x = [], (W - sum(widths) - gaps) / 2
            for w in widths:
                xs.append(x); x += w + m
        elif len(line) == 1:
            xs = [(W - widths[0]) / 2]
        else:                                                    # first word left, last right, equal gaps
            free = box_w - sum(widths)
            g = free / (len(line) - 1)
            xs, x = [], m
            for w in widths:
                xs.append(x); x += w + g
        for im, w, x in zip(line, widths, xs):
            placed.append((im.resize((max(1, int(w)), max(1, h)), Image.LANCZOS), int(x), y))
    return placed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input"); p.add_argument("output")
    p.add_argument("--font", default="helvetica"); p.add_argument("--max-words", type=int, default=3)
    p.add_argument("--margin", type=float, default=0.04); p.add_argument("--color", default="white")
    p.add_argument("--case", default="upper", choices=["upper", "as-is"]); p.add_argument("--hold", type=float, default=0.35)
    p.add_argument("--allow-download", action="store_true")
    p.add_argument("--words"); p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true")
    p.add_argument("--start", type=float, default=0); p.add_argument("--length", type=float)
    p.add_argument("--fit-to", nargs="*", default=[], help="extra words to size against, so separate parts of one video share one text size")
    p.add_argument("--same-size", action="store_true", help="every word the same size on every screen (sized so the longest word fits the width); no stretching")
    p.add_argument("--top", type=float, help="put each screen's words on one line along the top, this share of the height down (e.g. 0.08); keeps the face clear")
    a = p.parse_args()

    iw, ih = display_size(a.input)
    tall = ih > iw
    full_w = 1080 if tall else 1920
    ow = even(full_w / 2 if a.rough else min(full_w, iw))
    oh = even(ow * ih / iw)
    path, idx = find_font(a.font)
    font = ImageFont.truetype(path, 400, index=idx)
    color = a.color if not re.fullmatch(r"#?[0-9a-fA-F]{6}", a.color) else "#" + a.color.lstrip("#")

    tmp = tempfile.mkdtemp(prefix="bigwords_")
    try:
        span_start = a.start
        span_len = a.length or (max(0.1, duration(a.input) - a.start))
        if a.still is not None:
            span_start, span_len = max(0, a.still - 6), 8
        cache = a.output + ".words.json"
        if a.words:
            words = json.load(open(a.words))
        else:
            words = transcribe(a.input, span_start, span_len, tmp, a.allow_download)
            json.dump(words, open(cache, "w"), indent=1)
        words = [dict(w, raw=w["word"], text=clean(w["word"], a.case)) for w in words if clean(w["word"], a.case)]
        groups = group_words(words, max(1, min(3, a.max_words)))

        # timeline of screens: (start, end, png)
        blank = os.path.join(tmp, "blank.png")
        Image.new("RGBA", (ow, oh), (0, 0, 0, 0)).save(blank)
        states = []
        fixed_h, fixed_sx = None, 1.0
        if a.same_size:   # the largest letter height at which every screen's line still fits the width
            m = int(ow * a.margin); fits = []
            lo, hi = a.start, a.start + (a.length or 1e9)   # size to the words in the part being made
            sizing = [[w["text"] for w in g] for g in groups if lo <= g[0]["start"] < hi] or [[w["text"] for w in g] for g in groups]
            sizing += [[clean(t, a.case)] for t in a.fit_to if clean(t, a.case)]
            for g in sizing:
                ims = [word_img(t, font, color) for t in g]
                need = sum(im.width / im.height for im in ims)   # width per unit of height for the line
                fits.append((ow - 2 * m - m * (len(ims) - 1)) / need)
            slot_h = int(oh * 0.34) if a.top is not None else (oh - 2 * m if max(len(g) for g in groups) == 1 else (oh - 4 * m) // 3)
            # letters may be narrowed (the same for every word, never below 0.55) so the words can be taller
            fixed_h = int(min(min(fits) / 0.55, slot_h)); fixed_sx = min(1.0, min(fits) / fixed_h)
        for gi, g in enumerate(groups):
            placed = layout([w["text"] for w in g], ow, oh, font, a.margin, color, tall, a.top, fixed_h, fixed_sx)
            g_end = g[-1]["end"] + a.hold
            if gi + 1 < len(groups):
                g_end = min(g_end, groups[gi + 1][0]["start"])
            for k in range(len(g)):
                img = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
                for im, x, y in placed[:k + 1]:
                    img.alpha_composite(im, (x, y))
                f = os.path.join(tmp, f"s{gi:04d}_{k}.png"); img.save(f)
                t1 = g[k + 1]["start"] if k + 1 < len(g) else g_end
                states.append((g[k]["start"], max(t1, g[k]["start"] + 0.04), f))

        seek = a.still if a.still is not None else a.start
        if a.still is not None:
            cur = next((f for s, e, f in states if s <= seek < e), blank)
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(seek), "-i", a.input,
                   "-i", cur, "-filter_complex",
                   f"[0:v]scale={ow}:{oh},setsar=1[v];[v][1:v]overlay=format=auto,format=yuv420p[out]",
                   "-map", "[out]", "-frames:v", "1", a.output]
        else:
            # one overlay track: blank / word states with exact durations (concat demuxer)
            lst = os.path.join(tmp, "list.txt")
            t = seek
            with open(lst, "w") as L:
                for s, e, f in states:
                    if e <= seek:
                        continue
                    s = max(s, seek)
                    if s > t:
                        L.write(f"file '{blank}'\nduration {s - t:.3f}\n")
                    L.write(f"file '{f}'\nduration {e - s:.3f}\n"); t = e
                L.write(f"file '{blank}'\nduration {max(0.1, seek + span_len - t):.3f}\nfile '{blank}'\n")
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
            if a.length:
                cmd += ["-t", str(a.length)]
            cmd += ["-ss", str(seek), "-i", a.input, "-f", "concat", "-safe", "0", "-i", lst,
                    "-filter_complex", f"[0:v]scale={ow}:{oh},setsar=1[v];[1:v]format=rgba,setpts=PTS-STARTPTS[t];"
                    f"[v][t]overlay=format=auto:eof_action=pass,format=yuv420p[out]", "-map", "[out]"]
            if has_audio(a.input):
                cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
            crf, preset = ("28", "veryfast") if a.rough else ("18", "medium")
            cmd += ["-t", f"{span_len:.3f}", "-c:v", "libx264", "-crf", crf, "-preset", preset,
                    "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", a.output]
        subprocess.run(cmd, check=True)
        info = (f"{ow}x{oh}, font {a.font}, {len(words)} words in {len(groups)} screens, max {a.max_words} "
                f"per screen, margin {a.margin}")
        with open(a.output + ".settings.txt", "w") as f:
            f.write(info + "\nscreens: " + " | ".join(" ".join(w["text"] for w in g) for g in groups) + "\n")
            f.write(" ".join(shlex.quote(c) for c in cmd) + "\n")
        print(f"Done: {a.output} ({info})")
        print("Screens:", " | ".join(" ".join(w["text"] for w in g) for g in groups))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
