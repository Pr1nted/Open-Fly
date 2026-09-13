"""Open Fly's logo, in one colour: the favicon's fly redrawn as a silhouette.

    python3 docs/brand/make_logo.py <folder with PressStart2P-Regular.ttf> [out folder]

One ink, no background. The details the favicon gives in colour (the gap
between the eyes, the body stripes, the inside of the wings) are holes here, so the mark reads on any ground and takes
any colour. The SVGs fill with currentColor: inline, they follow the
surrounding text colour; as files, set fill yourself or use a PNG.
The wordmark is Press Start 2P rasterised on its own 8-pixel grid and drawn as
pixels, so the SVG needs no font. Press Start 2P is OFL.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(sys.argv[1], "PressStart2P-Regular.ttf")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))

MARK = """
....................
......XX....XX......
.....XXXX..XXXX.....
.....XXX.XX.XXX.....
...X....XXXX....X...
....X..XXXXXX..X....
.....XXXXXXXXXX.....
....XXX.XXXX.XXX....
...XXXX.XXXX.XXXX...
..XX..X.X..X.X..XX..
.XX..XX.XXXX.XX..XX.
.X..XX..X..X..XX..X.
.X.XX...XXXX...XX.X.
.XXX.....XX.....XXX.
.........XX.........
....................
""".split()
assert len(MARK) == 16 and all(len(r) == 20 for r in MARK)


def mark_bits():
    return {(x, y) for y, row in enumerate(MARK) for x, c in enumerate(row) if c == "X"}


def text_bits(text):
    font = ImageFont.truetype(FONT, 8)
    left, top, right, bottom = font.getbbox(text)
    im = Image.new("L", (right - left, bottom - top), 0)
    ImageDraw.Draw(im).text((-left, -top), text, font=font, fill=255)
    return {(x, y) for y in range(im.height) for x in range(im.width) if im.getpixel((x, y)) > 127}, im.width, im.height


def rows_to_rects(bits):
    """Merge each row's runs into one rect apiece: a small, exact SVG."""
    out = []
    for y in sorted({y for _, y in bits}):
        xs = sorted(x for x, yy in bits if yy == y)
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            out.append((start, y, prev - start + 1))
            if x is not None:
                start = prev = x
    return out


def svg(bits, w, h, title):
    rects = "".join(f'<rect x="{x}" y="{y}" width="{n}" height="1"/>' for x, y, n in rows_to_rects(bits))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" shape-rendering="crispEdges" '
            f'role="img" aria-label="{title}"><title>{title}</title><g fill="currentColor">{rects}</g></svg>\n')


def png(bits, w, h, scale, rgb, path, pad=0):
    im = Image.new("RGBA", ((w + 2 * pad) * scale, (h + 2 * pad) * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, y in bits:
        d.rectangle([(x + pad) * scale, (y + pad) * scale, (x + pad + 1) * scale - 1, (y + pad + 1) * scale - 1], fill=rgb + (255,))
    im.save(path, optimize=True)


# the mark, trimmed to its ink
raw = mark_bits()
x0, y0 = min(x for x, _ in raw), min(y for _, y in raw)
m = {(x - x0, y - y0) for x, y in raw}
MW, MH = max(x for x, _ in m) + 1, max(y for _, y in m) + 1
# the wordmark: the mark, a gap, "OPEN FLY" at 1 glyph pixel = 1 mark pixel, centred on the mark
t, tw, th = text_bits("OPEN FLY")
GAP = 5
ty = (MH - th) // 2
word = set(m) | {(MW + GAP + x, ty + y) for x, y in t}
WW, WH = MW + GAP + tw, MH
# stacked: the mark over the text
sx = (tw - MW) // 2 if tw > MW else 0
stack = {(sx + x, y) for x, y in m} | {(x, MH + 4 + y) for x, y in t}
SW, SH = max(tw, MW), MH + 4 + th

for name, bits, w, h in (("mark", m, MW, MH), ("wordmark", word, WW, WH), ("stacked", stack, SW, SH)):
    open(os.path.join(OUT, f"open-fly-{name}.svg"), "w").write(svg(bits, w, h, "Open Fly"))
    for ink, rgb in (("black", (0, 0, 0)), ("white", (255, 255, 255))):
        scale = {"mark": 64, "wordmark": 20, "stacked": 24}[name]
        png(bits, w, h, scale, rgb, os.path.join(OUT, f"open-fly-{name}-{ink}.png"), pad=1)
print("logo written to", OUT, {"mark": (MW, MH), "wordmark": (WW, WH), "stacked": (SW, SH)})
