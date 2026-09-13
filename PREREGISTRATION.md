# Pre-registration

Written and committed before the simulated brain played a single turn. Changing
anything below after seeing a result means the result is exploratory and has to
be reported as such.

## Build

- Open Doctrines commit `05881e0`, with `patches/opendoctrines-agent-door.patch`:
  the agent door gets the trained model's per-turn action budget (economy, war,
  navy 8; politics 3; a module ends when it picks action 0) and difficulty 3,
  as `tools/od_bench.py` uses.
- `OD_WORLD_SEED` is set to the game seed for every run, so a seed is one world.
- Brian2 2.10.1, codegen `cython`. FlyWire connectome v783 as distributed with
  philshiu/Drosophila_brain_model.

## Brain

- Equations and constants unchanged from `model.py` of the Shiu et al. model.
- Decision window 200 ms, preceded by a 2 ms flush with inputs off and a reset
  of `v` and `g`.
- Brian2 seed per turn: `crc32("20240922|ISO|turn")`.

## Input: game state to sensory neurons

Rates are `200 Hz * clip(signal, 0, 1)`, and 0 below 10 Hz.

| Channel | Neurons | Signal |
|---|---|---|
| sugar | 21 sugar gustatory receptor neurons (20 present in v783) | gain in world share / 0.5 pp + max(0, net / gross) |
| bitter | 21 bitter gustatory receptor neurons (20 present) | loss in world share / 0.5 pp + max(0, -net / gross) + 0.5 x new wars |
| water | 18 water gustatory receptor neurons | treasury / (12 x gross) |
| jon | 146 Johnston's organ neurons, CE + F + D_m (145 present) | wars / 3 |

Army size and the cost breakdown are deliberately not encoded.

## Output: descending neurons to actions

- The 1,303 FlyWire `descending` neurons (1,299 present in v783), grouped by
  cell type (472 units), dealt into 39 balanced groups with seed `783`, one
  group per action (economy 12, politics 12, war 8, navy 7).
- Score of an action = mean spikes per neuron of its group in the window.
- Per menu: legal actions with score > 0, highest first, up to the budget;
  ties broken by the per-turn seed; nothing fired means hold. Nothing ranked
  after action 0 is sent.

## Milestone 1 (this notebook)

The fly plays a full 120-turn seat, `1914:SWE:rung`, seed `20260801`, with at
least one action taken. Always-hold and random-legal play the same seat for
context. This is a demonstration, not a benchmark result, and no claim about
how well the fly plays is made from it.

## Before any claim about skill (not yet run)

- Door calibration first: the door must reproduce known scores.
- Conditions: fly, shuffled connectome (postsynaptic column permuted, seed
  `20240923`), input-blind brain (constant 50 Hz on every channel),
  random-legal, always-hold. Trained model reported in its own column, as a
  different setup (opening book, own seeding).
- Seats: the six of `tools/od_bench.py`. Seeds: the three bench seeds plus
  five fresh ones named before running.
- "Different" means a paired difference of at least 25 points, a 95% bootstrap
  interval over seeds excluding 0, and the same sign on at least 3 of the 4
  graded seats. Bistable seats are reported as survival counts only.
- "The fly played better than random" needs the real brain to beat random,
  always-hold, input-blind and shuffled. If shuffled matches it, the claim is
  that the interface played.
