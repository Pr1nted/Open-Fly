# Open Fly logo

The favicon's fly, redrawn as a one-colour silhouette on a transparent ground. It
takes any single colour. The details the favicon shows in colour (the gap between
the eyes, the body stripes, the inside of the wings) are holes, so it reads on
light, dark and busy backgrounds alike.

| File | What | Pixel grid |
|---|---|---|
| `open-fly-mark.svg` | the fly alone | 18 x 14 |
| `open-fly-wordmark.svg` | fly + OPEN FLY, side by side | 87 x 14 |
| `open-fly-stacked.svg` | fly over OPEN FLY | 64 x 26 |
| `open-fly-*-black.png`, `open-fly-*-white.png` | the same, ready-coloured, with one pixel of clear margin | |

## Using it

- **SVG** fills with `currentColor`. Inline in HTML, it takes the colour of the
  text around it (`<span style="color:#4dff9b">…svg…</span>`). As an `<img>` or a
  file it renders black; for another colour, edit `fill` or use a PNG.
- Always scale by **whole numbers** of its pixel grid, and keep
  `image-rendering: pixelated` for the PNGs. A fractional scale blurs or doubles
  pixels. The SVGs set `shape-rendering="crispEdges"`.
- Leave clear space around it of at least 2 grid pixels.
- One colour at a time: the console green `#4DFF9B`, Open Doctrines gold
  `#FFD700`, black or white. Never a gradient, and never the favicon's colours
  squeezed into the silhouette. The favicon is the colour version.

## Remaking it

```bash
python3 docs/brand/make_logo.py <folder with PressStart2P-Regular.ttf> docs/brand
```

The fly is the 20-column `MARK` grid in `make_logo.py`. The lettering is Press
Start 2P (SIL Open Font License), rasterised on its own 8-pixel grid and stored as
pixels, so nothing needs the font installed.
