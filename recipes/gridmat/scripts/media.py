"""Safe inputs and outputs for every recipe, on any computer.

Phone files break video tools in quiet ways. This file fixes them before a recipe touches them:
- photos: HEIC opens (Mac: built-in sips; elsewhere: pillow-heif), sideways phone photos are turned upright
- iPhone HDR video (HLG or PQ) is converted to normal colour first, or the recipe stops and says how
- only the first video and first audio track are used, so extra iPhone tracks can't crash ffmpeg
- outputs never overwrite a file, are tagged as standard Rec.709 colour, and keep the source frame rate
- temp folders never sit in a path with an apostrophe (it breaks ffmpeg filters)
"""
import json, os, platform, shutil, subprocess, sys, tempfile

from PIL import Image, ImageOps

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif")
HDR_TRANSFERS = ("arib-std-b67", "smpte2084")
# encode settings: standard colour, tagged, so phones and players show the right colour
COLOR_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
# use this as (or at the end of) -vf when the frames come from Pillow (RGB), so the colour maths is Rec.709
RGB_TO_YUV = ("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
              "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")   # ffmpeg 8 needs the frames tagged too
AUDIO_MAP = "a:0?"          # first audio track only, if there is one: "-map", f"1:{AUDIO_MAP}"

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles otherwise crash on non-Latin text
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def is_image(path):
    return path.lower().endswith(IMAGE_EXT)


def safe_output(path):
    """Refuse to overwrite: every version gets a new name."""
    if os.path.exists(path):
        raise SystemExit(f"{path} already exists. Never overwrite: use the next version number.")
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    return path


def temp_dir(prefix):
    """A temp folder whose path has no apostrophe."""
    base = tempfile.gettempdir()
    if "'" in base:
        for cand in (os.path.join(os.path.expanduser("~"), ".recipe-tmp"), "/tmp", "C:\\Temp"):
            if "'" not in cand:
                base = cand
                break
        os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix=prefix, dir=base)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise SystemExit(f"Can't read {path}: {out.stderr.strip()[:200]}")
    return json.loads(out.stdout)


def video_stream(info):
    for s in info.get("streams", []):
        if s.get("codec_type") == "video" and s.get("disposition", {}).get("attached_pic", 0) == 0:
            return s
    return None


def frame_rate(path, default=30.0):
    """The source's frame rate, so 24 fps footage isn't turned into 30 with repeated frames."""
    s = video_stream(probe(path)) or {}

    def rate(key):
        try:
            n, d = s.get(key, "0/0").split("/")
            r = float(n) / float(d)
            return r if 1 <= r <= 240 else None
        except (ValueError, ZeroDivisionError):
            return None
    avg, nominal = rate("avg_frame_rate"), rate("r_frame_rate")
    standard = (23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 120)
    # phone clips are variable-rate: their average (e.g. 29.36) isn't a real frame rate, so snap to the standard one
    for r in (nominal, avg):
        if r:
            near = min(standard, key=lambda x: abs(x - r))
            if abs(near - r) / near < 0.05:
                return near
    return round(avg or nominal or default, 3)


def has_filter(name):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, errors="replace")
    return any(line.split()[1:2] == [name] for line in out.stdout.splitlines() if len(line.split()) > 1)


def load_image(path):
    """Open any photo upright (phone rotation applied), including HEIC."""
    try:
        try:
            import pillow_heif  # optional
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        im = Image.open(path)
        im.load()
    except Exception:
        if path.lower().endswith((".heic", ".heif")) and platform.system() == "Darwin" and shutil.which("sips"):
            tmp = temp_dir("heic_")
            try:
                png = os.path.join(tmp, "photo.png")
                subprocess.run(["sips", "-s", "format", "png", path, "--out", png], capture_output=True, check=True)
                im = Image.open(png)
                im.load()
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        elif path.lower().endswith((".heic", ".heif")):
            raise SystemExit("This is an iPhone HEIC photo. Ask the user, then install the reader: "
                             f"{sys.executable} -m pip install pillow-heif   (or save the photo as a JPG)")
        else:
            raise
    return ImageOps.exif_transpose(im).convert("RGB")


def prepare_video(path, tmp):
    """Return a version of `path` that's safe to process: normal colour, first video and audio track.
    The original is never changed."""
    info = probe(path)
    v = video_stream(info)
    if v is None:
        raise SystemExit(f"{path} has no video track.")
    if v.get("color_transfer") not in HDR_TRANSFERS:
        return path
    out = os.path.join(tmp, "sdr_" + os.path.splitext(os.path.basename(path))[0] + ".mov")
    if has_filter("zscale"):
        vf = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf,
                        "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", *COLOR_TAGS, "-c:a", "aac", "-b:a", "320k", out],
                       check=True)
        return out
    if platform.system() == "Darwin" and shutil.which("avconvert"):
        r = subprocess.run(["avconvert", "--source", path, "--preset", "Preset1920x1080", "--output", out, "--replace"],
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out):
            s = video_stream(probe(out)) or {}
            if s.get("color_transfer") not in HDR_TRANSFERS:
                print(f"Converted iPhone HDR to normal colour: {os.path.basename(path)}")
                return out
    raise SystemExit(f"{os.path.basename(path)} is iPhone HDR video. Converting it needs an ffmpeg with zscale "
                     "(Mac: brew install ffmpeg-full). Or export it as SDR / 'Most Compatible' from the phone, then rerun.")
