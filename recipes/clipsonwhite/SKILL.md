---
name: clipsonwhite
description: Clips on white recipe from the editing recipes library. One to four phone clips (or photos) appear one at a time, side by side in a neat row on a white page, with equal gaps. Each clip starts playing when it appears. Use when someone types /clipsonwhite, or asks for "clips appearing one by one", "phone clips in a row", "vertical clips on white", "side by side on white" or "build up a row of clips".
---

# /clipsonwhite

One to four vertical clips pop into a neat row on a white page, one after another, with exactly equal gaps. Each clip starts playing the moment it appears.

## The choices (plain words → options)
- **Equal spacing:** `--equal` sizes the clips so every gap and every margin (left, right, top, bottom) is exactly the same. **Cream page:** `--bg "#F6F0E3"`.
- **Clips:** 1 to 4, in left-to-right order. Each is cropped from its centre to a 9:16 shape. Add `@seconds` after a file to start it at its best moment (`clip.mp4@12`), or `@start-end` to use only its best bit (`clip.mp4@0.5-3`). A clip never freezes: it leaves when its best bit ends. Fit `--length` to the best bits, starting on the word that introduces them. Look through each clip first and skip shaky or blurry parts. Photos work too.
- **Timing:** "quick" 0.3, "normal" 0.5 (default), "slow" 0.8 seconds between clips → `--every`, or exact times with `--at 0 0.4 1.2`.
- **Size:** clip height → `--height` (default 0.6 of the frame). **Gap:** "tight" 0.01, "normal" 0.02 (default), "airy" 0.08, normal 0.05 (default) → `--gap`.
- **Look (default, as approved):** rounded corners `--radius` (0.07; 0 = square), a soft shadow `--shadow` (0.25; 0 = none), and a soft off-white page with fine grain (`--bg paper`), or any colour.
- **Row position:** `--y` (0.5 centred, 0.65 lower). **Page colour:** `--bg`. **Frame:** 16:9 (default) or 9:16.
- **Ending:** the whole row cuts away at once, abruptly (default), before the next phrase starts. The row is automatically kept no longer than the clips' best bits, so nothing freezes or leaves early. `--exit 0.15` makes them leave one by one instead (only if asked).
- **Sound:** the first clip's by default (`--audio 2` keeps the second clip's, `0` makes it silent).

## If started with no details (wizard)
If the user just types `/clipsonwhite` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default (e.g. "Size: small, normal (default) or large?"). Start with the file(s) you need.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below (still first, then ask before rendering).

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg`
- On Windows, type `python` instead of `python3` in every command.
- If something is missing, it prints the right install command for that computer. Ask the user before installing anything; Python packages install with `--install`.

## Steps
1. Ask for the clips (and the best moment of each, if they care), plus any choices they haven't given, all in one short message. Otherwise use the defaults.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first. It's fast and needs no permission:
   `python3 <skill-dir>/scripts/clipsonwhite.py clipsonwhite_still_v1.png CLIP1 CLIP2 CLIP3 --still 1.2`
   Show it (all clips in) and ask if the size, gaps and order are right.
4. Ask before any video render. When they say yes, make a short rough cut with the same settings plus `--rough`.
5. Do the full render only after they approve the rough cut.
6. Never overwrite a file. Each new version gets the next number (v2, v3…). Every output comes with a `.settings.txt` holding the exact command.

## Reference look
Before rendering, look at a few frames of `demo/reference.mp4` and match its look, placement and timing (cream page, `--equal` spacing). Then compare a still of your result against it.

## Rules
- This is one effect on its own. Don't combine it with other recipes unless the user asks for that exact combination.
- Clips simply appear, with no slides, bounces, borders or shadows. For more than 4 clips or a 2x2 layout, use /grid instead.
- Their computer may be low on RAM and disk, so the script uses 2 threads. Don't run renders side by side.
