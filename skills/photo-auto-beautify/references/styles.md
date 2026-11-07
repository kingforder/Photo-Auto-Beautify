# Style presets and tested boundaries

Test images: CC BY-SA 4.0 samples from Wikimedia Commons (fog, architecture,
food) plus night/portrait frames from the user's test set. Local tests only; the
original images are not distributed with this skill.

## Black and white

`assets\looks\rt-bw.pp3` (our own Desaturation profile, not a copied RawTherapee
GPL profile)

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-bw" `
  -ProfileOnly -LookProfile assets\looks\rt-bw.pp3
```

- Works well for architecture, documentary and hard-light portraits;
- Bright frames may look too light; inspect one before batching;
- Do not stack it with Auto-Matched (that would add a second tone curve), hence
  `-ProfileOnly`.

## Dehaze

- `assets\looks\rt-dehaze.pp3`: Strength 55 / Depth 45 / Saturation 25, light;
- `assets\looks\rt-dehaze-strong.pp3`: Strength 85 / Depth 60 / Saturation 30, stronger.

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-dehaze" `
  -ProfileOnly -LookProfile assets\looks\rt-dehaze.pp3
```

Tested: mild on JPG fog scenes, mostly improving foreground contrast; RAW has
more headroom. The strong version darkens the sky, so sample first. Dehaze is
not sky replacement and cannot restore detail fully hidden by fog.

## Night / low light

Use a higher-ISO denoise profile, then add look2:

```powershell
powershell -File scripts\rt-batch.ps1 -InputDir $dir -Suffix "-night" `
  -IsoProfile High -LookProfile assets\looks\rt-look2.pp3
```

- Tested on a night JPG: light highlights preserved, shadow noise reduced;
- Strong denoise removes detail; use Medium for portraits/textured scenes;
- Do not add dehaze or heavy contrast to night scenes; it crushes the sky.

## Food / high-key still life

- Recommended: `-LookProfile assets\looks\rt-look2.pp3` (moderate contrast/saturation);
- **Do not use Pop 1**: tested white plates clipped immediately and highlights were lost;
- Food often needs a warmer white balance; adjust Temperature/Tint in RT rather
  than forcing a global preset.

## Architecture / perspective

- There is no reliable fully automatic CLI perspective correction yet;
  RawTherapee's GUI has Perspective → Automatic, which needs visual confirmation;
- `-ProfileOnly -LookProfile rt-look2.pp3` can handle base tone; leave perspective
  to a human;
- Lens distortion/vignetting can be handled by the LensProfile in an
  Auto-Matched profile.

## Summary

| Need | Automatable | Recommendation |
| --- | --- | --- |
| B&W | Yes | `rt-bw.pp3`, ProfileOnly |
| Dehaze | Partial | Try light first; be careful with strong |
| Night denoise | Yes | ISO High/Medium + look2 |
| Food | Partial | look2; avoid Pop 1 |
| Architecture perspective | No (visual check) | GUI/manual |
| Sky replacement/generative | No | Out of scope |
