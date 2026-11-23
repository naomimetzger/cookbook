"""Person cut-out masks for a folder of frames, on any computer.

Mac (macOS 14+ with Apple's Command Line Tools): Apple's built-in subject lifting (free, offline, best).
Anywhere else: rembg (free, offline after a one-time model download of about 176 MB).
The model is never downloaded without a yes: pass --allow-download (allow_download=True) after asking.
"""
import os, platform, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIFT = os.path.join(HERE, "bin", "lift")
MODEL = "u2net_human_seg"
MODEL_MB = 176
CLT_FIX = "Install Apple's Command Line Tools (free): xcode-select --install   then rerun."


def model_path():
    """Where rembg keeps its model (it downloads it there on first use)."""
    home = os.environ.get("U2NET_HOME", os.path.join(os.path.expanduser("~"), ".u2net"))
    return os.path.join(home, MODEL + ".onnx")


def is_new_mac():
    if platform.system() != "Darwin":
        return False
    try:
        return int(platform.mac_ver()[0].split(".")[0]) >= 14
    except ValueError:
        return False


def build_lift():
    """Build Apple's cut-out tool once. Returns None if it's ready, or what's wrong."""
    if os.path.exists(LIFT):
        return None
    r = subprocess.run(["xcrun", "--find", "swiftc"], capture_output=True, text=True)
    swiftc = r.stdout.strip() if r.returncode == 0 else ""
    if not swiftc:  # /usr/bin/swiftc can exist without the tools behind it, so ask xcrun
        return "The Mac's cut-out needs the Swift compiler, which isn't installed. " + CLT_FIX
    os.makedirs(os.path.dirname(LIFT), exist_ok=True)
    # build through xcrun so the compiler finds the Mac's SDK (calling the toolchain's swiftc directly can't)
    r = subprocess.run(["xcrun", "swiftc", "-O", os.path.join(HERE, "lift.swift"), "-o", LIFT],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not os.path.exists(LIFT):
        err = " ".join((r.stderr or r.stdout).strip().splitlines()[:3])[:300]
        return (f"Couldn't build the Mac's cut-out tool (swiftc failed: {err}). "
                "The Command Line Tools are probably missing or out of date. " + CLT_FIX)
    return None


def rembg_masks(frames, masks, point, allow_download=False):
    try:
        from rembg import new_session, remove
        from PIL import Image, ImageDraw
    except ImportError:
        raise SystemExit("The cut-out tool isn't installed on this computer. Ask the user, then run: "
                         f"{sys.executable} -m pip install \"rembg[cpu]\"   (and rerun)")
    if not os.path.exists(model_path()) and not allow_download:
        raise SystemExit(f"The cut-out needs a one-time model download (about {MODEL_MB} MB, saved in "
                         f"{os.path.dirname(model_path())}). Ask the user first. If they say yes, rerun with "
                         "--allow-download.")
    session = new_session(MODEL)
    os.makedirs(masks, exist_ok=True)
    for f in sorted(os.listdir(frames)):
        img = Image.open(os.path.join(frames, f)).convert("RGB")
        m = remove(img, session=session, only_mask=True).convert("L")
        if point:  # keep only the person under the point
            b = m.point(lambda v: 255 if v > 127 else 0)
            x, y = int(point[0] * (b.width - 1)), int(point[1] * (b.height - 1))
            if b.getpixel((x, y)) == 255:
                ImageDraw.floodfill(b, (x, y), 128)
                keep = b.point(lambda v: 255 if v == 128 else 0)
                m = Image.composite(m, Image.new("L", m.size, 0), keep)
        m.save(os.path.join(masks, os.path.splitext(f)[0] + ".png"))


def rembg_installed():
    import importlib.util
    return importlib.util.find_spec("rembg") is not None


def make_masks(frames, masks, point=(0.5, 0.4), allow_download=False):
    """One greyscale PNG per frame in `masks` (same name, .png), white = the person."""
    os.makedirs(masks, exist_ok=True)
    if is_new_mac():
        problem = build_lift()
        if problem is None:
            r = subprocess.run([LIFT, frames, masks, str(point[0]), str(point[1])],
                               capture_output=True, text=True, errors="replace")
            if r.returncode != 0:
                raise SystemExit("The Mac's cut-out tool failed: " + (r.stderr or r.stdout).strip()[:300])
            return
        if not rembg_installed():  # say what's actually wrong, not "rembg missing"
            raise SystemExit(problem)
        print(problem.split(". ")[0] + ". Using rembg instead.")
    rembg_masks(frames, masks, point, allow_download)


# Fonts: the user's own file first, then the first one found on this computer.
SYSTEM_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]


def find_font(candidates, override=None):
    for p in ([override] if override else []) + list(candidates) + SYSTEM_BOLD:
        p = os.path.expanduser(p)
        if os.path.exists(p):
            return p
    raise SystemExit("No bold font found. Pass --font PATH (a .ttf or .otf file).")
