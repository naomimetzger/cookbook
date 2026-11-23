---
name: midcaptions
description: Middle captions recipe from the editing recipes library. One or two small bold white capitals in the middle of the frame at chest height, with a soft dark shadow, changing every word or two as they're spoken, like a documentary interview reel. No box, no animation. Portrait-first, works wide too. Use when someone types /midcaptions, or asks for "one or two word captions", "captions in the middle", "interview captions", "chest height captions", "documentary reel captions" or "small caps captions".
---

# /midcaptions

One or two small bold capitals sit in the middle at chest height and change with every word or two, timed to the speech. A soft shadow keeps them readable on any shot.

## The choices (plain words → options)
- **Words on screen:** 1-2 by default (`--words-per`). With the /slideup combo use `--pattern "4 1 1 4 2 3 4 2 2 3"` (up to 4, varied). The right count depends on the recipe it is paired with.
- **Place:** `--y auto` (default): just below the face it finds (on a Mac), between 0.60 and 0.72 so it stays in Instagram's safe zone. If it can't look, 0.65 (chest height). `--y 0.68` sets it by hand; keep it between 0.14 and 0.75, never over the mouth.
- **Size:** `--size 0.021` of the frame height (small on purpose). **Weight:** `--weight ExtraBold`.
- **Font:** Satoshi Black by default (Naomi's pick; free at fontshare.com). If it isn't installed the script uses Inter and says so: offer to tell the user where to get Satoshi. `--font` takes any other font name or file. Fontshare fonts can't be bundled or shared: tell the user to download their own free copy from fontshare.com and install it.
- **Style:** `--color white`, `--shadow 0.45`, `--case upper|as-is`.
- **Shape:** `--frame auto|9:16|16:9`; a wide video made 9:16 is cropped round `--face X`.
- **Horizontal vs reels:** horizontal (16:9) videos use calmer timing, more white space and smaller text than vertical reels. Check which the user is making.

## If started with no details (wizard)
If the user just types `/midcaptions` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default. Start with the file(s) you need.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow faster-whisper`
- On Windows, type `python` instead of `python3` in every command. Ask before installing anything.
- Speech-to-text runs offline. It checks the language first and prints it. If it can't tell, it stops: ask the user which language, then add `--language es` (or fr, pt…).
- If a model is missing, the script stops and names it and its size (e.g. 'base', about 145 MB). Ask the user, then rerun with `--allow-download`.
- On a Mac the face check builds a small helper once (needs Apple's free Command Line Tools). Without it, the words sit at 0.65.

## Steps
1. Ask for the video, all in one short message.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first: `python3 <skill-dir>/scripts/midcaptions.py INPUT midcaptions_still_v1.png --still <a second with speech> [--hint "bet on yourself"]`. It transcribes the whole part. Show it with the "Words heard:" line and ask the user to check every word. Check the words sit on the chest, not the face. Fix names with `--hint "the right words"`, or fix spellings in the .words.json (keep the times) and rerun with `--words`.
4. Ask before any video render, then make a rough cut (`--rough`), then the final after a yes. Judge smoothness at full quality. Clip sound is kept.
5. Never overwrite a file. Each new version gets the next number (v2, v3…). Each output comes with a `.settings.txt`.

## Reference look
Before rendering, look at a few frames of `demo/reference.mp4` and match its look, placement and timing. Then compare a still of your result against it.

## Rules
- One effect on its own. Don't combine it with other recipes unless the user asks for that exact combination.
- One caption place for the whole video. No other text layers at the same time.
- Their computer may be low on RAM and disk, so the script uses 2 threads. Don't run renders side by side.
