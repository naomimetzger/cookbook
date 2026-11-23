#!/usr/bin/env python3
"""Check what this recipe needs on this computer (Mac, Windows or Linux) and say how to get it.

  python3 check_setup.py ffmpeg pillow [faster-whisper] [rembg] ...
  python3 check_setup.py --install pillow faster-whisper   # installs Python packages with pip

ffmpeg can't be installed by pip, so the right command for this computer is printed instead.
Exit code 0 = everything is ready, 1 = something is missing.
"""
import importlib.util, platform, shutil, subprocess, sys

PIP_NAMES = {"pillow": "PIL", "faster-whisper": "faster_whisper", "rembg": "rembg",
             "numpy": "numpy", "opencv-python-headless": "cv2", "onnxruntime": "onnxruntime",
             "pillow-heif": "pillow_heif"}
# what pip actually needs to install for a name (rembg only works with an onnxruntime, which [cpu] brings)
PIP_SPEC = {"rembg": "rembg[cpu]"}
# extra modules a package needs before it really works
NEEDS = {"rembg": ["onnxruntime"]}
MIN_PY = {"rembg": (3, 11), "faster-whisper": (3, 9)}


def ffmpeg_hint():
    s = platform.system()
    if s == "Darwin":
        return "brew install ffmpeg   (no Homebrew? see https://brew.sh)"
    if s == "Windows":
        return "winget install --id Gyan.FFmpeg -e   (then open a new terminal)"
    return "sudo apt install ffmpeg   (or your Linux package manager)"


def cutout_ready():
    """Mac 14+: Apple's subject lifting (needs the Swift compiler from the Command Line Tools). Else rembg."""
    if platform.system() == "Darwin":
        try:
            major = int(platform.mac_ver()[0].split(".")[0])
        except ValueError:
            major = 0
        if major >= 14:
            r = subprocess.run(["xcrun", "--find", "swiftc"], capture_output=True)
            if r.returncode == 0:
                return True, "Apple subject lifting"
            return False, "xcode-select --install   (Apple's Command Line Tools, free)"
    if sys.version_info[:2] < (3, 11):
        return False, "needs Python 3.11+ for rembg. Install Python 3.12 from python.org"
    if importlib.util.find_spec("rembg") and importlib.util.find_spec("onnxruntime"):
        return True, "rembg"
    return False, f'{sys.executable} -m pip install "rembg[cpu]"   (then a 176 MB model downloads once, on first use)'


def main():
    args = [a for a in sys.argv[1:] if a != "--install"]
    install = "--install" in sys.argv
    missing = []
    for need in args or ["ffmpeg", "pillow"]:
        if need == "ffmpeg":
            ok = shutil.which("ffmpeg") and shutil.which("ffprobe")
            print(f"{'ok ' if ok else 'MISSING'}  ffmpeg" + ("" if ok else f"  ->  {ffmpeg_hint()}"))
            if not ok:
                missing.append(need)
            continue
        if need == "cutout":
            ok, how = cutout_ready()
            print(f"{'ok ' if ok else 'MISSING'}  person cut-out" + (f" ({how})" if ok else f"  ->  {how}"))
            if not ok:
                missing.append(need)
            continue
        mod = PIP_NAMES.get(need, need.replace("-", "_"))
        spec = PIP_SPEC.get(need, need)
        low = MIN_PY.get(need)
        if low and sys.version_info[:2] < low:
            print(f"MISSING  {need}  ->  needs Python {low[0]}.{low[1]}+ (this is {sys.version.split()[0]}). "
                  "Install Python 3.12 from python.org, then use that python.")
            missing.append(need)
            continue
        found = lambda: importlib.util.find_spec(mod) is not None and all(
            importlib.util.find_spec(m) is not None for m in NEEDS.get(need, []))
        ok = found()
        if not ok and install:
            r = subprocess.run([sys.executable, "-m", "pip", "install", spec])
            ok = r.returncode == 0 and found()
        print(f"{'ok ' if ok else 'MISSING'}  {need}" + ("" if ok else f'  ->  {sys.executable} -m pip install "{spec}"'))
        if not ok:
            missing.append(need)
    print("Ready." if not missing else "Not ready: " + ", ".join(missing))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
