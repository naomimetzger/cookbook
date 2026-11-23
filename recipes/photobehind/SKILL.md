---
name: photobehind
description: Photo behind head recipe from the editing recipes library. Proof photos (titles, medals, podiums, events, press) pop in behind the speaker's head on the words that need them, one per beat, each replacing the last with a hard cut. The person is cut out automatically so the photo sits behind the head, with no shadow. Use when someone types /photobehind, or asks for "photos behind my head", "pictures pop up behind me", "show my titles when I say it", "proof photos over my head", or "put my pics in when I mention them".
---

# /photobehind

Real proof, shown the moment it's said, without leaving the talking head. For example, three title photos land behind the head on "and then I won, and won again", one per beat.

## The choices (plain words → options)
- **Which words:** the stretch of video (`--from 7.6 --to 13.6`) and when each photo lands, in seconds from that start (`--photo title1.png@0.40`). Land each photo on the stressed word; use word timings from a transcript, then check by ear.
- **Which photos:** the user's real photos only, never stock or mock-ups. Photos only, not videos: for a moment from a clip, use a still from it. Ask whether other people's faces should be blurred.
- **When they go:** `--end 3.0` (seconds from the start). The last photo leaves before the next scene.
- **Size/position:** `--scale 0.9`, `--top 0.18`. By default the photo is 27% of the frame's height, its top 20% down, centred over the head, with slightly rounded corners.

## If started with no details (wizard)
If the user just types `/photobehind` (or asks for it without details), don't guess. Run a short wizard:
1. Say in one line what this recipe does, then say: "You can also paste the ready-made prompt from the gallery to skip these questions."
2. Ask the choices in `prompt.md` one short message at a time, always offering the default: the video, the line, the photos in order, blurred faces or not.
3. Skip anything they've already told you. Accept "default" or "you choose".
4. Repeat the answers back as the filled-in prompt, then carry on with the Steps below.

## Setup (any computer)
Works on Mac, Windows and Linux. Before the first run, check what's needed:
`python3 <skill-dir>/scripts/check_setup.py ffmpeg pillow cutout`
- **Mac (macOS 14+):** the cut-out uses Apple's built-in subject lifting (free, offline). It builds itself on first run and needs the Xcode command line tools (`xcode-select --install`).
- **Windows / Linux:** the cut-out uses rembg (`rembg[cpu]`): `python3 <skill-dir>/scripts/check_setup.py --install rembg`. Its model downloads once (about 176 MB). The script stops and asks first; after a yes, add `--allow-download`.
- Phone files are handled: HEIC photos, sideways phone photos and iPhone HDR video.
- On Windows, type `python` instead of `python3`. Ask before installing anything.

## Steps
1. Ask for the video, the words and the photos in one message. Images pasted into a chat aren't files, so ask for the file names.
2. Check free disk space (stop under 2 GB). The script deletes its temporary frames as it goes.
3. Rough first: `python3 <skill-dir>/scripts/photobehind.py VIDEO piece_v1.mp4 --from S --to E --photo a.png@0.4 --photo b.png@1.2 --end 3.0 --rough`. Show 2–3 stills.
4. It also writes `piece_v1.cues.json`, the time of each photo, so a sound (like a camera shutter) can be laid on each one.
5. Full size only after a yes. Never overwrite a file; each version gets the next number, with a `.settings.txt`.

## Rules
- No shadow, frame, bounce or slide: a hard cut in, then a hard cut to the next photo.
- The photo never covers the eyes or mouth; only hair and the top of the head overlap it.
- Don't show the same photos twice in one video.
- Keep captions below the photos (about 54% down the frame or lower).
