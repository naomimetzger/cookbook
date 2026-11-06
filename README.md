# Naomi's Editing Cookbook

Tasteful edits for creators. Five free editing recipes for your AI (Claude Code, ChatGPT Codex, Grok or any AI that can run commands on your computer) that edit like a real editor would: one effect at a time, no bouncing captions, no pop-ups everywhere.

| Recipe | What it does |
|---|---|
| `/bigwords` | Huge words fill the frame, up to 3 at a time, each appearing exactly as you say it |
| `/midcaptions` | Small bold captions in the middle at chest height, one or two words at a time |
| `/slideup` | You slide up into the top half while your pictures slide in below, with optional captions |
| `/titlestack` | A three-word title stacked perfectly in line, one word at a time, with your clip in a rounded card |
| `/clipsonwhite` | Clips on cream: phone clips appear one at a time in a row, every gap exactly equal |

These 5 recipes are free.

## Install

Paste this into your AI:

```
Install the editing recipes from https://github.com/naomimetzger/cookbook into my skills, then tell me how to use them in three lines.
```

Or copy the folders in `recipes/` yourself:
- Claude Code: `~/.claude/skills/`
- ChatGPT Codex: `~/.agents/skills/`
- Other AIs: put the folder anywhere and say "follow the recipe in this folder"

Works with Claude Code, ChatGPT Codex and Grok.

## Use

Type a recipe name, like `/bigwords` (or "use the bigwords recipe"), and give it your video. It asks a few quick questions, shows you a still first, and only renders when you say yes. To browse the recipes and copy ready-made prompts, open `gallery/index.html`.

Works on Mac, Windows and Linux. You need Python 3 and ffmpeg. Each recipe checks what's missing and tells you how to get it.

Made by Naomi Metzger.

## Licence

Free to use on your own videos, including paid work. Not for resale. See [LICENSE](LICENSE).
