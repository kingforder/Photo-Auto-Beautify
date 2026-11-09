# Denoise and sharpness

These are separate controls with different tradeoffs.

## Definitions

**Denoise / noise reduction** suppresses luminance and chroma noise. It cannot
know which variation is noise and which is fine texture, so every increase in
strength also removes some real detail. It is most useful on high-ISO photos and
small-sensor phone images.

**Sharpness / 锐度** in photography usually means **acutance**: local contrast at
edges. Sharpening makes edges look crisper but does not add real resolution. It
cannot recover missed focus, motion blur, diffraction, or compression loss, and
too much produces halos, crunchy skin, and halos around high-contrast edges.

## Defaults

`photo-pipeline.py` uses `--denoise auto` and `--sharpen auto`:

| Source | Denoise | Sharpen |
| --- | --- | --- |
| Phone | off below ISO 800; `light` at 800–3199; `medium` at 3200+ | off (phone JPEGs are already sharpened) |
| Camera | off below ISO 1600; `light` at 1600–6399; `medium` at 6400+ | `light` |
| Unknown | `light` only at ISO 3200+ | off |

Rationale: phone images are often already denoised/sharpened by the camera app,
so a second aggressive pass looks artificial. Camera output usually benefits
from a light output sharpening after RawTherapee's rendering.

## Controls

```powershell
python scripts\photo-pipeline.py `
  --input "C:\photos" --output-dir "C:\photos\beauty" `
  --denoise light --sharpen light
```

| Option | Values | Meaning |
| --- | --- | --- |
| `--denoise` | `auto`, `off`, `light`, `medium`, `strong` | Luminance/chroma noise reduction |
| `--sharpen` | `auto`, `off`, `light`, `medium`, `strong` | Unsharp-mask output sharpening |

`auto` is resolved per photo from source and EXIF ISO. An explicit value applies
to every photo in the run. `--denoise strong --sharpen strong` is allowed but
rarely appropriate; inspect at 100% before keeping it.

These flags apply to `photo-pipeline.py`, including stack JPGs processed through
it. `burst-animate-beautify.py` still applies only a look profile; it does not
run denoise or output sharpening.

## Profiles

| Profile | Intent |
| --- | --- |
| `rt-denoise-light.pp3` | Mild luminance noise reduction, minimal texture loss |
| `rt-denoise-medium.pp3` | Visible noise reduction for high-ISO images |
| `rt-denoise-strong.pp3` | Strong smoothing; use only on genuinely noisy files |
| `rt-sharpen-light.pp3` | Subtle output sharpening with halo control |
| `rt-sharpen-medium.pp3` | Clearly crisper edges; watch halos and skin |
| `rt-sharpen-strong.pp3` | Deliberate crunchy look; not a default |

Denoise is applied before sharpening. For portraits, `light` is the safe
default; `strong` denoise plus `strong` sharpening can produce plastic skin.

## Limits

- Sharpening cannot fix out-of-focus or motion-blurred frames;
- Denoising cannot recover detail already lost to noise or compression;
- JPEG input has less headroom than RAW; strong sharpening clips and rings sooner;
- Night/high-ISO images may need denoise but should keep their mood; do not push
  shadow detail just to make noise visible;
- Always compare at 100% on a flat area and an edge before batching.

## Related

- `references/limits.md`: overall strength/decision matrix;
- `references/portrait.md`: portrait-specific treatment;
- `SKILL.md`: agent-facing defaults and preference mapping.
