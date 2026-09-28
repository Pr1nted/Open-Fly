#!/usr/bin/env python3
"""The preregistered matrix: five conditions x six seats x eight seeds.

    python3 tools/run_matrix.py --stage controls
    python3 tools/run_matrix.py --stage real
    python3 tools/run_matrix.py --stage shuffled

IN STAGES, and RESUMABLE. Every finished run is appended to the results JSONL
before the next one starts, and a run already in that file is skipped. Six
hours of brain simulation should not be lost to one crash at hour five, and
the file is the checkpoint rather than a separate one that could disagree
with it.

ONE BRAIN BUILD PER STAGE. Building the network is a second but the first
window pays ~35 s of Cython compilation, and the real brain serves two
conditions (fly, and input-blind, which is the same wiring under constant
input). So the stages are grouped by which brain they need, not by condition.

Conditions and constants are PREREGISTRATION.md's, not this file's opinion:
change one here and the run stops being the registered one.
"""
from __future__ import annotations

import argparse, json, os, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from open_fly import decode, driver                                    # noqa: E402
from open_fly.brain import FlyBrain                                    # noqa: E402
from open_fly.encode import Encoder                                    # noqa: E402
from open_fly.players import AlwaysHold, FlyPlayer, RandomLegal        # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLY = pathlib.Path(os.environ.get("OD_FLY_DATA", os.path.expanduser("~/.open_fly/fly")))
BINARY = os.environ.get("OD_PATCHED", os.path.expanduser("~/.open_fly/bin/OpenDoctrinesServer"))
DATA = os.environ.get("OD_DATA", os.path.expanduser("~/CLionProjects/OpenDoctrines/data"))

PARTITION_SEED, BRAIN_SEED, WINDOW_MS = 783, 20240922, 200.0
SHUFFLE_SEED = 20240923
BLIND_HZ = 50.0
TURNS = 120
SEATS = ["1914:FRA:rung", "1914:SWE:rung", "1939:USA:rung",
         "modern:CHN:rung", "1914:FRA:rush", "1939:NOR:hood"]
SEEDS = [20260801, 4242, 90210,
         1408520941, 2671880660, 4095702708, 3542270611, 1245491110]
OUT = ROOT / "docs" / "calibration" / "matrix.jsonl"
STAGES = {"controls": ["random", "hold"], "real": ["fly", "blind"], "shuffled": ["shuffled"]}


def build_brain(shuffle_seed=None):
    b = FlyBrain(str(FLY / "Completeness_783.csv"), str(FLY / "Connectivity_783.parquet"),
                 shuffle_seed=shuffle_seed)
    ids = json.load(open(ROOT / "open_fly" / "sensory_ids.json"))
    for ch in ("sugar", "bitter", "water", "jon"):
        b.add_channel(ch, ids[ch])
    units = decode.descending_units(str(FLY / "neuron_annotations.tsv"), b.index)
    return b, decode.make_groups(units, PARTITION_SEED)


def done_keys():
    if not OUT.exists():
        return set()
    keys = set()
    for line in OUT.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue                       # a line torn by a kill: rerun that one
        keys.add((r["condition"], r["seat"], r["seed"]))
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=sorted(STAGES))
    ap.add_argument("--turns", type=int, default=TURNS)
    a = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    have = done_keys()
    conditions = STAGES[a.stage]
    todo = [(c, s, d) for c in conditions for s in SEATS for d in SEEDS
            if (c, s, d) not in have]
    print(f"stage {a.stage}: {len(todo)} run(s) to do, {len(have)} already recorded",
          flush=True)
    if not todo:
        return 0

    brain = groups = None
    if a.stage in ("real", "shuffled"):
        t0 = time.time()
        brain, groups = build_brain(SHUFFLE_SEED if a.stage == "shuffled" else None)
        print(f"brain built in {time.time() - t0:.1f}s "
              f"(shuffle_seed={SHUFFLE_SEED if a.stage == 'shuffled' else None})", flush=True)

    started = time.time()
    for n, (cond, seat, seed) in enumerate(todo, 1):
        if cond == "hold":
            player = AlwaysHold()
        elif cond == "random":
            player = RandomLegal(seed)
        else:
            blind = {c: BLIND_HZ for c in ("sugar", "bitter", "water", "jon")} \
                if cond == "blind" else None
            player = FlyPlayer(brain, groups, Encoder(), window_ms=WINDOW_MS,
                               seed=BRAIN_SEED, blind_rates=blind)
        t0 = time.time()
        try:
            res = driver.run_seat(BINARY, DATA, seat, seed, player,
                                  label=cond, turns=a.turns)
            res.update(condition=cond, error=None)
        except Exception as e:                                       # noqa: BLE001
            # Recorded, not raised: one seat that times out should not cost the
            # other 47, and a missing row is indistinguishable from one never run.
            res = {"condition": cond, "seat": seat, "seed": seed, "score": None,
                   "error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 1)}
        with OUT.open("a") as f:
            f.write(json.dumps(res) + "\n")
        per = (time.time() - started) / n
        print(f"[{n}/{len(todo)}] {cond:9s} {seat:16s} {seed:>10}  "
              f"score {res.get('score')}  {res.get('wall_s')}s  "
              f"eta {(len(todo) - n) * per / 60:.0f} min", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
