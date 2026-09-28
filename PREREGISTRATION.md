# Pre-registration

Written and committed before the simulated brain played a single turn. Changing
anything below after seeing a result means the result is exploratory and has to
be reported as such.

## Build

- Open Doctrines commit `05881e0`, with `patches/opendoctrines-agent-door.patch`,
  `patches/opendoctrines-bench-cohort.patch` and
  `patches/opendoctrines-move-order-erase.patch`.
- **The build was not reproducible from this description until 2026-09-28.**
  The binary in use was built on 2026-09-13 from a working tree carrying a
  move-order fix that was never in `05881e0`, so "commit `05881e0` plus the
  door patch" and the binary that played were not the same program. Built as
  written, `05881e0` dies with SIGBUS at turn 104 once the cohort patch makes
  the opponents fight: `processArmyMovement` erases a pending order by index
  after `resolveAssault`, which can capture a province and drop other orders
  out of the same vector. The fix is carried as the third patch. Nothing was
  claimed from the old binary, and nothing run under it is reported.
- **The cohort patch was added 2026-09-28, before any condition was run**, and
  it changes what the seats are rather than how anything is scored. The door
  never declared its control cohort, so `isRandomCountry()` was false for every
  country and AISystem's gate on it meant nothing rushed: `:rush` and `:hood`
  played ordinary worlds while the log said otherwise. The controls caught it —
  `1914:FRA:rung` and `1914:FRA:rush` scored identically on 8 of 8 seeds under
  two different players. It also means the scripted rung was not in force on
  the other four seats, so all six seats change under this patch and no run
  made before it is comparable; the 96 control runs taken before it were
  discarded (`docs/calibration/matrix-precohort-INVALID.jsonl`) rather than
  reused. Door calibration was re-run against the rebuilt binary: 18 of 18
  identical, so the patch still does not touch scoring.
- The door patch proper:
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
  **Done, 2026-09-28: 18 of 18 identical** (`tools/calibrate_door.py`,
  `docs/calibration/door-calibration.json`). The patch edits `Game_AITrain.cpp`, which
  is also where the `[BENCH]` score is computed, so the two cannot be assumed
  independent. The patched binary and an unpatched build of the same commit
  (`05881e0`) were run through `od_bench.py`'s own `--eval-ai` invocation on
  all six seats and the three bench seeds, and scored the same on every one, to
  the precision the line prints. What this establishes is that the patch is
  inert for a normal evaluation at difficulty 3, which is the only difficulty
  the matrix uses; it says nothing about the patch's `aiDifficulty = 3`
  override at any other difficulty, and nothing is run at one.
- Conditions: fly, shuffled connectome (postsynaptic column permuted, seed
  `20240923`), input-blind brain (constant 50 Hz on every channel),
  random-legal, always-hold. Trained model reported in its own column, as a
  different setup (opening book, own seeding).
- Seats: the six of `tools/od_bench.py`. Seeds: the three bench seeds
  (`20260801`, `4242`, `90210`) plus the five below.
- The five fresh seeds, fixed 2026-09-28, before any condition was run:

      1408520941  2671880660  4095702708  3542270611  1245491110

  Derived rather than chosen, so that nobody -- including us -- can claim they
  were picked to suit an outcome, and so anyone can regenerate them:

      python3 -c "import random; r=random.Random('open-fly shuffled control'); \
                  print([r.getrandbits(32) for _ in range(5)])"

  None collides with a bench seed. All are inside the range `--seed` and
  `OD_WORLD_SEED` accept, which is `strtoul` into `unsigned int`; note that 0
  would have meant "unset" to `OD_WORLD_SEED` and none of these is 0.
- "Different" means a paired difference of at least 25 points, a 95% bootstrap
  interval over seeds excluding 0, and the same sign on at least 3 of the 4
  graded seats. Bistable seats are reported as survival counts only.
- "The fly played better than random" needs the real brain to beat random,
  always-hold, input-blind and shuffled. If shuffled matches it, the claim is
  that the interface played.
- **The shuffled brain is not activity-matched, and this was measured before
  the runs.** On one 200 ms window under the same input, the real wiring fired
  3,952 spikes and the shuffled one 2,260. Permuting the postsynaptic column
  destroys the recurrence that sustains firing, so the control differs in total
  drive as well as in who talks to whom. A difference in play between them is
  therefore not by itself evidence that the specific wiring computed anything:
  it is consistent with the real brain simply being louder. Total descending
  spikes are reported per condition alongside the scores so a reader can see
  which explanation the numbers support, and the input-blind condition is what
  separates drive from structure.
