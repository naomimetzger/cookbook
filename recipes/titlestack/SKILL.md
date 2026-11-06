---
name: titlestack
description: Title stack recipe from the editing recipes library. A three-line intro title with a big contrast in size and font, a small plain word, then a huge pixel-lettered coloured word, then a small plain word tucked to the right (e.g. the / FLASH CUT / transition), appearing one at a time on a paper-coloured page or over a clip. Use when someone types /titlestack, or asks for an "intro title", "mixed size title", "big word in the middle title", "hand-drawn title" or "title card like a YouTube tutorial".
---

# /titlestack

An intro title in three lines: a small plain word, a huge pixel-lettered word in deep red, and a small plain word pushed to the right edge of the big word. Each line appears in turn, and the contrast in size does the work.

## The choices (plain words → options)
- **Words:** `--top the --big "FLASH CUT" --bottom transition`. The big line should be 1–3 words; the small lines can be left out.
- **Behind it:** a cream paper page (default, `--bg` for another colour), or over their clip or image with `--over FILE`.
- **Colours:** big word `--color` (default deep red #9B111E), small words `--ink` (default near-black).
- **Fonts:** big `--big-font` (pixel = blocky pixel lettering (default), hand, bold, condensed, serif, or their own file); small `--small-font` (rounded (default), bold, serif). If they show a reference, pick the closest and say which.
- **Lean:** `--slant 0.18` (default) gives brush-lettering lean, 0 is upright.
- **Fixed proportions and order (always):** the top word plays first, then the big word, then the bottom word. The small words are always 42% of the big word's height. The top word lines up exactly with the big word's left edge, and the bottom word with its right edge. All gaps are equal. Don't change these.
- **Rounded clip or photo underneath (pairs well):** `--card FILE` puts it in a rounded card under the title, exactly as wide as the big word. Use `--card-start` for where a clip starts and `--card-radius` for the corners (default 0.04).
- **Timing:** `--every 0.35` seconds between lines (0 = all at once). **Position:** `--y` (0.3 default, near the top). **Frame:** 9:16 (default) or 16:9.

## If started with no details (wizard)
If the user just types `/titlestack` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default (e.g. "Size: small, normal (default) or large?"). Start with the file(s) you need.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below (still first, then ask before rendering).

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow`
- On Windows, type `python` instead of `python3` in every command.
- If something is missing, it prints the right install command for that computer. Ask the user before installing anything; Python packages install with `--install`.

## Steps
1. Ask for the three lines of text (and a clip to put it over, if any), plus any choices they haven't given, all in one short message. Otherwise use the defaults.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first. It's fast and needs no permission:
   `python3 <skill-dir>/scripts/titlestack.py titlestack_still_v1.png --top the --big "FLASH CUT" --bottom transition --still 1.5`
   Show it and check the big word fills the width without crowding the edges.
4. Ask before any video render. When they say yes, make a short rough cut with the same settings plus `--rough`.
5. Do the full render only after they approve the rough cut.
6. Never overwrite a file. Each new version gets the next number (v2, v3…). Every output comes with a `.settings.txt` holding the exact command.

## Reference look
Before rendering, look at a few frames of `demo/reference.mp4` and match its look, placement and timing. Then compare a still of your result against it.

## Rules
- This is one effect on its own. Don't combine it with other recipes unless the user asks for that exact combination.
- No pops, bounces, shadows or outlines: lines simply appear.
- Their computer may be low on RAM and disk, so the script uses 2 threads. Don't run renders side by side.
