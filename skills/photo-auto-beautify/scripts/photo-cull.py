#!/usr/bin/env python3
"""Photo culling report: sharpness, exposure and near-duplicates.

Read-only. It ranks/flag images but never edits or deletes them. Intended as a
first pass before batch beautification: blurry or duplicated shots should be
reviewed by the user.
"""

import argparse
import os
import sys

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


def load(path):
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img = np.asarray(pil)
    return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


def metrics(img):
    h, w = img.shape[:2]
    scale = min(1.0, 1200.0 / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1 else img
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    rgb = small.astype(np.float32)
    lum = 0.2126 * rgb[..., 2] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 0]
    mean = float(lum.mean())
    hot = float((lum >= 250).mean() * 100)
    dark = float((lum <= 10).mean() * 100)
    return {"sharpness": round(sharp, 1), "mean": round(mean, 1), "hot": round(hot, 2), "dark": round(dark, 2)}


def ahash(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
    bits = (small > small.mean()).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--report", default="cull-report.md")
    args = p.parse_args()

    exts = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    rows = []
    for name in sorted(os.listdir(args.input)):
        if not name.lower().endswith(exts):
            continue
        path = os.path.join(args.input, name)
        try:
            img = load(path)
            m = metrics(img)
            m.update(file=name, hash=ahash(img))
            rows.append(m)
        except Exception as e:
            rows.append({"file": name, "error": str(e)})

    valid = [r for r in rows if "error" not in r]
    median_sharp = float(np.median([r["sharpness"] for r in valid])) if valid else 0
    for r in valid:
        flags = []
        if r["sharpness"] < max(30.0, median_sharp * 0.4):
            flags.append("相对模糊")
        if r["mean"] >= 205:
            flags.append("整体偏亮")
        if r["mean"] <= 38 and r["dark"] >= 25:
            flags.append("整体偏暗")
        if r["hot"] >= 10:
            flags.append("高光偏多")
        r["flags"] = "、".join(flags) if flags else "正常"

    # Near-duplicates: Hamming distance <= 4 on a 256-bit average hash.
    groups = []
    used = set()
    for i, a in enumerate(valid):
        if i in used:
            continue
        group = [a["file"]]
        for j in range(i + 1, len(valid)):
            if j in used:
                continue
            b = valid[j]
            dist = (a["hash"] ^ b["hash"]).bit_count()
            sharp_ratio = max(a["sharpness"], b["sharpness"]) / max(1.0, min(a["sharpness"], b["sharpness"]))
            # A blurred frame keeps the same layout, so it also matches the
            # average hash. Only call it a duplicate when sharpness is similar.
            if dist <= 4 and sharp_ratio <= 3.0:
                group.append(b["file"])
                used.add(j)
        if len(group) > 1:
            groups.append(group)
        used.add(i)

    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# 选片报告（只提示，不改/不删图）\n\n")
        f.write(f"范围：{args.input}，{len(rows)} 张。\n\n")
        f.write("| 文件 | 清晰度 | 均值 | 高光% | 暗部% | 提示 |\n")
        f.write("| --- | ---: | ---: | ---: | ---: | --- |\n")
        for r in valid:
            f.write(f"| {r['file']} | {r['sharpness']} | {r['mean']} | {r['hot']} | {r['dark']} | {r['flags']} |\n")
        for r in rows:
            if "error" in r:
                f.write(f"| {r['file']} | - | - | - | - | 读取失败：{r['error']} |\n")
        f.write("\n## 近似重复\n\n")
        if groups:
            for g in groups:
                f.write("- " + " / ".join(g) + "\n")
        else:
            f.write("未发现近似重复。\n")
        f.write("\n> 清晰度是整图拉普拉斯方差，背景虚化/大面积纯色会拉低分数；"
                "亮/暗提示也不代表错误，需结合场景判断。\n")

    print(f"images={len(rows)} flagged={sum(1 for r in valid if r['flags'] != '正常')} duplicates={len(groups)}")
    for r in valid:
        print(f"  {r['file']}: sharp={r['sharpness']} mean={r['mean']} {r['flags']}")
    print(f"report -> {args.report}")


if __name__ == "__main__":
    main()
