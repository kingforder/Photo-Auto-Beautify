# Portrait color pipeline

The default pipeline is deliberately mask-free:

- a light portrait base look;
- a global skin-tone LUT that lifts skin-like colors smoothly;
- no face mask, no skin smoothing, no local whitening.

Because the transform is color-based and continuous, there are no cutout edges
or pixel-level transition artifacts. Face, neck and hands share the same skin
tone, so they stay consistent.

The LUT amount follows the effective level: `min` 0.35, `medium` 0.65,
`high` 1.0, `max` 1.15. With the default `--strength auto`, phone portraits use
`min` (0.35, deliberately light), camera portraits use `high` (the original
portrait look), and unknown sources use `medium` conservatively.
`--phone-strength medium` makes phone portraits a step stronger; `--strength`
forces one level for every photo.

Output sharpening is independent of the LUT. Camera portraits get `light` by
default; phone portraits get none because phone JPEGs are already sharpened.
Avoid `medium`/`strong` sharpening on skin unless the user explicitly wants a
crunchier look — it emphasizes pores and can create halos.

## Legacy face-beautify module (optional, not used by default)

The old mask-based module below remains available for experiments (`face-beautify.py`),
but the default pipeline does not call it.

Conservative by design: skin smoothing plus slight sclera/teeth brightening.
**No face reshaping, no identity changes, no generated content.**

## Capabilities

- Detect faces with OpenCV YuNet (five landmarks: eyes, nose, mouth corners);
- Downscale large images to 1600 px for detection, then map boxes back to avoid
  duplicate/false boxes;
- Build an elliptical face mask that excludes eyes, eyebrows and lips;
- Smooth skin with a bilateral filter while retaining 18% of the original
  micro-texture to avoid a plastic look;
- Lift skin luminance and pull red/yellow toward neutral inside the face mask,
  for a brighter, less sallow complexion;
- Whitening is weighted by luminance: eye sockets and shadowed skin under
  glasses stay dark instead of turning into gray patches;
- Reduce lip redness slightly so a whitened face does not look unbalanced;
- Optionally brighten low-saturation, bright sclera/teeth regions slightly;
- Skip images with zero usable faces and note them in the report;
- Default `--min-face-ratio 0.04`: faces narrower than 4% of the frame are
  ignored to avoid smoothing bystanders or the back of a head;
- Write `-face.jpg`; the original is untouched.

## Not supported

- Removing every pore or changing skin tone/identity;
- Slimming the face, enlarging eyes, or changing expression;
- Acne/scar removal (needs local retouching or generative models);
- RAW input; render to JPG with RawTherapee first.

## Install

```powershell
$env:PYTHON = "C:\path\to\python.exe"   # optional; defaults to python
powershell -ExecutionPolicy Bypass -File scripts\setup-face.ps1
```

Dependencies: `opencv-python-headless`, `numpy`, `Pillow`; the 232 KB model lives
in `assets\models\face_detection_yunet_2023mar.onnx` and is SHA256-checked.

If pip is unavailable, unpack an OpenCV wheel into `face-deps`, or put an
existing `cv2` on `PYTHONPATH`.

## Usage

```powershell
$env:PYTHONPATH = "..\..\face-deps"

python scripts\face-beautify.py `
  --input "C:\photos\portraits" `
  --output "C:\photos\portraits\out" `
  --strength 2 `
  --report ".\face-report.md"
```

Strengths:

| Level | Skin blend | Suitable for |
| --- | ---: | --- |
| 1 | 0.35 | Natural, keeps texture; recommended for most portraits |
| 2 | 0.55 | Visible smoothing, facial edges preserved |
| 3 | 0.72 | Strong smoothing, pores mostly gone; small images/social only |

Options: `--no-eyes`, `--no-teeth`, `--dry-run` (report face counts without writing).

## Tested

On a public-domain official portrait (2687×3356):

- one face detected;
- level 1: light smoothing, skin texture retained;
- level 2: clear smoothing, eyes/brows/lips stay sharp;
- level 3: close to "airbrushed"; pores disappear and a plastic look begins.

Batch test: one portrait + one city image (no face). The portrait produced
`-face.jpg`; the city was marked `skipped: no face`; neither original changed.

On the test folder (39 RAW previews + 8 JPG):

- usable portraits: **0**;
- `P1022133`: back of a head, false positive; face width 31 px (3.4%) filtered
  by the minimum ratio;
- `P1022141`: distant profile, 21×29 px (2.3%), filtered;
- no other detections. Conclusion: that folder is not suitable for face beauty;
  use a dedicated portrait folder.

## Limits and risks

- Profiles, occlusion, group photos, backlight and low resolution reduce
  detection/mask quality;
- Deep or highlighted skin may become too pale after whitening; review samples
  and lower the strength when needed;
- Level 3 looks fake easily; default to 1–2;
- Acne, scars and under-eye structure are not handled; only global smoothing;
- Do not apply by default to news, documentary or ID photos; identity and
  authenticity are the user's decision;
- Everything is local; no face data is uploaded.

## Suggested workflow

1. Run `--dry-run` to see detection counts;
2. Pick 2–3 representative images and render levels 1/2/3;
3. Confirm the strength with the user, then batch;
4. Write `-face` outputs and keep originals;
5. List "no face / multiple faces" images in the report for manual review.
