#!/usr/bin/env python3
"""Triage + beautify pipeline.

Policy:
  * no problem  -> source-aware beauty (phone medium, camera high, unknown medium)
  * obvious     -> keep original, write a *-fixed.jpg candidate, ask the user
  * suspect     -> no file, only a suggestion
  * final state -> originals + beauty files + fixed candidates, no previews/temp
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageOps

try:
    import cv2
except ImportError:
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.environ.get("FACE_DEPS"), os.path.join(here, "..", "..", "face-deps")):
        if candidate and os.path.isdir(candidate):
            sys.path.insert(0, os.path.abspath(candidate))
            break
    import cv2

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import image_formats  # noqa: E402

_RT_CANDIDATES = [
    os.environ.get("RT_ROOT"),
    os.path.abspath(os.path.join(SKILL, "..", "rt-5.13", "RawTherapee_5.13_win64_x86_64_release")),
    os.path.abspath(os.path.join(SKILL, "..", "rt-5.13", "squashfs-root", "usr", "bin")),
    os.path.abspath(os.path.join(SKILL, "..", "rt-5.13", "squashfs-root")),
    os.path.abspath(os.path.join(SKILL, "..", "rt-5.13")),
]
DEFAULT_RT = next((p for p in _RT_CANDIDATES if p and os.path.exists(p)), _RT_CANDIDATES[1])
DEFAULT_RM = os.environ.get("RAWMAKASE") or os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "RAWmakase", "rawmakase.exe"
)
DEFAULT_MODEL = os.path.join(SKILL, "assets", "models", "face_detection_yunet_2023mar.onnx")
LOOKS = {
    "min": "rt-look1.pp3",
    "medium": "rt-look2.pp3",
    "high": "rt-look3.pp3",
    "max": "rt-look4.pp3",
}
# Portrait base is deliberately one step below general "medium": light contrast,
# low saturation, then a mask-free global skin-tone LUT.
PORTRAIT_LOOKS = {
    "min": "rt-portrait-light.pp3",
    "medium": "rt-portrait-light.pp3",
    "high": "rt-portrait-light.pp3",
    "max": "rt-look2-portrait.pp3",
}
# The base profile is already light; the global LUT is the variable part.
# Phone/medium therefore gets a visibly gentler portrait treatment than
# camera/high without introducing masks or local retouching.
LUT_AMOUNT = {
    "min": 0.35,
    "medium": 0.65,
    "high": 1.0,
    "max": 1.15,
}
DENOISE_LOOKS = {
    "light": "rt-denoise-light.pp3",
    "medium": "rt-denoise-medium.pp3",
    "strong": "rt-denoise-strong.pp3",
}
SHARPEN_LOOKS = {
    "light": "rt-sharpen-light.pp3",
    "medium": "rt-sharpen-medium.pp3",
    "strong": "rt-sharpen-strong.pp3",
}

PHONE_MAKES = (
    "apple", "xiaomi", "redmi", "huawei", "honor", "oppo", "vivo",
    "oneplus", "realme", "google", "motorola", "nokia", "nothing",
    "zte", "tcl", "alcatel", "meizu", "smartisan", "lenovo", "asus",
)
CAMERA_MAKES = (
    "canon", "nikon", "fujifilm", "panasonic", "olympus",
    "om digital", "pentax", "ricoh", "leica", "hasselblad",
    "phase one", "sigma", "mamiya", "contax", "kodak", "dji",
    "gopro", "insta360", "casio", "sanyo",
)
PHONE_MODEL_HINTS = (
    "iphone", "pixel", "xperia", "redmi", "moto", "sm-", "sm_",
    "cph-", "xt-", "pgt-", "pjd", "els-", "ana-",
    "lya-", "bla-", "jny-", "stk-", "bvl-", "vog-", "lio-",
    "mar-", "tas-", "noh-", "nop-", "nla-", "nth-", "nco-",
    "xq-", "xq_", "so-",
)
SONY_CAMERA_PREFIXES = ("ilce", "ilca", "dsc", "nex", "slt", "zv-", "a7", "a9")


def load_face_module():
    path = os.path.join(SKILL, "scripts", "face-beautify.py")
    spec = importlib.util.spec_from_file_location("face_beautify", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip()
        raise RuntimeError(f"{' '.join(cmd[:3])}... failed: {msg}")
    return p.stdout


def measure(path, face_mod, model):
    pil = image_formats.load_rgb(path)
    img = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    scale = min(1.0, 1200.0 / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1 else img
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    rgb = small.astype(np.float32)
    lum = 0.2126 * rgb[..., 2] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 0]
    p5, p95 = np.percentile(lum, [5, 95])
    faces = face_mod.detect(img, model, 0.6)
    faces = [f for f in faces if float(f[2]) >= w * 0.04]
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    sat = float(hsv[..., 1].mean() / 255.0 * 100)
    face_sat = 0.0
    if faces:
        f = max(faces, key=lambda z: float(z[2]) * float(z[3]))
        x, y, bw, bh = [float(v) * scale for v in f[:4]]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(hsv.shape[1], int(x + bw)), min(hsv.shape[0], int(y + bh))
        if x2 > x1 and y2 > y1:
            face_sat = float(hsv[y1:y2, x1:x2, 1].mean() / 255.0 * 100)
    return {
        "mean": float(lum.mean()),
        "range": float(p95 - p5),
        "hot": float((lum >= 250).mean() * 100),
        "dark": float((lum <= 10).mean() * 100),
        "sharp": sharp,
        "faces": len(faces),
        "sat": sat,
        "face_sat": face_sat,
    }


def classify(m, median_sharp):
    if m["mean"] >= 200 and m["hot"] >= 20 and m["range"] <= 80:
        return "obvious_over"
    if m["mean"] <= 25 and m["dark"] >= 40:
        return "obvious_under"
    if m["sharp"] < median_sharp * 0.2:
        return "obvious_blur"
    # Bright sky is normal in portraits/landscapes; only flag isolated clipping
    # on non-portrait images, or a genuinely dark frame.
    if (not m["faces"] and m["hot"] >= 5) or (m["mean"] <= 55 and m["dark"] >= 8):
        return "suspect"
    if m["range"] <= 55 or m["sharp"] < median_sharp * 0.45:
        return "suspect"
    return "ok"


def scene_of(m):
    if m["faces"]:
        return "portrait"
    if m["mean"] <= 75 and m["hot"] < 3:
        return "night"
    if m["mean"] >= 175 and m["dark"] <= 2:
        return "highkey"
    if m["range"] < 130:
        return "landscape"
    return "general"


def exif_text(exif, tag):
    try:
        value = exif.get(tag)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return ""


def exif_int(exif, tag):
    try:
        value = exif.get(tag)
        if value:
            return int(str(value).strip())
    except Exception:
        pass
    return 0


def exiftool_source_metadata(path):
    """Read Make/Model/Software/LensModel/ISO from RAW or unusual containers."""
    exe = os.environ.get("EXIFTOOL") or shutil.which("exiftool")
    if not exe:
        return {}
    try:
        p = subprocess.run(
            [exe, "-j", "-Make", "-Model", "-Software", "-LensModel", "-ISO", path],
            capture_output=True, timeout=10,
        )
        if p.returncode != 0 or not p.stdout.strip():
            return {}
        row = json.loads(p.stdout.decode("utf-8", errors="replace").lstrip("\ufeff"))[0]
        return {
            key: str(row.get(key) or "").strip()
            for key in ("Make", "Model", "Software", "LensModel", "ISO")
        }
    except Exception:
        return {}


def read_source_metadata(path):
    meta = {"make": "", "model": "", "software": "", "lens": "", "iso": 0}
    try:
        image_formats.ensure_heif()
        with Image.open(path) as im:
            exif = im.getexif()
            meta["make"] = exif_text(exif, 271)
            meta["model"] = exif_text(exif, 272)
            meta["software"] = exif_text(exif, 305)
            meta["lens"] = exif_text(exif, 42036)
            meta["iso"] = exif_int(exif, 34855) or exif_int(exif, 34867)
    except Exception:
        pass
    if not (meta["make"] or meta["model"]):
        extra = exiftool_source_metadata(path)
        meta["make"] = meta["make"] or extra.get("Make", "")
        meta["model"] = meta["model"] or extra.get("Model", "")
        meta["software"] = meta["software"] or extra.get("Software", "")
        meta["lens"] = meta["lens"] or extra.get("LensModel", "")
        try:
            meta["iso"] = meta["iso"] or int(extra.get("ISO") or 0)
        except ValueError:
            pass
    return meta


def source_from_metadata(meta):
    """Classify a photo as phone/camera/unknown from Make and Model.

    Ambiguous brands are resolved by model family; a missing or unrecognized
    tag stays unknown instead of guessing.
    """
    make = (meta.get("make") or "").strip()
    model = (meta.get("model") or "").strip()
    make_l = make.lower()
    model_l = model.lower()
    evidence = " ".join(x for x in (make, model) if x).strip() or "no EXIF Make/Model"

    if "sony ericsson" in make_l:
        return "phone", evidence
    if any(hint in model_l for hint in PHONE_MODEL_HINTS):
        return "phone", evidence
    if "samsung" in make_l:
        if model_l.startswith(("nx", "wb")):
            return "camera", evidence
        return "phone", evidence
    if "sony" in make_l:
        if model_l.startswith(SONY_CAMERA_PREFIXES):
            return "camera", evidence
        if "xperia" in model_l:
            return "phone", evidence
        return "unknown", evidence
    if any(token in make_l for token in PHONE_MAKES):
        return "phone", evidence
    if any(token in make_l for token in CAMERA_MAKES):
        return "camera", evidence
    return "unknown", evidence


def detect_source(path, forced="auto", meta=None):
    meta = meta or read_source_metadata(path)
    source, evidence = source_from_metadata(meta)
    if forced and forced != "auto":
        return forced, f"forced {forced}; {evidence}"
    return source, evidence


def auto_detail(source, iso):
    """Conservative detail policy: phone noise, camera high-ISO noise, camera
    output sharpening. Phone images are already sharpened by their camera app,
    so they are not sharpened again by default."""
    denoise = "off"
    if source == "phone":
        if iso >= 3200:
            denoise = "medium"
        elif iso >= 800:
            denoise = "light"
    elif source == "camera":
        if iso >= 6400:
            denoise = "medium"
        elif iso >= 1600:
            denoise = "light"
    elif source == "unknown" and iso >= 3200:
        denoise = "light"
    sharpen = "light" if source == "camera" else "off"
    return denoise, sharpen


def resolve_detail(source, iso, denoise, sharpen):
    if denoise == "auto" or sharpen == "auto":
        auto_denoise, auto_sharpen = auto_detail(source, iso)
        if denoise == "auto":
            denoise = auto_denoise
        if sharpen == "auto":
            sharpen = auto_sharpen
    return denoise, sharpen


def effective_strength(source, strength, phone_strength):
    """Resolve one level per photo; explicit --strength always wins."""
    if strength != "auto":
        return strength
    if source == "phone":
        return phone_strength
    if source == "camera":
        return "high"
    return "medium"


def strength_policy(strength, phone_strength):
    if strength != "auto":
        return f"forced {strength} for all photos"
    return f"auto (phone={phone_strength}, camera=high, unknown=medium)"


def unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base}-{n}{ext}"):
        n += 1
    return f"{base}-{n}{ext}"


def beauty_name(src, is_raw, outdir, overwrite_originals=False):
    base, ext = os.path.splitext(os.path.basename(src))
    # Safe default: never touch the source. The dangerous opt-in only applies
    # to normal JPG/JPEG, where the result can be written back in place.
    if overwrite_originals and not is_raw and ext.lower() in (".jpg", ".jpeg"):
        return src
    if is_raw:
        candidate = os.path.join(outdir, base + ".jpg")
        if not os.path.exists(candidate):
            return candidate
    return unique(os.path.join(outdir, base + "-beauty.jpg"))


def fixed_name(src, outdir):
    base = os.path.splitext(os.path.basename(src))[0]
    return unique(os.path.join(outdir, base + "-fixed.jpg"))


def rt_tool(rt):
    bases = [rt, os.path.join(rt, "usr", "bin"), os.path.join(rt, "squashfs-root", "usr", "bin")]
    for base in bases:
        for name in ("rawtherapee-cli.exe", "rawtherapee-cli"):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    raise FileNotFoundError(
        f"rawtherapee-cli not found under {rt!r}; pass --rt-root pointing at the "
        "RawTherapee folder (Windows) or usr/bin (Linux AppImage extract)."
    )


def rt_profiles(rt):
    bases = [rt, os.path.join(rt, "usr", "bin"), os.path.join(rt, "squashfs-root", "usr", "bin")]
    for base in bases:
        path = os.path.join(base, "profiles")
        if os.path.isdir(path):
            return path
    raise FileNotFoundError(f"RawTherapee profiles folder not found under {rt!r}")


def render_rt(src, dst, is_raw, scene, strength, rt, tmp, m=None,
              denoise="off", sharpen="off"):
    cli = rt_tool(rt)
    profiles = []
    if is_raw:
        iso = "High" if scene == "night" else "Low"
        auto = os.path.join(rt_profiles(rt), f"Auto-Matched Curve - ISO {iso}.pp3")
        if not os.path.isfile(auto):
            raise FileNotFoundError(f"missing RawTherapee profile: {auto}")
        profiles.append(auto)
    look_name = (PORTRAIT_LOOKS if scene == "portrait" else LOOKS)[strength]
    if scene == "portrait" and m and m.get("face_sat", 0) >= 30:
        # Already saturated: do not push it further.
        if strength == "high":
            look_name = "rt-portrait-light-neutral.pp3"
        elif strength == "max":
            look_name = "rt-look2-portrait-neutral.pp3"
    profiles.append(os.path.join(SKILL, "assets", "looks", look_name))
    if denoise != "off":
        profiles.append(os.path.join(SKILL, "assets", "looks", DENOISE_LOOKS[denoise]))
    if sharpen != "off":
        profiles.append(os.path.join(SKILL, "assets", "looks", SHARPEN_LOOKS[sharpen]))
    out = os.path.join(tmp, os.path.splitext(os.path.basename(src))[0] + "-rt.jpg")
    cmd = [cli, "-o", out]
    for p in profiles:
        cmd += ["-p", p]
    cmd += ["-j92", "-Y", "-c", src]
    run(cmd)
    shutil.copy2(out, dst)
    return dst


def global_skin_lut(src, dst, amount=1.0):
    """Mask-free skin-tone whitening via a smooth per-pixel color transform.

    ``amount`` scales the effect so phone/medium stays gentler than camera/high
    while using the same base profile and no spatial mask.
    """
    arr = np.asarray(image_formats.load_rgb(src)).astype(np.uint8)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).astype(np.float32)
    hue = hsv[..., 0] * 2.0
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0
    w = (
        np.exp(-((hue - 30.0) / 18.0) ** 2)
        * np.exp(-((sat - 0.35) / 0.22) ** 2)
        * np.clip((val - 0.10) / 0.25, 0.0, 1.0)
    )
    amount = max(0.0, min(1.5, float(amount)))
    w = w * amount
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB).astype(np.float32)
    l, a, b = cv2.split(lab)
    l = l + 9.0 * w
    a = 128.0 + (a - 128.0) * (1.0 - 0.10 * w)
    b = 128.0 + (b - 128.0) * (1.0 - 0.16 * w)
    out = cv2.cvtColor(
        cv2.merge([l, np.clip(a, 0, 255), np.clip(b, 0, 255)]).astype(np.uint8),
        cv2.COLOR_LAB2RGB,
    )
    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return dst


def fix_over(src, dst, is_raw, rt, rm, tmp):
    if is_raw and os.path.exists(rm):
        run([rm, "render", src, dst, "--xmp", os.path.join(SKILL, "assets", "xmp", "fix-over.xmp"),
             "--exposure=-2.5", "--overwrite"])
        return "RAWmakase XMP -2.5EV"
    look = os.path.join(SKILL, "assets", "looks", "rt-fix-over.pp3")
    out = os.path.join(tmp, "fix-over.jpg")
    run([rt_tool(rt), "-o", out, "-p", look, "-j92", "-Y", "-c", src])
    shutil.copy2(out, dst)
    return "RT fix-over (best effort)"


def fix_under(src, dst, rt, tmp):
    look = os.path.join(SKILL, "assets", "looks", "rt-fix-under.pp3")
    out = os.path.join(tmp, "fix-under.jpg")
    run([rt_tool(rt), "-o", out, "-p", look, "-j92", "-Y", "-c", src])
    shutil.copy2(out, dst)
    return "RT fix-under +1.5EV"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir")
    p.add_argument("--strength", choices=["auto", "min", "medium", "high", "max"],
                   default="auto",
                   help="auto by source (default); min/medium/high/max force all photos")
    p.add_argument("--phone-strength", choices=["min", "medium"], default="medium",
                   help="level for phone photos when --strength is auto (default medium)")
    p.add_argument("--source", choices=["auto", "phone", "camera", "unknown"],
                   default="auto",
                   help="override EXIF source detection (default auto)")
    p.add_argument("--denoise", choices=["auto", "off", "light", "medium", "strong"],
                   default="auto",
                   help="noise reduction: auto is phone/high-ISO only (default auto)")
    p.add_argument("--sharpen", choices=["auto", "off", "light", "medium", "strong"],
                   default="auto",
                   help="output sharpening: auto is light for camera only (default auto)")
    p.add_argument("--rt-root", default=DEFAULT_RT)
    p.add_argument("--rawmakase", default=DEFAULT_RM)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite-originals", action="store_true",
                   help="dangerous: write normal JPG/JPEG beauty results back to the original path")
    p.add_argument("--temp-dir", help="writable temp folder (default: system temp)")
    p.add_argument("--report", default="pipeline-report.md")
    args = p.parse_args()

    if not os.path.isdir(args.input):
        raise SystemExit(f"input not found: {args.input}")
    outdir = args.output_dir or args.input
    os.makedirs(outdir, exist_ok=True)
    if args.overwrite_originals:
        print("WARNING: --overwrite-originals is enabled; JPG/JPEG originals will be replaced in place.")
    face_mod = load_face_module()
    tmp_base = args.temp_dir or tempfile.gettempdir()
    # Use a plain subdirectory (not tempfile.mkdtemp: its restrictive ACL makes
    # RAWmakase's atomic temp file fail with access denied on Windows).
    tmp = os.path.join(tmp_base, f"photo-pipeline-{os.getpid()}")
    os.makedirs(tmp, exist_ok=True)
    rows = []
    try:
        files = [
            f for f in sorted(os.listdir(args.input))
            if os.path.splitext(f)[1].lower() in image_formats.ALL_EXT
            and not f.lower().startswith(".")
            and not any(f.lower().endswith(s + os.path.splitext(f)[1].lower()) for s in ("-beauty", "-fixed"))
            and not re.search(r"-rt\d*(?=\.|$)", f.lower())
        ]
        for name in files:
            src = os.path.join(args.input, name)
            is_raw = name.lower().endswith(image_formats.RAW_EXT)
            meta = read_source_metadata(src)
            source, source_evidence = detect_source(src, args.source, meta=meta)
            iso = int(meta.get("iso") or 0)
            strength = effective_strength(source, args.strength, args.phone_strength)
            denoise, sharpen = resolve_detail(source, iso, args.denoise, args.sharpen)
            try:
                # WebP/AVIF/HEIC/HEIF/JXL are converted to a working TIFF once;
                # all later steps (RT, face, metrics) use that copy.
                working = src if (is_raw or name.lower().endswith(image_formats.RT_NATIVE)) else image_formats.normalize_for_rt(src, tmp)
                if is_raw:
                    preview = os.path.join(tmp, os.path.splitext(name)[0] + "-preview.jpg")
                    if os.path.isfile(args.rawmakase):
                        run([args.rawmakase, "render", src, preview, "--max-edge", "900", "--overwrite"])
                    else:
                        # Linux/macOS: no RAWmakase; use RT's camera-matched
                        # profile for the analysis preview.
                        auto = os.path.join(rt_profiles(args.rt_root), "Auto-Matched Curve - ISO Low.pp3")
                        run([rt_tool(args.rt_root), "-o", preview, "-p", auto, "-j92", "-Y", "-c", src])
                else:
                    preview = working
                m = measure(preview, face_mod, args.model)
                rows.append({"file": name, "src": src, "working": working, "raw": is_raw,
                             "preview": preview, "m": m, "source": source,
                             "source_evidence": source_evidence, "iso": iso,
                             "strength": strength, "denoise": denoise,
                             "sharpen": sharpen})
            except Exception as e:
                rows.append({"file": name, "src": src, "working": src, "raw": is_raw, "m": None,
                             "source": source, "source_evidence": source_evidence,
                             "iso": iso, "strength": strength, "denoise": denoise,
                             "sharpen": sharpen, "error": str(e), "note": str(e)})

        valid = [r for r in rows if r.get("m")]
        median_sharp = float(np.median([r["m"]["sharp"] for r in valid])) if valid else 0
        for r in rows:
            if not r.get("m"):
                r["class"] = "error"
                r["scene"] = "-"
                continue
            r["class"] = classify(r["m"], median_sharp)
            r["scene"] = scene_of(r["m"])

        for r in rows:
            r["action"] = "none"
            r["output"] = ""
            if "note" not in r:
                r["note"] = ""
            if args.dry_run:
                continue
            src = r.get("working") or r["src"]
            m, cls = r["m"], r["class"]
            if cls == "error":
                r["note"] = r.get("error", "read/convert failed")
                r["action"] = "suggest"
                continue
            if cls == "ok":
                dst = beauty_name(r["src"], r["raw"], outdir, args.overwrite_originals)
                tmp_out = os.path.join(tmp, os.path.splitext(os.path.basename(r["src"]))[0] + "-beauty.jpg")
                render_rt(src, tmp_out, r["raw"], r["scene"], r["strength"],
                          args.rt_root, tmp, m, r["denoise"], r["sharpen"])
                if r["scene"] == "portrait":
                    try:
                        global_skin_lut(tmp_out, dst, LUT_AMOUNT[r["strength"]])
                        r["note"] = "global skin LUT"
                    except Exception:
                        shutil.copy2(tmp_out, dst)
                        r["note"] = "skin LUT failed; base only"
                else:
                    shutil.copy2(tmp_out, dst)
                if os.path.abspath(dst) == os.path.abspath(r["src"]):
                    r["note"] = (r["note"] + "; original overwritten (irreversible)").lstrip("; ")
                r["action"] = "beauty"
                r["output"] = dst
            elif cls in ("obvious_over", "obvious_under"):
                dst = fixed_name(r["src"], outdir)
                if cls == "obvious_over":
                    r["note"] = fix_over(src, dst, r["raw"], args.rt_root, args.rawmakase, tmp)
                else:
                    r["note"] = fix_under(src, dst, args.rt_root, tmp)
                r["action"] = "fixed"
                r["output"] = dst
            elif cls == "obvious_blur":
                r["note"] = "Whole-frame blur; cannot repair reliably. Reshoot or check focus."
                r["action"] = "suggest"
            else:
                reasons = []
                if m["hot"] >= 3:
                    reasons.append("Highlights clipped")
                if m["mean"] <= 55 and m["dark"] >= 8:
                    reasons.append("Dark/night/silhouette")
                if m["range"] <= 55:
                    reasons.append("Low contrast")
                if m["sharp"] < median_sharp * 0.45:
                    reasons.append("Low sharpness")
                r["note"] = ", ".join(reasons) or "Statistical outlier"
                r["action"] = "suggest"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# Auto beautify pipeline report\n\n")
        f.write(f"Input: {args.input}\n\n")
        f.write(f"Strength policy: {strength_policy(args.strength, args.phone_strength)}\n\n")
        f.write(f"Source override: {args.source}\n\n")
        f.write("## Normal photos (beautified)\n\n")
        f.write("| Original | Source | Scene | Strength | Detail | Output | Notes |\n| --- | --- | --- | --- | --- | --- | --- |\n")
        for r in rows:
            if r["action"] in ("beauty",) or (args.dry_run and r["class"] == "ok"):
                out = os.path.basename(r["output"]) if r["output"] else "(dry-run)"
                detail = f"DN {r['denoise']} / SH {r['sharpen']}"
                f.write(f"| {r['file']} | {r['source']} | {r['scene']} | {r['strength']} | {detail} | {out} | {r['note']} |\n")
        f.write("\n## Obvious problems (fixed candidates, waiting for confirmation)\n\n")
        f.write("| Original | Issue | Fixed file | Method |\n| --- | --- | --- | --- |\n")
        for r in rows:
            if r["class"] in ("obvious_over", "obvious_under"):
                f.write(f"| {r['file']} | {r['class']} | {os.path.basename(r['output']) if r['output'] else '(dry-run)'} | {r['note']} |\n")
        if any(r["class"] in ("obvious_over", "obvious_under") for r in rows):
            f.write("\nConfirm whether to keep these `*-fixed.jpg` files; do not delete the originals before confirming.\n")
        f.write("\n## Obvious problems that cannot be auto-fixed\n\n")
        f.write("| Original | Scene | Suggestion |\n| --- | --- | --- |\n")
        for r in rows:
            if r["class"] == "obvious_blur":
                f.write(f"| {r['file']} | {r['scene']} | {r['note']} |\n")
        f.write("\n## Suspect images (suggestions only, no files)\n\n")
        f.write("| Original | Scene | Concern / suggestion |\n| --- | --- | --- |\n")
        for r in rows:
            if r["action"] == "suggest" and r["class"] not in ("obvious_blur", "error"):
                f.write(f"| {r['file']} | {r['scene']} | {r['note']} |\n")
        f.write("\n## Read/convert failures\n\n")
        f.write("| Original | Reason |\n| --- | --- |\n")
        for r in rows:
            if r["class"] == "error":
                f.write(f"| {r['file']} | {r.get('error') or r['note']} |\n")
        f.write("\n## Plan\n\n")
        f.write("- Source is inferred from EXIF Make/Model: phone uses the phone level, camera uses high, unknown uses medium (conservative).\n")
        f.write("- `--strength` forces one level for every photo; `--source` overrides EXIF detection when metadata is missing or wrong.\n")
        f.write("- Detail is conservative: denoise auto is phone at ISO 800+, camera at ISO 1600+; sharpening auto is camera light; phone/unknown off. Stronger levels are explicit.\n")
        f.write("- Denoising reduces noise but also softens detail; sharpening raises edge acutance and can create halos, but cannot recover missed focus or motion blur.\n")
        f.write("- Camera general scenes use look3 (`high`); phone/medium uses look2; portraits use the light portrait base.\n")
        f.write("- Portrait: light base + global skin-tone LUT; the LUT is scaled down for min/medium, so phone portraits stay gentler. No face mask, smoothing, or local whitening.\n")
        f.write("- A high face-saturation reading switches to a neutral portrait base.\n")
        f.write("- Night uses ISO High + the selected look; high-key/food use the selected look.\n")
        f.write("- Non-RAW/JPEG/PNG/TIFF inputs are normalized to a working TIFF; obvious overexposed RAW uses RAWmakase XMP -2.5EV.\n")
        f.write("- No overwrite by default; `--overwrite-originals` applies only to normal JPG/JPEG; other formats keep their originals.\n")
        f.write("- Suspect images produce no files; previews and temporary files are cleaned up.\n")

    print(f"processed={len(rows)} report={args.report}")
    for r in rows:
        print(f"  {r['file']}: {r['source']} / {r['strength']} / "
              f"dn={r['denoise']} sh={r['sharpen']} / {r['class']} / {r['scene']} "
              f"-> {r['action']} {os.path.basename(r['output']) if r['output'] else ''}")


if __name__ == "__main__":
    main()
