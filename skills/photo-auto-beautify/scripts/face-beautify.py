#!/usr/bin/env python3
"""Conservative face beautification for JPEG/PNG/TIFF portraits.

What it does (all local, no generative model):
  * detect faces with OpenCV YuNet (5 landmarks)
  * smooth skin inside a face mask while keeping eyes/brows/lips untouched
  * optionally brighten sclera and teeth a little

It never reshapes the face and never overwrites the source. RAW files must be
converted first (RawTherapee output is fine).
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageOps

try:
    import cv2
except ImportError:
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.environ.get("FACE_DEPS"),
        os.path.join(here, "..", "..", "face-deps"),
    ):
        if candidate and os.path.isdir(candidate):
            sys.path.insert(0, os.path.abspath(candidate))
            break
    import cv2

DEFAULT_MODEL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "assets",
    "models",
    "face_detection_yunet_2023mar.onnx",
)
STRENGTH = {1: 0.35, 2: 0.55, 3: 0.72}


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0


def dedupe(faces):
    """YuNet can report the same face twice; keep the best box per cluster."""
    out = []
    for f in sorted(faces, key=lambda v: float(v[-1]), reverse=True):
        if all(iou(f[:4], g[:4]) < 0.35 for g in out):
            out.append(f)
    return out


def detect(img, model, threshold):
    h, w = img.shape[:2]
    # YuNet is trained around ~1k-pixel faces; downscaling large images makes
    # detection both faster and much more reliable (and avoids duplicate boxes).
    scale = min(1.0, 1600.0 / max(h, w))
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1 else img
    sh, sw = small.shape[:2]
    det = cv2.FaceDetectorYN.create(model, "", (sw, sh), threshold, 0.3, 5000)
    _, faces = det.detect(small)
    if faces is None:
        return []
    faces = dedupe(faces)
    if scale < 1:
        for f in faces:
            f[:14] /= scale
    return faces


def feather(mask, sigma):
    return cv2.GaussianBlur(mask, (0, 0), max(1.0, sigma))


def process_face(img, face, strength, do_eyes, do_teeth):
    h, w = img.shape[:2]
    x, y, bw, bh = [float(v) for v in face[:4]]
    x, y = max(0, x), max(0, y)
    bw, bh = min(bw, w - x), min(bh, h - y)
    if bw < 30 or bh < 30:
        return img

    # 5 landmarks: right eye, left eye, nose, right mouth corner, left mouth corner
    pts = face[4:14].reshape(5, 2).astype(np.float32)
    eyes = pts[:2]
    mouth = pts[3:5]
    mouth_center = mouth.mean(axis=0)

    face_mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(
        face_mask,
        (int(x + bw / 2), int(y + bh / 2)),
        (int(bw * 0.47), int(bh * 0.56)),
        0, 0, 360, 255, -1,
    )
    # Exclude eyes, brows and lips from skin smoothing.
    for ex, ey in eyes:
        r = max(8, int(bw * 0.14))
        cv2.circle(face_mask, (int(ex), int(ey)), r, 0, -1)
        cv2.ellipse(
            face_mask,
            (int(ex), int(ey - bh * 0.12)),
            (int(bw * 0.17), int(bh * 0.07)),
            0, 0, 360, 0, -1,
        )
    cv2.ellipse(
        face_mask,
        (int(mouth_center[0]), int(mouth_center[1])),
        (int(bw * 0.30), int(bh * 0.12)),
        0, 0, 360, 0, -1,
    )
    face_mask = feather(face_mask, bw * 0.02).astype(np.float32) / 255.0

    smooth = cv2.bilateralFilter(img, 0, 28, max(6, int(bw * 0.02)))
    # Keep some original micro-texture so skin does not become plastic.
    smooth = cv2.addWeighted(smooth, 0.82, img, 0.18, 0)
    alpha = (face_mask * strength)[..., None]
    out = img.astype(np.float32) * (1 - alpha) + smooth.astype(np.float32) * alpha
    out = np.clip(out, 0, 255).astype(np.uint8)

    if do_eyes:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
        for ex, ey in eyes:
            r = max(10, int(bw * 0.13))
            m = np.zeros((h, w), np.uint8)
            cv2.circle(m, (int(ex), int(ey)), r, 255, -1)
            m = feather(m, r * 0.35).astype(np.float32) / 255.0
            sclera = ((hsv[..., 1] < 80) & (hsv[..., 2] > 90)).astype(np.float32)
            mm = (m * sclera * 0.35)[..., None]
            out = np.clip(out.astype(np.float32) + (255 - out.astype(np.float32)) * mm, 0, 255).astype(np.uint8)

    if do_teeth:
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
        m = np.zeros((h, w), np.uint8)
        cv2.ellipse(
            m,
            (int(mouth_center[0]), int(mouth_center[1])),
            (int(bw * 0.24), int(bh * 0.08)),
            0, 0, 360, 255, -1,
        )
        m = feather(m, bw * 0.01).astype(np.float32) / 255.0
        teeth = ((hsv[..., 1] < 55) & (hsv[..., 2] > 110)).astype(np.float32)
        mm = (m * teeth * 0.30)[..., None]
        out = np.clip(out.astype(np.float32) + (255 - out.astype(np.float32)) * mm, 0, 255).astype(np.uint8)

    return out


def beautify(path, model, strength, do_eyes, do_teeth, min_face_ratio=0.04, max_faces=3):
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    faces = detect(img, model, 0.6)
    all_faces = faces
    # Ignore background/tiny faces: they cannot be beautified meaningfully and
    # are often false positives (backs of heads, statues, patterns).
    min_w = img.shape[1] * min_face_ratio
    faces = [f for f in faces if float(f[2]) >= min_w]
    if not faces:
        return None, 0, "no usable face"
    if len(faces) > max_faces or len(all_faces) > max_faces * 4:
        return None, len(all_faces), f"group photo ({len(all_faces)} faces)"
    out = img
    for face in faces:
        out = process_face(out, face, strength, do_eyes, do_teeth)
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB), len(faces), "ok"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output")
    p.add_argument("--suffix", default="-face")
    p.add_argument("--strength", type=int, choices=[1, 2, 3], default=2)
    p.add_argument("--min-face-ratio", type=float, default=0.04,
                   help="skip faces narrower than this fraction of image width")
    p.add_argument("--max-faces", type=int, default=3,
                   help="skip group photos with more usable faces than this")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--no-eyes", action="store_true")
    p.add_argument("--no-teeth", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="only report detected faces")
    p.add_argument("--report", default="face-report.md")
    args = p.parse_args()

    if not os.path.isfile(args.model):
        raise SystemExit(f"YuNet model not found: {args.model}")
    outdir = args.output or args.input
    os.makedirs(outdir, exist_ok=True)
    exts = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
    files = [
        f for f in sorted(os.listdir(args.input))
        if f.lower().endswith(exts) and not f.lower().endswith("-face" + os.path.splitext(f)[1])
    ]

    rows = []
    for name in files:
        src = os.path.join(args.input, name)
        try:
            out_img, count, reason = beautify(
                src, args.model, STRENGTH[args.strength],
                not args.no_eyes, not args.no_teeth,
                args.min_face_ratio, args.max_faces,
            )
        except Exception as e:
            rows.append({"file": name, "faces": 0, "status": f"error: {e}"})
            continue

        if reason != "ok":
            rows.append({"file": name, "faces": count, "status": f"skipped: {reason}"})
            continue
        if args.dry_run:
            rows.append({"file": name, "faces": count, "status": "dry-run"})
            continue

        dst = os.path.join(outdir, os.path.splitext(name)[0] + args.suffix + ".jpg")
        Image.fromarray(out_img).save(dst, quality=95, subsampling=0)
        rows.append({"file": name, "faces": count, "status": "ok", "output": dst})

    with open(args.report, "w", encoding="utf-8-sig") as f:
        f.write("# 人像美化报告（仅生成新文件，不改原图）\n\n")
        f.write(f"输入：{args.input}\n\n")
        f.write("| 文件 | 检测到人脸 | 状态 |\n| --- | ---: | --- |\n")
        for r in rows:
            f.write(f"| {r['file']} | {r['faces']} | {r['status']} |\n")
        f.write("\n> 仅做皮肤平滑与轻微眼白/牙齿提亮；不做瘦脸、不生成内容。\n")
    print(f"processed={len(rows)} ok={sum(r['status'] == 'ok' for r in rows)} report={args.report}")
    for r in rows:
        print(f"  {r['file']}: faces={r['faces']} {r['status']}")


if __name__ == "__main__":
    main()
