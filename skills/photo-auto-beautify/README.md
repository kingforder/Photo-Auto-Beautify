# Photo Auto Beautify · Agent Skill for local batch photo beautification

> **Import this Skill into an AI agent; it is not an end-user CLI manual.**
> The agent translates the user's preferences into presets, levels, burst
> choices, and cleanup behavior, then runs the local scripts internally.

> No subscription, no uploads, no one-by-one editing: the backend turns a whole
> batch of RAW/JPG/HEIC files into deliverable results.

A shell-only backend for an Agent Skill. Every readable photo gets a basic
beauty output; obvious problems add a fixed candidate for confirmation, and
suspect/soft images add a warning instead of being skipped.

- Basic beauty is mandatory; triage only adds candidates/warnings.
- Source-aware default: phone → `min` (or `--phone-strength medium` for more), camera → `high`, unknown → `medium`; `--strength` forces one level.
- Conservative detail pass: denoise and output sharpening are auto-tuned by source/ISO; sharpening raises edge acutance, not real detail.
- Low-risk finishing: capped neutral WB, neutral-guarded vibrance, and a gentle highlight shoulder; no automatic style conversion.
- Portraits use a light base plus a mask-free global skin-tone LUT; the LUT is gentler on phone/min and full on camera/high.
- No face mask, smoothing, or local whitening: no cutout edges or pixel artifacts.
- A saturation guard picks a neutral portrait base when the face is already saturated.
- All readable RAW → a JPG with the same name; other formats → `<name>-beauty.jpg`.
- Obvious over/under-exposure → basic beauty **plus** `<name>-fixed.jpg`, ask first.
- Suspect or blurred images → basic beauty **plus** a warning; never skipped.
- Optional burst pass: group by time/camera/hash, keep one best frame by default (max two, only for a clearly different keeper), optionally stack or animate (WebP/GIF); best frames stay in the original folder, and `--apply-cleanup` can move remaining burst RAW to a review folder. Separate and non-destructive by default.
- Final state: originals + beauty files + fixed candidates; previews/temp removed.
- **Originals are never overwritten by default.** `--overwrite-originals` is an
  explicit, dangerous opt-in for normal JPG/JPEG only; RAW and other formats stay intact.

## Built on open source

Every processing step is open source, and the skill itself is **0BSD**. The core
stack is RawTherapee (GPLv3), OpenCV (Apache-2.0), YuNet (MIT), Pillow (HPND),
NumPy (BSD-3-Clause) and Python (PSF); `pillow-heif`, `ffmpeg` and RAWmakase are
optional. No proprietary SDK, cloud API, account or subscription is required;
scripts are readable and run locally. See `THIRD_PARTY_NOTICES.md`.

## Supported formats

RAW (RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW, and more), JPEG, PNG, TIFF,
WebP, AVIF, HEIC/HEIF, JPEG XL, BMP, GIF (first frame); output is always JPEG.
HEIC needs `pillow-heif`; JXL needs `ffmpeg` (libjxl).

## Requirements

- Python 3 + Pillow + NumPy + OpenCV (face/culling/format conversion)
- `pillow-heif` for HEIC/HEIF; `ffmpeg` for JPEG XL
- RawTherapee 5.13: `scripts/setup-rt.ps1` on Windows, `scripts/setup-rt.sh` on Linux
- Optional: `exiftool` for RAW source detection (otherwise RAW stays unknown → medium)
- Optional: RAWmakase (RAW previews and overexposure correction)

## Install and use

From GitHub:

```bash
npx skills add kingforder/Photo-Auto-Beautify
```

Or copy `skills/photo-auto-beautify/` into your agent's skills directory.

Windows example:

```powershell
$env:PYTHONPATH = "..\face-deps"
python scripts\photo-pipeline.py --input "C:\photos" --output-dir "C:\photos" `
  --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

- `--strength auto` (default): phone → `min`, camera → `high`, unknown → `medium`.
- `--phone-strength min|medium`: phone level (default `min`; `medium` adds more).
- `--source auto|phone|camera|unknown`: override EXIF detection for stripped files.
- `--denoise auto|off|light|medium|strong`: conservative noise reduction.
- `--sharpen auto|off|light|medium|strong`: output sharpening (acutance).
- `--wb auto|off`, `--vibrance auto|off|light|medium`, `--highlight-rolloff auto|off|light|medium`: low-risk finishing.

Linux/WSL example:

```bash
# Debian/Ubuntu only, if venv/pip are missing:
# sudo apt install python3-venv python3-pip
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
  --report "$HOME/photos/pipeline-report.md"
```

Linux needs Pillow/NumPy/OpenCV/pillow-heif in the active Python environment.

Chinese readers: see the [Chinese README](../../README.zh-CN.md).

## License

- Original code, scripts, docs and look profiles: **0BSD** (see `LICENSE`).
- Bundled YuNet model: **MIT** (see `assets/models/LICENSE`).
- RawTherapee: **GPLv3**, downloaded on demand, not bundled.
- OpenCV / NumPy / Pillow / Python: their own licenses.

See `THIRD_PARTY_NOTICES.md`.

## Privacy

All face and photo processing is local. No photos or face data are uploaded.
