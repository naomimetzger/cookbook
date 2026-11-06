---
name: bigwords
description: Big words recipe from the editing recipes library. Huge words fill the frame, up to 3 at a time, each appearing the moment it's spoken, with equal margins and spacing. In a wide video "hi I'm Naomi" shows HI on the left, then I'M on the right, then NAOMI across the bottom. It transcribes the speech for the timing (free, offline) and matches a font from a reference if given. Use when someone types /bigwords, or asks for "big text", "giant words", "kinetic text that fills the screen", "words timed to my voice", "full-screen captions" or "text that fills the scene".
---

# /bigwords

Giant words that fill the frame, timed to the speech. Each screen holds up to 3 words, and each word appears exactly when it's said. When the screen is full (or there's a pause or a sentence ends), the next screen starts fresh.

## The layout
- **Wide video:** up to 2 lines. With 3 words, the top line has the 1st word on the left and the 2nd on the right, and the 3rd fills the bottom line. With 1–2 words, it's one line in the middle.
- **Phone video:** one word per line, stacked, up to 3 lines.
- Every word on a screen has the same height. The outside margin and the gap between lines are the same size (`--margin`, default 4% of the width). Words are squeezed or stretched a little to fill each line, never beyond what still looks like the font.

## The font ("font detected")
- If the user shows a reference (a screenshot or video still), look at it and pick the closest style: `helvetica` (condensed black, default, the classic look), `helvetica-bold`, `impact`, `din`, `avenir`. Or use their own font file with `--font path/to/font.ttf`.
- Say which font you picked and why in one line. Each style falls back to the closest font on that computer (Mac, Windows or Linux).
- Other options: colour `--color` (default white), `--case upper` (default) or `as-is`, `--max-words 1–3`, `--hold` (seconds the last word stays, default 0.35).

## If started with no details (wizard)
If the user just types `/bigwords` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default (e.g. "Size: small, normal (default) or large?"). Start with the file(s) you need.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below (still first, then ask before rendering).

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow faster-whisper`
- On Windows, type `python` instead of `python3` in every command.
- If something is missing, it prints the right install command for that computer. Ask the user before installing anything; Python packages install with `--install`.
- Speech-to-text runs offline with faster-whisper. If no model is on the computer yet, the script stops and says so. Ask the user, then rerun with `--allow-download` (one-time, about 150 MB).

## Steps
1. Ask for the video, plus a font reference if they have one. Everything else has defaults.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first. It's fast and needs no permission, and it also transcribes that moment:
   `python3 <skill-dir>/scripts/bigwords.py INPUT bigwords_still_v1.png --still 2 [--font impact]`
   Show it, plus the "Screens:" list it prints. Check the words are right.
4. **Fixing words:** the timings are saved as `OUTPUT.words.json`. Correct any spelling there (keep the times) and rerun with `--words that-file.json`.
5. Ask before any video render. When they say yes, make a short rough cut: `--rough --length 5`.
6. Do the full render only after they approve the rough cut.
7. Never overwrite a file. Each new version gets the next number (v2, v3…). Every output comes with a `.settings.txt` holding the screens and the exact command.

- **Same size, along the top:** `--max-words 1 --same-size --top 0.07` shows one word at a time, every word the same size, on one line near the top so the face stays clear. `--fit-to WORD ...` sizes separate parts of one video to the same size. `--font` takes any .ttf/.otf file, e.g. your own copy of Bootzy.

## Reference look
Before rendering, look at a few frames of `demo/reference.mp4` and match its look, placement and timing (the creator's pick: the classic layout, up to 3 huge words filling the frame, in Bootzy, white). Then compare a still of your result against it.

## Rules
- This is one effect on its own: no bounces, pops, colours per word or emojis. Words simply appear on the beat.
- Never more than 3 words on screen.
- Their computer may be low on RAM and disk, so the script uses 2 threads. Don't run renders side by side.
