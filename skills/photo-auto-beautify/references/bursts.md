# Burst detection, stacking, and animation

Optional, local, non-destructive. The main photo pipeline does not call this;
run it as a separate pass before or after beauty.

## What it does

1. Scan a folder and read capture time, camera make/model, and dimensions.
2. Group frames into bursts when they are close in time, from the same camera,
   and perceptually similar.
3. Pick the sharpest frame, with a clipping penalty.
4. Optionally align and stack the frames (median / mean / exposure fusion).
5. Optionally write an animated WebP or GIF.
6. Write `bursts.json` and `bursts.md`; originals are never modified.

## Command

```powershell
python scripts\burst-detect.py `
  --input "C:\photos" `
  --output-dir "C:\photos\bursts" `
  --stack --animate
```

Default behavior is grouping + best frame only. Pixel outputs require explicit
flags.

Useful options:

| Option | Default | Meaning |
| --- | --- | --- |
| `--min-frames` | 3 | Minimum frames in a burst |
| `--gap` | 1.5 | Max seconds between adjacent frames |
| `--hash-distance` | 14 | Max perceptual-hash Hamming distance |
| `--stack` | off | Write a stacked JPEG |
| `--stack-mode` | median | `median`, `mean`, or `fusion` |
| `--force-stack` | off | Stack even when motion is detected |
| `--motion-threshold` | 0.05 | Changed-pixel fraction that marks motion |
| `--animate` | off | Write an animated file |
| `--animate-format` | webp | `webp` (smaller) or `gif` |
| `--max-animate-frames` | 24 | Frame cap |
| `--max-width` | 1280 | Animation width cap |
| `--fps` | 10 | Fallback speed when times are missing |
| `--dry-run` | off | Group and report without writing |

## Outputs

```text
bursts/
  bursts.json
  bursts.md
  burst-001-stack.jpg     # only with --stack
  burst-001.webp          # only with --animate (or .gif)
```

The JSON records the frames, start/end time, best frame, stack/animation paths,
and notes. The original files stay where they are.

## Detection rules

- EXIF `DateTimeOriginal` when available; Pillow for raster files;
- optional `exiftool` fallback for RAW files (recommended);
- filename timestamp fallback (`IMG_YYYYMMDD_HHMMSS`);
- filesystem mtime as the last resort;
- same camera model/dimensions and a perceptual-hash similarity guard, so two
  unrelated photos taken one second apart do not become a burst.

RAW files can be grouped from metadata, but stacking/animation needs a
decodable raster. Render RAW first, or use the main pipeline's JPG output.

## Stacking caveats

- **Static scenes / night**: median or mean reduces noise; alignment is
  translation/euclidean ECC on a downscaled proxy.
- **People/portraits**: moving subjects ghost under median/mean. The tool
  measures aligned frame differences and skips the stack above
  `--motion-threshold` (default 5% changed pixels); use best-frame or animation,
  or pass `--force-stack` if you really want the ghosted version.
- **Exposure fusion** needs exposure diversity; if the burst is flat, the tool
  falls back to mean and records that in the report.
- Cropping removes a small border after alignment.

## Animation caveats

- Frames are aligned, cropped to a common area, and resized to `--max-width`.
- WebP is preferred; GIF is larger and has a 256-color palette.
- Long bursts are sampled to `--max-animate-frames`.
- This is an animated still image, not a Live Photo or video with audio.
- Output size grows with frame count and dimensions; generate only on request.

## Open-source stack

- Pillow: image I/O, WebP/GIF animation;
- OpenCV: ECC alignment, median/mean/Mertens fusion, Laplacian sharpness;
- exiftool: optional RAW metadata fallback;
- ffmpeg: optional, not required by this script.

No cloud API, account, or paid service is used.
