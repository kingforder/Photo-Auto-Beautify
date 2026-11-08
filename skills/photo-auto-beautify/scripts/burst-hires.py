#!/usr/bin/env python3
"""Render selected burst groups from RAW at higher resolution, then stack.

Reads a bursts.json produced by burst-detect.py. RAW frames are rendered with
RawTherapee using the same look pipeline, downscaled only to a safe working
size, aligned and stacked. Original files are never modified.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="folder containing original RAW files")
    p.add_argument("--bursts", required=True, help="bursts.json from burst-detect.py")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--rt-root", required=True)
    p.add_argument("--look-profile", default="rt-look3.pp3")
    p.add_argument("--auto-profile", default="Auto-Matched Curve - ISO Low.pp3")
    p.add_argument("--max-side", type=int, default=3000)
    p.add_argument("--temp-dir", help="ASCII temp folder for RawTherapee output")
    p.add_argument("--groups", default="", help="comma-separated burst ids; default all with a stack")
    return p.parse_args()


def find_tool(rt_root, name):
    for base in (rt_root, os.path.join(rt_root, "usr", "bin"),
                 os.path.join(rt_root, "squashfs-root", "usr", "bin")):
        for exe in (name + ".exe", name):
            path = os.path.join(base, exe)
            if os.path.isfile(path):
                return path
    raise FileNotFoundError(f"{name} not found under {rt_root}")


def profile_dir(rt_root):
    for base in (rt_root, os.path.join(rt_root, "usr", "bin"),
                 os.path.join(rt_root, "squashfs-root", "usr", "bin")):
        path = os.path.join(base, "profiles")
        if os.path.isdir(path):
            return path
    raise FileNotFoundError(f"RawTherapee profiles not found under {rt_root}")


def load_burst_module():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "burst-detect.py")
    spec = importlib.util.spec_from_file_location("burst_detect", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = parse_args()
    bd = load_burst_module()
    with open(args.bursts, encoding="utf-8") as fh:
        manifest = json.load(fh)
    wanted = {g.strip() for g in args.groups.split(",") if g.strip()}
    items = [
        item for item in manifest.get("bursts", [])
        if item.get("stack") and (not wanted or item["id"] in wanted)
    ]
    if not items:
        raise SystemExit("no stacked groups selected")

    cli = find_tool(args.rt_root, "rawtherapee-cli")
    auto = os.path.join(profile_dir(args.rt_root), args.auto_profile)
    look = args.look_profile
    if not os.path.isfile(look):
        look = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "assets", "looks", args.look_profile)
    if not os.path.isfile(look):
        raise FileNotFoundError(f"look profile not found: {args.look_profile}")

    os.makedirs(args.output_dir, exist_ok=True)
    tmp = args.temp_dir or tempfile.mkdtemp(prefix="burst-hires-")
    os.makedirs(tmp, exist_ok=True)
    rows = []
    try:
        for item in items:
            frames = []
            for name in item["frames"]:
                source = os.path.join(args.input, name)
                if not os.path.isfile(source):
                    continue
                rendered = os.path.join(tmp, os.path.splitext(name)[0] + ".jpg")
                cmd = [cli, "-o", rendered, "-p", auto, "-p", look,
                       "-j95", "-Y", "-c", source]
                proc = subprocess.run(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                if proc.returncode != 0:
                    detail = proc.stderr.decode("utf-8", errors="replace")[-300:]
                    raise RuntimeError(f"RT failed for {name}: {detail}")
                rgb = bd.load_rgb(rendered)
                h, w = rgb.shape[:2]
                scale = min(1.0, args.max_side / max(h, w))
                if scale < 1.0:
                    rgb = bd.cv2.resize(
                        rgb, (int(w * scale), int(h * scale)),
                        interpolation=bd.cv2.INTER_AREA,
                    )
                    out = os.path.join(tmp, os.path.splitext(name)[0] + "-scaled.jpg")
                    Image.fromarray(rgb).save(out, quality=95, subsampling=0)
                else:
                    out = rendered
                frames.append({"name": name, "path": source, "pixel_path": out})
            if len(frames) < 2:
                rows.append((item["id"], 0, "not enough rendered frames"))
                continue
            best = next((f for f in frames if f["name"] == item["best"]), frames[0])
            prefix = os.path.splitext(item["best"])[0]
            dest = os.path.join(args.output_dir, f"{prefix}-hires-stack.jpg")
            out, note = bd.write_stack(frames, best, dest, "median", force=False)
            rows.append((item["id"], len(frames), note if out else note))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    lines = [
        "# High-resolution burst stacks",
        "",
        f"Input: {os.path.abspath(args.input)}",
        f"Bursts: {os.path.abspath(args.bursts)}",
        "",
        "| Burst | Frames | Result |",
        "| --- | --- | --- |",
    ]
    for bid, count, note in rows:
        lines.append(f"| {bid} | {count} | {note} |")
    with open(os.path.join(args.output_dir, "hires-stacks.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    for bid, count, note in rows:
        print(f"{bid}: frames={count} {note}")


if __name__ == "__main__":
    main()
