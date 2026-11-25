"""Shared video plumbing for this recipe: colour-correct reading and writing, rotation, sizes, temp files.

Why this exists, rather than plain ffmpeg calls:
  - iPhone HDR clips (HLG, BT.2020) look washed out and lose their colour unless converted. They are converted
    here with a table taken from the Mac's own HDR-to-SDR conversion (hlg_to_709.cube, works on any computer).
  - iPhone photos are often Display P3 and sideways. They are converted and turned here.
  - Video made from RGB frames shifts colour unless it's encoded AND tagged as BT.709, so every output is.
"""
import io, json, os, platform, shlex, shutil, subprocess, sys, tempfile
from contextlib import contextmanager
from fractions import Fraction
from types import SimpleNamespace

from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
HLG_CUBE = os.path.join(HERE, "hlg_to_709.cube")
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp")
EXACT = "flags=bicubic+accurate_rnd+full_chroma_int"
MIN_FREE_GB = 2.0


def is_image(path):
    return path.lower().endswith(IMAGE_TYPES)


def need_file(path, what="File"):
    path = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isfile(path):
        raise SystemExit(f"{what} not found: {path}")
    return path


def check_space(*folders):
    for folder in folders + (tempfile.gettempdir(),):
        free = shutil.disk_usage(folder).free / 1024 ** 3
        if free < MIN_FREE_GB:
            raise SystemExit(f"Only {free:.1f} GB free. Stop and clear space first (2 GB minimum).")


def new_output(path, still=None):
    """An absolute path that doesn't exist yet. Never overwrites, so never in place either."""
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.exists(path):
        raise SystemExit(f"{path} exists. Never overwrite: use the next version number.")
    ext = os.path.splitext(path)[1].lower()
    if still is True and ext not in (".png", ".jpg", ".jpeg"):
        raise SystemExit("A still needs an output ending in .png or .jpg")
    if still is False and ext not in (".mp4", ".mov", ".m4v"):
        raise SystemExit("A clip needs an output ending in .mp4")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    check_space(os.path.dirname(path))
    return path


@contextmanager
def workspace(name):
    folder = tempfile.mkdtemp(prefix=name + "_")
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def probe(path):
    path = need_file(path, "Video")
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    vids = [s for s in data["streams"] if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    if not vids:
        raise SystemExit(f"No picture in {path}")
    v = vids[0]
    w, h = int(v["width"]), int(v["height"])
    sar = v.get("sample_aspect_ratio", "1:1").replace(":", "/")
    sar = Fraction(sar) if sar not in ("0/1", "N/A") else Fraction(1)
    w = round(w * sar)
    turn = 0
    for side in v.get("side_data_list", []):
        turn = int(side.get("rotation", turn))
    turn = int(v.get("tags", {}).get("rotate", turn))
    if abs(turn) % 180 == 90:
        w, h = h, w
    rate = v.get("avg_frame_rate", "0/0")
    if rate.endswith("/0") or rate.startswith("0/"):
        rate = v.get("r_frame_rate", "30/1")
    fps = Fraction(rate) if not rate.endswith("/0") else Fraction(30)
    std = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30), Fraction(50), Fraction(60)]
    near = min(std, key=lambda s: abs(float(s - fps)))
    if fps > 61:  # slow-motion and screen recordings
        fps = Fraction(30)
    elif abs(float(near - fps)) < 0.03 * float(near):
        fps = near
    space, pix = v.get("color_space", "unknown"), v.get("pix_fmt", "")
    if space.startswith("bt2020"):
        matrix = "bt2020"
    elif space == "bt709":
        matrix = "bt709"
    elif space in ("smpte170m", "bt470bg"):
        matrix = "bt601"
    else:  # untagged: players assume BT.709 for HD, BT.601 below that
        matrix = "bt709" if min(w, h) >= 720 else "bt601"
    # iPhone clips can carry a spatial sound track ffmpeg can't read next to the normal one: use one it can
    sound = [s["index"] for s in data["streams"]
             if s.get("codec_type") == "audio" and s.get("codec_name", "none") not in ("none", "unknown")]
    return SimpleNamespace(
        path=path, w=w, h=h, fps=fps, matrix=matrix, transfer=v.get("color_transfer", "unknown"),
        range="pc" if v.get("color_range") == "pc" or pix.startswith("yuvj") else "tv",
        rgb=pix.startswith(("rgb", "bgr", "gbr", "argb", "abgr", "pal8")), squeeze=sar != 1,
        duration=float(v.get("duration") or data["format"].get("duration") or 0),
        audio=bool(sound), audio_index=sound[0] if sound else None)


def is_hdr(info):
    return info.transfer in ("arib-std-b67", "smpte2084")


def colour_filters(info):
    """Filters that turn this clip into ordinary SDR BT.709 RGB."""
    if info.transfer == "smpte2084":
        raise SystemExit(f"{os.path.basename(info.path)} is PQ HDR (HDR10). Make an SDR copy first, e.g. on a Mac:\n"
                         "  avconvert --source IN.mov --preset Preset1920x1080 --output OUT.mov")
    square = [f"scale={info.w}:{info.h}", "setsar=1"] if info.squeeze else []
    if info.rgb:
        return square
    to_rgb = f"scale=in_color_matrix={info.matrix}:in_range={info.range}:out_range=pc:{EXACT}"
    if info.transfer == "arib-std-b67":
        return square + [to_rgb, "format=rgb48le", "lut3d=file=hlg_to_709.cube:interp=tetrahedral", "format=rgb24"]
    return square + [to_rgb, "format=rgb24"]


def parse_crop(text, w, h):
    if not text:
        return None
    try:
        x, y, cw, ch = (int(float(v)) for v in (text.split(",") if isinstance(text, str) else text))
    except ValueError:
        raise SystemExit("A crop is X,Y,WIDTH,HEIGHT in pixels of the upright picture, e.g. 230,820,1600,2844")
    if x < 0 or y < 0 or cw < 2 or ch < 2 or x + cw > w or y + ch > h:
        raise SystemExit(f"Crop {x},{y},{cw},{ch} doesn't fit inside {w}x{h}.")
    return x, y, cw, ch


def work_size(w, h, crop=None, rough=False):
    """Full size = 1080 on the short side (never enlarged); rough = half of that. Always even."""
    if crop:
        w, h = crop[2], crop[3]
    s = min(1.0, 1080 / min(w, h)) * (0.5 if rough else 1.0)
    return max(2, 2 * round(w * s / 2)), max(2, 2 * round(h * s / 2))


def clip_range(info, start, end):
    start = 0.0 if start is None else start
    end = info.duration if end is None else end
    if start < 0 or end <= start:
        raise SystemExit("--to has to be after --from, and --from can't be negative.")
    if end > info.duration + 0.1:
        raise SystemExit(f"{os.path.basename(info.path)} is only {info.duration:.2f}s long, so it can't run to {end:.2f}s.")
    return start, max(1, round((end - start) * float(info.fps)))


def read_frames(info, size, start=0.0, count=None, fps=None, crop=None, cube=None):
    """Upright RGB frames (PIL), colour-correct. `cube` is an optional look LUT on top."""
    W, H = size
    with workspace("read") as luts:
        if info.transfer == "arib-std-b67":
            shutil.copy(HLG_CUBE, os.path.join(luts, "hlg_to_709.cube"))
        chain = [f"fps={Fraction(fps or info.fps)}"] + colour_filters(info)
        if cube:
            shutil.copy(cube, os.path.join(luts, "look.cube"))
            chain.append("lut3d=file=look.cube:interp=tetrahedral")
        if crop:
            chain.append(f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}:exact=1")
        chain.append(f"scale={W}:{H}:{EXACT}")
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{start:.4f}", "-i", info.path, "-map", "0:V:0",
               "-vf", ",".join(chain)] + (["-frames:v", str(count)] if count else []) + \
              ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=luts)  # cwd, so LUT paths need no escaping
        got, last, done = 0, None, False
        try:
            while True:
                buf = proc.stdout.read(W * H * 3)
                if len(buf) < W * H * 3:
                    break
                last = Image.frombytes("RGB", (W, H), buf)
                got += 1
                yield last
            done = True
        finally:
            proc.stdout.close()
            if not done:
                proc.kill()
            code = proc.wait()
        if code and not (count and got >= count):
            raise SystemExit(f"ffmpeg couldn't read {info.path}")
        if not got:
            raise SystemExit(f"No frames at {start:.2f}s in {info.path}")
        if count and got < count:
            if count - got > 1:  # one frame of rounding is fine, more would be a freeze
                raise SystemExit(f"{os.path.basename(info.path)} ran out {count - got} frames early. It won't be frozen to fill.")
            yield last


def load_image(path):
    """Any photo as upright sRGB."""
    path = need_file(path, "Picture")
    with workspace("photo") as tmp:
        src = path
        if path.lower().endswith((".heic", ".heif")):
            if platform.system() == "Darwin":
                src = os.path.join(tmp, "photo.jpg")
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "100", path, "--out", src],
                               check=True, capture_output=True)
            else:
                raise SystemExit("Turn the HEIC photo into a JPG first (this computer can't read HEIC).")
        im = ImageOps.exif_transpose(Image.open(src))
        im.load()
        icc = im.info.get("icc_profile")
        alpha = im.convert("RGBA").getchannel("A") if im.mode in ("RGBA", "LA", "P") else None
        rgb = im.convert("RGB")
        if icc:
            try:
                prof = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                rgb = ImageCms.profileToProfile(rgb, prof, ImageCms.createProfile("sRGB"), outputMode="RGB")
            except ImageCms.PyCMSError:
                pass  # e.g. a greyscale profile: already converted by PIL
        if alpha is not None and alpha.getextrema()[0] < 255:
            rgb = Image.composite(rgb, Image.new("RGB", rgb.size, (255, 255, 255)), alpha)
        return rgb


def load_still(path, at=0.0, crop=None, rough=False):
    """One picture from a photo or a moment in a video, at working size."""
    if is_image(path):
        im = load_image(path)
        c = parse_crop(crop, *im.size)
        size = work_size(*im.size, c, rough)
        if c:
            im = im.crop((c[0], c[1], c[0] + c[2], c[1] + c[3]))
        return im.resize(size, Image.LANCZOS)
    info = probe(path)
    c = parse_crop(crop, info.w, info.h)
    return next(read_frames(info, work_size(info.w, info.h, c, rough), start=at or 0.0, count=1, crop=c))


class Writer:
    """MP4 encoded and tagged BT.709, with the clip's own sound for the same stretch. Use with `with`."""

    def __init__(self, out, size, fps, count, sound=None, start=0.0, rough=False):
        fps = Fraction(fps)
        self.out, self.count, dur = out, 0, float(count / fps)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-color_range", "pc",
               "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-"]
        has_sound = sound is not None and sound.audio
        if has_sound:
            cmd += ["-ss", f"{start:.4f}", "-t", f"{dur:.4f}", "-i", sound.path]
        vf = (f"scale=out_color_matrix=bt709:out_range=tv:{EXACT},format=yuv420p,"
              "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709")
        cmd += ["-map", "0:v"] + (["-map", f"1:{sound.audio_index}"] if has_sound else []) + ["-vf", vf,
               "-c:v", "libx264", "-crf", "21" if rough else "17", "-preset", "veryfast" if rough else "slow",
               "-color_range", "tv", "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709"]
        if has_sound:
            cmd += ["-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
        elif sound is not None:
            print("Note: the input has no sound, so this output has none either.")
        self.proc = subprocess.Popen(cmd + ["-t", f"{dur:.4f}", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def add(self, im):
        try:
            self.proc.stdin.write(im.tobytes())
        except BrokenPipeError:
            raise SystemExit("ffmpeg stopped while writing the video.")
        self.count += 1

    def __enter__(self):
        return self

    def __exit__(self, kind, *_):
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        code = self.proc.wait()
        if kind or code:
            if os.path.exists(self.out):
                os.remove(self.out)  # only this run's own unfinished file
            if not kind:
                raise SystemExit(f"ffmpeg couldn't write {self.out}")


def person_masks(frames, tmp, point, allow_download=False):
    """Cut-out mask per frame (list of PNG paths). A frame where nobody is found borrows its nearest neighbour."""
    from cutout import make_masks
    f_dir, m_dir = os.path.join(tmp, "f"), os.path.join(tmp, "m")
    os.makedirs(f_dir)
    for i, im in enumerate(frames):
        im.save(os.path.join(f_dir, f"{i:05d}.jpg"), quality=95)
    make_masks(f_dir, m_dir, point, allow_download)
    shutil.rmtree(f_dir)
    paths = [os.path.join(m_dir, n) for n in sorted(os.listdir(m_dir))]
    found = [i for i, p in enumerate(paths) if Image.open(p).convert("L").getextrema()[1] > 128]
    if not found:
        raise SystemExit("Couldn't find a person to cut out. Point at them with --point X Y (0-1 from top-left).")
    if len(found) < len(paths):
        print(f"Note: nobody found on {len(paths) - len(found)} of {len(paths)} frames, used the nearest frame's cut-out there.")
    known = set(found)
    return [p if i in known else paths[min(found, key=lambda j: abs(j - i))] for i, p in enumerate(paths)]


def read_mask(path, size, feather=0.0):
    from PIL import ImageFilter
    m = Image.open(path).convert("L").resize(size)
    return m.filter(ImageFilter.GaussianBlur(feather)) if feather else m


# ---------- text ----------
FONT_DIRS = (os.path.join(HERE, "..", "fonts"), "~/Library/Fonts", "/Library/Fonts",
             "~/.fonts", "~/.local/share/fonts", "~/AppData/Local/Microsoft/Windows/Fonts", "C:/Windows/Fonts")
FONTS = {"mono": ("GeistMono[wght].ttf", "GeistMono-Regular.ttf", "GeistMono-Regular.otf"),
         "display": ()}
FALLBACK = {"mono": ("/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consola.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            "display": ("/System/Library/Fonts/Supplemental/Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")}


def find_font(kind, override=None):
    if override:
        return need_file(override, "Font")
    for folder in FONT_DIRS:
        for name in FONTS[kind]:
            p = os.path.join(os.path.expanduser(folder), name)
            if os.path.isfile(p):
                return p
    for p in FALLBACK[kind]:
        if os.path.isfile(p):
            if FONTS[kind]:
                print(f"Note: {FONTS[kind][0]} isn't on this computer, using {os.path.basename(p)}. Pass --font to change it.")
            else:
                print(f"Using {os.path.basename(p)}. For more character pass --font with your own display font.")
            return p
    raise SystemExit("No font found. Pass --font PATH.")


def font(path, size, weight="Regular"):
    f = ImageFont.truetype(path, max(4, round(size)))
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass  # not a variable font, or no such weight
    return f


def text_width(text, f, track=0.0):
    if not track:
        return f.getlength(text)
    return sum(f.getlength(c) for c in text) + track * f.size * (len(text) - 1)


def fit_text(text, path, size, max_width, track=0.0, weight="Regular"):
    """The asked size, or smaller if that wouldn't fit."""
    f = font(path, size, weight)
    while f.size > 6 and text_width(text, f, track) > max_width:
        f = font(path, f.size - 1, weight)
    return f


def draw_centred(layer, text, f, cx, baseline, fill, track=0.0):
    d = ImageDraw.Draw(layer)
    if not track:
        d.text((cx, baseline), text, font=f, fill=fill, anchor="ms")
        return
    x = cx - text_width(text, f, track) / 2
    for c in text:
        d.text((x, baseline), c, font=f, fill=fill, anchor="ls")
        x += f.getlength(c) + track * f.size


COLOURS = {"white": (255, 255, 255), "black": (17, 17, 17), "ink": (28, 28, 28), "red": (196, 22, 32),
           "pink": (233, 172, 163), "yellow": (255, 225, 74), "blue": (36, 58, 214)}


def colour(value):
    if value in COLOURS:
        return COLOURS[value]
    v = value.lstrip("#")
    if len(v) != 6 or any(c not in "0123456789abcdefABCDEF" for c in v):
        raise SystemExit(f"Colour {value!r}: use one of {', '.join(COLOURS)} or a hex code like #C41620")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def split_time(value):
    text, _, t = value.rpartition("@")
    try:
        return text, float(t)
    except ValueError:
        raise SystemExit(f"{value!r}: write it as TEXT@SECONDS, e.g. \"BET ON@0.76\"")


def write_settings(out):
    with open(os.path.splitext(out)[0] + ".settings.txt", "w") as f:
        f.write(shlex.join(sys.argv) + "\n")
    print("wrote", out)
