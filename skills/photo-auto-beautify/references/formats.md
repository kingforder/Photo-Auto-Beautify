# Input format matrix

Output is always JPEG by default. Normal RAW files produce `<name>.jpg`; other
normal formats produce `<name>-beauty.jpg`.

| Input | Decoder | Status |
| --- | --- | --- |
| RAW: RW2/DNG/CR2/CR3/NEF/ARW/RAF/ORF/PEF/SRW/… (full list in `scripts/image_formats.py`) | RawTherapee | Native |
| JPEG / PNG / TIFF | RawTherapee | Native |
| WebP | Pillow → working TIFF → RawTherapee | Supported |
| AVIF | Pillow (AVIF built in since Pillow 12) → TIFF | Supported |
| HEIC / HEIF | pillow-heif → TIFF | Supported (requires pillow-heif) |
| JPEG XL (.jxl) | ffmpeg (libjxl) → TIFF | Supported (requires ffmpeg) |
| BMP | Pillow → TIFF | Supported |
| GIF (static first frame) | Pillow → working TIFF | Supported (first frame) |

Embedded ICC profiles are honored: Xiaomi's DCI-P3 JPEGs are converted to sRGB
for analysis/format conversion, so their colors are not mistaken for sRGB.

## Dependencies

- `opencv-python-headless`, `numpy`, `Pillow`: portraits, culling, format conversion;
- `pillow-heif`: HEIC/HEIF; `setup-face.ps1` tries to install it;
- `ffmpeg` with libjxl: JPEG XL; set the `FFMPEG` environment variable if it is
  not on `PATH`;
- RawTherapee: renders RAW/JPEG/PNG/TIFF.

If a HEIC/JXL decoder is missing, the pipeline lists the reason under
"read/convert failures" and keeps processing the rest of the batch.

## Limits

- Output is always JPEG; AVIF/HEIC/JXL output is not supported (RawTherapee
  cannot write those formats).
- Animated/multi-image containers use the primary image or first frame only.
- 16-bit TIFF/PNG input is processed as an 8-bit working copy; final JPEG is 8-bit.
- RAW camera support depends on RawTherapee 5.13; very new models may be missing.

## Tested

- PNG/TIFF: processed directly by RawTherapee;
- WebP/AVIF/HEIC: converted to a working TIFF, then rendered by RT;
- JXL: ffmpeg decodes to a 16-bit TIFF, then RT renders it;
- Output names are based on the original basename, never on intermediate names
  such as `sample-normalized-beauty`.
