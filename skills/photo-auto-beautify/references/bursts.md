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
| `--input` | required | Folder of originals |
| `--raster-dir` | off | Matching rendered JPGs for RAW pixels (same stem) |
| `--min-frames` | 3 | Minimum frames in a burst |
| `--gap` | 1.5 | Max seconds between adjacent frames |
| `--hash-distance` | 14 | Max perceptual-hash Hamming distance |
| `--stack` | off | Write a stacked JPEG |
| `--stack-mode` | median | `median`, `mean`, or `fusion` |
| `--force-stack` | off | Stack even when motion is detected |
| `--motion-threshold` | 0.08 | Changed-pixel fraction that marks motion |
| `--highlight-threshold` | 0.09 | Changed bright-pixel fraction that marks moving highlights |
| `--animate` | off | Write an animated file |
| `--animate-format` | webp | `webp` (smaller) or `gif` |
| `--max-animate-frames` | 24 | Frame cap |
| `--max-width` | 1280 | Animation width cap |
| `--fps` | 10 | Fallback speed when times are missing |
| `--best-per-burst` | 1 | Best RAW frames copied per burst |
| `--no-save-best` | off | Do not copy best frames |
| `--apply-cleanup` | off | Move non-best burst RAW files to the trash folder |
| `--trash-dir` | `<input>/待删除` | Destination for cleanup |
| `--dry-run` | off | Group and report without writing |

## Outputs

```text
bursts/
  bursts.json
  bursts.md
  best/                         # copies of selected best frames
    burst-001-best-1-P102....RW2
  burst-001-stack.jpg           # only with --stack
  burst-001.webp                # only with --animate (or .gif)
```

The JSON records the frames, start/end time, best frame(s), stack/animation paths,
and cleanup results. The original files stay where they are unless
`--apply-cleanup` is explicitly used.

`--apply-cleanup` is intentionally opt-in:

- selected best frames are copied to `bursts/best/` and stay in place; only
  frames with valid image metrics are eligible when valid alternatives exist;
- the remaining **burst RAW** files are moved to `<input>/待删除`;
- non-burst RAW files are not touched;
- no file is deleted; review the trash folder and remove it yourself;
- run once with `--dry-run --apply-cleanup` to see the plan first.

## Detection rules

- EXIF `DateTimeOriginal` when available; Pillow for raster files;
- optional `exiftool` fallback for RAW files (recommended);
- filename timestamp fallback (`IMG_YYYYMMDD_HHMMSS`);
- filesystem mtime as the last resort;
- same camera model/dimensions and a perceptual-hash similarity guard, so two
  unrelated photos taken one second apart do not become a burst.

RAW files can be grouped from metadata, but stacking/animation needs a
decodable raster. Render RAW first, or use `--raster-dir` with the beauty JPGs
(same stem); metadata still comes from the original RAW.

For RAW bursts, install open-source `exiftool`; without it the tool falls back
to filename/mtime, and copied RAW files may have copy time instead of capture
time.

## Stacking caveats

- **Static scenes / night**: median or mean reduces noise; alignment is
  translation/euclidean ECC on a downscaled proxy.
- **People/portraits**: moving subjects ghost under median/mean. The tool
  measures aligned frame differences and skips the stack above
  `--motion-threshold` (default 8% changed pixels); use best-frame or animation,
  or pass `--force-stack` if you really want the ghosted version.
- **Exposure fusion** needs exposure diversity; if the burst is flat, the tool
  falls back to mean and records that in the report.
- Cropping removes a small border after alignment.

## High-resolution RAW stacks

`burst-hires.py` reads a `bursts.json`, renders the selected RAW frames through
RawTherapee with the same look profile, downsizes only to a safe working size,
aligns and median-stacks them.

```powershell
python scripts\burst-hires.py `
  --input "C:\photos" `
  --bursts "C:\photos\bursts\bursts.json" `
  --output-dir "C:\photos\bursts-hires" `
  --rt-root "C:\path\to\RawTherapee" `
  --temp-dir "C:\temp\burst-hires" `
  --max-side 3000
```

- `--temp-dir` should be ASCII; RawTherapee may fail to save to non-ASCII temp
  paths.
- Default look is `rt-look3.pp3`; override with `--look-profile`.
- Selected groups are stacked with `median`, even if motion was detected; use
  this only for groups that were marked stackable.
- **Moving sun/highlights**: the tool measures changed bright pixels and skips
  the stack above `--highlight-threshold` (default 9%); use best-frame/animation,
  or `--force-stack` for a deliberately ghosted/median version.
- For those groups, compare the stack with the best frame and prefer best-frame.

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
