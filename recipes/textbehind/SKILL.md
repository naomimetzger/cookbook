---
name: textbehind
description: Text behind head recipe from the editing recipes library. A big title sits partly behind the speaker's head (the person is cut out automatically and put in front of the words), with optional lines in front over the body. Made for reel covers and hook titles, in two looks, bold caps in two colours or white lowercase stacked above the head, with no shadows. Use when someone types /textbehind, or asks for "text behind my head", "title behind me", "a cover photo", "thumbnail with text", "hook title tucked behind", or "make covers for my reels".
---

# /textbehind

A bold title tucked behind the head looks designed, not slapped on. Use it on one frame for a reel cover, or on a hook clip, where the text stays behind the head on every frame and each line lands as it's said.

## The choices (plain words → options)
- **Cover or hook clip:** a cover uses one frame (`--at 30.0`). A clip uses `--from 0 --to 4.1`, and `--on 0 1.2` says when each line lands (behind lines first, then front lines).
- **Words:** `--behind "11 TITLES"` goes behind the head, and `--front "1 YEAR" "SPONSORED"` sits over the body. Use the exact words from the hook.
- **Look:**
  - `--style caps` (default): bold capitals. Behind lines in `--behind-colour pink`, front lines in `--front-colour white`. Colours can be any hex code, e.g. `#FFE14A`.
  - `--style lowercase`: white lowercase stacked above the head, e.g. `--front "11 titles" "? years" "sponsored"`.
- **Font:** `--font path/to/font.ttf` (a characterful display font works best). Without it, a bold system font is used.
- **Size/position:** the behind lines sit just behind the top of the head (found from the cut-out), and long lines shrink to fit. `--scale 0.9` makes the text smaller, `--shift -0.03` moves the behind lines up, and `--point X Y` picks the person when there's more than one.

## If started with no details (wizard)
If the user just types `/textbehind` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default. Start with the file you need.
3. Skip anything they've already told you. Accept "default" or "you choose".
4. Repeat the answers back as the filled-in prompt from `prompt.md`, then carry on with the Steps below.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow cutout`
- **Mac (macOS 14+):** the cut-out uses Apple's built-in subject lifting (free, offline). It builds itself on first run and needs the Xcode command line tools (`xcode-select --install`).
- **Windows / Linux:** the cut-out uses rembg (`rembg[cpu]`): `python3 <skill-dir>/scripts/check_setup.py --install rembg`. Its model downloads once (about 176 MB). The script stops and asks first; after a yes, add `--allow-download`.
- Phone files are handled: HEIC photos, sideways phone photos and iPhone HDR video.
- On Windows, type `python` instead of `python3`. Ask before installing anything.

## Steps
1. Pick the frame first: show 3–4 candidate stills (smiling, eyes open, not blinking, not mid-word, not leaning), and let the user choose.
2. Check free disk space (stop under 2 GB).
3. Make the still: `python3 <skill-dir>/scripts/textbehind.py VIDEO cover_v1.png --at T --behind ... --front ...`. Show it, ideally next to the user's grid or their other covers so they look like a set.
4. For a hook clip, make a rough version first (`--rough`, half size), then full size only after a yes.
5. Never overwrite a file. Each new version gets the next number (v2, v3…), and each output comes with a `.settings.txt`.

## Rules
- No shadows, outlines, glows, stars or emoji on the text.
- The face stays clear: the behind line sits above the eyes, so only hair and the top of the head overlap it.
- Covers for several versions of one reel use the same frame and layout, so the grid looks cohesive.
- In a video, keep text inside the Instagram safe zone (at 1080x1920: below the top 250 px, above the bottom 380 px, 120 px clear on each side). Covers can use the full width.
