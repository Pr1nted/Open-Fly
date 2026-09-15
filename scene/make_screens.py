"""The monitor's picture, one PNG per video frame, from a real game.

The map is the game's own timelapse export of the save the fly's run wrote
(`OpenDoctrines --export-timelapse`), cropped to Scandinavia. The side panel is
that same run's turn log: the orders the fly gave, its descending-neuron spikes,
and the sensory rates the game state was encoded into. Nothing on the screen is
invented; a frame shows turn floor(k / frames_per_turn) of the log.

    python scene/make_screens.py --gif fly.gif --turns fly.turns.jsonl --out out/screens \
        --font DejaVuSans.ttf [--scale 2] [--crop 0.427,0.073,0.677,0.323] [--hold 48]

--scale multiplies the 1600x900 layout; export the timelapse at matching size
(7680x3840 for --scale 2) or the map is upscaled.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageSequence

ECON = ["save", "industry", "fort", "port", "specialize", "destroyer", "carrier",
        "fund up", "fund down", "focus bldg", "focus army", "focus navy"]
POL = ["hold", "enact", "pacify up", "pacify dn", "cancel", "alliance", "nap",
       "guarantee", "calming", "conciliate", "repress", "trade"]
WAR = ["hold", "recruit", "reinforce", "attack", "declare war", "artillery", "ceasefire", "stage"]
NAVY = ["hold", "move", "bombard", "embark", "land", "scrap", "engage"]
NAMES = {"e": ("Economy", ECON), "p": ("Politics", POL), "w": ("War", WAR), "n": ("Navy", NAVY)}

BG, PANEL, INK, MUTED, ACCENT, RED = (12, 14, 20), (22, 26, 36), (230, 232, 238), (140, 146, 160), (242, 184, 75), (220, 70, 60)


def order_label(tok):
    mod, _, idx = tok.partition(":")
    title, names = NAMES[mod]
    i = int(idx)
    return title, names[i] if 0 <= i < len(names) else idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", required=True)
    ap.add_argument("--turns", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--crop", default="0.427,0.073,0.677,0.323")
    ap.add_argument("--frames-per-turn", type=int, default=6)
    ap.add_argument("--hold", type=int, default=48)
    ap.add_argument("--taps", default=None, help="write the fly's key taps per frame here")
    args = ap.parse_args()

    S = args.scale
    s = lambda v: int(round(v * S))
    W, H = s(1600), s(900)
    turns = [json.loads(l) for l in open(args.turns)]
    os.makedirs(args.out, exist_ok=True)
    f = lambda size: ImageFont.truetype(args.font, s(size))
    mid, small, tiny = f(24), f(20), f(16)
    cx0, cy0, cx1, cy1 = (float(v) for v in args.crop.split(","))

    gif = Image.open(args.gif)
    gw, gh = gif.size
    box = (int(cx0 * gw), int(cy0 * gh), int(cx1 * gw), int(cy1 * gh))
    fpt = args.frames_per_turn
    taps, n = [], 0
    vals = [r["share"] for r in turns]
    top = max(vals) * 1.1 or 1.0

    def render(map_rgb, k):
        ti = min(k // fpt, len(turns) - 1)
        t = turns[ti]
        info = t.get("info") or {}
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, s(56)], fill=PANEL)
        d.text((s(20), s(12)), "OPEN DOCTRINES", font=mid, fill=ACCENT)
        d.text((s(290), s(14)), f"1914  ·  Sweden  ·  Turn {t['turn'] + 1} / 120", font=small, fill=INK)
        d.text((W - s(20), s(14)), "Commander: Drosophila melanogaster", font=small, fill=MUTED, anchor="ra")
        im.paste(map_rgb.resize((s(1100), s(550)), Image.LANCZOS), (0, s(56)))
        d.rectangle([0, s(56), s(1100) - 1, s(606) - 1], outline=(50, 56, 70), width=max(1, s(2)))
        war = t.get("war") or ""
        war = " ".join(war) if isinstance(war, list) else str(war)
        war = war if war and war != "(nobody)" else "nobody"
        stats = [("Land", f"{t['share']:.2f}% of the world"), ("Army", f"{int(t['army']):,}"),
                 ("Treasury", f"{t['treasury']:,.0f}"), ("At war with", war[:40])]
        for i, (k_, v) in enumerate(stats):
            x = s(24 + i * 270)
            d.text((x, s(622)), k_, font=tiny, fill=MUTED)
            d.text((x, s(644)), v, font=small, fill=RED if k_ == "At war with" and war != "nobody" else INK)
        sx0, sy0, sx1, sy1 = s(24), s(700), s(1076), s(880)
        d.rectangle([sx0, sy0, sx1, sy1], fill=PANEL)
        d.text((sx0 + s(12), sy0 + s(8)), "Land held, % of the world", font=tiny, fill=MUTED)
        pts = [(sx0 + s(10) + (sx1 - sx0 - s(20)) * i / 119, sy1 - s(10) - (sy1 - sy0 - s(40)) * v / top)
               for i, v in enumerate(vals[: ti + 1])]
        if len(pts) > 1:
            d.line(pts, fill=ACCENT, width=s(3))
        if pts:
            r = s(5)
            d.ellipse([pts[-1][0] - r, pts[-1][1] - r, pts[-1][0] + r, pts[-1][1] + r], fill=ACCENT)
        d.rectangle([s(1100), s(56), W, H], fill=PANEL)
        px = s(1124)
        d.text((px, s(76)), "THE FLY'S ORDERS", font=mid, fill=ACCENT)
        orders = [tok for tok in t.get("tokens", []) if not tok.endswith(":0")]
        y = s(116)
        if not orders:
            d.text((px, y), "(holds)", font=small, fill=MUTED)
        for tok in orders[:13]:
            title, name = order_label(tok)
            d.text((px, y), title, font=tiny, fill=MUTED)
            d.text((px + s(100), y - s(2)), name, font=small, fill=INK)
            y += s(30)
        if len(orders) > 13:
            d.text((px, y), f"+{len(orders) - 13} more", font=tiny, fill=MUTED)
        by = s(560)
        d.text((px, by), "BRAIN THIS TURN", font=mid, fill=ACCENT)
        spikes = info.get("dn_spikes", 0)
        d.text((px, by + s(40)), f"{spikes} descending-neuron spikes", font=small, fill=INK)
        d.rectangle([px, by + s(72), W - s(24), by + s(88)], fill=(40, 46, 60))
        d.rectangle([px, by + s(72), px + int((W - s(24) - px) * min(spikes / 750, 1.0)), by + s(88)], fill=ACCENT)
        rates = info.get("rates", {})
        for i, (ch, label) in enumerate((("sugar", "sugar (treasury)"), ("bitter", "bitter (losses)"),
                                         ("water", "water (land)"), ("jon", "hearing (war)"))):
            yy = by + s(112 + i * 42)
            rr = rates.get(ch, 0.0)
            d.text((px, yy), label, font=tiny, fill=MUTED)
            d.rectangle([px, yy + s(20), W - s(24), yy + s(30)], fill=(40, 46, 60))
            d.rectangle([px, yy + s(20), px + int((W - s(24) - px) * min(rr / 200.0, 1.0)), yy + s(30)],
                        fill=(110, 170, 230))
        d.text((px, H - s(34)), "138,639 neurons · FlyWire v783", font=tiny, fill=MUTED)
        return im, ti, len(orders)

    im = None
    for k, fr in enumerate(ImageSequence.Iterator(gif)):
        # crop before converting: a full 7680x3840 RGB frame is 88 MB
        map_rgb = fr.crop(box).convert("RGB")
        im, ti, n_orders = render(map_rgb, k)
        n += 1
        im.save(os.path.join(args.out, f"screen_{n:04d}.png"))
        sub = k % fpt
        taps.append((1 + (ti + sub // 2) % 2) if sub in (0, 2, 4) and n_orders > sub // 2 else 0)
    for _ in range(args.hold):
        n += 1
        im.save(os.path.join(args.out, f"screen_{n:04d}.png"))
        taps.append(0)
    if args.taps:
        json.dump(taps, open(args.taps, "w"))
    print(f"{n} screens at {W}x{H}, {sum(1 for t in taps if t)} key taps")


if __name__ == "__main__":
    main()
