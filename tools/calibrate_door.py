#!/usr/bin/env python3
"""Door calibration: does the agent-door patch change the game it measures?

    OD_PLAIN=<unpatched server at 05881e0> python3 tools/calibrate_door.py

Build the unpatched reference in a worktree of its own -- a shared build
directory hands you objects from another commit and the comparison silently
becomes a different one:

    git -C <opendoctrines> worktree add --detach /tmp/od-calib 05881e0
    cmake -S /tmp/od-calib -B /tmp/od-calib/build-calib -DCMAKE_BUILD_TYPE=Release
    cmake --build /tmp/od-calib/build-calib --target OpenDoctrinesServer -j8


The patch edits src/Game_AITrain.cpp, which is also where the [BENCH] score is
computed, so the two cannot be assumed independent. This runs BOTH binaries --
the patched one Open Fly drives, and an unpatched build of the SAME commit
(05881e0) -- through od_bench.py's own --eval-ai invocation, on the bench seats
and the three bench seeds, and compares the scores.

The comparison is against an unpatched build of the same commit, not against
today's tree: fifteen days of game changes sit between them, and a difference
there would say nothing about the patch.

Any disagreement means the matrix would be measured on a different game from
the one od_bench's numbers describe.
"""
import json, os, re, subprocess, sys, time

ROOT = os.environ.get("OD_ROOT", os.path.expanduser("~/CLionProjects/OpenDoctrines"))
PATCHED = os.environ.get("OD_PATCHED", os.path.expanduser("~/.open_fly/bin/OpenDoctrinesServer"))
PLAIN = os.environ.get("OD_PLAIN", "/tmp/od-calib/build-calib/OpenDoctrinesServer")
MODEL = os.path.join(ROOT, "data", "ai", "model.bin")
SCORE = re.compile(r"^\[BENCH\] seat (\S+)\s+score ([0-9.]+)")
TURNS, DIFFICULTY, RUSH_VARIANT = 120, 3, 3
SEEDS = [20260801, 4242, 90210]
SEATS = [("1914", "FRA", "rung"), ("1914", "SWE", "rung"), ("1939", "USA", "rung"),
         ("modern", "CHN", "rung"), ("1914", "FRA", "rush"), ("1939", "NOR", "hood")]


def run(binary, mapname, iso, world, seed):
    env = dict(os.environ, OD_EVAL_MODEL=MODEL)
    # --data on BOTH, though od_bench passes it on neither: the server resolves
    # data as <bindir>/../data, and the patched binary lives in ~/.open_fly/bin
    # where there is none. Giving it to only the one that needs it would make
    # the two runs differ in their arguments as well as in their build.
    cmd = [binary, "--eval-ai", "1", str(TURNS), str(seed), str(DIFFICULTY),
           "--scenarios", "--bench-seat", f"{mapname}:{iso}",
           "--data", os.path.join(ROOT, "data")]
    if world == "rush":
        cmd += ["--vs-exploit", str(RUSH_VARIANT)]
    elif world == "hood":
        cmd += ["--vs-exploit", str(RUSH_VARIANT), "--rush-neighbours", "1"]
    t0 = time.time()
    try:
        out = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True,
                             text=True, errors="replace", timeout=7200).stdout
    except (subprocess.SubprocessError, OSError) as e:
        return None, time.time() - t0, f"FAILED {e}"
    for line in out.splitlines():
        if m := SCORE.match(line):
            return float(m.group(2)), time.time() - t0, ""
    return None, time.time() - t0, "no [BENCH] line"


def main():
    only = sys.argv[1:] or None
    rows, bad = [], 0
    for mapname, iso, world in SEATS:
        label = f"{mapname}:{iso}:{world}"
        if only and label not in only:
            continue
        for seed in SEEDS:
            a, ta, ea = run(PATCHED, mapname, iso, world, seed)
            b, tb, eb = run(PLAIN, mapname, iso, world, seed)
            same = (a is not None and b is not None and abs(a - b) < 1e-9)
            if not same:
                bad += 1
            rows.append({"seat": label, "seed": seed, "patched": a, "plain": b,
                         "same": same, "err": (ea + eb).strip(),
                         "secs": round(ta + tb, 1)})
            print(f"{label:18s} {seed:>10}  patched {a}  plain {b}  "
                  f"{'ok' if same else 'DIFFERS'}  {round(ta+tb,1)}s", flush=True)
    json.dump(rows, open(os.environ.get("OD_OUT", "docs/calibration/door-calibration.json"), "w"), indent=1)
    print(f"\n{len(rows) - bad}/{len(rows)} identical")
    print("CALIBRATION PASSES" if bad == 0 else
          "CALIBRATION FAILS -- the patch changes the game it measures")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
