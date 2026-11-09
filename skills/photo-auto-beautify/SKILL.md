---
name: photo-auto-beautify
description: Agent Skill for local, free batch photo beautification. Import it into an AI agent; the agent adapts presets, levels, and burst cleanup to the user's taste and runs the local scripts. Triage, source-aware levels, scene-aware color, denoise/sharpness, low-risk finishing, portraits, bursts, culling, mainstream formats; originals preserved.
license: 0BSD
---

# Photo Auto Beautify

> **This is an Agent Skill, not a command-line manual.**
>
> Import it into an agent. The agent should understand the user's preferences,
> choose/adjust the beauty level and options, and run the scripts internally.
> The CLI examples below are implementation details for the agent (and for
> auditing/debugging), not instructions the end user should have to memorize.

Turn a folder of originals into deliverable results: triage first, then either
beautify, produce a fixed candidate, or suggest only. Levels are source-aware by
default: phone images use balanced/low beauty, camera images use the high look;
originals are never modified; only originals and results remain.

## How the agent should use this Skill

1. **Translate intent, not flags.** “自然一点 / 不要假白 / 皮肤白一点 /
   保留眼镜阴影 / 连拍只留最好的” are preferences. Choose the closest
   strength, portrait base, LUT behavior, burst mode, and cleanup policy.
2. **Inspect before deciding.** Read the triage report, source counts, and scene
   counts; do not blindly apply the same level to portraits, night, landscape,
   and bursts.
3. **Stay inside the documented boundaries.** The agent may tune levels,
   profiles, burst thresholds, and cleanup choices, but must not invent face
   reshaping, sky replacement, or generative edits.
4. **Confirm destructive choices.** Moving originals to `待删除` requires
   explicit user approval; never silently delete or overwrite originals.
5. **Explain the tradeoff briefly.** For example: “更白但可能损失阴影” or
   “这组有人物走动，堆叠会鬼影，建议用动图/最佳帧”.

The agent can adjust:

| User preference | Agent action |
| --- | --- |
| “自然一点 / 不要假白” | Prefer lower portrait base / neutral look; keep shadows |
| “脸再白一点” | Adjust portrait whitening/LUT strength within safe limits |
| “照片发灰 / 颜色闷” | Keep `--vibrance auto` or use `light`; do not add global saturation first |
| “高光太硬 / 天空刺眼” | Keep `--highlight-rolloff auto`; explain that clipped detail cannot be recovered |
| “明显偏绿 / 偏黄” | Keep `--wb auto`; do not neutralize a deliberately warm sunset |
| “手机拍的别修太重 / 相机片保留质感” | Keep `--strength auto`; phone uses `--phone-strength min` (default), camera uses high; override `--source` only when EXIF is missing or wrong |
| “噪点太多 / 高感太重” | Enable `--denoise light` (or `medium`); inspect flat areas before using `strong` |
| “锐一点 / 提升锐度” | Use `--sharpen light` (or `medium`); explain that this raises edge acutance, not true detail |
| “连拍只留最好的” | Keep 1 best frame per burst (default; max 2), verify, then cleanup |
| “不要动原片” | Skip `--apply-cleanup`; keep best frames in place |
| “要动图 / 不要堆叠” | Enable animation, skip stack; respect motion guards |
| “这组是风景/夜景” | Use the matching scene look; do not force portrait treatment |

## Capability map

| Area | Status | Notes |
| --- | --- | --- |
| Triage | Stable | Normal / obvious problem / suspect; whole-frame blur is flagged separately |
| Exposure and color | Stable | Auto white balance, exposure, highlights/shadows, contrast, saturation; auto level by source plus four explicit strengths |
| Source awareness | Rule-based | EXIF Make/Model → phone / camera / unknown; phone min, camera high, unknown medium |
| Scene awareness | Rule-based | Portrait, night, high-key, landscape, general; picks a preset per scene |
| Portrait | Conservative | Light base + global skin-tone LUT; no face mask, smoothing, or local whitening |
| Detail | Optional | Conservative denoise and output sharpening; auto by source/ISO, explicit light/medium/strong |
| Finishing | Conservative | Capped neutral WB, neutral-guarded vibrance, gentle highlight rolloff; no style conversion |
| Styles | Extensible | B&W, dehaze, night, food; more looks can be added |
| Culling | Stable | Blur, exposure outliers, near-duplicates; reports only, never deletes |
| Bursts | Optional | Preprocess first: group, best, stack/animation, optional cleanup; beauty retained outputs after |
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
| Normal | Source-aware: phone min, camera high, unknown medium; `--strength` forces one level |
| Obvious problem | Keep the original, write a `<name>-fixed.jpg` candidate, then ask |
| Suspect | Suggestions only; no file |
| Obvious but unrepairable | Whole-frame blur etc.; recommend a reshoot or focus check |

### Source-aware levels

Source is inferred from EXIF `Make`/`Model`; no filename guessing. The default
`--strength auto` maps it like this:

| Source | Default level | Portrait treatment |
| --- | --- | --- |
| Phone | `min` (default; use `--phone-strength medium` for more) | Light base + 0.35 LUT (0.65 for `medium`) |
| Camera | `high` | Light base + 1.0 LUT |
| Unknown | `medium` | Conservative; avoids over-processing stripped files |

- `--strength min|medium|high|max` forces that level for every photo, including
  phones; use it when the user explicitly asks for one look.
- `--source phone|camera|unknown` overrides detection, for example a camera RAW
  with stripped metadata or a phone file that reports an unusual make.
- RAW source detection uses ExifTool when Pillow cannot read the metadata;
  without ExifTool those RAW files fall back to `unknown` (medium).
- Camera high is the original punchy look; phone min is deliberately restrained,
  especially for portraits. Unknown medium is the safe default when provenance
  cannot be established.

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
  --report "C:\photos\pipeline-report.md"
```

- `--strength auto` is the default: phone → min, camera → high, unknown → medium;
- `--phone-strength min|medium`: phone level (default `min`; `medium` for more);
- `--source auto|phone|camera|unknown`: override EXIF source detection;
- `--denoise auto|off|light|medium|strong`: noise reduction; auto is conservative;
- `--sharpen auto|off|light|medium|strong`: output sharpening; auto is camera light;
- `--wb auto|off`, `--vibrance auto|off|light|medium`, `--highlight-rolloff auto|off|light|medium`: low-risk finishing;
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

The default only groups bursts and picks **one** best frame; add `--stack` and/or
`--animate` explicitly. Best frames stay in the original input folder (no
separate copy folder). `--best-per-burst` accepts only `1` (default) or `2`:
keep a second frame only when it is a clearly different keeper (expression,
pose, or moment), never just to preserve extra coverage. Invalid/suspect frames
are skipped when valid alternatives exist. `--apply-cleanup` is opt-in and
moves only the remaining burst RAW files to `<input>/待删除`; the selected best
files stay in place. Cleanup is skipped for a group if its best frames cannot
be verified in the input folder. Generated stack JPGs have no reliable EXIF;
when beautifying them, pass `--source camera` or `--source phone` explicitly.

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

## Burst-first workflow

For a folder that contains bursts, preprocess before the beauty pass:

1. Detect/group bursts and select one best frame (at most two, and only for a
   clearly distinct second keeper).
2. Decide stack **or** animation from motion/highlight checks.
3. Optionally verify best frames and move remaining burst RAW to `待删除`.
4. Apply beauty to every retained output: best RAW, stack JPG, animation, and
   non-burst originals.

Best frames stay in the original folder. Cleanup is a paired operation: never
move non-best frames if the best frames cannot be verified in place. Full
details: `references/workflow.md`.

## Scenes and styles

- Scenes: `portrait`, `night`, `highkey`, `landscape`, `general`;
- Strength: `auto` by source by default (phone `min`, camera `high`, unknown
  `medium`); `--strength` forces `min`/`medium`/`high`/`max` for all;
- Portraits use a light base look followed by a **global skin-tone LUT**;
  there is no face mask, smoothing, or local whitening in the default path;
- The LUT is color-based and smooth; face, neck and hands share the same skin tone;
- LUT amount scales with level: `min` 0.35, `medium` 0.65, `high` 1.0, `max` 1.15;
  so a phone/min portrait is visibly gentler than a camera/high portrait;
- If detected face saturation is already high, a neutral portrait base is used;
- `max` uses a stronger color-safe portrait base, still without masks;
- Styles: B&W, light/strong dehaze, night, food; looks live in `assets/looks/`;
- The main pipeline only applies the scene look; B&W/dehaze are invoked
  separately through `rt-batch.ps1` or the look profiles and are not mixed in;
- B&W/dehaze use `-ProfileOnly` to avoid a second tone-curve pass.

## Noise and sharpness

Two different operations:

- **Denoise** suppresses luminance/chroma noise. It always trades away some
  texture; the stronger the setting, the more detail is smoothed.
- **Sharpening / 锐度** raises edge acutance — local contrast at edges. It looks
  sharper but does not add real detail, cannot recover missed focus or motion
  blur, and overdoing it creates halos and crunchy skin.

Default `--denoise auto` / `--sharpen auto`:

| Source | Denoise | Sharpen |
| --- | --- | --- |
| Phone | off below ISO 800; `light` 800–3199; `medium` 3200+ | off (phone JPEGs are already sharpened) |
| Camera | off below ISO 1600; `light` 1600–6399; `medium` 6400+ | `light` |
| Unknown | `light` only at ISO 3200+ | off |

- `--denoise off|light|medium|strong` and `--sharpen off|light|medium|strong`
  override auto; `strong` is deliberately explicit and should be checked at 100%.
- Denoise runs before sharpening, so a noisy high-ISO image is not just
  sharpened noise.
- For portraits, stay at `light` unless the user asks otherwise; `medium` or
  `strong` can emphasize pores and skin texture.
- Use `--denoise off --sharpen off` for a strictly natural documentary result.
- These controls cannot invent detail: a blurry or out-of-focus frame stays
  blurry. Do not promise “resolution enhancement”.

## Finishing

Three low-risk finishing controls run after the RawTherapee render and portrait
LUT. All are global; none is a style conversion.

| Option | Default | What it does |
| --- | --- | --- |
| `--wb auto|off` | `auto` | Corrects only a small, confident cast from near-neutral pixels; capped at 2 LAB units |
| `--vibrance auto|off|light|medium` | `auto` (`light`) | Lifts muted colors while protecting skin and near-neutral pixels |
| `--highlight-rolloff auto|off|light|medium` | `auto` (`light`) | Softens the shoulder into near-white |

- `--wb auto` skips images without enough neutral pixels; it must not neutralize
  a deliberately warm sunset or colored wall.
- Vibrance has a neutral guard so clouds/walls do not turn pink, and a skin guard
  so faces do not go orange. Global saturation is not increased further.
- Highlight rolloff is not highlight reconstruction; clipped detail stays
  clipped. It only makes the transition into white less harsh.
- Use `off` for any control when the user wants a strictly untouched color
  response. `medium` is available but should be checked at 100%.
- Style packs, film simulation, duotone, sky replacement, and generative edits
  are **not** part of this pass; a style change requires an explicit user
  decision and a separate request.

## Boundaries

- No face reshaping, face swap, sky replacement, or generative rewriting;
- Clipped highlights, crushed blacks, and severe blur cannot be invented;
- Sharpening cannot recover missed focus or motion blur; denoise trades texture for noise removal;
- Burst stacking can ghost moving people; use best-frame or animation for those;
- Scene detection is rule-based, not semantic understanding;
- Detailed limits live in `references/`.

## References

- `references/limits.md`: tested strength limits and decision matrix
- `references/detail.md`: denoise, sharpness/acutance, and their limits
- `references/finishing.md`: WB, vibrance, highlight rolloff, and style boundaries
- `references/portrait.md`: portrait capabilities and limits
- `references/bursts.md`: burst grouping, stacking, animation, and limits
- `references/workflow.md`: burst-first preprocessing then beauty order
- `references/styles.md`: B&W, dehaze, night, food
- `references/formats.md`: input formats and dependencies
- `scripts/photo-pipeline.py`: main pipeline
- `scripts/burst-detect.py`: optional burst grouping/stack/animation
- `scripts/burst-hires.py`: optional high-resolution RAW stack
- `scripts/burst-animate-beautify.py`: frame-level beauty for neutral animations
- `scripts/setup-rt.sh`: Linux/WSL RawTherapee setup
- `requirements.txt`: Python dependencies for Linux/macOS
- `LICENSE` / `THIRD_PARTY_NOTICES.md`: 0BSD and third-party licenses
