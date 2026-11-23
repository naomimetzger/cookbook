---
name: gridmat
description: Grid mat recipe from the editing recipes library. A plain cutting-mat style grid background (fine lines, stronger lines every five, optional numbered ruler edge, optional slight tilt) in green, blue, pink, cream or black, with the user's clip or photo on top as a rounded card with a soft shadow. Use when someone types /gridmat, or asks for a "cutting mat background", "grid background", "desk mat look", "craft mat background" or "put my video on a grid".
---

# /gridmat

A crafty, hand-made background: a cutting mat grid in a chosen colour, with the clip or photo resting on top as a card with a soft shadow. Calm, no motion except the clip itself.

## The choices (plain words → options)
- **Mat colour:** green (default), blue, pink, cream or black → `--mat` (or any hex colour).
- **Tilt:** flat (default) or slightly tilted like a desk photo → `--angle 6`.
- **Ruler numbers:** `--ruler` adds small numbers along the top and left edges.
- **Card:** size `--size` (0.62 of the height), corners `--radius` (0.03), shadow `--shadow` ("none" 0, "gentle" 0.35 (default), "strong" 0.55).
- **Frame:** follows the media (wide or phone), or force with `--frame`.

## If started with no details (wizard)
If the user just types `/gridmat` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` (in this skill's folder) one short message at a time, in plain words, always offering the default. Start with the clip or photo.
3. Skip anything they've already told you. Accept "default" or "you choose" and use the defaults.
4. When you have the answers, repeat them back as the filled-in prompt from `prompt.md`, then carry on with the Steps below.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow`
- On Windows, type `python` instead of `python3` in every command. Ask before installing anything.
- Phone files just work: HEIC photos open, sideways phone photos are turned upright, and iPhone HDR clips are changed to normal colour first. The clip's own frame rate is kept.

## Steps
1. Ask for the clip or photo and the mat colour, all in one short message.
2. Check free disk space (`python3 -c "import shutil;print(shutil.disk_usage('.').free//2**30,'GB free')"`). If less than 2 GB is free, stop and tell them.
3. Make a still first (`--still 1`), then ask before a rough cut (`--rough --length 3`), then the final after a yes. The clip's sound is kept.
4. Never overwrite a file (the script refuses if the name is taken). Each new version gets the next number.

## Rules
- One effect on its own. No stickers, doodles or extra props unless asked; those would be other recipes.
- Their computer may be low on RAM and disk, so the script uses 2 threads.
