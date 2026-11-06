#!/usr/bin/env python3
"""Middle captions recipe (/midcaptions): one or two small bold white capitals in the middle of the
frame at chest height, with a soft dark shadow, changing with every word or two as they're spoken, like
a documentary interview reel. No box, no animation. Portrait-first, works on wide video too.

  python3 midcaptions.py VIDEO OUTPUT [options]

  --words-per 2   most words on screen at once (1-4)
  --pattern "4 1 1 4 2 3 4 2 2 3"  word counts per screen in turn (max 4), for rhythm
  --y 0.55        where the words sit (0-1 down; about chest height on a seated speaker)
  --size 0.021    capital height as a share of the frame height
  --font NAME     a font by name or file; default Satoshi (free from fontshare.com), else Inter (bundled)
  --weight ExtraBold (Bold, SemiBold)   --color white   --shadow 0.45 (0 = none)   --case upper|as-is
  --linger 0.2    a line stays this long after its last word, then clears (never into the next sentence)
  --cuts T T …    shot-change times: a line never carries across one
  --frame auto    auto, 9:16 or 16:9 (a wide video made 9:16 is cropped round --face X)   --face 0.5
  --words fixed.json   --allow-download   --start --length --still SECONDS --rough

Works on Mac, Windows and Linux. Needs ffmpeg, Pillow and faster-whisper. Inter is bundled.
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

# ---------- speech timing (free, offline) ----------
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
    # Word times from one pass can be off by half a second on short words after a pause. Listen three
    # slightly different ways (plain, with a short silence in front, with voice detection) and, for each
    # word, take the middle of the three times. One-off mistakes get outvoted.
    padded = os.path.join(tmp, "a_pad.wav"); lead = 0.37
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(lead), "-i", "anullsrc=r=16000:cl=mono",
                    "-i", wav, "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", padded], check=True)
    def run(f, vad, shift):
        segs, _ = model.transcribe(f, word_timestamps=True, vad_filter=vad)
        return [{"word": w.word.strip(), "start": w.start - shift, "end": w.end - shift} for s in segs for w in (s.words or [])]
    passes = [run(wav, False, 0), run(padded, False, lead), run(wav, True, 0)]
    words = passes[0]
    key = lambda ws: [re.sub(r"[^\w']", "", w["word"].lower()) for w in ws]
    same = [p for p in passes[1:] if key(p) == key(words)]
    for i, w in enumerate(words):
        starts = sorted([w["start"]] + [p[i]["start"] for p in same])
        w["start"] = starts[len(starts) // 2]
    for w in words:
        w["start"] = round(max(0.0, w["start"]) + start, 3); w["end"] = round(max(w["end"], 0.0) + start, 3)
    for a, b in zip(words, words[1:]):
        if b["start"] < a["start"]:
            b["start"] = a["start"]
    return snap_to_voice(words, wav, start)


def snap_to_voice(words, wav, offset):
    """If a word is placed in pure silence, move it forward to where the voice actually starts (up to 0.5s)."""
    try:
        import numpy as np, wave
        with wave.open(wav) as f:
            sr = f.getframerate(); y = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float32) / 32768
    except Exception:
        return words
    hop = sr // 100
    env = np.sqrt(np.convolve(y ** 2, np.ones(hop * 2) / (hop * 2), "same")[::hop])
    if not len(env):
        return words
    thr = max(1e-4, np.percentile(env, 95) * 0.06)
    for i, w in enumerate(words):
        k = int((w["start"] - offset) * 100)
        if 0 <= k < len(env) and env[max(0, k - 2):k + 3].max() < thr:
            on = next((j for j in range(k, min(len(env), k + 50)) if env[j] >= thr), None)
            if on is not None:
                w["start"] = round(offset + on / 100, 3)
                w["end"] = round(max(w["end"], w["start"] + 0.08), 3)
                for q in words[i + 1:]:
                    if q["start"] < w["start"]:
                        q["start"] = w["start"]
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


# ---------- rise captions ----------


def find_word(words, target, after=0.0):
    """Start/end of the first spoken word matching target (case and punctuation ignored) after a time."""
    t = re.sub(r"[^\w']", "", target).lower()
    for w in words:
        if w["start"] >= after - 0.01 and re.sub(r"[^\w']", "", w["word"]).lower() == t:
            return w["start"], w["end"]
    return None


def get_words(a, video, start, length, tmp):
    """Use a saved words file if given, else transcribe and save one next to the output for fixing."""
    import json
    if getattr(a, "words", None):
        return json.load(open(a.words))
    words = transcribe(video, start, length, tmp, getattr(a, "allow_download", False))
    json.dump(words, open(os.path.splitext(a.output)[0] + ".words.json", "w"), indent=1)
    return words


# ---------- phrase captions: static, measured, placed in one fixed spot ----------
def inter_font(size, weight):
    from PIL import ImageFont
    p = os.path.join(HERE, "..", "fonts", "InterVariable.ttf")
    if os.path.exists(p):
        f = ImageFont.truetype(p, size)
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
        return f
    fp, fi = find_font("bold"); return ImageFont.truetype(fp, size, index=fi)


def make_phrases(words, max_chars, max_lines, pause=0.45):
    """Group spoken words into phrases of up to max_lines lines of max_chars. A new phrase starts after
    the end of a sentence, a pause, or when it's full. Returns [{lines, start, end}]."""
    out = []
    st = {"lines": [], "cur": "", "first": None, "end": None}
    def flush():
        ls = st["lines"] + ([st["cur"]] if st["cur"] else [])
        if ls:
            out.append({"lines": ls, "start": st["first"], "end": st["end"]})
        st.update(lines=[], cur="", first=None, end=None)
    for i, w in enumerate(words):
        t = w["word"].strip()
        if not t:
            continue
        if st["cur"] and len(st["cur"]) + 1 + len(t) > max_chars:
            if len(st["lines"]) + 1 >= max_lines:
                flush()
            else:
                st["lines"].append(st["cur"]); st["cur"] = ""
        if st["first"] is None:
            st["first"] = w["start"]
        st["cur"] = (st["cur"] + " " + t).strip(); st["end"] = w["end"]
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["start"] - w["end"]) if nxt else 9
        ln = len(" ".join(st["lines"] + [st["cur"]]))
        if re.search(r"[.!?]$", t) or gap > pause or nxt is None or (t.endswith(",") and ln >= max_chars * 0.5):
            flush()
    return out


def caption_track(a, video, phrases, render, W, H, seek, length, out, info, linger=0.5, bridge=1.0, dim=0.0, crop=None):
    crop = crop or f"crop={W}:{H}"
    """Each phrase shows from its first word until the next phrase (or linger after its last word).
    Pictures are joined into one timed track and laid over the video in one go."""
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="captions_")
    blank = os.path.join(tmp, "blank.png"); Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    seq, t = [], seek
    for i, ph in enumerate(phrases):
        s = max(ph["start"], t)
        nxt = phrases[i + 1]["start"] if i + 1 < len(phrases) else 1e9
        e = nxt if nxt - ph["end"] < bridge else ph["end"] + linger
        e = min(e, seek + length)
        for c in getattr(a, "cuts", None) or []:
            if s < c < e and c - s < 0.2:             # starts a hair before a cut: start it on the cut instead
                s = c
            elif s < c < e:                           # never carry a line across a shot change
                e = c; break
        if e <= s:
            continue
        if s > t:
            seq.append((blank, s - t))
        png = os.path.join(tmp, f"p{i:04d}.png"); render(ph["lines"]).save(png)
        seq.append((png, e - s)); t = e
    if t < seek + length:
        seq.append((blank, seek + length - t))
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p_, d in seq:
            f.write(f"file '{p_}'\nduration {d:.3f}\n")
        f.write(f"file '{seq[-1][0]}'\n")
    if a.still is not None:
        hit, acc = blank, seek
        for p_, d in seq:
            if acc <= a.still < acc + d:
                hit = p_; break
            acc += d
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{a.still:.3f}", "-i", video, "-i", hit,
               "-filter_complex", f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,{crop},setsar=1,eq=brightness={-dim:.3f}[v];[v][1:v]overlay=0:0[out]",
               "-map", "[out]"]
        finish(a, cmd, out, None, 0, info); return
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{seek:.3f}", "-t", f"{length:.3f}", "-i", video,
           "-f", "concat", "-safe", "0", "-i", lst,
           "-filter_complex", f"[0:v]fps=30,scale={W}:{H}:force_original_aspect_ratio=increase,{crop},setsar=1,eq=brightness={-dim:.3f},format=yuv420p[v];"
                              f"[1:v]fps=30,format=rgba[c];[v][c]overlay=0:0:format=auto:shortest=1,format=yuv420p[out]", "-map", "[out]"]
    finish(a, cmd, out, 0 if has_audio(video) else None, length, info)


def band_brightness(video, seek, length, y0, y1, n=5):
    """Average brightness (0-1) of a horizontal band of the frame, sampled across the clip."""
    from PIL import Image
    import io
    vals = []
    for i in range(n):
        t = seek + length * (i + 0.5) / n
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=320:-2",
                            "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        if r.stdout:
            im = Image.open(io.BytesIO(r.stdout)).convert("L")
            band = im.crop((0, int(im.height * y0), im.width, int(im.height * y1)))
            from PIL import ImageStat; vals.append(ImageStat.Stat(band).mean[0] / 255)
    return sum(vals) / len(vals) if vals else 0.0


def draw_lines(W, H, lines, font, color, cy=None, base=None, gap=0.5, shadow=0.0):
    """Lines centred on their actual letters, equal gaps measured from capital height.
    Place the block by its centre (cy) or by the last line's baseline (base)."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hb = font.getbbox("H"); cap = hb[3] - hb[1]
    step = cap * (1 + gap)
    block = cap + step * (len(lines) - 1)
    top = (cy * H - block / 2) if cy is not None else (base * H - block)
    for i, ln in enumerate(lines):
        bb = font.getbbox(ln)
        x = W / 2 - (bb[0] + bb[2]) / 2
        d.text((x, top + step * i - hb[1]), ln, font=font, fill=color)
    if shadow > 0:
        sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(cap * 0.25)).point(lambda v: int(v * shadow))
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 255)); dark.putalpha(sh)
        img = Image.alpha_composite(dark, img)
    return img


STOP = set(("a an the and or but of to in on at by for with from is are was were be it its it's i me my you your we our "
            "so as that this these those than then just very really pelo pela de do da e o os as um uma que").split())


ITALIC_NAMES = ["atelierfleuritalic", "atelierfleur"]   # Naomi's chosen italic (4 Nov); found if installed or in Downloads
ITALIC_DIRS = ["~/Library/Fonts", "/Library/Fonts", "C:/Windows/Fonts", "~/AppData/Local/Microsoft/Windows/Fonts",
               "~/.fonts", "~/.local/share/fonts", "/usr/share/fonts", "~/Downloads"]


def find_named_font(names):
    for d in ITALIC_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                k = re.sub(r"[^a-z0-9]", "", f.lower())
                if f.lower().endswith((".otf", ".ttf")) and any(n in k for n in names):
                    return os.path.join(root, f)
            if root.count(os.sep) - d.count(os.sep) > 1:
                break
    return None


def serif_italic(size, choice=None):
    from PIL import ImageFont
    if choice and os.path.exists(choice):
        return ImageFont.truetype(choice, size)
    found = find_named_font([re.sub(r"[^a-z0-9]", "", choice.lower())] if choice else ITALIC_NAMES)
    if found:
        return ImageFont.truetype(found, size)
    if choice:
        print(f"Italic font '{choice}' isn't installed; using a standard serif italic.")
    for path in ("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", "C:/Windows/Fonts/georgiai.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return inter_font(size, "Regular")


def pick_words(lines, spec, kind):
    """Which words get the accent colour or the italic serif. auto: accent = the one longest key word of
    the phrase (6+ letters); serif = the small linking words."""
    words = [w for l in lines for w in l.split()]
    key = lambda w: re.sub(r"[^\w']", "", w.lower())
    if spec == "off":
        return set()
    if spec != "auto":
        return {key(w) for w in spec.split()}
    if kind == "serif":
        return {key(w) for w in words if key(w) in STOP}
    cands = [w for w in words if key(w) not in STOP and len(key(w)) >= 6]
    return {key(max(cands, key=lambda w: len(key(w))))} if cands else set()


def draw_mixed(W, H, lines, sans, serif, color, accent, accents, serifs, cy, shadow=0.0, gap=0.45):
    """Words share one baseline; each word is bold sans or italic serif, white or the accent colour.
    Lines are centred on their measured width; line gaps measured from the capital height."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hb = sans.getbbox("H"); cap = hb[3] - hb[1]; step = cap * (1 + gap)
    block = cap + step * (len(lines) - 1); top = cy * H - block / 2
    key = lambda w: re.sub(r"[^\w']", "", w.lower())
    space = sans.getlength(" ") * 0.9
    for i, ln in enumerate(lines):
        parts = [(w, serif if key(w) in serifs else sans, accent if key(w) in accents else color) for w in ln.split()]
        widths = [f.getlength(w) for w, f, _ in parts]
        total = sum(widths) + space * (len(parts) - 1)
        x = W / 2 - total / 2; base = top + step * i + cap
        for (w, f, c), wd in zip(parts, widths):
            d.text((x, base), w, font=f, fill=c, anchor="ls"); x += wd + space
    if shadow > 0:
        sh = img.getchannel("A").filter(ImageFilter.GaussianBlur(cap * 0.25)).point(lambda v: int(v * shadow))
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 255)); dark.putalpha(sh)
        img = Image.alpha_composite(dark, img)
    return img


def find_family(name, weight):
    """Find an installed (or downloaded) font family by name, picking the closest weight file."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    order = {"ExtraBold": ["extrabold", "black", "bold"], "Bold": ["bold", "black"], "SemiBold": ["semibold", "bold"],
             "Black": ["black", "extrabold", "bold"]}.get(weight, [weight.lower()]) + ["regular", ""]
    hits = []
    for d in ITALIC_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        base = d.count(os.sep)
        for root, dirs, files in os.walk(d):
            if root.count(os.sep) - base > 5:
                dirs[:] = []; continue
            if "web" in root.lower():
                continue
            for f in files:
                k = re.sub(r"[^a-z0-9]", "", f.lower())
                if f.lower().endswith((".otf", ".ttf")) and k.startswith(key) and "italic" not in k and "variable" not in k:
                    hits.append(os.path.join(root, f))
    for wgt in order:
        for h in sorted(hits, key=len):
            k = re.sub(r"[^a-z0-9]", "", os.path.basename(h).lower())[len(key):]
            if k.split("otf")[0].split("ttf")[0] == wgt:
                return h
    return sorted(hits, key=len)[0] if hits else None


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("video"); p.add_argument("output")
    p.add_argument("--words-per", type=int, default=2, choices=[1, 2, 3, 4])
    p.add_argument("--pattern", help='word counts per screen, in turn, e.g. "4 1 1 4 2 3 4 2 2 3" (max 4); repeats'); p.add_argument("--y", type=float, default=0.55)
    p.add_argument("--size", type=float, default=0.021); p.add_argument("--weight", default="ExtraBold")
    p.add_argument("--font", default="Satoshi", help='a font by name ("Satoshi", "Chubbo", "Tanker") or a font file; default Inter (bundled)')
    p.add_argument("--color", default="white"); p.add_argument("--shadow", type=float, default=0.45)
    p.add_argument("--case", default="upper", choices=["upper", "as-is", "lower"])
    p.add_argument("--frame", default="auto", choices=["auto", "9:16", "16:9"]); p.add_argument("--face", type=float, default=0.5)
    p.add_argument("--linger", type=float, default=0.2, help="seconds a line stays after its last word when there is a pause")
    p.add_argument("--cuts", type=float, nargs="*", default=[], help="shot-change times: a line never carries across one")
    p.add_argument("--words"); p.add_argument("--allow-download", action="store_true")
    p.add_argument("--start", type=float, default=0); p.add_argument("--length", type=float)
    p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true")
    a = p.parse_args()
    iw, ih = display_size(a.video)
    if a.frame == "auto":
        a.frame = "16:9" if iw >= ih else "9:16"
    W, H = (1920, 1080) if a.frame == "16:9" else (1080, 1920)
    if a.rough:
        W, H = W // 2, H // 2
    length = a.length or max(0.1, duration(a.video) - a.start)
    tmp = tempfile.mkdtemp(prefix="midcaptions_")
    words = [w for w in get_words(a, a.video, a.start, length, tmp) if w["word"].strip()]
    # 1-2 words per screen: a new screen after a sentence end, a comma, or a pause
    pattern = [max(1, min(4, int(n))) for n in a.pattern.split()] if a.pattern else None
    phrases, cur, pi = [], [], 0
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if pattern:   # follow the rhythm; only a sentence end or a long pause cuts a screen short
            brk = re.search(r"[.!?]$", w["word"]) or nxt is None or (nxt["start"] - w["end"]) > 0.5
            full = len(cur) >= pattern[pi % len(pattern)]
        else:
            brk = re.search(r"[.,!?;:]$", w["word"]) or nxt is None or (nxt["start"] - w["end"]) > 0.3
            full = len(cur) >= a.words_per
        if full or brk:
            pi += 1
            phrases.append({"lines": [" ".join(x["word"] for x in cur)], "start": cur[0]["start"], "end": cur[-1]["end"]}); cur = []
    def load(size):
        if a.font:
            path = a.font if os.path.exists(a.font) else find_family(a.font, a.weight)
            if path:
                from PIL import ImageFont
                return ImageFont.truetype(path, size)
            print(f"Font '{a.font}' isn't on this computer. Get it free at fontshare.com (Satoshi) and install it; using Inter for now.")
            a.font = None
        return inter_font(size, a.weight)
    f0 = load(200); hb = f0.getbbox("H")
    font = load(int(200 * a.size * H / (hb[3] - hb[1])))
    casef = (lambda t: t.upper()) if a.case == "upper" else (lambda t: t.lower()) if a.case == "lower" else (lambda t: t)
    render = lambda lines: draw_lines(W, H, [casef(l) for l in lines], font, a.color, cy=a.y, gap=0.45, shadow=a.shadow)
    print("Screens: " + " | ".join(ph["lines"][0] for ph in phrases))
    crop = f"crop={W}:{H}:(iw-{W})*{a.face}:(ih-{H})/2"
    caption_track(a, a.video, phrases, render, W, H, a.start, length, a.output,
                  f"{W}x{H}, {len(phrases)} screens, {a.words_per} words max, y {a.y}, size {a.size}, Inter {a.weight}",
                  linger=a.linger, bridge=0.25, crop=crop)


if __name__ == "__main__":
    main()
