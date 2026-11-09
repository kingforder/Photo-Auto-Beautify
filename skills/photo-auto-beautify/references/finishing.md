# Finishing: white balance, vibrance, highlight rolloff

These are the low-risk finishing steps after RawTherapee rendering and the
portrait LUT. They are deliberately subtle and global; none of them is a style
conversion.

## Defaults

| Option | Default | Effect |
| --- | --- | --- |
| `--wb` | `auto` | Corrects only a small, confident cast from near-neutral pixels |
| `--vibrance` | `auto` (`light`) | Lifts muted colors while protecting skin and near-neutral pixels |
| `--highlight-rolloff` | `auto` (`light`) | Softens the transition into near-white |

`off` disables a control. `light`/`medium` are available for vibrance and
highlight rolloff; `wb` is `auto`/`off` only.

## White balance

`neutral_white_balance()` samples low-chroma pixels (LAB chroma < 6) in the
mid-tone range and shifts `a`/`b` toward neutral only when:

- at least 2,000 neutral pixels exist;
- the measured cast is above 1 LAB unit;
- the correction is capped at 2 LAB units.

This avoids forcing a sunset, foliage, or colored wall to gray. It is a
**micro-adjustment**, not a replacement for a proper white-balance decision.

## Vibrance

`add_vibrance()` boosts saturation most in muted colors and least in already
saturated ones (`(1 - S)^2`). Two guards matter:

- **neutral guard**: almost-gray pixels (clouds, walls) get no boost, so they do
  not turn pink or cyan;
- **skin guard**: skin hues are damped to avoid orange/pink complexions.

The global look's `Saturation` is intentionally left alone; vibrance is a
separate, gentler control.

## Highlight rolloff

`highlight_rolloff()` applies a gentle shoulder above LAB `L=190` and keeps
`L=255` at white. It softens the transition into highlights; it does **not**
recover detail that was already clipped by the sensor or JPEG compression.

## Order

```text
RawTherapee render -> skin LUT (portraits) -> WB -> vibrance -> highlight rolloff
```

## Examples

```powershell
# Defaults: all three auto (light vibrance/rolloff)
python scripts\photo-pipeline.py --input "C:\photos" --output-dir "C:\photos\beauty"

# Disable finishing entirely
python scripts\photo-pipeline.py ... --wb off --vibrance off --highlight-rolloff off

# A little more color/soft highlights, still conservative
python scripts\photo-pipeline.py ... --vibrance medium --highlight-rolloff medium
```

## Boundaries

- No LUT/style packs, film emulation, duotone, sky replacement, or generative
  edits are applied automatically. Style conversion requires an explicit user
  decision and is outside this finishing pass.
- White balance should not be used to “fix” a deliberately warm sunset.
- Highlight rolloff is not highlight reconstruction.
- Strong vibrance is not offered; use a user-requested style if that is the goal.
