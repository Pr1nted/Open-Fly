# Launching Open Fly

The draft plan for putting Open Fly in front of people, and through it Open
Doctrines. Nothing here happens before the green light for 1.2.1a.

## Why it can work

"A connectome plays a game" is a format people already share. The precedents are
real and recent:

- **FlyWire (October 2024).** The complete adult fruit-fly connectome, published as
  a package in *Nature*. Mainstream coverage everywhere, with the brain renders as
  the images.
- **Shiu et al. (*Nature*, 2024).** The whole-brain model Open Fly runs. It
  predicted feeding and grooming circuits from wiring alone. This is what makes
  "simulate a fly brain" a real sentence rather than a gimmick.
- **DishBrain (Kagan et al., *Neuron*, 2022).** Living neurons in a dish "learning"
  Pong. It spread widely, and it drew heavy criticism for how "learning" and
  "sentience" were framed.

Each spread for the same reason: a real brain, a familiar game, and a picture you
understand in one second. Open Fly has all three, and one thing the others did not.
Anyone can open it in a browser and watch it think.

## The one rule: say exactly what it is

DishBrain is the warning. The fastest way to lose the science audience, and then
everyone who reads them, is a claim that is bigger than the work. Every post, title
and caption follows these:

| Say | Never say |
|---|---|
| a **simulated** fruit-fly brain | a fly plays / a real fly |
| wired from the FlyWire connectome | a digital fly / uploaded fly |
| we map game events to sensory neurons | the fly understands / wants / feels |
| it is not trained and it plays badly | AI / learns / gets smarter |
| the mapping was preregistered | it chose to declare war (as intent) |

Bad play is the hook, not the embarrassment. "It held less land than doing
nothing" is funny, true, and invites "try to beat the fly".

## Assets

All from the page and the scene tools, nothing staged:

- **30-second clip** in 16:9 and 9:16. Open close on the brain lighting up, pull
  back to the fly at the keyboard, cut to the wall map as its country shrinks, end
  on the title card. Captions burned in, no voiceover needed.
- **GIF, 8 seconds, under 10 MB**: brain spike, keyboard tap, map change. For
  Reddit and Bluesky, where autoplay video underperforms.
- `docs/itch/thumbnail.png` as the link card. `cover.png` and `banner.png` for itch.
- **One screenshot of the orders panel mid-war**, for the "what does it actually
  do" question.

## Channels, in order of fit

| Where | Angle | Notes |
|---|---|---|
| **Hacker News (Show HN)** | "Show HN: The FlyWire fruit-fly connectome playing a strategy game in the browser" | Lead with the port matching Brian2 spike for spike, and the 25 MiB packing. HN rewards the engineering. Post Tue-Thu, 14:00-16:00 UTC. Stay in the thread. |
| **r/grandstrategy, r/4Xgaming** | "I let a fruit-fly brain play my grand strategy game. It declared war on everyone." | The audience that turns into Open Doctrines players. Link the game in the first comment. |
| **r/neuroscience, r/compmathneuro** | the model, the encoding, the preregistration | Read their self-promotion rules first. Post as a question about the encoding choices, not as a launch. |
| **r/InternetIsBeautiful, r/webdev** | runs entirely in a browser tab | |
| **Bluesky / X** | the clip | The neuroscience community is mostly on Bluesky now. Tag nobody who has not engaged first. Credit FlyWire and Shiu et al. by name in the post. |
| **YouTube Shorts, TikTok** | the 9:16 clip | "This fly brain has 138,639 neurons and no idea it is at war." |
| **itch.io** | the project page, and a devlog on the Open Doctrines page | Cross-link both ways. |
| **Open Doctrines Discord** | announcement, plus a "beat the fly" channel or thread | |
| **Press** | a short email to games-and-science writers | Only after HN or Reddit has traction. Link the page, the clip and a one-paragraph explanation. |

## Timing with 1.2.1a

1. **Day 0:** Open Doctrines 1.2.1a releases. The Follow Open Doctrines workflow
   builds Open Fly against it (set `OPEN_FLY_LIVE` first). The Open Fly itch page
   goes public, and the website section goes up.
2. **Day 1:** check the page on three machines (a Mac, a Windows laptop, a
   low-end Chromebook) and fix anything. Record the clip from the live 1.2.1a page.
3. **Day 2 (Tue-Thu):** Show HN, then r/grandstrategy two hours later, then the
   clip on Bluesky, X and Shorts.
4. **Day 3-4:** r/neuroscience, r/InternetIsBeautiful. Press emails if day 2 went well.
5. **Next release:** the automatic devlog is the follow-up post: "the fly played
   the new version".

The day or two of gap matters. The fly's traffic should land on a game version that
has been out long enough to be stable.

## Point attention at the game

The fly is the hook. The game is what we want people to keep.

- Every Open Fly surface links Open Doctrines above the fold: the page's game label,
  the itch description and the devlog footer.
- Suggest "Can you do better than the fly? Play Sweden 1914" with the same map and seat.
- Links from Open Fly to Open Doctrines carry `?ref=openfly`. It names the source,
  never the person. itch and Pages analytics then show whether the fly sends players.

## Before launch: checklist

- [x] **FlyWire data terms, checked 2026-09-13.** FlyWire's public release (v783) is
      **CC BY-NC 4.0** (flywire.ai/guidelines; the Zenodo connectivity record says
      CC BY 4.0, and we follow the stricter one). Redistributing the converted files is
      allowed with attribution, a licence link and a note that they were changed, and
      **never commercially**. The credit is on the page, in `web/data/LICENSE.txt`,
      in `NOTICE` and in the itch description. See the non-commercial rules below.
- [ ] **Keep every Open Fly surface non-commercial**, which is what CC BY-NC requires
      and what Open Doctrines' own licence requires too: itch pricing "No payments"
      with no donate button, no ads on the site, and **no monetisation on the clip**
      (YouTube Partner, TikTok Creator Rewards). A sponsor, a paid tier or selling the
      art would need FlyWire's written permission first.
- [ ] Send the courtesy note to the FlyWire team (draft: `docs/outreach/flywire-courtesy-note.md`),
      with a working preview link, at least a week before going public. It costs nothing, and it is how this becomes
      "people we cite liked it" instead of "people we cite objected".
- [ ] Decide whether the Open Fly repository goes public at launch. HN will ask for
      the source.
- [ ] `OPEN_FLY_LIVE` set, Pages project created, secrets set (see `docs/releasing.md`).
- [ ] The itch page out of Draft, with the theme and CSS pasted and checked at phone width.
- [ ] Website section merged (see `docs/website.md`).
- [ ] The page tested on Chrome, Firefox and Safari (DecompressionStream and module
      workers are required).
- [ ] The 30 s clip, the GIF and the link card all show 1.2.1a.
- [ ] A pinned FAQ comment ready for the threads: is it trained? (no); is it a real
      fly? (no, a simulation of a real fly's wiring); why does it play badly?; what
      are the senses mapped to?
