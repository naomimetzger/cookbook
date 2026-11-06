---
name: slideup
description: Slide up recipe from the editing recipes library. A vertical push like a documentary reel - the speaker's shot slides up and off the top while a blurred copy of the image rises from the bottom, and the sharp image rides up and settles slowly in the centre, in stepped, filmic motion. Portrait-first (9:16), works wide too. Use when someone types /slideup, or asks for an "image slides up", "push up to a photo", "show the page", "archive card over a blur", "like the Michelangelo episode" or "photo slides in from the bottom".
---

# /slideup

On the line that names it, the speaker's shot slides up and off the top while a blurred, dimmed copy of the image rises from the bottom to fill the frame. The sharp image rides up behind it and settles slowly in the centre with a long, soft landing (no bounce). The motion is stepped at 12 positions a second, like the reference, so it feels filmic and hand-made. It holds, then cuts straight back. The voice keeps playing.

## The choices (plain words → options)
- **Layout:** `--layout stack` (default): you slide up to the top and the picture slides up from the bottom to fill the lower part (`--split 0.5`), so both are on screen together, edge to edge. On a wide shot the speaker eases out to a wider framing as the picture rises, so the top part is not over-zoomed; the two always meet edge to edge. `--face-y 0.35` (portrait shots) keeps the face centred in the top part. `--layout full`: the picture takes the whole frame over a blurred copy of itself.
- **Image:** `--image` a photo, archive page, screenshot or clip (clips keep moving).
- **Several pictures:** `--image a.jpg b.jpg c.jpg --at 2.0 3.6 4.4`: the first slides up into the bottom panel; each later one simply replaces it (a hard cut) on its word. About 3 per video reads well.
- **Slide back down:** `--out SECONDS` (stack layout) slides the picture back down and the speaker fills the frame again, e.g. before a closing aside; `--out-push 0.3` sets its speed.
- **Timing:** `--at` (the word that names it). `--hold 0` (default) keeps the picture there to the end; a number cuts back after that many seconds.
- **Motion:** `--push 0.6` (speaker off, background on), `--settle 1.5` (image comes to rest), `--steps 12` (0 = fully smooth).
- **Card:** `--width auto` (0.62 for tall images, 0.86 for wide ones), `--y 0.47` where it settles, `--shadow 0.3`.
- **Background:** `--blur 0.035`, `--dim 0.12`.
- **Shape:** `--frame auto|9:16|16:9`; a wide video made 9:16 is cropped round `--face X`.
- **Horizontal vs reels:** built portrait-first from a reel reference; on wide video the card is smaller and calmer.

## With /midcaptions (approved combo)
Render the slide-up first, then run /midcaptions on its output with `--y 0.535` (just under the join, at the top of the picture, like the reference) and `--pattern "4 1 1 4 2 3 4 2 2 3"` (up to 4 words, varied). Use the same words file.

## If started with no details (wizard)
If the user just types `/slideup` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default. Start with the file(s) you need.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow`
- On Windows, type `python` instead of `python3` in every command. Ask before installing anything.

## Steps
1. Ask for the video, the image, and the word it should land on, all in one short message.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first: `python3 <skill-dir>/scripts/slideup.py INPUT slideup_still_v1.png --image IMAGE --at T --still <T + 1>`. Show it and check the image matches what's being said at that moment, and reads clearly.
4. Ask before any video render, then make a rough cut (`--rough`), then the final after a yes. Judge smoothness at full quality. Clip sound is kept.
5. Never overwrite a file. Each new version gets the next number (v2, v3…). Each output comes with a `.settings.txt`.

## Reference look
Before rendering, look at a few frames of `demo/reference.mp4` and match its look, placement and timing. Then compare a still of your result against it.

## Rules
- One effect on its own. Don't combine it with other recipes unless the user asks for that exact combination.
- Real proof only (the actual page, photo or screenshot), and it must match the words at that moment. Once or twice per video.
- Their computer may be low on RAM and disk, so the script uses 2 threads. Don't run renders side by side.
