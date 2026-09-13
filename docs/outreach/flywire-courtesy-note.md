# Courtesy note to the FlyWire team

A draft. **Not sent.** Send it before Open Fly goes public, with a working preview
link, so they see the project from us before they see it on Hacker News.

**To:** flywire@princeton.edu, the general address on home.flywire.ai. That page
lists Amy Sterling (Crowdsourcing and Outreach Manager) as the outreach contact,
so address her by name if you prefer.
**Optional Cc:** Philip Shiu, whose model this runs. Contact him through the
paper's corresponding author or the GitHub repository, not a guessed address.
**From:** the address you want replies at. The note does not include one.

Fill in the brackets before sending: the preview link and the date.

---

**Subject:** Open Fly: the FlyWire connectome playing a strategy game in the browser

Hello FlyWire team,

I'm Pr1nted, the solo developer of Open Doctrines, a free, non-commercial grand
strategy game. I've built a small side project on FlyWire's public release 783.
Before it goes public, I wanted to tell you about it, show you how it credits
FlyWire, and give you the chance to ask for changes.

**What it is.** Open Fly runs the whole-brain leaky integrate-and-fire model from
Shiu et al. (2024) on the 783 connectome, entirely in a web browser, and connects
it to the game. Each turn, what happened to the player's country stimulates the
sugar, bitter, water and Johnston's organ neurons. The brain then runs for 200 ms
of simulated time, and spikes in descending neurons choose the country's actions.
A 3D view shows the brain spiking beside a cartoon fly at a desk. The JavaScript
port matches the original Brian2 model spike for spike on a scripted input.

Preview: [preview link]

**How we describe it.** Plainly: it is a simulation of a fly's wiring, not a fly.
It is not trained, and it plays badly (it holds less land than a country that
does nothing). The mapping between the game and the neurons is our own design,
and we wrote it down before the fly played. We avoid claims about understanding,
learning or intent.

**How it uses and credits FlyWire's data.**

- Connectivity and completeness for 783, as prepared by Shiu et al., re-encoded
  as a binary table. Positions, super classes and descending-neuron annotations
  come from `flywire_annotations`.
- The page credits "Connectome: FlyWire, Princeton University and collaborators,
  CC BY-NC 4.0, converted for the browser". It links to a licence file that lists
  the changes we made and the papers from your citation table: Dorkenwald et al.,
  Schlegel et al., Zheng et al., Buhmann et al., Heinrich et al., Eckstein, Bates
  et al., Matsliah, Yu et al., and Berg et al.
- It is strictly non-commercial: no payments, donations, ads or monetised videos.

**Three questions:**

1. Are you comfortable with this use and the credit wording? I'm glad to change
   either.
2. Is there a one-line description of FlyWire you would like us to use on the
   page and in posts?
3. Is there anything in how we describe the connectome or the model that you would
   correct?

We plan to launch around [date], alongside the Open Doctrines 1.2.1a release.
There is no need to reply if you are happy with it. If you are not, I would much
rather hear it before launch than after.

Thank you for making the connectome open. This project could only exist because
you did.

Best,
Pr1nted
Open Doctrines: https://opendoctrines.pages.dev

---

## Before sending

- [ ] Replace [preview link] with a deploy that works (the Pages URL, or a Pages
      preview deployment if production is not live yet).
- [ ] Replace [date].
- [ ] Check that the preview's credit line and `data/LICENSE.txt` match what the
      note says.
- [ ] Send it from an address you read, and note the date in `docs/launch.md`.
