#!/usr/bin/env python3
"""Input format support for the photo pipeline.

RAW and JPEG/PNG/TIFF go straight to RawTherapee. WebP/AVIF/HEIC/HEIF/BMP/GIF
are decoded with Pillow (HEIC needs pillow-heif), JPEG XL with ffmpeg, and
written to a temporary 16-bit TIFF for RawTherapee.

Embedded ICC profiles (for example Xiaomi's DCI-P3 JPEGs) are converted to
sRGB before analysis/conversion, so P3 files are not mistaken for sRGB.
"""

import glob
import io
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageCms, ImageOps

RAW_EXT = (
    ".3fr", ".ari", ".arw", ".bay", ".cr2", ".cr3", ".crw", ".dcr", ".dng",
    ".erf", ".fff", ".gpr", ".iiq", ".k25", ".kdc", ".mdc", ".mef", ".mos",
    ".mrw", ".nef", ".nrw", ".obm", ".odc", ".orf", ".pef", ".raf", ".raw",
    ".rw2", ".rwl", ".rwz", ".sr2", ".srf", ".srw", ".x3f",
)
RT_NATIVE = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
PIL_EXT = (".webp", ".avif", ".heic", ".heif", ".bmp", ".gif")
JXL_EXT = (".jxl",)
ALL_EXT = RAW_EXT + RT_NATIVE + PIL_EXT + JXL_EXT


def _deps_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    out = []
    if os.environ.get("FACE_DEPS"):
        out.append(os.environ["FACE_DEPS"])
    out.append(os.path.join(here, "..", "..", "face-deps"))
    return [os.path.abspath(p) for p in out if os.path.isdir(p)]


def ensure_heif():
    """Import pillow-heif and, for a manually unpacked wheel, add its DLL dir."""
    # Add the DLL directory before the first import: a failed first import can
    # leave the extension module in a half-initialized state.
    for deps in _deps_dirs():
        for dll_dir in glob.glob(os.path.join(deps, "pillow_heif-*.data", "platlib")):
            try:
                os.add_dll_directory(dll_dir)
            except Exception:
                pass
    try:
        import pillow_heif
    except Exception:
        return False
    try:
        pillow_heif.register_heif_opener()
        return True
    except Exception:
        return False


def load_rgb(path):
    """Load with EXIF orientation and convert embedded ICC (e.g. DCI-P3) to sRGB."""
    ensure_heif()
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        icc = im.info.get("icc_profile")
        if icc:
            try:
                src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                dst = ImageCms.createProfile("sRGB")
                return ImageCms.profileToProfile(
                    im, src, dst, outputMode="RGB", renderingIntent=0
                )
            except Exception:
                pass
        return im.convert("RGB")


def ffmpeg_path():
    exe = os.environ.get("FFMPEG")
    if exe and os.path.isfile(exe):
        return exe
    found = shutil.which("ffmpeg")
    return found


def normalize_for_rt(src, tmp):
    """Return a path RawTherapee can read, converting unsupported formats."""
    ext = os.path.splitext(src)[1].lower()
    if ext in RAW_EXT or ext in RT_NATIVE:
        return src

    base = os.path.splitext(os.path.basename(src))[0]
    # Include the source extension so same-basename files (a.webp + a.avif)
    # never share one working TIFF.
    tag = ext.lstrip(".")
    out = os.path.join(tmp, f"{base}-{tag}-normalized.tif")

    if ext in PIL_EXT:
        if ext in (".heic", ".heif") and not ensure_heif():
            raise RuntimeError("HEIC/HEIF needs pillow-heif (pip install pillow-heif).")
        load_rgb(src).save(out, format="TIFF", compression="tiff_lzw")
        return out

    if ext in JXL_EXT:
        ff = ffmpeg_path()
        if not ff:
            raise RuntimeError("JPEG XL needs ffmpeg with libjxl on PATH (or set FFMPEG).")
        p = subprocess.run(
            [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
             "-frames:v", "1", "-pix_fmt", "rgb48le", out],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        if p.returncode != 0 or not os.path.exists(out):
            raise RuntimeError("ffmpeg could not decode JPEG XL: " + (p.stderr or "").strip())
        return out

    raise RuntimeError(f"unsupported format: {ext}")


def supported_name():
    return "RAW, JPEG, PNG, TIFF, WebP, AVIF, HEIC/HEIF, JXL, BMP, GIF"


if __name__ == "__main__":
    print(supported_name())
    print("pillow-heif:", ensure_heif())
    print("ffmpeg:", ffmpeg_path() or "missing")
