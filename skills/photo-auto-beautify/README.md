# Photo Auto Beautify · Local, free batch photo beautification

> No subscription, no uploads, no one-by-one editing: one command turns a whole
> batch of RAW/JPG/HEIC files into deliverable results.

A shell-only photo pipeline skill. Normal photos are beautified automatically;
obvious problems produce a fixed candidate for confirmation; suspect images get
suggestions only.

- Default medium beauty; `--strength min/medium/max` selects the level.
- Normal RAW → a JPG with the same name; other formats → `<name>-beauty.jpg`.
- Obvious over/under-exposure → keep the original, write `<name>-fixed.jpg`, ask first.
- Suspect or blurred images → suggestions only, no file.
- Final state: originals + beauty files + fixed candidates; previews/temp removed.
- **Originals are never overwritten by default.** `--overwrite-originals` is an
  explicit, dangerous opt-in for normal JPG/JPEG only; RAW and other formats stay intact.

## Supported formats

RAW (RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW, and more), JPEG, PNG, TIFF,
WebP, AVIF, HEIC/HEIF, JPEG XL, BMP, GIF (first frame); output is always JPEG.
HEIC needs `pillow-heif`; JXL needs `ffmpeg` (libjxl).

## Requirements

- Python 3 + Pillow + NumPy + OpenCV (face/culling/format conversion)
- `pillow-heif` for HEIC/HEIF; `ffmpeg` for JPEG XL
- RawTherapee 5.13: `scripts/setup-rt.ps1` on Windows, `scripts/setup-rt.sh` on Linux
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
  --strength medium --temp-dir "C:\temp\photo-pipeline" `
  --report "C:\photos\pipeline-report.md"
```

Linux/WSL example:

```bash
# Debian/Ubuntu only, if venv/pip are missing:
# sudo apt install python3-venv python3-pip
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-rt.sh
python3 scripts/photo-pipeline.py \
  --input "$HOME/photos" --output-dir "$HOME/photos" \
  --strength medium --report "$HOME/photos/pipeline-report.md"
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
