# Tested limits of one-click beauty

Test set: 39 Panasonic RW2 files + 8 JPG files, RawTherapee 5.13,
Auto-Matched Curve plus three look levels. All numbers were measured on the same
batch; output is sRGB JPEG.

## Levels

| Level | Profile | Notes |
| --- | --- | --- |
| `-rt` | `Auto-Matched Curve - ISO Low.pp3` only | Camera JPEG emulation; almost a no-op for JPG input |
| `-rt2` | + `rt-look2.pp3`: Contrast 18 / Saturation 12 / Black -5 / Highlight 30 / Shadow 20 | General default |
| `-rt3` | + `rt-look3.pp3`: Contrast 28 / Saturation 18 / Black -8 / Highlight 40 / Shadow 30 | Upper bound for low-saturation scenes |
| `look4` | + `rt-look4.pp3`: Contrast 45 / Saturation 28 / Black -12 / Highlight 50 / Shadow 40 | Diagnostic only; deliberately excessive |

## Full 47-image set

```text
Mean saturation: rt 22.8%  →  rt2 28.6%  →  rt3 31.9%
rt→rt2: mean +5.8 (range +1.9 to +9.6)
rt2→rt3: mean +3.2 (range +1.1 to +5.5)  ← diminishing returns
```

## By scene (saturation %)

| Scene | rt | rt2 | rt3 | look4 |
| --- | ---: | ---: | ---: | ---: |
| Normal city P1021913 | 32.1 | 41.1 | 46.4 | 54.8 |
| Sunset silhouette P1021648 | 36.6 | 43.4 | 47.0 | 52.7 |
| Night P1021774 | 25.8 | 31.8 | 35.3 | 41.1 |
| Overexposed P1021922 | 2.5 | 5.0 | 6.5 | 9.2 |
| Saturated red flower P1022126 | 70.6 | 78.6 | 82.2 | 87.2 |

Red-flower channel clipping: rt 0.6% → rt2 4.2% → rt3 7.1% → look4 11.9%.

Near-white pixels in the overexposed frame: rt 57.6% → rt2 53.9% → rt3 51.0%
→ look4 49.6%; still unusable.

## Limits

**Lower bound = camera match**

- JPG input barely changes (P1021642 saturation 15.0 → 14.8);
- RAW restores camera color but adds little creative intent.

**Safe upper bound = before channels start clipping**

- Low-saturation scenes (overcast, city, fog) can take rt3;
- Already-saturated subjects (red flowers, neon, skin) start losing channel
  detail at rt2/rt3;
- look4 is visibly over-saturated; it exists to show where it breaks.

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
| Normal daylight, city, overcast | `-rt2` default; `-rt3` for low saturation |
| Sunset/night/silhouette | `-rt2` upper bound; keep the mood; do not lift shadows |
| Flowers/neon/skin | `-rt` or `-rt2`; check channel clipping first |
| Over/under-exposed | Do not auto-fix; correct exposure manually |
| JPG input | Expect small gains; look2 changes more but watch clipped whites |

## Rules of use

1. Check first, choose a level second; anomalies are reported, not auto-fixed.
2. Run 1–3 samples before a batch and confirm saturated subjects survive.
3. Use a new suffix per batch (`-rt2`/`-rt3`) and keep the previous version for comparison.
4. State clearly in the report which looks are scene-intent (bright sky, night,
   silhouette) and which are exposure anomalies.
