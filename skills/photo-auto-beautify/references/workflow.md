# Burst-first workflow

This is the required order for burst sets. Beauty must not run before burst
preprocessing.

```text
1. Detect bursts
2. Group frames
3. Select best frame(s)
4. Decide: stack OR animation
5. Optional paired cleanup
6. Beauty on every retained output
```

## 1. Preprocess

Use `burst-detect.py` first:

```powershell
python scripts\burst-detect.py `
  --input "C:\photos" `
  --raster-dir "C:\photos\rendered" `
  --output-dir "C:\photos\bursts" `
  --min-frames 3 --gap 2 `
  --best-per-burst 2 `
  --stack --animate
```

`--raster-dir` supplies decodable frames for RAW (same stem). Best frames stay
in the original input folder; they are not copied to a separate best folder.

### Decision rule

| Burst content | Keep | Output |
| --- | --- | --- |
| Static scene / city / clouds | Best frame(s) | High-resolution stack |
| People walking / cars / birds / moving sun | Best frame(s) | Animation |
| Too few valid frames | Best available | No stack/animation |

The tool also measures motion and moving highlights. A stack is skipped when
those guards trigger; the best frame and animation remain.

### Optional paired cleanup

Only with an explicit `--apply-cleanup`:

1. verify selected best frames exist in the original folder;
2. restore any staged best frame to the original folder;
3. move the remaining **burst RAW** to `<input>/待删除`;
4. leave non-burst RAW untouched;
5. if best verification fails, skip cleanup for that group.

Never move non-best frames without the corresponding best frames in place.
The trash folder is a review area, not permanent deletion.

## 2. Beauty

After preprocessing, apply the normal beauty pass to every retained image:

- **best-frame RAW** in the input folder;
- **stack JPGs** under `bursts/`;
- **animation** frames/output;
- non-burst originals in the input folder.

Best-frame RAW and non-burst originals go through `photo-pipeline.py` normally.
Stack JPGs can be processed as a separate input folder. Animations are beautified
frame-by-frame after encoding:

```powershell
python scripts\burst-animate-beautify.py `
  --input "C:\photos\bursts" `
  --output-dir "C:\photos\beauty-out\animations" `
  --rt-root "C:\path\to\RawTherapee" `
  --look-profile "rt-look3.pp3"
```

This decodes each neutral animation, renders every frame with the same look,
and re-encodes while preserving durations and loop.

The current CLI split is:

```powershell
# best RAW + non-burst originals
python scripts\photo-pipeline.py `
  --input "C:\photos" --output-dir "C:\photos\beauty-out" `
  --strength high --rt-root "C:\path\to\RawTherapee"

# stack JPGs (put them in a stacks-only folder first)
python scripts\photo-pipeline.py `
  --input "C:\photos\bursts\stacks" `
  --output-dir "C:\photos\beauty-out\stacks" `
  --strength high --rt-root "C:\path\to\RawTherapee"
```

Implementation note: the animation is encoded from the raster supplied to
`burst-detect.py` via `--raster-dir`. If the animation must be beautified, pass
neutral frames to preprocessing, then run `burst-animate-beautify.py` on the
encoded neutral animations. A single orchestrator that renders neutral frames,
preprocesses, and runs all three beauty targets in one command is not included
yet; the commands in this document are the supported composition.

## 3. What is final

Retained deliverables:

```text
best RAW (original folder)
non-burst RAW (original folder)
stack JPG(s)
animated WebP/GIF
beauty JPGs for all of the above
```

Everything else that was moved to `待删除` should not be beautified.

## 4. Safety rules

- Burst preprocessing is non-destructive by default.
- Cleanup is opt-in and only moves files to a review folder.
- Best frames must be verified in the original folder before any non-best move.
- Originals are never overwritten by the beauty pass.
- If a group has no valid raster, skip stack/animation; retain its best frame.
- Do not stack moving people/cars/birds or moving sun/highlights; use animation
  or the best frame instead.
