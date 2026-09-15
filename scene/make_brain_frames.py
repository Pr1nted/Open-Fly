"""The fly's brain, one transparent PNG per video frame, from its recorded spikes.

Every neuron sits at its FlyWire position (voxel coordinates x 4, 4, 40 nm) and
glows faintly; the ones that fired during a turn's 200 ms flash and decay.
Descending neurons -- the ones read as orders -- are amber. The brain turns
slowly so its depth reads in a still video.

    python scene/make_brain_frames.py --positions positions.npz --spikes spikes.npz \
        --frames 769 --out out/brain [--size 1280x720]
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", required=True)
    ap.add_argument("--spikes", required=True)
    ap.add_argument("--frames", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--frames-per-turn", type=int, default=6)
    ap.add_argument("--turns", type=int, default=120)
    args = ap.parse_args()
    W, H = (int(v) for v in args.size.split("x"))
    os.makedirs(args.out, exist_ok=True)

    P = np.load(args.positions, allow_pickle=False)
    Z = np.load(args.spikes)
    pos = P["pos"].astype(np.float64)
    sc = P["super_class"]
    missing = np.isnan(pos).any(axis=1)
    nm = pos * np.array([4.0, 4.0, 40.0])
    lo, hi = np.nanmin(nm, 0), np.nanmax(nm, 0)
    c = (lo + hi) / 2
    s = 1.0 / (hi[0] - lo[0])
    x = np.nan_to_num((nm[:, 0] - c[0]) * s)
    y = np.nan_to_num(-(nm[:, 1] - c[1]) * s)
    z = np.nan_to_num((nm[:, 2] - c[2]) * s)
    keep = ~missing

    n = len(pos)
    base = np.tile(np.array([0.30, 0.62, 0.58]), (n, 1))
    weight = np.full(n, 0.28)
    optic = np.isin(sc, ["optic", "visual_projection", "visual_centrifugal"])
    base[optic] = (0.30, 0.48, 0.58); weight[optic] = 0.16
    sens = np.isin(sc, ["sensory", "sensory_ascending"])
    base[sens] = (0.50, 0.82, 0.68); weight[sens] = 0.34
    dn = np.zeros(n, bool); dn[Z["dn"]] = True
    base[dn] = (0.95, 0.68, 0.25); weight[dn] = 1.6
    hot = np.array([1.0, 0.95, 0.80])

    act = np.zeros(n)
    last = -1
    decay = np.exp(-7.0 / args.fps)
    for k in range(args.frames):
        turn = min(args.turns - 1, k // args.frames_per_turn)
        if turn != last:
            idx, cnt = Z[f"idx_{turn}"], Z[f"cnt_{turn}"].astype(np.float64)
            act[idx] = np.maximum(act[idx], np.minimum(1.0, 0.45 + 0.18 * np.log2(1 + cnt)))
            last = turn
        else:
            act *= decay
            act[act < 0.002] = 0

        ang = k / args.fps * 0.2
        ca, sa = np.cos(ang), np.sin(ang)
        X = x * ca + z * sa
        D = -x * sa + z * ca
        f = 1.0 / (1.0 + D * 0.35)
        scale = W * 0.92
        px = (W / 2 + X * f * scale).astype(np.int32)
        py = (H / 2 - y * f * scale).astype(np.int32)
        ok = keep & (px >= 1) & (px < W - 1) & (py >= 1) & (py < H - 1)

        col = base * (weight * (1 - act))[:, None] + hot[None, :] * (act * 1.6)[:, None]
        buf = np.zeros((H, W, 3))
        np.add.at(buf, (py[ok], px[ok]), col[ok])
        lit = ok & (act > 0.05)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            np.add.at(buf, (py[lit] + dy, px[lit] + dx), col[lit] * 0.55)

        sharp = np.clip(buf, 0, 4)
        img8 = Image.fromarray(np.clip(sharp * 120, 0, 255).astype(np.uint8))
        glow = np.asarray(img8.filter(ImageFilter.GaussianBlur(4)), dtype=np.float64) / 120
        tone = 1 - np.exp(-(sharp * 1.3 + glow * 1.1))
        alpha = np.clip(tone.max(axis=2) * 2.6, 0, 1)
        rgba = np.dstack([tone, alpha])
        Image.fromarray((rgba * 255).astype(np.uint8), "RGBA").save(os.path.join(args.out, f"brain_{k + 1:04d}.png"))
    print(f"{args.frames} brain frames at {W}x{H}")


if __name__ == "__main__":
    main()
