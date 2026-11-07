# Photo Auto Beautify

**Local, free, batch photo beautification for AI agents.**

**English** | [中文](README.zh-CN.md)

A shell-only photo pipeline skill. It triages a folder into
**normal / obvious problem / suspect**, then:

- beautifies normal photos at medium strength by default;
- keeps the original and writes a `*-fixed.jpg` candidate for obvious problems;
- only reports suggestions for suspect or unrepairable images;
- removes previews and temporary files, leaving originals + results.

Built for RAW and mainstream raster formats (JPEG/PNG/TIFF/WebP/AVIF/HEIC/JXL/
BMP/GIF), with scene-aware presets (portrait / night / high-key / landscape /
general), optional face smoothing, and no full-frame generative edits.

## Install

Published through [skills.sh](https://www.skills.sh):

```bash
npx skills add kingforder/Photo-Auto-Beautify
```

Or copy `skills/photo-auto-beautify/` into your agent's skills directory.

### Optional Claude Code plugin

This repo is also a Claude Code plugin root (`.claude-plugin/plugin.json`):

```bash
claude --plugin-dir .
```

## Requirements

- Windows 10/11, or Linux / WSL2 (WSL2 verified; WSL1 should work but is untested)
- Python 3.10+ with Pillow, NumPy, OpenCV
- `pillow-heif` for HEIC/HEIF, `ffmpeg` (libjxl) for JPEG XL
- RawTherapee 5.13: `scripts/setup-rt.ps1` on Windows, `scripts/setup-rt.sh` on Linux
- Optional: RAWmakase (MIT) for RAW previews and overexposure correction

## Usage

```powershell
$Skill = ".\skills\photo-auto-beautify"
$env:PYTHONPATH = "..\face-deps"

python "$Skill\scripts\photo-pipeline.py" `
  --input "C:\photos" --output-dir "C:\photos" `
  --strength medium `
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength min|medium|max` — default medium.
- `--dry-run` — plan only, no output.
- Normal RAW → `<name>.jpg`; other normal formats → `<name>-beauty.jpg`.
- Obvious → `<name>-fixed.jpg`; ask the user before keeping it.
- Suspect/blur → no file, only suggestions.

Linux / WSL:

```bash
cd skills/photo-auto-beautify
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
  --strength medium \
  --report "$HOME/photos/pipeline-report.md"
```

Linux needs Pillow/NumPy/OpenCV/pillow-heif in the active Python environment;
use a venv or your distro packages. RAW previews fall back to RawTherapee when
RAWmakase is not installed.

### Overwriting originals (dangerous)

The default never modifies a source file. Only when the user explicitly insists,
add `--overwrite-originals`:

- normal JPG/JPEG only, written back in place;
- RAW stays untouched and still produces `<name>.jpg`;
- PNG/WebP/HEIC/JXL still produce `-beauty.jpg`, never overwritten;
- `*-fixed.jpg` candidates are still separate and need confirmation;
- irreversible — back up first; never enable by default.

See [`skills/photo-auto-beautify/SKILL.md`](skills/photo-auto-beautify/SKILL.md)
for the full policy, scene table and limits.

## Repository layout

```text
.
├── .claude-plugin/plugin.json
├── skills/photo-auto-beautify/
│   ├── SKILL.md
│   ├── scripts/
│   ├── assets/
│   └── references/
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.zh-CN.md
```

## License

- Original code, scripts, docs and look profiles: **0BSD** (see `LICENSE`).
- Bundled YuNet model: **MIT** (see `skills/photo-auto-beautify/assets/models/LICENSE`).
- RawTherapee: **GPLv3**, downloaded separately, not bundled.
- OpenCV / NumPy / Pillow / Python: their own licenses.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Privacy

All photo and face processing is local. No images or face data are uploaded.
