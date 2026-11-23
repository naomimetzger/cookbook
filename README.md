# Naomi's Editing Cookbook

Tasteful edits for creators. Preview, customise and copy prompts at [naomimetzger.com/cookbook](https://naomimetzger.com/cookbook). Nine free editing recipes for your AI (Claude Code, ChatGPT Codex or any AI that can run commands on your computer) that edit like a real editor would: one effect at a time, no bouncing captions, no pop-ups everywhere.

| Recipe | What it does |
|---|---|
| `/bigwords` | Huge words fill the frame, up to 3 at a time, each appearing exactly as you say it |
| `/midcaptions` | Small bold captions in the middle at chest height, one or two words at a time |
| `/slideup` | You slide up into the top half while your pictures slide in below, with optional captions |
| `/titlestack` | A three-word title stacked perfectly in line, one word at a time, with your clip in a rounded card |
| `/clipsonwhite` | Clips on cream: phone clips appear one at a time in a row, every gap exactly equal |
| `/textbehind` | A big title tucked behind your head, for reel covers and hook titles, in bold caps or white lowercase |
| `/topimages` | One to three of your pictures across the top with you cut out in front, and a two-line title over your chest. A hook and its matching cover |
| `/photobehind` | Proof photos pop in behind your head on the words that need them, one per beat |
| `/gridmat` | Your clip or photo as a card on a green cutting-mat grid (or blue, pink, cream, black) |

These 9 recipes are free.

## Install

Paste this into your AI:

```
Install the editing recipes from https://github.com/naomimetzger/cookbook into my skills, then tell me how to use them in three lines.
```

Or copy the folders in `recipes/` yourself:
- Claude Code: `~/.claude/skills/`
- ChatGPT Codex: `~/.agents/skills/`
- Other AIs: put the folder anywhere and say "follow the recipe in this folder"

Works with Claude Code and ChatGPT Codex.

## Use

Type a recipe name, like `/bigwords` (or "use the bigwords recipe"), and give it your video. It asks a few quick questions, shows you a still first, and only renders when you say yes. **Customise and tweak each recipe, then copy your prompt, at [naomimetzger.com/cookbook](https://naomimetzger.com/cookbook).**

Tested on Mac. Windows and Linux are in beta: they should work, but tell me if something breaks. You need Python 3.11 or newer and ffmpeg. Each recipe checks what's missing and tells you how to get it, and asks before installing anything.

iPhone files are handled for you: HEIC photos, sideways photos and HDR video are converted to normal colour first, and your originals are never changed. Every render is saved under a new name, so nothing is overwritten.

Made by Naomi Metzger.

## Licence

Free to use on your own videos, including paid work. Not for resale. See [LICENSE](LICENSE).
