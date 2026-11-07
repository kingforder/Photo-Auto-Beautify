#!/usr/bin/env python3
"""Report exposure/contrast anomalies for a photo folder.

RAW files are read from --previews (small JPEG renders); JPG/TIFF originals are
read directly from --images. Generated outputs such as name-rt2.jpg are skipped.

This script only reports. It never edits an image.
"""

import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image

OUTPUT_RE = re.compile(r"-rt\d*$", re.IGNORECASE)


def metrics(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Near-white by luminance: a saturated red flower clipping one channel is
    # not an exposure problem; sky/sun/specular highlights raise luminance.
    hot = lum >= 250
    dark = lum <= 10
    p5, p50, p95, p99 = np.percentile(lum, [5, 50, 95, 99])
    return {
        "width": im.width,
        "height": im.height,
        "mean": round(float(lum.mean()), 1),
        "std": round(float(lum.std()), 1),
        "p5": round(float(p5), 1),
        "p50": round(float(p50), 1),
        "p95": round(float(p95), 1),
        "p99": round(float(p99), 1),
        "range": round(float(p95 - p5), 1),
        "hot_pct": round(float(100 * hot.mean()), 2),
        "dark_pct": round(float(100 * dark.mean()), 2),
        "mean_rb": round(float(r.mean() / max(b.mean(), 1e-6)), 2),
    }


def classify(r):
    """Only prompt-worthy calls; never an instruction to change the photo."""
    if r["mean"] >= 200 and r["range"] <= 80 and r["hot_pct"] >= 20:
        return "强提示：全局过曝/洗白"
    if r["mean"] <= 25 and r["dark_pct"] >= 40:
        return "强提示：全局欠曝"
    if r["hot_pct"] >= 8:
        return "提示：高光裁切明显（可能是亮天空/太阳/灯光）"
    if r["hot_pct"] >= 3:
        return "提示：局部高光（可能是亮天空/灯光）"
    if r["mean"] <= 55 and r["dark_pct"] >= 8:
        return "提示：偏暗（可能是夜景/剪影）"
    if r["range"] <= 55 and 60 <= r["mean"] <= 200:
        return "提示：低对比（可能是雾天/水面）"
    return "正常"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--images", required=True, help="folder with original JPG/TIFF files")
    p.add_argument("--previews", required=True, help="folder with small JPEG renders of RAW files")
    p.add_argument("--report", default="image-check-report.md")
    p.add_argument("--json", default="image-metrics.json")
    args = p.parse_args()

    rows = []

    if os.path.isdir(args.previews):
        for name in sorted(os.listdir(args.previews)):
            if not name.lower().endswith(".jpg"):
                continue
            path = os.path.join(args.previews, name)
            m = metrics(path)
            m.update(source="RAW", name=os.path.splitext(name)[0], path=path)
            rows.append(m)

    for name in sorted(os.listdir(args.images)):
        if not name.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff")):
            continue
        base = os.path.splitext(name)[0]
        if OUTPUT_RE.search(base) or base.endswith("-x"):
            continue
        path = os.path.join(args.images, name)
        m = metrics(path)
        m.update(source="JPG", name=base, path=path)
        rows.append(m)

    for r in rows:
        r["flag"] = classify(r)

    rows.sort(key=lambda r: (r["flag"] == "正常", -r["hot_pct"], r["mean"]))
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    flagged = [r for r in rows if r["flag"] != "正常"]
    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# 图片异常检查报告（仅提示，未修改任何文件）\n\n")
        f.write(
            f"范围：{len(rows)} 张（RAW 预览 + 原 JPG）；"
            "指标：平均亮度 mean、动态范围 p95-p5、高光裁切 hot%、暗部 dark%。\n\n"
        )
        f.write("## 需要你判断的提示\n\n")
        if flagged:
            f.write("| 文件 | 来源 | 判断 | mean | range | hot% | dark% |\n")
            f.write("| --- | --- | --- | ---: | ---: | ---: | ---: |\n")
            for r in flagged:
                f.write(
                    f"| {r['name']} | {r['source']} | {r['flag']} | {r['mean']} | "
                    f"{r['range']} | {r['hot_pct']} | {r['dark_pct']} |\n"
                )
        else:
            f.write("未发现明显异常。\n")
        f.write("\n## 其余\n\n")
        f.write(f"{len(rows) - len(flagged)} 张未发现明显异常。\n")
        f.write(
            "\n> 提示只代表统计上偏离，不代表照片有问题；亮天空、太阳、夜景灯光、"
            "剪影和雾天都可能触发。最终是否处理由你判断。\n"
        )

    print(f"rows={len(rows)} flagged={len(flagged)}")
    for r in flagged:
        print(f"  {r['name']:16} {r['source']:3} {r['flag']}")
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
