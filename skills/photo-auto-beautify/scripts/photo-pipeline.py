#!/usr/bin/env python3
"""Triage + beautify pipeline.

Policy:
  * no problem  -> medium beauty by default (or min/max), output JPEG
  * obvious     -> keep original, write a *-fixed.jpg candidate, ask the user
  * suspect     -> no file, only a suggestion
  * final state -> originals + beauty files + fixed candidates, no previews/temp
"""

import argparse
import importlib.util
import os
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
DEFAULT_RT = os.path.abspath(os.path.join(SKILL, "..", "rt-5.13", "RawTherapee_5.13_win64_x86_64_release"))
DEFAULT_RM = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "RAWmakase", "rawmakase.exe")
DEFAULT_MODEL = os.path.join(SKILL, "assets", "models", "face_detection_yunet_2023mar.onnx")
LOOKS = {"min": "rt-look1.pp3", "medium": "rt-look2.pp3", "max": "rt-look3.pp3"}
FACE_STRENGTH = {"min": 1, "medium": 2, "max": 3}
RAW_EXT = (".rw2", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".pef", ".srw")
JPG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


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
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
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
    return {
        "mean": float(lum.mean()),
        "range": float(p95 - p5),
        "hot": float((lum >= 250).mean() * 100),
        "dark": float((lum <= 10).mean() * 100),
        "sharp": sharp,
        "faces": len(faces),
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


def unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base}-{n}{ext}"):
        n += 1
    return f"{base}-{n}{ext}"


def beauty_name(src, is_raw, outdir):
    base = os.path.splitext(os.path.basename(src))[0]
    if is_raw:
        candidate = os.path.join(outdir, base + ".jpg")
        if not os.path.exists(candidate):
            return candidate
    return unique(os.path.join(outdir, base + "-beauty.jpg"))


def fixed_name(src, outdir):
    base = os.path.splitext(os.path.basename(src))[0]
    return unique(os.path.join(outdir, base + "-fixed.jpg"))


def render_rt(src, dst, is_raw, scene, strength, rt, tmp):
    profiles = []
    if is_raw:
        iso = "High" if scene == "night" else "Low"
        profiles.append(os.path.join(rt, "profiles", f"Auto-Matched Curve - ISO {iso}.pp3"))
    profiles.append(os.path.join(SKILL, "assets", "looks", LOOKS[strength]))
    out = os.path.join(tmp, os.path.splitext(os.path.basename(src))[0] + "-rt.jpg")
    cmd = [os.path.join(rt, "rawtherapee-cli.exe"), "-o", out]
    for p in profiles:
        cmd += ["-p", p]
    cmd += ["-j92", "-Y", "-c", src]
    run(cmd)
    shutil.copy2(out, dst)
    return dst


def apply_face(path, dst, strength, face_mod, model):
    out, count, reason = face_mod.beautify(
        path, model, FACE_STRENGTH[strength], True, True, 0.04, 3
    )
    if reason != "ok":
        return 0, reason
    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return count, "ok"


def fix_over(src, dst, is_raw, rt, rm, tmp):
    if is_raw and os.path.exists(rm):
        run([rm, "render", src, dst, "--xmp", os.path.join(SKILL, "assets", "xmp", "fix-over.xmp"),
             "--exposure=-2.5", "--overwrite"])
        return "RAWmakase XMP -2.5EV"
    look = os.path.join(SKILL, "assets", "looks", "rt-fix-over.pp3")
    out = os.path.join(tmp, "fix-over.jpg")
    run([os.path.join(rt, "rawtherapee-cli.exe"), "-o", out, "-p", look, "-j92", "-Y", "-c", src])
    shutil.copy2(out, dst)
    return "RT fix-over (best effort)"


def fix_under(src, dst, rt, tmp):
    look = os.path.join(SKILL, "assets", "looks", "rt-fix-under.pp3")
    out = os.path.join(tmp, "fix-under.jpg")
    run([os.path.join(rt, "rawtherapee-cli.exe"), "-o", out, "-p", look, "-j92", "-Y", "-c", src])
    shutil.copy2(out, dst)
    return "RT fix-under +1.5EV"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output-dir")
    p.add_argument("--strength", choices=["min", "medium", "max"], default="medium")
    p.add_argument("--rt-root", default=DEFAULT_RT)
    p.add_argument("--rawmakase", default=DEFAULT_RM)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--temp-dir", help="writable temp folder (default: system temp)")
    p.add_argument("--report", default="pipeline-report.md")
    args = p.parse_args()

    if not os.path.isdir(args.input):
        raise SystemExit(f"input not found: {args.input}")
    outdir = args.output_dir or args.input
    os.makedirs(outdir, exist_ok=True)
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
            if f.lower().endswith(RAW_EXT + JPG_EXT)
            and not f.lower().startswith(".")
            and not any(f.lower().endswith(s + os.path.splitext(f)[1].lower()) for s in ("-beauty", "-fixed"))
            and "-rt" not in f.lower()
        ]
        for name in files:
            src = os.path.join(args.input, name)
            is_raw = name.lower().endswith(RAW_EXT)
            if is_raw:
                preview = os.path.join(tmp, os.path.splitext(name)[0] + "-preview.jpg")
                run([args.rawmakase, "render", src, preview, "--max-edge", "900", "--overwrite"])
            else:
                preview = src
            m = measure(preview, face_mod, args.model)
            rows.append({"file": name, "src": src, "raw": is_raw, "preview": preview, "m": m})

        median_sharp = float(np.median([r["m"]["sharp"] for r in rows])) if rows else 0
        for r in rows:
            r["class"] = classify(r["m"], median_sharp)
            r["scene"] = scene_of(r["m"])

        for r in rows:
            r["action"] = "none"
            r["output"] = ""
            r["note"] = ""
            if args.dry_run:
                continue
            src, m, cls = r["src"], r["m"], r["class"]
            if cls == "ok":
                dst = beauty_name(src, r["raw"], outdir)
                tmp_out = os.path.join(tmp, os.path.splitext(os.path.basename(src))[0] + "-beauty.jpg")
                render_rt(src, tmp_out, r["raw"], r["scene"], args.strength, args.rt_root, tmp)
                if r["scene"] == "portrait":
                    count, reason = apply_face(tmp_out, dst, args.strength, face_mod, args.model)
                    if reason != "ok":
                        shutil.copy2(tmp_out, dst)
                    r["note"] = f"face={count}"
                else:
                    shutil.copy2(tmp_out, dst)
                r["action"] = "beauty"
                r["output"] = dst
            elif cls in ("obvious_over", "obvious_under"):
                dst = fixed_name(src, outdir)
                if cls == "obvious_over":
                    r["note"] = fix_over(src, dst, r["raw"], args.rt_root, args.rawmakase, tmp)
                else:
                    r["note"] = fix_under(src, dst, args.rt_root, tmp)
                r["action"] = "fixed"
                r["output"] = dst
            elif cls == "obvious_blur":
                r["note"] = "整图模糊，无法可靠修复；建议重拍/检查对焦"
                r["action"] = "suggest"
            else:
                reasons = []
                if m["hot"] >= 3:
                    reasons.append("高光偏多")
                if m["mean"] <= 55 and m["dark"] >= 8:
                    reasons.append("偏暗/夜景/剪影")
                if m["range"] <= 55:
                    reasons.append("低对比")
                if m["sharp"] < median_sharp * 0.45:
                    reasons.append("清晰度偏低")
                r["note"] = "、".join(reasons) or "统计上偏离"
                r["action"] = "suggest"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# 自动美化流水线报告\n\n")
        f.write(f"输入：{args.input}\n\n档位：{args.strength}\n\n")
        f.write("## 正常图片（已美化）\n\n")
        f.write("| 原图 | 场景 | 输出 | 备注 |\n| --- | --- | --- | --- |\n")
        for r in rows:
            if r["action"] in ("beauty",) or (args.dry_run and r["class"] == "ok"):
                out = os.path.basename(r["output"]) if r["output"] else "(dry-run)"
                f.write(f"| {r['file']} | {r['scene']} | {out} | {r['note']} |\n")
        f.write("\n## 明显问题（已生成修正文件，待你确认）\n\n")
        f.write("| 原图 | 问题 | 修正文件 | 方式 |\n| --- | --- | --- | --- |\n")
        for r in rows:
            if r["class"] in ("obvious_over", "obvious_under"):
                f.write(f"| {r['file']} | {r['class']} | {os.path.basename(r['output']) if r['output'] else '(dry-run)'} | {r['note']} |\n")
        if any(r["class"] in ("obvious_over", "obvious_under") for r in rows):
            f.write("\n请确认这些 `*-fixed.jpg` 是否保留；确认前不要删除原图。\n")
        f.write("\n## 明显问题但无法自动修复\n\n")
        f.write("| 原图 | 场景 | 建议 |\n| --- | --- | --- |\n")
        for r in rows:
            if r["class"] == "obvious_blur":
                f.write(f"| {r['file']} | {r['scene']} | {r['note']} |\n")
        f.write("\n## 疑似问题（只给建议，未生成文件）\n\n")
        f.write("| 原图 | 场景 | 疑点/建议 |\n| --- | --- | --- |\n")
        for r in rows:
            if r["action"] == "suggest" and r["class"] != "obvious_blur":
                f.write(f"| {r['file']} | {r['scene']} | {r['note']} |\n")
        f.write("\n## 方案说明\n\n")
        f.write("- 正常图片默认 look2；`--strength min/max` 切换 look1/look3。\n")
        f.write("- 人像自动加皮肤平滑（强度随档位 1/2/3），不做瘦脸。\n")
        f.write("- 夜景用 ISO High + look2；高调/食物用 look2。\n")
        f.write("- 明显过曝：RAW 用 RAWmakase XMP -2.5EV；JPG 用 RT 尽力修正。\n")
        f.write("- 疑似问题不生成任何文件；中间预览/暂存已清理。\n")

    print(f"processed={len(rows)} report={args.report}")
    for r in rows:
        print(f"  {r['file']}: {r['class']} / {r['scene']} -> {r['action']} {os.path.basename(r['output']) if r['output'] else ''}")


if __name__ == "__main__":
    main()
