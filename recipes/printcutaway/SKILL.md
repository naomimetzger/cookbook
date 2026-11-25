---
name: printcutaway
description: Paper collage cutaway from your own footage, from the editing recipes library. For one key line the speaker becomes a moving black and white dot-print cut-out on pale grid paper at 12 poses a second (lips still follow the words), a blue pen ring draws round the head and big words land as they're said, the key one in red. No generated images or credits. Use when someone types /printcutaway, or asks for a 'collage cutaway', 'turn me into a halftone print', 'paper collage of me', or a 'Vox-style moment from my own video'.
---

# /printcutaway

A 1-2 second change of scene on the line that matters, made only from the talking footage, so it's always in sync.

## The choices (plain words → options)
- **The line:** `--from` and `--to` in seconds of the video. Start on the voice onset of its first word.
- **Words:** `--word "BET ON@0.76" --word "YOURSELF@0.95"` (seconds from `--from`, up to 3 lines). Bold caps in dark ink, last line red. Without `--font` it uses a bold system font: a characterful display font of your own looks best (`--font path/to/font.ttf`). `--word-colour`, `--key-colour`.
- **Ring:** on by default and draws on over 4 poses. `--no-ring`, `--ring-size 0.9`, `--ring-colour blue`.
- **Framing:** use the same `--crop` as the shot before it.

## If started with no details (wizard)
If the user just types `/printcutaway` (or asks without details), don't guess. Run a short wizard:
1. Say in one line what this does, then: "You can also paste the ready-made prompt to skip these questions."
2. Ask these one short message at a time, always offering the default: the video, the line, the one to three big words and which is the key word, then ring or no ring.
3. Skip anything already answered. Accept "default" or "you choose".
4. Repeat the answers back as the filled-in `prompt.md`, then carry on with the Steps.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow numpy cutout`
- **Mac (macOS 14+):** the cut-out uses Apple's built-in subject lifting (free, offline). It builds itself on first run and needs Apple's Command Line Tools (`xcode-select --install`).
- **Windows / Linux (beta):** the cut-out uses rembg: `python3 <skill-dir>/scripts/check_setup.py --install rembg`. Its model downloads once (about 176 MB): the script stops and asks first, and after a yes add `--allow-download`.
- Phone files are handled: HEIC photos, sideways phone photos and iPhone HDR video.
- On Windows, type `python` instead of `python3`. Ask before installing anything.

## Steps
1. Get word times from the transcript, then correct them from the sound. A word never appears before it's said.
2. Still: `python3 <skill-dir>/scripts/printcutaway.py VIDEO still_v1.png --from S --to E --word "WORDS@t" --still 1.2`
3. Rough after a yes: `python3 <skill-dir>/scripts/printcutaway.py VIDEO scene_v1.mp4 --from S --to E --word "WORDS@t" --rough`
4. Check every pose has the whole head, and that the cut in lands on the same frame as the voice.

## Rules
- One idea only: the print, the ring and the words. No small labels or stickers.
- Hard cut in and out. The only camera move is the slow 3.5% push.
- Don't caption the same words underneath.
- Colour is handled for you: iPhone HDR clips are converted so they don't wash out, photos are turned upright, and every video is encoded and tagged BT.709. Don't pre-extract frames with plain ffmpeg, that brings both faults back.
- Never overwrite. Each version gets the next number and a `.settings.txt`. Full size only after the user says yes.
- Stop if free disk is under 2 GB (the script checks too). Temporary files clean themselves up.
