"""Person cut-out masks for a folder of frames, on any computer.

Mac (macOS 14+ with Xcode command line tools): Apple's built-in subject lifting (free, offline, best).
Anywhere else: rembg (free, offline after a one-time model download of about 45 MB).
"""
import os, platform, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIFT = os.path.join(HERE, "bin", "lift")


def apple_ready():
    if platform.system() != "Darwin":
        return False
    try:
        if int(platform.mac_ver()[0].split(".")[0]) < 14:
            return False
    except ValueError:
        return False
    if os.path.exists(LIFT):
        return True
    if not shutil.which("swiftc"):
        return False
    os.makedirs(os.path.dirname(LIFT), exist_ok=True)
    return subprocess.run(["swiftc", "-O", os.path.join(HERE, "lift.swift"), "-o", LIFT],
                          capture_output=True).returncode == 0


def rembg_masks(frames, masks, point):
    try:
        from rembg import new_session, remove
        from PIL import Image, ImageDraw
    except ImportError:
        raise SystemExit("The cut-out tool isn't installed on this computer. Ask the user, then run: "
                         f"{sys.executable} -m pip install \"rembg[cpu]\"   (and rerun)")
    session = new_session("u2net_human_seg")
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


def make_masks(frames, masks, point=(0.5, 0.4)):
    """One greyscale PNG per frame in `masks` (same name, .png), white = the person."""
    os.makedirs(masks, exist_ok=True)
    if apple_ready():
        subprocess.run([LIFT, frames, masks, str(point[0]), str(point[1])], check=True, capture_output=True)
    else:
        rembg_masks(frames, masks, point)


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
