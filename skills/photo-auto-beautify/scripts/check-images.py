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
        return "Strong hint: global overexposure/washed out"
    if r["mean"] <= 25 and r["dark_pct"] >= 40:
        return "Strong hint: global underexposure"
    if r["hot_pct"] >= 8:
        return "Hint: obvious highlight clipping (bright sky/sun/lights)"
    if r["hot_pct"] >= 3:
        return "Hint: local highlights (bright sky/lights)"
    if r["mean"] <= 55 and r["dark_pct"] >= 8:
        return "Hint: dark (night/silhouette)"
    if r["range"] <= 55 and 60 <= r["mean"] <= 200:
        return "Hint: low contrast (fog/water)"
    return "OK"


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

    rows.sort(key=lambda r: (r["flag"] == "OK", -r["hot_pct"], r["mean"]))
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    flagged = [r for r in rows if r["flag"] != "OK"]
    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# Image anomaly check (suggestions only; no files modified)\n\n")
        f.write(
            f"Scope: {len(rows)} images (RAW previews + original JPG); "
            "metrics: mean luminance, dynamic range p95-p5, highlight clipping hot%, dark%.\n\n"
        )
        f.write("## Items for your judgment\n\n")
        if flagged:
            f.write("| File | Source | Finding | mean | range | hot% | dark% |\n")
            f.write("| --- | --- | --- | ---: | ---: | ---: | ---: |\n")
            for r in flagged:
                f.write(
                    f"| {r['name']} | {r['source']} | {r['flag']} | {r['mean']} | "
                    f"{r['range']} | {r['hot_pct']} | {r['dark_pct']} |\n"
                )
        else:
            f.write("No obvious anomalies found.\n")
        f.write("\n## Others\n\n")
        f.write(f"{len(rows) - len(flagged)} images showed no obvious anomaly.\n")
        f.write(
            "\n> Flags indicate statistical deviation, not a bad photo; bright sky, sun, "
            "night lights, silhouettes and fog can all trigger them. Whether to act is your call.\n"
        )

    print(f"rows={len(rows)} flagged={len(flagged)}")
    for r in flagged:
        print(f"  {r['name']:16} {r['source']:3} {r['flag']}")
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
