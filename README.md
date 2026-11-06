# Naomi's Editing Cookbook

Tasteful edits for creators. Five free editing recipes for Claude Code that edit like a real editor would: one effect at a time, no bouncing captions, no pop-ups everywhere.

| Recipe | What it does |
|---|---|
| `/bigwords` | Huge words fill the frame, up to 3 at a time, each appearing exactly as you say it |
| `/midcaptions` | Small bold captions in the middle at chest height, one or two words at a time |
| `/slideup` | You slide up into the top half while your pictures slide in below, with optional captions |
| `/titlestack` | A three-word title stacked perfectly in line, one word at a time, with your clip in a rounded card |
| `/clipsonwhite` | Clips on cream: phone clips appear one at a time in a row, every gap exactly equal |

These 5 recipes are free.

## Install

Paste this into Claude Code:

```
Install the editing recipes from https://github.com/naomimetzger/cookbook into my Claude Code skills, then tell me how to use them in three lines.
```

Or copy the folders in `recipes/` into `~/.claude/skills/` yourself.

## Use

Type a recipe name, like `/bigwords`, and give it your video. It asks a few quick questions, shows you a still first, and only renders when you say yes. To browse the recipes and copy ready-made prompts, open `gallery/index.html`.

Works on Mac, Windows and Linux. You need Python 3 and ffmpeg. Each recipe checks what's missing and tells you how to get it.

Made by Naomi Metzger.

## Licence

Free to use on your own videos, including paid work. Not for resale. See [LICENSE](LICENSE).
