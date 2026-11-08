#!/usr/bin/env python3
"""Detect bursts, pick the best frame, and optionally stack or animate them.

Local, non-destructive, open-source only:
  * burst grouping by EXIF time + camera + perceptual-hash similarity
  * best-frame selection by sharpness and clipping
  * optional pixel stacking (median/mean/exposure fusion)
  * optional animated WebP/GIF
  * JSON + Markdown manifest; originals are never modified

RAW files can be grouped from metadata, but stacking/animation needs a
decodable raster; use JPG/PNG/TIFF (or render RAW first) for pixel output.
"""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps

try:
    import cv2
except ImportError:
    sys.exit("OpenCV is required: pip install opencv-python-headless")

if hasattr(cv2, "setLogLevel"):
    cv2.setLogLevel(0)

RASTER_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
RAW_EXT = {".rw2", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".dng"}


def parse_args():
    p = argparse.ArgumentParser(description="Detect and process photo bursts locally.")
    p.add_argument("--input", required=True, help="folder of photos")
    p.add_argument("--output-dir", help="default: <input>/bursts")
    p.add_argument("--raster-dir",
                   help="optional folder of rendered JPGs matching RAW stems, used for pixels")
    p.add_argument("--min-frames", type=int, default=3)
    p.add_argument("--gap", type=float, default=1.5, help="max seconds between frames")
    p.add_argument("--hash-distance", type=int, default=14)
    p.add_argument("--stack", action="store_true", help="write a median/mean/fusion stack")
    p.add_argument("--stack-mode", choices=["median", "mean", "fusion"], default="median")
    p.add_argument("--force-stack", action="store_true",
                   help="stack even when motion/ghosting is detected")
    p.add_argument("--motion-threshold", type=float, default=0.08,
                   help="fraction of changed pixels that marks motion (default 0.08)")
    p.add_argument("--highlight-threshold", type=float, default=0.09,
                   help="fraction of changed bright pixels that marks moving highlights")
    p.add_argument("--animate", action="store_true", help="write animated WebP/GIF")
    p.add_argument("--animate-format", choices=["webp", "gif"], default="webp")
    p.add_argument("--max-animate-frames", type=int, default=24)
    p.add_argument("--max-width", type=int, default=1280)
    p.add_argument("--fps", type=float, default=10.0)
    p.add_argument("--best-per-burst", type=int, default=1,
                   help="number of best frames to save per burst (default 1)")
    p.add_argument("--no-save-best", action="store_true",
                   help="do not copy selected best frames")
    p.add_argument("--apply-cleanup", action="store_true",
                   help="move non-best burst RAW files to --trash-dir")
    p.add_argument("--trash-dir",
                   help="default: <input>/待删除; only used with --apply-cleanup")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def exif_value(exif, tag):
    try:
        value = exif.get(tag)
        if value:
            return str(value).strip()
    except Exception:
        pass
    return ""


def exiftool_metadata(path):
    """Optional EXIF fallback for RAW files when exiftool is installed."""
    exe = shutil.which("exiftool")
    if not exe:
        return {}
    try:
        out = subprocess.run(
            [exe, "-j", "-DateTimeOriginal", "-Make", "-Model", "-ImageWidth",
             "-ImageHeight", path],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return {}
        row = json.loads(out.stdout)[0]
        return {
            "datetime": row.get("DateTimeOriginal", ""),
            "make": row.get("Make", ""),
            "model": row.get("Model", ""),
            "width": int(row.get("ImageWidth") or 0),
            "height": int(row.get("ImageHeight") or 0),
        }
    except Exception:
        return {}


def parse_datetime(raw):
    raw = (raw or "").strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except Exception:
            pass
    return None


def filename_time(name):
    match = re.search(r"(20\d{6})[_-](\d{6})", os.path.basename(name))
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S").timestamp()
    except Exception:
        return None


def read_metadata(path):
    """Return capture time, camera and dimensions; fall back to EXIF tool,
    filename timestamp, then mtime."""
    dt = None
    make = model = ""
    width = height = 0
    try:
        with Image.open(path) as im:
            width, height = im.size
            exif = im.getexif()
            make = exif_value(exif, 271)
            model = exif_value(exif, 272)
            raw = exif_value(exif, 36867) or exif_value(exif, 306)
            sub = exif_value(exif, 37521)
            if raw:
                dt = parse_datetime(raw)
                if dt is not None and sub:
                    dt += float("0." + sub)
    except Exception:
        pass

    if dt is None:
        extra = exiftool_metadata(path)
        if extra:
            dt = parse_datetime(extra.get("datetime"))
            make = make or extra.get("make", "")
            model = model or extra.get("model", "")
            width = width or extra.get("width", 0)
            height = height or extra.get("height", 0)

    if dt is None:
        dt = filename_time(path)
    if dt is None:
        try:
            dt = os.path.getmtime(path)
        except OSError:
            dt = 0.0
    return {
        "path": os.path.abspath(path),
        "name": os.path.basename(path),
        "mtime": dt,
        "make": make,
        "model": model,
        "width": width,
        "height": height,
    }


def load_rgb(path):
    with Image.open(path) as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))


def dhash(rgb, size=8):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def hamming(a, b):
    return int(a ^ b).bit_count()


def sharpness(rgb):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    y0, y1 = int(h * 0.12), int(h * 0.88)
    x0, x1 = int(w * 0.12), int(w * 0.88)
    crop = gray[y0:y1, x0:x1]
    if crop.size == 0:
        crop = gray
    return float(cv2.Laplacian(crop, cv2.CV_64F).var())


def clipping_penalty(rgb):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hot = float((gray >= 250).mean())
    dark = float((gray <= 5).mean())
    return min(1.0, hot * 2.0 + dark * 1.5)


def add_image_metrics(frame):
    frame["hash"] = None
    frame["sharp"] = 0.0
    frame["clip"] = 0.0
    frame["score"] = 0.0
    pixel_path = frame.get("pixel_path", frame["path"])
    if not pixel_path.lower().endswith(tuple(RASTER_EXT)):
        return frame
    try:
        rgb = load_rgb(pixel_path)
        frame["hash"] = dhash(rgb)
        frame["sharp"] = sharpness(rgb)
        frame["clip"] = clipping_penalty(rgb)
        frame["score"] = frame["sharp"] * (1.0 - 0.8 * frame["clip"])
    except Exception as exc:
        frame["error"] = str(exc)
    return frame


def matching_raster(path, raster_dir):
    if not raster_dir:
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
        candidate = os.path.join(raster_dir, stem + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def scan(input_dir, raster_dir=None):
    frames = []
    for name in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(name)[1].lower()
        if ext not in RASTER_EXT | RAW_EXT:
            continue
        path = os.path.join(input_dir, name)
        if not os.path.isfile(path):
            continue
        meta = read_metadata(path)
        meta["ext"] = ext
        meta["pixel_path"] = matching_raster(path, raster_dir) or path
        frames.append(add_image_metrics(meta))
    frames.sort(key=lambda f: (f["mtime"], f["name"]))
    return frames


def same_camera(a, b):
    if a["make"] and b["make"] and a["make"].lower() != b["make"].lower():
        return False
    if a["model"] and b["model"] and a["model"].lower() != b["model"].lower():
        return False
    if a["width"] and b["width"] and abs(a["width"] - b["width"]) > 2:
        return False
    if a["height"] and b["height"] and abs(a["height"] - b["height"]) > 2:
        return False
    return True


def same_scene(a, b, max_distance):
    if a["hash"] is None or b["hash"] is None:
        return True
    return hamming(a["hash"], b["hash"]) <= max_distance


def group_frames(frames, gap, min_frames, max_distance):
    groups = []
    current = []
    for frame in frames:
        if not current:
            current = [frame]
            continue
        prev = current[-1]
        close = 0 <= (frame["mtime"] - prev["mtime"]) <= gap
        if close and same_camera(prev, frame) and same_scene(prev, frame, max_distance):
            current.append(frame)
        else:
            if len(current) >= min_frames:
                groups.append(current)
            current = [frame]
    if len(current) >= min_frames:
        groups.append(current)
    return groups


def best_frame(group):
    return max(group, key=lambda f: (f["score"], f["sharp"]))


def best_frames(group, count):
    valid = [
        f for f in group
        if f.get("hash") is not None or f.get("score", 0) > 0
    ]
    pool = valid or group
    return sorted(pool, key=lambda f: (f["score"], f["sharp"]), reverse=True)[:max(1, count)]


def unique_path(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{stem}-{i}{ext}"):
        i += 1
    return f"{stem}-{i}{ext}"


def ensure_best_in_root(selected, input_dir, best_dir, dry_run=False):
    """Best frames must live in the input folder; stage copies are moved back
    or removed. Returns the root paths (or planned paths in dry-run)."""
    saved = []
    for frame in selected:
        root_path = os.path.join(input_dir, frame["name"])
        staged = []
        if os.path.isdir(best_dir):
            staged = [
                os.path.join(best_dir, n) for n in os.listdir(best_dir)
                if n.endswith(frame["name"])
            ]
        if os.path.exists(root_path):
            saved.append(root_path)
            if not dry_run:
                for extra in staged:
                    if os.path.abspath(extra) != os.path.abspath(root_path):
                        os.remove(extra)
            continue
        if not staged:
            raise FileNotFoundError(f"missing best frame: {frame['name']}")
        if dry_run:
            saved.append(root_path)
            continue
        os.makedirs(input_dir, exist_ok=True)
        dest = unique_path(root_path)
        shutil.move(staged[0], dest)
        for extra in staged[1:]:
            os.remove(extra)
        saved.append(dest)
    if not dry_run and os.path.isdir(best_dir) and not os.listdir(best_dir):
        os.rmdir(best_dir)
    return saved


def move_non_best(group, selected, trash_dir, dry_run=False):
    keep = {f["name"] for f in selected}
    moved = []
    for frame in group:
        if frame["name"] in keep:
            continue
        if frame["ext"] not in RAW_EXT:
            continue
        if dry_run:
            moved.append(os.path.join(trash_dir, frame["name"]))
            continue
        os.makedirs(trash_dir, exist_ok=True)
        dest = unique_path(os.path.join(trash_dir, frame["name"]))
        shutil.move(frame["path"], dest)
        moved.append(dest)
    return moved


def format_time(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def resize_for_align(rgb, max_side=1600):
    h, w = rgb.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale >= 1.0:
        return rgb, 1.0
    return cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA), scale


def align_to(reference, moving):
    """Return moving warped to reference; fall back to unchanged on failure."""
    ref_small, scale = resize_for_align(reference)
    mov_small, _ = resize_for_align(moving)
    ref_gray = cv2.cvtColor(ref_small, cv2.COLOR_RGB2GRAY)
    mov_gray = cv2.cvtColor(mov_small, cv2.COLOR_RGB2GRAY)
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5)
    try:
        _, warp = cv2.findTransformECC(
            ref_gray, mov_gray, warp, cv2.MOTION_EUCLIDEAN, criteria, None, 5
        )
    except cv2.error:
        return moving, False
    if scale != 1.0:
        warp = warp.copy()
        warp[0, 2] /= scale
        warp[1, 2] /= scale
    h, w = moving.shape[:2]
    aligned = cv2.warpAffine(
        moving, warp, (w, h),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REFLECT,
    )
    return aligned, True


def load_frames(group, best):
    """Return decodable frames plus the index of the best frame, if present."""
    out = []
    best_index = None
    for frame in group:
        try:
            rgb = load_rgb(frame.get("pixel_path", frame["path"]))
        except Exception:
            continue
        if frame is best:
            best_index = len(out)
        out.append(rgb)
    return out, best_index


def crop_common(images, border_ratio=0.02):
    h = min(im.shape[0] for im in images)
    w = min(im.shape[1] for im in images)
    images = [cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA) for im in images]
    b = int(min(h, w) * border_ratio)
    return [im[b:h - b, b:w - b] for im in images]


def write_stack(group, best, path, mode, force=False, motion_threshold=0.08,
                highlight_threshold=0.09):
    frames, best_index = load_frames(group, best)
    if len(frames) < 2:
        return None, "not enough decodable frames"
    ref = frames[best_index] if best_index is not None else frames[len(frames) // 2]
    aligned = []
    for im in frames:
        warped, _ = align_to(ref, im)
        aligned.append(warped)
    aligned = crop_common(aligned)
    if not aligned:
        return None, "empty aligned frames"

    ref_i = aligned[0].astype(np.int16)
    changed_mask = np.zeros(ref_i.shape[:2], dtype=bool)
    for im in aligned[1:]:
        diff = np.abs(im.astype(np.int16) - ref_i)
        changed_mask |= diff.max(axis=2) > 24
    changed = float(changed_mask.mean())
    if changed > motion_threshold and not force:
        return None, f"motion detected ({changed * 100:.1f}% changed); skipped stack; use best/animation"

    bright = ref_i.max(axis=2) > 180
    highlight_motion = float(changed_mask[bright].mean()) if bright.any() else 0.0
    if highlight_motion > highlight_threshold and not force:
        return None, (
            f"moving highlight detected ({highlight_motion * 100:.1f}% bright pixels); "
            "skipped stack; use best/animation"
        )

    stack = np.stack([im.astype(np.float32) for im in aligned], axis=0)
    mode_label = mode
    if mode == "mean":
        out = stack.mean(axis=0)
    elif mode == "fusion":
        # Mertens fusion needs exposure diversity; identical frames can yield
        # a black result, so fall back to mean when the burst is flat.
        means = [float(im.mean()) for im in aligned]
        if max(means) - min(means) < 2.0:
            out = stack.mean(axis=0)
            mode_label = "mean fallback (no exposure diversity)"
        else:
            merge = cv2.createMergeMertens()
            out = merge.process([im.astype(np.float32) / 255.0 for im in aligned]) * 255.0
    else:
        out = np.median(stack, axis=0)
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(path, quality=95, subsampling=0)
    return path, f"{mode_label} stack of {len(aligned)} frames"


def load_animated_frames(group, best, max_width):
    frames, best_index = load_frames(group, best)
    if len(frames) < 2:
        return [], []
    ref = frames[best_index] if best_index is not None else frames[len(frames) // 2]
    aligned = []
    for im in frames:
        warped, _ = align_to(ref, im)
        aligned.append(warped)
    aligned = crop_common(aligned)
    h, w = aligned[0].shape[:2]
    if w > max_width:
        nh = int(h * max_width / w)
        aligned = [cv2.resize(im, (max_width, nh), interpolation=cv2.INTER_AREA) for im in aligned]
    rgb_frames = [Image.fromarray(im) for im in aligned]
    durations = []
    for i in range(1, len(group)):
        delta = group[i]["mtime"] - group[i - 1]["mtime"]
        durations.append(int(np.clip(delta * 1000.0, 40, 250)))
    durations.append(100)
    return rgb_frames, durations


def write_animation(group, best, path, fmt, max_width, fps, max_frames):
    rgb, durations = load_animated_frames(group, best, max_width)
    if len(rgb) < 2:
        return None, "not enough decodable frames"
    if len(rgb) > max_frames:
        step = max(1, math.ceil(len(rgb) / max_frames))
        rgb = rgb[::step]
        durations = durations[::step]
    if len(durations) != len(rgb):
        durations = [int(1000 / max(fps, 1))] * len(rgb)
    if fmt == "gif":
        rgb = [im.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for im in rgb]
        rgb[0].save(
            path, save_all=True, append_images=rgb[1:], duration=durations,
            loop=0, optimize=True, disposal=2,
        )
    else:
        rgb[0].save(
            path, save_all=True, append_images=rgb[1:], duration=durations,
            loop=0, format="WEBP", quality=88, method=6,
        )
    return path, f"{len(rgb)} frames, {fmt}"


def main():
    args = parse_args()
    input_dir = os.path.abspath(args.input)
    out_dir = os.path.abspath(args.output_dir or os.path.join(input_dir, "bursts"))
    if not os.path.isdir(input_dir):
        raise SystemExit(f"input not found: {input_dir}")

    frames = scan(input_dir, os.path.abspath(args.raster_dir) if args.raster_dir else None)
    groups = group_frames(frames, args.gap, args.min_frames, args.hash_distance)
    results = []
    selected_by_id = {}
    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)

    for idx, group in enumerate(groups, 1):
        best = best_frame(group)
        prefix = os.path.splitext(best["name"])[0]
        selected = best_frames(group, args.best_per_burst)
        item = {
            "id": f"burst-{idx:03d}",
            "prefix": prefix,
            "frames": [f["name"] for f in group],
            "start": format_time(group[0]["mtime"]),
            "end": format_time(group[-1]["mtime"]),
            "best": best["name"],
            "best_score": round(best["score"], 2),
            "best_frames": [f["name"] for f in selected],
            "best_files": [],
            "stack": None,
            "animation": None,
            "moved": [],
        }
        if args.apply_cleanup or not args.no_save_best:
            try:
                item["best_files"] = ensure_best_in_root(
                    selected, input_dir, os.path.join(out_dir, "best"),
                    args.dry_run,
                )
            except Exception as exc:
                item["best_note"] = f"best save failed: {exc}"
        if not args.dry_run and args.stack:
            path = os.path.join(out_dir, f"{prefix}-stack.jpg")
            out, note = write_stack(
                group, best, path, args.stack_mode,
                args.force_stack, args.motion_threshold, args.highlight_threshold,
            )
            item["stack"] = os.path.basename(out) if out else None
            item["stack_note"] = note
        if not args.dry_run and args.animate:
            ext = "webp" if args.animate_format == "webp" else "gif"
            path = os.path.join(out_dir, f"{prefix}.{ext}")
            out, note = write_animation(
                group, best, path, args.animate_format,
                args.max_width, args.fps, args.max_animate_frames,
            )
            item["animation"] = os.path.basename(out) if out else None
            item["animation_note"] = note
        results.append(item)
        selected_by_id[item["id"]] = selected

    trash_dir = os.path.abspath(
        args.trash_dir or os.path.join(input_dir, "待删除")
    )
    moved_all = []
    if args.apply_cleanup:
        for group, item in zip(groups, results):
            if item.get("best_note"):
                item["moved_note"] = "skipped cleanup: best save failed"
                continue
            moved = move_non_best(
                group, selected_by_id[item["id"]], trash_dir, args.dry_run
            )
            item["moved"] = [os.path.basename(p) for p in moved]
            moved_all.extend(moved)

    if not args.dry_run:
        with open(os.path.join(out_dir, "bursts.json"), "w", encoding="utf-8") as fh:
            json.dump({
                "input": input_dir,
                "min_frames": args.min_frames,
                "gap_seconds": args.gap,
                "best_per_burst": args.best_per_burst,
                "cleanup": {
                    "applied": bool(args.apply_cleanup),
                    "trash_dir": trash_dir if args.apply_cleanup else None,
                    "moved": [os.path.basename(p) for p in moved_all],
                },
                "bursts": results,
            }, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(out_dir, "bursts.md"), "w", encoding="utf-8") as fh:
            fh.write("# Burst detection report\n\n")
            fh.write(f"Input: {input_dir}\n\n")
            fh.write(f"Bursts: {len(results)} (min {args.min_frames} frames, gap {args.gap}s)\n\n")
            fh.write(f"Best frames per burst: {args.best_per_burst}\n\n")
            fh.write("| Burst | Frames | Best | Saved | Stack | Animation | Moved |\n")
            fh.write("| --- | --- | --- | --- | --- | --- | --- |\n")
            for item in results:
                fh.write(
                    f"| {item['id']} | {len(item['frames'])} | {item['best']} | "
                    f"{len(item['best_files'])} | {item['stack'] or '-'} | "
                    f"{item['animation'] or '-'} | {len(item['moved'])} |\n"
                )
            if args.apply_cleanup:
                fh.write(f"\nCleanup: moved {len(moved_all)} RAW files to `{trash_dir}`.\n")
    for item in results:
        print(
            f"{item['id']}: {len(item['frames'])} frames, best={item['best']}, "
            f"saved={len(item['best_files'])}, moved={len(item['moved'])}"
        )
    print(f"bursts={len(results)} output={out_dir if not args.dry_run else '(dry-run)'}")
    if args.apply_cleanup:
        print(f"cleanup={'planned' if args.dry_run else 'applied'} trash={trash_dir}")


if __name__ == "__main__":
    main()
