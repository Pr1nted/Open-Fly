# Strategy Fly

A **simulated** fruit fly brain plays [Open Doctrines](https://github.com/Pr1nted/Open-Doctrines).

The brain is the leaky integrate-and-fire model of the whole adult *Drosophila*
brain from Shiu et al. (2024), built on the FlyWire connectome: 138,639 neurons
and about 15 million synaptic connections. Each game turn, changes in the
country's fortunes stimulate real sensory neuron populations (sugar, bitter,
water, antennal), the brain runs for 200 ms, and its descending neurons, the
brain's output to the body, choose the actions. It plays through the game's
benchmark agent door with the same menu and the same per-turn action budget as
the game's own trained AI.

It is not a living fly, and nothing about it learned to play. How game events
reach the brain and how its output reaches the game is our design, written down
in [PREREGISTRATION.md](PREREGISTRATION.md) before it played.

## Status

Milestone 1: the fly plays a full seat. No claim about how well it plays yet.

## Run it

Open `notebooks/strategy_fly_colab.ipynb` in Google Colab (File, Upload
notebook) and run all cells. The notebook is generated from this repository by
`python3 tools/make_notebook.py`, so it needs no access to the repository.

## Credits

- Brain model: Shiu et al., "A Drosophila computational brain model reveals
  sensorimotor processing", *Nature* 634, 210-219 (2024).
  [philshiu/Drosophila_brain_model](https://github.com/philshiu/Drosophila_brain_model), MIT.
- Connectome: Dorkenwald et al., "Neuronal wiring diagram of an adult brain",
  *Nature* 634, 124-138 (2024); Schlegel et al., "Whole-brain annotation and
  multi-connectome cell typing of *Drosophila*", *Nature* 634, 139-152 (2024).
  FlyWire data is downloaded at run time and not redistributed here.
- Game: Open Doctrines by Pr1nted.

See [NOTICE](NOTICE) for licences.
