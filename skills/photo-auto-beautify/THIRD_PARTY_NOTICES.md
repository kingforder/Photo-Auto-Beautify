# Third-Party Notices

This repository's original code, scripts, documentation and look profiles are
released under the **0BSD** license (see `LICENSE`). Third-party components
keep their own licenses, as listed below.

## Bundled: YuNet face detection model

- File: `assets/models/face_detection_yunet_2023mar.onnx`
- Source: OpenCV Zoo, `models/face_detection_yunet`
- License: **MIT**
- Copyright: (c) 2020 Shiqi Yu <shiqi.yu@gmail.com>
- Full text: `assets/models/LICENSE`
- Upstream: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet

The model is redistributed unchanged under its MIT license. The MIT notice
must remain with the model file.

## Downloaded, not bundled: RawTherapee

- Used by: `scripts/setup-rt.ps1`, `scripts/setup-rt.sh`,
  `scripts/rt-batch.ps1`, `scripts/photo-pipeline.py`
- License: **GNU GPL v3**
- Copyright: RawTherapee contributors
- Upstream: https://github.com/RawTherapee/RawTherapee

The RawTherapee portable build is **not included** in this repository or its
skill archive. `setup-rt.ps1` downloads it from the official GitHub release
and verifies a SHA256 digest at install time. RawTherapee remains a separate
GPLv3 program; redistributing it requires complying with GPLv3. This project
only invokes `rawtherapee-cli.exe` as a separate process and does not link
RawTherapee code.

## Optional external tool: RAWmakase

- Used by: previews and RAW overexposure correction (optional)
- License: **MIT**
- Upstream: https://github.com/pch/rawmakase

RAWmakase is not bundled. It is used only when installed by the user.

## Installed at runtime: Python packages

`setup-face.ps1` installs OpenCV into a local dependency folder; the scripts
also require NumPy and Pillow. These packages are not bundled and keep their
own licenses:

- **OpenCV** — Apache License 2.0
- **NumPy** — BSD 3-Clause
- **Pillow** — HPND / PIL license
- **Python** — PSF License
- **pillow-heif** — BSD 3-Clause; it bundles libheif (LGPL-3.0), libde265
  (LGPL-3.0) and x265 (GPL-2.0) for HEIC decoding. It is installed separately
  by `setup-face.ps1`; this project does not distribute those binaries. Users
  are responsible for the combined license terms of the installed wheel.
- **ffmpeg** — optional external tool for JPEG XL. Distribution builds vary;
  the copy used for testing is a GPLv3 build. It is not bundled here.

Users installing these packages are responsible for their licenses.

## Not included

- No Adobe DCP camera profiles, LUTs, or Adobe Color profiles are bundled.
- No RAW or JPEG test photos from the author's collection are bundled.
- The CC BY-SA 4.0 sample images used during local testing are not part of
  this repository or the skill archive.

## Notes

This notice is provided for convenience and is not legal advice. If you
redistribute a modified bundle, verify the licenses of the exact versions of
RawTherapee, OpenCV, NumPy, Pillow and any models you include.
