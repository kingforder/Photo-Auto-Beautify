# Tested limits of one-click beauty

Test set: 39 Panasonic RW2 files + 8 JPG files, RawTherapee 5.13,
Auto-Matched Curve plus four look levels. Measurements below use the original
camera-match / look2 / look3 / look4 profiles; `look1` (the new `min` level) is a
lighter profile and was not part of that 47-image run.

## Levels

| Level | Profile | Intent |
| --- | --- | --- |
| `min` | `rt-look1.pp3` | Natural, light touch |
| `medium` | `rt-look2.pp3` | Balanced |
| `high` (camera/default) | `rt-look3.pp3` | Punchy, social-ready |
| `max` | `rt-look4.pp3` | Extra; intentionally allowed to overdo it |

> Source-aware default: phone → `medium`, camera → `high`, unknown → `medium`.
> `--strength` forces one level for all photos; `--phone-strength min|medium`
> lowers the phone level further.
>
> Naming change: the previous `max` level (look3) is now `high`; `max` selects
> look4, the extra over-the-top level.
>
> Portrait `high` uses the light `rt-portrait-light.pp3` (Contrast 10 /
> Saturation 2), followed by a mask-free global skin-tone LUT. The LUT amount is
> 1.0 at `high`, 0.65 at `medium`, 0.35 at `min`, and 1.15 at `max`; phone/medium
> therefore gets a gentler portrait than camera/high. `max` also uses the
> stronger `rt-look2-portrait.pp3`. If the detected face saturation is already
> high, neutral-saturation variants are used.

## Measured reference

| Metric | Camera match | look2 | look3 | look4 |
| --- | ---: | ---: | ---: | ---: |
| Mean saturation (47 images) | 22.8% | 28.6% | 31.9% | — |

```text
camera → look2: mean +5.8 (range +1.9 to +9.6)
look2 → look3: mean +3.2 (range +1.1 to +5.5)  ← diminishing returns
```

## By scene (saturation %)

| Scene | Camera | look2 | look3 | look4 |
| --- | ---: | ---: | ---: | ---: |
| Normal city P1021913 | 32.1 | 41.1 | 46.4 | 54.8 |
| Sunset silhouette P1021648 | 36.6 | 43.4 | 47.0 | 52.7 |
| Night P1021774 | 25.8 | 31.8 | 35.3 | 41.1 |
| Overexposed P1021922 | 2.5 | 5.0 | 6.5 | 9.2 |
| Saturated red flower P1022126 | 70.6 | 78.6 | 82.2 | 87.2 |

Red-flower channel clipping: camera 0.6% → look2 4.2% → look3 7.1% → look4 11.9%.

Near-white pixels in the overexposed frame: camera 57.6% → look2 53.9% → look3
51.0% → look4 49.6%; still unusable.

## Limits

**Lower bound = camera match**

- JPG input barely changes (P1021642 saturation 15.0 → 14.8);
- RAW restores camera color but adds little creative intent.

**Camera default `high` (look3)**

- Chosen for a punchy, social-ready look, not for documentary realism;
- Already saturated subjects may lose channel detail; use `medium` when the
  scene should stay natural;
- Phone images default to `medium` (look2) instead of this level;
- It is intentionally stronger than the old default (`look2`).

**Safe upper bound = before channels start clipping**

- Low-saturation scenes (overcast, city, fog) can take look3;
- Already-saturated subjects (red flowers, neon, skin) start losing channel
  detail at look2/look3;
- `max` (look4) is visibly over-saturated and may clip; it exists because some
  users explicitly want the exaggerated result.

**Absolute limits**

- Overexposure/crushed blacks cannot be recovered: P1021922 stays ≥51% near-white
  at every level;
- Silhouettes, night scenes and strong backlight need human intent; global auto
  averages them out;
- JPG already compressed dynamic range and clips earlier than RAW;
- Resolution/detail never increases; only tone and color change.

## Decision matrix

| Scene | Recommendation |
| --- | --- |
| Camera photo, normal daylight/city | `high` (automatic) |
| Phone photo | `medium` (automatic); `--phone-strength min` for a lighter portrait |
| Source metadata missing | `medium` (automatic, conservative); use `--source camera` or `--source phone` when known |
| Normal daylight, city, overcast | `high` default; `medium` for a natural look |
| Sunset/night/silhouette | `medium` or `high`; keep the mood; do not lift shadows |
| Flowers/neon/skin | `min` or `medium`; check channel clipping first |
| Over/under-exposed | Do not auto-fix; correct exposure manually |
| JPG input | `medium`/`high`; `max` clips highlights more easily |
| User says "just make it beautiful" | `high`; `max` only when they accept an overdone look |

## Rules of use

1. Check first, choose a level second; anomalies are reported, not auto-fixed.
2. Run 1–3 samples before a batch and confirm saturated subjects survive.
3. Use a new suffix per batch and keep the previous version for comparison.
4. State clearly in the report which looks are scene-intent (bright sky, night,
   silhouette) and which are exposure anomalies.
