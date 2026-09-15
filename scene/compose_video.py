"""Captions over the rendered frames, then an MP4.

    python scene/compose_video.py --frames out/frames --out out/open_fly.mp4 \
        --font DejaVuSans.ttf --end "line one" --end "line two" ...
"""
import argparse
import glob
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", required=True)
    ap.add_argument("--title", default="A simulated fruit fly brain plays Open Doctrines")
    ap.add_argument("--subtitle", default="FlyWire connectome · 138,639 neurons · 15 million synapses")
    ap.add_argument("--end", action="append", default=[])
    ap.add_argument("--fps", type=int, default=24)
    args = ap.parse_args()

    frames = sorted(glob.glob(os.path.join(args.frames, "frame_*.png")))
    n = len(frames)
    tmp = tempfile.mkdtemp()
    f = lambda s: ImageFont.truetype(args.font, s)
    title_end, end_start = args.fps * 5, n - args.fps * 2

    for i, path in enumerate(frames):
        im = Image.open(path).convert("RGBA")
        w, h = im.size
        s = h / 720
        over = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        if i < title_end:
            a = int(255 * min(1.0, (title_end - i) / args.fps))
            d.rectangle([0, h - int(118 * s), w, h], fill=(0, 0, 0, int(a * 0.62)))
            d.text((int(36 * s), h - int(104 * s)), args.title, font=f(int(38 * s)), fill=(255, 255, 255, a))
            d.text((int(36 * s), h - int(52 * s)), args.subtitle, font=f(int(22 * s)), fill=(242, 184, 75, a))
        if i >= end_start and args.end:
            a = int(255 * min(1.0, (i - end_start + 1) / (args.fps * 0.5)))
            lh = int(46 * s)
            bh = lh * len(args.end) + int(40 * s)
            y0 = (h - bh) // 2
            d.rectangle([int(w * 0.18), y0, int(w * 0.82), y0 + bh], fill=(0, 0, 0, int(a * 0.78)))
            for j, line in enumerate(args.end):
                d.text((w // 2, y0 + int(20 * s) + j * lh), line, font=f(int((32 if j == 0 else 26) * s)),
                       fill=(242, 184, 75, a) if j == 0 else (255, 255, 255, a), anchor="ma")
        d.text((w - int(20 * s), h - int(30 * s)), "opendoctrines.pages.dev", font=f(int(18 * s)),
               fill=(255, 255, 255, 150), anchor="ra")
        Image.alpha_composite(im, over).convert("RGB").save(os.path.join(tmp, f"c_{i + 1:04d}.png"))

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(args.fps),
                    "-i", os.path.join(tmp, "c_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "18", "-movflags", "+faststart", args.out], check=True)
    print("wrote", args.out, n, "frames")


if __name__ == "__main__":
    main()
