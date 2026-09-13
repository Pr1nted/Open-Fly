import sys
from PIL import Image
OUT = sys.argv[1]
P = {".": (3,8,6,255), "Y": (255,215,0,255), "G": (77,255,155,255), "g": (26,77,51,255), "L": (46,143,92,255),
     "D": (46,143,92,255), "R": (255,77,77,255), "r": (170,40,40,255), "W": (184,245,210,255)}
GRID = """
YYYYYYYYYYYYYYYY
................
....RRr..rRR....
....RRGGGGRR....
.....rGGGGr.....
.DDD..GWWG..DDD.
DDgDD.GGGG.DDgDD
DgggDDGWWGDDgggD
.DggDDGGGGDDggD.
..DDDDGWWGDDDD..
...L..GGGG..L...
..L...GWWG...L..
......GGGG......
.......GG.......
................
................
""".split()
assert len(GRID) == 16 and all(len(r) == 16 for r in GRID)
base = Image.new("RGBA", (16, 16))
for y, row in enumerate(GRID):
    for x, c in enumerate(row):
        base.putpixel((x, y), P[c])
sizes = {}
for s in (16, 32, 48, 64, 128, 180, 256, 512):
    im = base.resize((s, s), Image.NEAREST); sizes[s] = im
    im.save(f"{OUT}/favicon-{s}.png", optimize=True)
sizes[48].save(f"{OUT}/favicon.ico", sizes=[(16,16),(32,32),(48,48)], append_images=[sizes[16], sizes[32]])
# a big preview on a light and a dark tab strip, to judge it at real size too
prev = Image.new("RGBA", (560, 200), (235,235,235,255))
prev.paste(sizes[128], (20, 36)); prev.paste(sizes[32], (170, 84)); prev.paste(sizes[16], (220, 92))
dark = Image.new("RGBA", (260, 200), (40,40,44,255)); dark.paste(sizes[32], (40, 84)); dark.paste(sizes[16], (100, 92)); dark.paste(sizes[64], (150, 68))
prev.paste(dark, (300, 0)); prev.save(f"{OUT}/preview.png")
print("ok")
