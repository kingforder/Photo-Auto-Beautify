#!/usr/bin/env python3
"""Apply a RawTherapee look to every frame of an animated WebP/GIF.

Used after burst preprocessing when the animation was encoded from neutral
frames. Frames are decoded, rendered through RT with the look profile, then
re-encoded; frame durations and loop are preserved.
"""

import argparse
import os
import shutil
import subprocess
import tempfile

from PIL import Image


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="folder of animated WebP/GIF files")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--rt-root", required=True)
    p.add_argument("--look-profile", default="rt-look3.pp3")
    p.add_argument("--temp-dir", help="ASCII temp folder for RT frames")
    p.add_argument("--format", choices=["webp", "gif"], default="webp")
    p.add_argument("--max-width", type=int, default=1280)
    return p.parse_args()


def find_tool(rt_root, name):
    for base in (rt_root, os.path.join(rt_root, "usr", "bin"),
                 os.path.join(rt_root, "squashfs-root", "usr", "bin")):
        for exe in (name + ".exe", name):
            path = os.path.join(base, exe)
            if os.path.isfile(path):
                return path
    raise FileNotFoundError(f"{name} not found under {rt_root}")


def main():
    args = parse_args()
    cli = find_tool(args.rt_root, "rawtherapee-cli")
    look = args.look_profile
    if not os.path.isfile(look):
        here = os.path.dirname(os.path.abspath(__file__))
        look = os.path.join(here, "..", "assets", "looks", args.look_profile)
    if not os.path.isfile(look):
        raise FileNotFoundError(f"look profile not found: {args.look_profile}")

    os.makedirs(args.output_dir, exist_ok=True)
    tmp = args.temp_dir or tempfile.mkdtemp(prefix="burst-anim-beauty-")
    os.makedirs(tmp, exist_ok=True)
    try:
        for name in sorted(os.listdir(args.input)):
            if not name.lower().endswith((".webp", ".gif")):
                continue
            src = os.path.join(args.input, name)
            with Image.open(src) as im:
                frames = []
                durations = []
                for i in range(getattr(im, "n_frames", 1)):
                    im.seek(i)
                    rgb = im.convert("RGB")
                    png = os.path.join(tmp, f"{os.path.splitext(name)[0]}-{i:03d}.png")
                    rgb.save(png, format="PNG")
                    rendered = os.path.join(tmp, f"{os.path.splitext(name)[0]}-{i:03d}.jpg")
                    proc = subprocess.run(
                        [cli, "-o", rendered, "-p", look, "-j92", "-Y", "-c", png],
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    )
                    if proc.returncode != 0:
                        detail = proc.stderr.decode("utf-8", errors="replace")[-200:]
                        raise RuntimeError(f"RT failed for {name} frame {i}: {detail}")
                    with Image.open(rendered) as out:
                        rgb = out.convert("RGB")
                    w, h = rgb.size
                    if w > args.max_width:
                        rgb = rgb.resize((args.max_width, int(h * args.max_width / w)))
                    frames.append(rgb)
                    durations.append(im.info.get("duration", 100))
            if not frames:
                continue
            ext = "webp" if args.format == "webp" else "gif"
            dest = os.path.join(args.output_dir, os.path.splitext(name)[0] + "." + ext)
            if args.format == "gif":
                frames = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for f in frames]
                frames[0].save(dest, save_all=True, append_images=frames[1:],
                               duration=durations, loop=0, optimize=True, disposal=2)
            else:
                frames[0].save(dest, save_all=True, append_images=frames[1:],
                               duration=durations, loop=0, format="WEBP",
                               quality=88, method=6)
            print(f"{name}: {len(frames)} frames -> {dest}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
