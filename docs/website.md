# Open Fly on the Open Doctrines website (draft)

This is a plan, not a page. The real section will be designed on the site. This
file fixes the parts that are not design: where Open Fly is hosted, how it is
framed, what must not happen on load, and the release-day steps.

## Where it lives

**Its own Cloudflare Pages project, `open-fly`**, at `open-fly.pages.dev`. It is
not a folder of `opendoctrines.pages.dev`.

- The two sites release on different triggers. Open Fly redeploys whenever the
  game tags, and whenever the fly changes. The game's site should never be
  redeployed to change the fly, or the reverse.
- Open Fly is about 70 MB of static files. Keeping them off the main site keeps
  its deploys small.
- Pages' 25 MiB per-file limit is already handled in Open Fly: `tools/pack_web.py`
  splits the connectome and the game data into gzip parts, and the page
  reassembles and SHA-256-checks them. Nothing on the main site needs to know.

A custom subdomain (for example `fly.` on a future domain) is a DNS change in the
Pages dashboard later. The iframe URL is then the only line to update.

## Framing rules

- Open Fly's `web/_headers` sends no `X-Frame-Options` and no `frame-ancestors`,
  so it can be framed by the website, by itch.io and by anyone else who wants to
  embed it. More embeds are the goal for this project.
- The website's `packaging/web/_headers` sets no CSP either, so nothing blocks the
  frame on the parent side. If a CSP is ever added there, it needs
  `frame-src https://open-fly.pages.dev`.

## The section

**Nothing loads until the visitor asks.** The iframe costs about 65 MB and a busy
CPU. The section therefore shows the still and a button, and only creates the
iframe on click. `loading="lazy"` alone is not enough: it would start the
download for anyone who scrolls past.

Suggested placement: after the hero on `index.html`, as its own
`<section class="narrow" id="open-fly">`, and as a nav link.

```html
<section class="narrow" id="open-fly">
  <p class="label">Side project · Open Fly</p>
  <h2>A fruit-fly brain plays Open Doctrines</h2>
  <p>138,639 simulated neurons, wired from the FlyWire connectome of a real fruit fly,
     playing the game live in your browser. It was not trained, and it plays badly.
     You can watch every spike.</p>

  <div class="fly-frame" data-src="https://open-fly.pages.dev/?ref=opendoctrines">
    <img src="/img/open-fly-thumbnail.webp" width="1280" height="720"
         alt="A cartoon fly at a desk playing Open Doctrines, its brain glowing beside it">
    <button type="button" class="play">Watch the fly play <small>about 65 MB</small></button>
  </div>

  <p class="fine">
    <a href="https://open-fly.pages.dev/">Open it full screen</a> ·
    <a href="https://pr1nted.itch.io/open-fly">itch.io</a> ·
    <a href="https://open-fly.pages.dev/devlog/">Devlog</a>
  </p>
</section>
```

```css
.fly-frame { position: relative; aspect-ratio: 16 / 9; background: #030806; border: 1px solid #1a4d33; }
.fly-frame img, .fly-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; object-fit: cover; }
.fly-frame .play { position: absolute; left: 50%; top: 50%; translate: -50% -50%; }
@media (max-width: 700px) { .fly-frame .play small::after { content: " · best on a desktop"; } }
```

```js
// Swap the still for the page only on a click: nothing downloads for visitors who scroll past.
document.querySelectorAll(".fly-frame").forEach((box) => {
  box.querySelector("button").addEventListener("click", () => {
    const f = document.createElement("iframe");
    f.src = box.dataset.src;
    f.title = "Open Fly: a simulated fruit-fly brain playing Open Doctrines";
    f.allow = "fullscreen";
    box.replaceChildren(f);
    f.focus();
  });
});
```

The iframe gets no `sandbox` attribute. The page needs module workers,
`crypto.subtle` and a file picker for `.odmap` import. A sandbox loose enough to
allow all of that (`allow-scripts allow-same-origin`) protects nothing.

`/img/open-fly-thumbnail.webp` is `docs/itch/thumbnail.png` converted to WebP.
Optionally, add an `embed` query flag in Open Fly later that hides its own
header when framed, if the section design wants that.

## Elsewhere on the site

- **Nav:** `<a href="/#open-fly">Open Fly</a>`, between "For teachers" and "Source".
- **press.html:** a short Open Fly paragraph, the thumbnail, and the one-line and
  one-paragraph descriptions from Open Fly's README. Journalists will ask about it first.
- **classroom.html:** one line. A real connectome, a transparent encoding and a
  preregistration make a good lesson on what simulations can and cannot claim.
- **sitemap.xml / llms.txt:** add `https://open-fly.pages.dev/` as a related project.

## Release-day checklist (on the green light for 1.2.1a)

1. In Open Fly: set the repository variable `OPEN_FLY_LIVE=true`, and confirm the
   Pages project and secrets (`docs/releasing.md`).
2. Tag 1.2.1a in Open Doctrines as usual. The release workflow dispatches Open Fly,
   or the six-hourly poll picks the tag up.
3. Confirm `https://open-fly.pages.dev/` shows `Open Doctrines v1.2.1a` in the game
   label, and the devlog entry exists.
4. Merge the website section, deploy the site, and click through the section once
   on a desktop and once on a phone.
5. Set the itch.io page to Public, and paste the devlog.
6. Then start `docs/launch.md`.
