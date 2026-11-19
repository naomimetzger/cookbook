#!/usr/bin/env python3
"""Check what this recipe needs on this computer (Mac, Windows or Linux) and say how to get it.

  python3 check_setup.py ffmpeg pillow [faster-whisper] [rembg] ...
  python3 check_setup.py --install pillow faster-whisper   # installs Python packages with pip

ffmpeg can't be installed by pip, so the right command for this computer is printed instead.
Exit code 0 = everything is ready, 1 = something is missing.
"""
import importlib.util, platform, shutil, subprocess, sys

PIP_NAMES = {"pillow": "PIL", "faster-whisper": "faster_whisper", "rembg": "rembg",
             "numpy": "numpy", "opencv-python-headless": "cv2", "onnxruntime": "onnxruntime"}


def ffmpeg_hint():
    s = platform.system()
    if s == "Darwin":
        return "brew install ffmpeg   (no Homebrew? see https://brew.sh)"
    if s == "Windows":
        return "winget install --id Gyan.FFmpeg -e   (then open a new terminal)"
    return "sudo apt install ffmpeg   (or your Linux package manager)"


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
        mod = PIP_NAMES.get(need, need.replace("-", "_"))
        ok = importlib.util.find_spec(mod) is not None
        if not ok and install:
            r = subprocess.run([sys.executable, "-m", "pip", "install", need])
            ok = r.returncode == 0 and importlib.util.find_spec(mod) is not None
        print(f"{'ok ' if ok else 'MISSING'}  {need}" + ("" if ok else f"  ->  {sys.executable} -m pip install {need}"))
        if not ok:
            missing.append(need)
    print("Ready." if not missing else "Not ready: " + ", ".join(missing))
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
