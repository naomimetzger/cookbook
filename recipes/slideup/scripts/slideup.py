#!/usr/bin/env python3
"""Slide up recipe (/slideup): a vertical push in the style of a documentary reel. The speaker's shot
slides up and off the top while a blurred, dimmed copy of the image rises from the bottom to fill the
frame, and the sharp image rides up behind it and settles slowly in the centre. The motion is stepped
(12 positions a second) for a filmic, hand-made feel. It holds, then cuts straight back. The voice keeps
playing. Portrait-first (9:16), works wide too.

  python3 slideup.py VIDEO OUTPUT --image photo.jpg --at 12.4 [options]

  --image FILE      a photo, archive page, screenshot or clip (clips keep moving)
  --at SECONDS      when the push starts (on the word that names it)    --hold 3  seconds until it cuts back
  --push 0.6        seconds for the speaker to slide off and the background to arrive
  --settle 1.5      seconds for the sharp image to rise and come to rest (long, soft landing, no bounce)
  --steps 12        motion positions per second (12 = filmic stepped motion, 0 = fully smooth)
  --width auto      card width as a share of the frame (auto: 0.62 for tall images, 0.86 for wide ones)
  --y 0.47          where the card's centre settles (0-1 down)
  --blur 0.035  --dim 0.12  --shadow 0.3
  --frame auto      auto, 9:16 or 16:9 (a wide video made 9:16 is cropped round --face X)   --face 0.5
  --start / --length / --still SECONDS / --rough

Works on Mac, Windows and Linux. Needs ffmpeg and Pillow.
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

# ---------- shared transition engine (two shots, a drawn transition between them) ----------
import io


def grab_frames(path, t0, dur, fps, W, H, fit="cover"):
    """Frames of a clip (or a repeated image) from t0 for dur seconds, sized W x H."""
    from PIL import Image
    n = max(1, int(round(dur * fps)))
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if fit == "cover"
          else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black@0")
    if is_image(path):
        im = Image.open(path).convert("RGB")
        buf = io.BytesIO(); im.save(buf, "PNG")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             input=buf.getvalue(), capture_output=True).stdout
        one = Image.frombytes("RGB", (W, H), raw[:W * H * 3])
        return [one] * n
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-t", f"{dur + 0.5:.3f}",
                          "-vf", f"fps={fps},{vf}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    fr = [Image.frombytes("RGB", (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3]) for i in range(len(raw) // (W * H * 3))]
    if not fr:
        fr = [Image.new("RGB", (W, H), "black")]
    while len(fr) < n:
        fr.append(fr[-1])
    return fr[:n]


def ease_io(u):
    u = max(0.0, min(1.0, u))
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def stitch(a, out, A, B, startA, holdA, startB, holdB, T, fps, W, H, seq_dir, info, prep_a="", prep_b=""):
    """A for holdA, the drawn transition (PNG sequence, T seconds), then B for holdB. Sound crossfades."""
    seek_b = startB + T
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    cmd += source_args(A, startA, holdA + T + 0.2)
    cmd += ["-framerate", str(fps), "-i", os.path.join(seq_dir, "%05d.png")]
    cmd += source_args(B, seek_b if not is_image(B) else 0, holdB + 0.2)
    vf = lambda i, extra: (f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={fps}"
                           f"{extra},format=yuv420p")
    lines = [vf(0, prep_a) + f",trim=duration={holdA:.3f},setpts=PTS-STARTPTS[v0]",
             f"[1:v]fps={fps},setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v1]",
             vf(2, prep_b) + f",trim=duration={holdB:.3f},setpts=PTS-STARTPTS[v2]",
             "[v0][v1][v2]concat=n=3:v=1:a=0[out]"]
    total = holdA + T + holdB
    ha, hb = has_audio(A), has_audio(B)
    amap = []
    if ha or hb:
        la = "[0:a]" if ha else None
        lb = "[2:a]" if hb else None
        if not la:
            cmd += ["-f", "lavfi", "-t", f"{holdA + T:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]; la = "[3:a]"
        if not lb:
            cmd += ["-f", "lavfi", "-t", f"{holdB + T:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]; lb = "[3:a]"
        lines.append(f"{la}aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={holdA + T:.3f}[aa];"
                     f"{lb}aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={holdB + T:.3f}[ab];"
                     f"[aa][ab]acrossfade=d={T:.3f}[aout]")
        amap = ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-filter_complex", ";".join(lines), "-map", "[out]"] + amap
    crf, preset = ("28", "veryfast") if a.rough else ("18", "medium")
    cmd += ["-t", f"{total:.3f}", "-c:v", "libx264", "-crf", crf, "-preset", preset, "-pix_fmt", "yuv420p",
            "-threads", "2", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    with open(out + ".settings.txt", "w") as f:
        f.write(info + "\n" + " ".join(shlex.quote(c) for c in cmd) + "\n")
    print(f"Done: {out} ({info})")


def paper_page(W, H, colour="#F7F7F5", grain=0.03):
    from PIL import Image
    base = Image.new("RGB", (W, H), colour)
    if grain > 0:
        n = Image.effect_noise((W, H), 20).convert("RGB")
        base = Image.blend(base, n, grain)
    return base


def round_mask(w, h, r):
    from PIL import Image, ImageDraw
    m = Image.new("L", (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 3 - 1, h * 3 - 1], radius=r * 3, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def soft_shadow(w, h, r, strength, blur):
    from PIL import Image, ImageDraw, ImageFilter
    pad = int(blur * 3)
    m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(m).rounded_rectangle([pad, pad, pad + w, pad + h], radius=r, fill=int(255 * strength))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    im = Image.new("RGBA", m.size, (0, 0, 0, 255)); im.putalpha(m)
    return im, pad


def main():
    import argparse
    from PIL import Image
    p = argparse.ArgumentParser()
    p.add_argument("video"); p.add_argument("output")
    p.add_argument("--image", required=True, nargs="+", help="one picture, or several that take turns in the bottom panel (stack layout)")
    p.add_argument("--at", type=float, required=True, nargs="+", help="when each picture slides up (one time per picture)")
    p.add_argument("--hold", type=float, default=0, help="seconds until it cuts back; 0 = stay to the end")
    p.add_argument("--out", type=float, help="stack layout: at this time the picture slides back down and the speaker fills the frame again")
    p.add_argument("--out-push", type=float, help="seconds for the slide back down (default: same as --push)"); p.add_argument("--push", type=float, default=0.6)
    p.add_argument("--settle", type=float, default=1.5); p.add_argument("--steps", type=float, default=12)
    p.add_argument("--width", default="auto"); p.add_argument("--y", type=float, default=0.47)
    p.add_argument("--blur", type=float, default=0.035); p.add_argument("--dim", type=float, default=0.12)
    p.add_argument("--shadow", type=float, default=0.3); p.add_argument("--radius", type=float, default=0.003)
    p.add_argument("--frame", default="auto", choices=["auto", "9:16", "16:9"]); p.add_argument("--face", type=float, default=0.5)
    p.add_argument("--layout", default="stack", choices=["stack", "full"], help="stack: you slide up to the top and the picture fills the bottom, both on screen; full: the picture takes the whole frame")
    p.add_argument("--split", type=float, default=0.5, help="stack: share of the frame the picture takes at the bottom")
    p.add_argument("--face-y", type=float, default=0.35, help="stack: how far down the speaker's face is (0-1), so it stays centred in the top part")
    p.add_argument("--start", type=float, default=0); p.add_argument("--length", type=float)
    p.add_argument("--still", type=float); p.add_argument("--rough", action="store_true")
    a = p.parse_args()
    images, times = a.image, a.at
    if len(times) != len(images):
        raise SystemExit("Give one --at time for each --image")
    a.image, a.at = images[0], times[0]
    iw, ih = display_size(a.video)
    if a.frame == "auto":
        a.frame = "16:9" if iw >= ih else "9:16"
    W, H = (1920, 1080) if a.frame == "16:9" else (1080, 1920)
    if a.rough:
        W, H = W // 2, H // 2
    cw0, ch0 = display_size(a.image)
    share = (0.62 if ch0 > cw0 else 0.86) if a.width == "auto" else float(a.width)
    if W > H:
        share *= 0.55
    cw = W * share; ch = cw * ch0 / cw0
    if ch > H * 0.66:
        ch = H * 0.66; cw = ch * cw0 / ch0
    cw, ch = even(cw), even(ch)
    x0 = (W - cw) // 2; y_end = int(H * a.y - ch / 2)
    r = max(1, int(W * a.radius))
    tmp = tempfile.mkdtemp(prefix="slideup_")
    mask = os.path.join(tmp, "mask.png"); round_mask(cw, ch, r).save(mask)
    sh, pad = soft_shadow(cw, ch, r, a.shadow, max(4, ch * 0.025)) if a.shadow > 0 else (Image.new("RGBA", (2, 2)), 0)
    shp = os.path.join(tmp, "shadow.png"); sh.save(shp)
    seek = a.start
    if a.still is not None:          # a still: render the effect up to that moment and keep the last frame
        length = max(1 / 24, a.still - a.start + 1 / 24)
    else:
        length = a.length or max(0.1, duration(a.video) - seek)
    t0 = a.at - seek; t1 = (t0 + a.hold) if a.hold > 0 else 1e6
    C = "\\,"
    # time, stepped to --steps positions a second (filmic), then the two eases
    q = f"(floor(t*{a.steps:g})/{a.steps:g})" if a.steps > 0 else "t"
    u = f"min(max(({q}-{t0:.3f})/{a.push:.3f}{C}0){C}1)"
    push = f"if(lt({u}{C}0.5){C}4*pow({u}{C}3){C}1-pow(2-2*{u}{C}3)/2)"            # ease in-out
    if a.out is not None:      # slide back down: the same eased, stepped move in reverse
        _to = a.out - seek; _op = a.out_push or a.push
        _uo = f"min(max(({q}-{_to:.3f})/{_op:.3f}{C}0){C}1)"
        _po = f"if(lt({_uo}{C}0.5){C}4*pow({_uo}{C}3){C}1-pow(2-2*{_uo}{C}3)/2)"
        push = f"({push})*(1-{_po})"
    us = f"min(max(({q}-{t0:.3f})/{a.settle:.3f}{C}0){C}1)"
    settle = f"(1-pow(1-{us}{C}4))"                                                # long soft landing
    on = f"between(t{C}{t0:.3f}{C}{t1:.3f})"
    e = f"if({on}{C}{push}{C}0)"
    lag = int(H * 0.42)
    y_card = f"{y_end}+{H}*(1-{push})+{lag}*(1-{settle})"
    sc = f"scale={W}:{H}:force_original_aspect_ratio=increase"
    crop = f"crop={W}:{H}:(iw-{W})*{a.face}:(ih-{H})/2"
    img_in = ["-loop", "1", "-framerate", "24", "-t", f"{length + 0.2:.3f}", "-i", a.image] if is_image(a.image) else \
             ["-stream_loop", "-1", "-t", f"{length + 0.2:.3f}", "-i", a.image]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{seek:.3f}", "-t", f"{length + 0.05:.3f}", "-i", a.video]
    cmd += img_in + ["-loop", "1", "-i", mask, "-loop", "1", "-i", shp]
    chain = [f"[0:v]fps=24,{sc},{crop},setsar=1,format=yuv420p[v]",
             f"color=c=black:s={W}x{H}:r=24,format=yuv420p[base]",
             f"[1:v]fps=24,setsar=1,split[ib][ic]",
             f"[ib]{sc},crop={W}:{H},gblur=sigma={H * a.blur:.1f},eq=brightness={-a.dim:.3f}:saturation=0.75,format=yuv420p[bg]",
             f"[ic]scale={cw}:{ch}:flags=lanczos,setsar=1,format=rgba[c0];[2:v]format=gray,scale={cw}:{ch}[m];[c0][m]alphamerge[card]",
             f"[base][v]overlay=x=0:y='-{H}*{e}':eval=frame:shortest=1[v1]",
             f"[v1][bg]overlay=x=0:y='{H}*(1-{push})':eval=frame:enable='{on}':eof_action=pass[v2]",
             f"[v2][3:v]overlay=x={x0 - pad}:y='{y_card}-{pad}+{int(ch * 0.012)}':eval=frame:enable='{on}':format=auto[v3]",
             f"[v3][card]overlay=x={x0}:y='{y_card}':eval=frame:enable='{on}':format=auto:eof_action=pass,format=yuv420p[out]"]
    if a.layout == "stack":
        # the first picture slides up into the bottom panel; each later one simply replaces it on its word
        extra = []
        for im in images[1:]:
            extra += (["-loop", "1", "-framerate", "24", "-t", f"{length + 0.2:.3f}", "-i", im] if is_image(im) else
                      ["-stream_loop", "-1", "-t", f"{length + 0.2:.3f}", "-i", im])
        cmd += extra
        ph = even(H * a.split)
        top = H - ph
        vw, vh = display_size(a.video)
        if vw / vh * top >= W:
            # a wide shot: as the picture comes up, the speaker eases out (less zoomed) into the top part,
            # showing the whole height of their shot instead of a tight crop
            zf = H / top
            pw = even(vw * top / vh)
            ot = f"(floor(on/24*{a.steps:g})/{a.steps:g})" if a.steps > 0 else "(on/24)"
            uz = f"min(max(({ot}-{t0:.3f})/{a.push:.3f}{C}0){C}1)"
            pz = f"if(lt({uz}{C}0.5){C}4*pow({uz}{C}3){C}1-pow(2-2*{uz}{C}3)/2)"
            onz = f"between(on/24{C}{t0:.3f}{C}{t1:.3f})"
            if a.out is not None:      # slide back down: the same eased, stepped move in reverse
                to = a.out - seek; op = a.out_push or a.push
                uo = f"min(max(({ot}-{to:.3f})/{op:.3f}{C}0){C}1)"
                po = f"if(lt({uo}{C}0.5){C}4*pow({uo}{C}3){C}1-pow(2-2*{uo}{C}3)/2)"
                pz = f"({pz})*(1-{po})"
            zexpr = f"if({onz}{C}{zf:.5f}+(1-{zf:.5f})*{pz}{C}{zf:.5f})"
            # the pictures sit in the shot's own frame, right under the speaker, and the whole frame eases out:
            # the speaker shrinks up into the top part and the picture rises with it, edge to edge, no gap
            zoomed = True
            speaker = (f"[0:v]fps=24,scale={pw}:{top},setsar=1,crop={W}:{top}:({pw}-{W})*{a.face}:0,"
                       f"pad={W}:{H}:0:0:black[canvas0]")
            shift = 0
        else:
            zoomed = False
            speaker = f"[0:v]fps=24,{sc},{crop},setsar=1,format=yuv420p[v]"
            shift = int(max(0, min(ph, a.face_y * H - top / 2)))
        if zoomed:
            chain = [speaker, f"[1:v]fps=24,setsar=1,scale={W}:{ph}:force_original_aspect_ratio=increase,crop={W}:{ph},format=yuv420p[pic]",
                     f"[canvas0][pic]overlay=x=0:y={top}:enable='gte(t{C}{t0:.3f})':eof_action=pass[c0]"]
            for k, tk in enumerate(times[1:], 1):
                chain.append(f"[{3 + k}:v]fps=24,setsar=1,scale={W}:{ph}:force_original_aspect_ratio=increase,crop={W}:{ph},format=yuv420p[pic{k}]")
                chain.append(f"[c{k - 1}][pic{k}]overlay=x=0:y={top}:enable='gte(t{C}{tk - seek:.3f})':eof_action=pass[c{k}]")
            chain.append(f"[c{len(images) - 1}]zoompan=z='{zexpr}':x='(iw-iw/zoom)/2':y=0:d=1:s={W}x{H}:fps=24,format=yuv420p[out]")
        chain = chain if zoomed else [speaker,
                 f"color=c=black:s={W}x{H}:r=24,format=yuv420p[base]",
                 f"[1:v]fps=24,setsar=1,scale={W}:{ph}:force_original_aspect_ratio=increase,crop={W}:{ph},format=yuv420p[pic]",
                 f"[base][v]overlay=x=0:y='-{shift}*{e}':eval=frame:shortest=1[v1]",
                 f"[v1][pic]overlay=x=0:y='{H}-{ph}*{push}':eval=frame:enable='{on}':eof_action=pass[p0]"]
        for k, tk in enumerate(times[1:] if not zoomed else [], 1):
            tk = tk - seek
            onk = f"between(t{C}{tk:.3f}{C}{t1:.3f})"
            chain.append(f"[{3 + k}:v]fps=24,setsar=1,scale={W}:{ph}:force_original_aspect_ratio=increase,crop={W}:{ph},format=yuv420p[pic{k}]")
            chain.append(f"[p{k - 1}][pic{k}]overlay=x=0:y={H - ph}:enable='{onk}':eof_action=pass[p{k}]")   # later pictures simply replace it (hard cut)
        if not zoomed:
            chain.append(f"[p{len(images) - 1}]format=yuv420p[out]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[out]"]
    if a.still is not None:
        tmpv = os.path.join(tmp, "still.mp4")
        subprocess.run(cmd + ["-an", "-c:v", "libx264", "-crf", "16", "-t", f"{length:.3f}", tmpv], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", tmpv, "-update", "1", a.output], check=True)
        print(f"Done: {a.output}"); return
    finish(a, cmd, a.output, 0 if has_audio(a.video) else None, length,
           f"{W}x{H}, card {cw}x{ch} settles at y {y_end}, push at {a.at}s ({a.push}s), settle {a.settle}s, {a.steps:g} steps/s, hold {a.hold}s")


if __name__ == "__main__":
    main()
