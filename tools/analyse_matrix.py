#!/usr/bin/env python3
"""Read docs/calibration/matrix.jsonl and apply the preregistered rules.

    python3 tools/analyse_matrix.py

The rules are PREREGISTRATION.md's and are not re-decided here:

  * Seats are scored the way od_bench.py scores them -- min(share/par, 5) * 100,
    so 100 means "ended the size it started". The raw [BENCH] line is a world
    share, which is NOT the scale the 25-point threshold is written on.
  * 1914:FRA:rush and modern:CHN:rung are od_bench's KNOWN_BISTABLE: they hold
    or they are annihilated, and a mean over them describes no run that ever
    happened. Reported as survival counts, never averaged.
  * "Different" = a paired difference of at least 25 points, a 95% bootstrap
    interval over seeds excluding 0, and the same sign on at least 3 of the 4
    graded seats. All three, not any of them.
  * "The fly played better than random" requires the real brain to beat random,
    always-hold, input-blind AND shuffled. If shuffled matches it, the claim is
    that the interface played.
"""
from __future__ import annotations

import collections, json, pathlib, random, statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAR = {"1914:FRA:rung": 6.7, "1914:SWE:rung": 1.0, "1939:USA:rung": 5.6,
       "modern:CHN:rung": 2.5, "1914:FRA:rush": 6.7, "1939:NOR:hood": 1.3}
BISTABLE = {"1914:FRA:rush", "modern:CHN:rung"}
GRADED = [s for s in PAR if s not in BISTABLE]
CAP, BOOT = 5.0, 20000


def seat_score(share, par):
    return min(share / par, CAP) * 100.0 if par > 0 else 0.0


def main():
    rows = [json.loads(l) for l in (ROOT / "docs/calibration/matrix.jsonl").read_text().splitlines()]
    pts = {(r["condition"], r["seat"], r["seed"]): seat_score(r["score"], PAR[r["seat"]])
           for r in rows}
    share = {(r["condition"], r["seat"], r["seed"]): r["score"] for r in rows}
    seeds = sorted({r["seed"] for r in rows})
    conds = ["fly", "shuffled", "blind", "random", "hold"]

    print("PER-SEAT MEAN SCORE  (100 = ended the size it started; bistable seats marked)\n")
    print(f"  {'seat':<17}" + "".join(f"{c:>10}" for c in conds))
    for seat in PAR:
        tag = " [bistable]" if seat in BISTABLE else ""
        line = f"  {seat:<17}"
        for c in conds:
            line += f"{statistics.mean(pts[(c, seat, s)] for s in seeds):>10.0f}"
        print(line + tag)

    print("\n\nSURVIVAL ON THE BISTABLE SEATS  (held = share > 0.25 x par)\n")
    print(f"  {'seat':<17}" + "".join(f"{c:>10}" for c in conds))
    for seat in BISTABLE:
        line = f"  {seat:<17}"
        for c in conds:
            held = sum(1 for s in seeds if share[(c, seat, s)] > 0.25 * PAR[seat])
            line += f"{held:>7}/{len(seeds)}"
        print(line)

    print("\n\nPAIRED COMPARISONS, GRADED SEATS ONLY  (fly minus each control)\n")
    rng = random.Random(20240924)
    verdicts = {}
    for other in ("shuffled", "blind", "random", "hold"):
        per_seat = {st: statistics.mean(pts[("fly", st, s)] - pts[(other, st, s)] for s in seeds)
                    for st in GRADED}
        # Bootstrap over SEEDS: a seed is one world, and the seat means within
        # it are not independent of each other.
        by_seed = {s: statistics.mean(pts[("fly", st, s)] - pts[(other, st, s)] for st in GRADED)
                   for s in seeds}
        mean = statistics.mean(by_seed.values())
        draws = sorted(statistics.mean(rng.choice(list(by_seed.values())) for _ in seeds)
                       for _ in range(BOOT))
        lo, hi = draws[int(0.025 * BOOT)], draws[int(0.975 * BOOT)]
        agree = sum(1 for v in per_seat.values() if (v > 0) == (mean > 0))
        ok = abs(mean) >= 25 and (lo > 0 or hi < 0) and agree >= 3
        verdicts[other] = ok
        print(f"  fly - {other:<9} mean {mean:+7.1f}  95% CI [{lo:+7.1f},{hi:+7.1f}]  "
              f"sign agrees {agree}/4  -> {'DIFFERENT' if ok else 'not different'}")
        for st, v in sorted(per_seat.items(), key=lambda kv: -abs(kv[1])):
            print(f"      {st:<17} {v:+8.1f}")

    print("\n\nTHE PREREGISTERED CLAIM\n")
    need = ("random", "hold", "blind", "shuffled")
    beat = [n for n in need if verdicts[n] and
            statistics.mean(statistics.mean(pts[("fly", st, s)] - pts[(n, st, s)] for st in GRADED)
                            for s in seeds) > 0]
    print(f"  beats, by the preregistered bar: {', '.join(beat) if beat else 'none of the four'}")
    if set(beat) == set(need):
        print("  -> 'the fly played better than random' is supported.")
    elif not verdicts["shuffled"]:
        print("  -> the real wiring is NOT distinguishable from the shuffled one.")
        print("     Per the preregistration, the claim is that the INTERFACE played,")
        print("     not the fly's connectome.")
    else:
        print("  -> not supported: the real brain did not beat all four.")


if __name__ == "__main__":
    raise SystemExit(main())
