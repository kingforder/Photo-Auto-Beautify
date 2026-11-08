---
name: photo-auto-beautify
description: Local, free batch photo beautification: no uploads, no subscription; triage, scene-aware color, portrait and style presets, culling, and mainstream formats; one command per batch, originals preserved.
license: 0BSD
---

# Photo Auto Beautify

Turn a folder of originals into deliverable results: triage first, then either
beautify, produce a fixed candidate, or suggest only. The default is the high
look; originals are never modified; only originals and results remain.

## Capability map

| Area | Status | Notes |
| --- | --- | --- |
| Triage | Stable | Normal / obvious problem / suspect; whole-frame blur is flagged separately |
| Exposure and color | Stable | Auto white balance, exposure, highlights/shadows, contrast, saturation; four strengths |
| Scene awareness | Rule-based | Portrait, night, high-key, landscape, general; picks a preset per scene |
| Portrait | Conservative | Light base + global skin-tone LUT; no face mask, smoothing, or local whitening |
| Styles | Extensible | B&W, dehaze, night, food; more looks can be added |
| Culling | Stable | Blur, exposure outliers, near-duplicates; reports only, never deletes |
| Bursts | Optional | Group by time/camera/hash, pick best, optional stack or animated WebP/GIF; non-destructive |
| Formats | Broad | RAW, JPEG, PNG, TIFF, WebP, AVIF, HEIC/HEIF, JXL, BMP, GIF |
| Delivery | Stable | Original protection, consistent naming, fixed-candidate confirmation, cleanup |
| Extensibility | Design goal | New scenes, styles and detectors plug in through scripts/config |

## Roadmap (not a commitment)

- **Perspective and lens**: vertical correction for architecture, distortion, vignetting, chromatic aberration.
- **HDR and bracketing**: deghosting and advanced exposure fusion beyond the optional burst stack.
- **Restoration and enhancement**: old-photo repair, upscaling, denoising, scratch removal.
- **Subject and background**: portrait/product segmentation, background replacement, blur.
- **Semantic scenes**: finer recognition of food, real estate, events, stage, street.
- **Delivery tools**: watermarks, batch rename, metadata, contact sheets, multi-size export.

These directions do not change the current principles: **originals preserved,
results traceable, anomalies surfaced first**. Availability depends on the actual
scripts and references.

## Default policy

| Class | Action |
| --- | --- |
| Normal | High beauty by default; `min`/`medium`/`max` when the user asks |
| Obvious problem | Keep the original, write a `<name>-fixed.jpg` candidate, then ask |
| Suspect | Suggestions only; no file |
| Obvious but unrepairable | Whole-frame blur etc.; recommend a reshoot or focus check |

Output naming:

- Normal RAW → `<name>.jpg` (same name as the RAW)
- Other normal formats → `<name>-beauty.jpg`
- Obvious problem → `<name>-fixed.jpg`
- Final state: originals + beauty files + fixed candidates only; previews/temp removed

**Originals are never overwritten by default.** Only when the user explicitly
insists and accepts the irreversible result should you add
`--overwrite-originals`:

- normal JPG/JPEG only, written back in place;
- RAW stays untouched and still produces `<name>.jpg`;
- PNG/WebP/HEIC/JXL still produce `-beauty.jpg` and are never overwritten;
- `*-fixed.jpg` remains a candidate and is never auto-applied;
- back up first; never enable it by default.

## Quick start

```powershell
python scripts\photo-pipeline.py `
  --input "C:\photos" --output-dir "C:\photos" `
  --strength high `
  --report "C:\photos\pipeline-report.md"
```

- `--dry-run`: plan only;
- `--temp-dir`: writable temp folder for restricted environments;
- `--overwrite-originals`: dangerous, JPG/JPEG only, explicit user request only;
- read the report and confirm `*-fixed.jpg` before keeping it.

Optional burst pass (separate, non-destructive):

```powershell
python scripts\burst-detect.py `
  --input "C:\photos" --output-dir "C:\photos\bursts" `
  --stack --animate
```

The default only groups bursts and picks the best frame; add `--stack` and/or
`--animate` explicitly. Best frames are copied to `bursts/best/` by default;
`--best-per-burst N` keeps more than one. `--apply-cleanup` is opt-in and moves
only the remaining burst RAW files to `<input>/待删除`; selected best files stay
in place and nothing is deleted automatically.

For RAW files, metadata can come from the original RAW while pixels come from
rendered JPGs with the same stem:

```powershell
python scripts\burst-detect.py `
  --input "C:\photos" --raster-dir "C:\photos\beauty-out" `
  --output-dir "C:\photos\bursts" --stack --animate
```

For selected groups, render RAW at higher resolution and stack:

```powershell
python scripts\burst-hires.py `
  --input "C:\photos" --bursts "C:\photos\bursts\bursts.json" `
  --output-dir "C:\photos\bursts-hires" `
  --rt-root "C:\path\to\RawTherapee" --temp-dir "C:\temp\burst-hires"
```

`--temp-dir` must be an ASCII path; RawTherapee can fail to save under some
non-ASCII temp locations. High-resolution stacking is for static scenes; moving
sun/highlights or people are better served by best-frame/animation.

On Linux/WSL, run `bash scripts/setup-rt.sh` first and use `python3`; the pipeline
auto-detects the extracted AppImage under `rt-5.13/squashfs-root`. On macOS the
same Python flow is expected but not yet verified.

## Platforms

| Platform | Status | Notes |
| --- | --- | --- |
| Windows 10/11 | Verified | PowerShell setup, portable RT |
| Linux / WSL2 | Verified | AppImage extraction, no FUSE required |
| WSL1 | Expected | Same userland flow as Linux; not tested here |
| macOS | Expected | Python flow should work; RT build not yet verified |

## Scenes and styles

- Scenes: `portrait`, `night`, `highkey`, `landscape`, `general`;
- Strength: `min` natural, `medium` balanced, `high` default punchy for general
  scenes, `max` extra (intentionally allowed to overdo it);
- Portraits use a light base look followed by a **global skin-tone LUT**;
  there is no face mask, smoothing, or local whitening in the default path;
- The LUT is color-based and smooth; face, neck and hands share the same skin tone;
- If detected face saturation is already high, a neutral portrait base is used;
- `max` uses a stronger color-safe portrait base, still without masks;
- Styles: B&W, light/strong dehaze, night, food; looks live in `assets/looks/`;
- The main pipeline only applies the scene look; B&W/dehaze are invoked
  separately through `rt-batch.ps1` or the look profiles and are not mixed in;
- B&W/dehaze use `-ProfileOnly` to avoid a second tone-curve pass.

## Boundaries

- No face reshaping, face swap, sky replacement, or generative rewriting;
- Clipped highlights, crushed blacks, and severe blur cannot be invented;
- Burst stacking can ghost moving people; use best-frame or animation for those;
- Scene detection is rule-based, not semantic understanding;
- Detailed limits live in `references/`.

## References

- `references/limits.md`: tested strength limits and decision matrix
- `references/portrait.md`: portrait capabilities and limits
- `references/bursts.md`: burst grouping, stacking, animation, and limits
- `references/styles.md`: B&W, dehaze, night, food
- `references/formats.md`: input formats and dependencies
- `scripts/photo-pipeline.py`: main pipeline
- `scripts/burst-detect.py`: optional burst grouping/stack/animation
- `scripts/burst-hires.py`: optional high-resolution RAW stack
- `scripts/setup-rt.sh`: Linux/WSL RawTherapee setup
- `requirements.txt`: Python dependencies for Linux/macOS
- `LICENSE` / `THIRD_PARTY_NOTICES.md`: 0BSD and third-party licenses
