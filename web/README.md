# Strategy Fly in the browser

A simulated fruit fly brain plays Open Doctrines, and both run in the page:

- **The game** is Open Doctrines compiled to WebAssembly (`agent/`, Open Doctrines'
  own `OpenDoctrinesAgent` target), in `game-worker.js`.
- **The brain** is the FlyWire whole-brain model of Shiu et al. (2024), 138,639
  neurons and 15 million synapses, in `brain.js` and `brain-worker.js`.
- **The page** (`index.html`) reads the position, turns it into sensory rates, runs
  a 200 ms brain window, reads the descending neurons as orders, and plays them.
  Pick a map and a country, or import any `.odmap`. If the fly's country is wiped
  out, the same game starts again with a new seed.

## Run it

```bash
tools/build_web_agent.sh ../OpenDoctrines          # the game module
.venv/bin/python tools/export_web_brain.py --fly-data <folder> --out web/data   # the brain
python3 -m http.server 8767 --directory web
```

`<folder>` holds `Completeness_783.csv`, `Connectivity_783.parquet` and
`neuron_annotations.tsv` (see `notebooks/`). Open http://localhost:8767.

## A new version of Open Doctrines

```bash
tools/build_web_agent.sh ../OpenDoctrines v1.2.1a
```

replaces `web/agent/` with that version's module and records it in
`web/agent/VERSION`. The rules the fly plays under live in Open Doctrines
(`src/Game_Agent.cpp`), so nothing here changes with the game.

## Is it the same brain as the Python one?

`node tools/validate_brain.mjs web/data <probes.json>` compares the browser brain
with Brian2 on the stage-1 stimuli. With the same scripted input the two produce
the same spikes on the same steps from the same neurons; with random input they
are the same process (descending-neuron spikes within a few percent, action
groups correlated 0.99-1.00).

## Not yet

- Hosting: `data/connectome.bin` is 91 MB and `agent/OpenDoctrinesAgent.data` 22 MB,
  larger than a single Cloudflare Pages file may be. Serving it from the website
  means splitting both.
