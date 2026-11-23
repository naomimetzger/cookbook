---
name: topimages
description: Images over the top recipe from the editing recipes library. One to three images run across the top of the frame with the speaker cut out in front of them (hair over the images) and a two-line title in light mono type over the body. Works as a hook clip on every frame and as the matching cover. Use when someone types /topimages, or asks for 'two photos above my head', 'images across the top behind me', 'the art of... hook', 'collage hook', or 'a cover with images on top'.
---

# /topimages

The opening that says what the reel is about before a word is heard. The images end at the eye line, the head sits in front of them, and the cover is the same scene on the best frame.

## The choices (plain words → options)
- **Images:** `--image left.jpg --image right.png` (1-3, left to right, equal widths).
- **How each one sits:** one `--fit` per image, in the same order. `cover` fills the tile (default, choose the part with `--anchor 0.85,0`), `top` shows the whole picture at the top with its own background colour carried down.
- **Title:** `--title "THE ART OF" "BETTING ON YOURSELF"` (small line, big line), or one line. Geist Mono Regular (included, free under its open font licence), white, shrinks to stay in the safe width. `--font`, `--weight`, `--colour`, `--text-scale`.
- **Closer framing:** `--crop X,Y,W,H` in pixels of the upright video, same shape as the output.
- **Where the images end:** `--band 0.448` (default).
- **Cover or clip:** `--at 120` makes a still, `--from` and `--to` make a clip.

## If started with no details (wizard)
If the user just types `/topimages` (or asks without details), don't guess. Run a short wizard:
1. Say in one line what this does, then: "You can also paste the ready-made prompt to skip these questions."
2. Ask these one short message at a time, always offering the default: the video, the line it plays over, the images in order, the two title lines, close or as filmed, then which frame for the cover.
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
1. Show 3-4 candidate frames for the cover (smiling, eyes open, hands down) and one still of the scene, side by side with the reference if there is one.
2. Still: `python3 <skill-dir>/scripts/topimages.py VIDEO cover_v1.png --at T --image A --image B --title "SMALL LINE" "BIG LINE"`
3. Rough clip after a yes: `python3 <skill-dir>/scripts/topimages.py VIDEO hook_v1.mp4 --from S --to E (same options) --rough`
4. Look at the first, middle and last frame. If the head hides the subject of an image, change its `--anchor`.

## Rules
- Head and hair always in front. The face stays clear of the title.
- No shadow, outline or motion on the title. It's there from the first frame.
- No caption while the title is up.
- Colour is handled for you: iPhone HDR clips are converted so they don't wash out, photos are turned upright, and every video is encoded and tagged BT.709. Don't pre-extract frames with plain ffmpeg, that brings both faults back.
- Never overwrite. Each version gets the next number and a `.settings.txt`. Full size only after the user says yes.
- Stop if free disk is under 2 GB (the script checks too). Temporary files clean themselves up.
