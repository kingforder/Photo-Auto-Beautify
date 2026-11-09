# Photo Auto Beautify

**An Agent Skill for local, free, batch photo beautification.**

**English** | [中文](README.zh-CN.md)

> **Import this Skill into an AI agent; it is not a CLI manual for end users.**
>
> The agent should read the user's taste and constraints, choose the beauty
> level/preset, and run the scripts internally. CLI flags are implementation
> details for the agent, not something users need to memorize.

The Skill has a shell-only backend. It triages a folder into
**normal / obvious problem / suspect**, then:

- beautifies every readable image source-aware: phone images at the natural level, camera images at the high level;
- uses a light portrait base plus a mask-free global skin-tone LUT; the LUT is gentler on phone/min and full on camera/high; no face mask, smoothing, or local whitening;
- adds conservative denoise and output sharpening, auto-tuned by source/ISO; **sharpness means edge acutance, not invented detail**;
- finishes with capped neutral white balance, neutral-guarded vibrance, and a gentle highlight shoulder; no automatic style conversion;
- adds a `*-fixed.jpg` candidate for obvious problems while still keeping the basic beauty output;
- still beautifies suspect or soft frames and records a warning instead of skipping them;
- treats low-saturation dusk/sunset softness as a normal scene, not automatic blur;
- detects bursts, keeps one best frame by default (max two, only for a clearly different keeper), and optionally stacks or animates them (separate, non-destructive pass); best frames stay in the original folder and remaining burst RAW can optionally be moved to a review folder;
- removes previews and temporary files, leaving originals + results.

Built for RAW and mainstream raster formats (JPEG/PNG/TIFF/WebP/AVIF/HEIC/JXL/
BMP/GIF), with source-aware levels, scene-aware presets (portrait / night /
high-key / landscape / general), burst preprocessing, and no full-frame
generative edits. The agent may adjust levels and presets to the user's request
within the documented limits.

## Built on open source

This is not a proprietary black box: every processing step is powered by
open-source components, and the skill itself is released under **0BSD**.

| Component | Role | License |
| --- | --- | --- |
| **RawTherapee** | RAW/JPEG/PNG/TIFF rendering | GPLv3 |
| **YuNet** (OpenCV Zoo) | face detection | MIT |
| **OpenCV** | face detection, image analysis | Apache-2.0 |
| **NumPy** | numeric analysis | BSD-3-Clause |
| **Pillow** | image I/O and format conversion | HPND |
| **Python** | runtime | PSF |
| **pillow-heif** (optional) | HEIC/HEIF decoding | BSD-3-Clause |
| **ffmpeg** (optional) | JPEG XL decoding | build-dependent |
| **RAWmakase** (optional) | RAW previews and exposure fixes | MIT |

No proprietary SDK, cloud API, account or subscription is required. All scripts
are readable and run locally. RawTherapee is downloaded from its official
release; the bundled YuNet model keeps its MIT notice and is SHA256-checked.
The full inventory, including bundled codec licenses, is in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

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
- Optional: `exiftool` for RAW `Make`/`Model` (source detection; without it RAW is treated as unknown)
- Optional: RAWmakase (MIT) for RAW previews and overexposure correction

## Usage

```powershell
$Skill = ".\skills\photo-auto-beautify"
$env:PYTHONPATH = "..\face-deps"

python "$Skill\scripts\photo-pipeline.py" `
  --input "C:\photos" --output-dir "C:\photos" `
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength auto` — default; reads EXIF `Make`/`Model`:
  phone → `min`, camera → `high`, unknown → `medium`.
- `--phone-strength min|medium` — phone level (default `min`; use `medium` for more).
- `--source auto|phone|camera|unknown` — override detection when metadata is
  stripped or reports an unusual make.
- `--denoise auto|off|light|medium|strong` — noise reduction; auto is conservative.
- `--sharpen auto|off|light|medium|strong` — output sharpening; auto is camera light.
- `--wb auto|off` — capped neutral-cast correction.
- `--vibrance auto|off|light|medium` — neutral-guarded color lift.
- `--highlight-rolloff auto|off|light|medium` — gentle highlight shoulder.
- `--strength min|medium|high|max` — force one level for every photo; `max` is
  intentionally over-the-top for users who want maximum punch.
- `--dry-run` — plan only, no output.
- All readable RAW → `<name>.jpg`; other formats → `<name>-beauty.jpg`.
- Obvious → basic beauty **plus** `<name>-fixed.jpg`; ask before keeping the candidate.
- Suspect/blur → basic beauty **plus** a warning; not skipped.

Linux / WSL:

```bash
cd skills/photo-auto-beautify
# Debian/Ubuntu only, if venv/pip are missing:
# sudo apt install python3-venv python3-pip
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
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
