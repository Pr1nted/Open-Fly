"""Build notebooks/open_fly_colab.ipynb from the package sources.

The notebook is self-contained so it can be uploaded to Colab and run without
cloning this repository at all: every package file and the Open Doctrines
patch are written out by %%writefile cells generated from the repo, which
stays the one source of truth.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "/content/open_fly_pkg"
OD_COMMIT = "05881e0"
SEAT, SEED = "1914:SWE:rung", 20260801


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text, exact=False):
    # exact=True keeps the text byte for byte. %%writefile bodies must end in
    # the file's own final newline: a patch without one fails `git apply`.
    src = text if exact else text.strip("\n")
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.splitlines(True)}


cells = [md(f"""
# Open Fly

A **simulation** of the FlyWire fruit fly connectome (Shiu et al. 2024 model) plays
**Open Doctrines** through the game's benchmark agent door, under the same action
budget as the game's trained AI. It is not a living fly, and the way game events
reach its taste neurons and its descending neurons reach the game is our invention,
fixed in advance in `PREREGISTRATION.md`.

This notebook stops at the first milestone: **the fly plays a full seat.**
Run all cells in order. Runtime: CPU is enough.
""")]

# BEFORE the %%writefile cells: %%writefile does not create directories, and
# the first version of this notebook made them in the build cell, after the
# files had already failed to write.
cells.append(code(f"""
!mkdir -p {PKG}/open_fly {PKG}/patches /content/results; nproc; free -g | head -2; python3 --version
"""))

for rel in ["open_fly/__init__.py", "open_fly/protocol.py", "open_fly/driver.py",
            "open_fly/brain.py", "open_fly/encode.py", "open_fly/decode.py",
            "open_fly/players.py", "open_fly/sensory_ids.json",
            "patches/opendoctrines-agent-door.patch"]:
    body = (ROOT / rel).read_text()
    cells.append(code(f"%%writefile {PKG}/{rel}\n{body}", exact=True))

cells.append(md("## 1. Build the game server (headless, about 10 minutes)"))
cells.append(code(f"""
%%bash
set -e
mkdir -p {PKG}/open_fly {PKG}/patches /content/results
apt-get -qq update
apt-get -qq install -y build-essential cmake ninja-build git git-lfs python3 libasound2-dev libx11-dev libxrandr-dev libxi-dev libgl1-mesa-dev libglu1-mesa-dev libxcursor-dev libxinerama-dev libwayland-dev libxkbcommon-dev > /dev/null
cd /content
[ -d od ] || git clone -q https://github.com/Pr1nted/Open-Doctrines od
cd od
git checkout -q {OD_COMMIT}
git lfs pull > /dev/null 2>&1 || true
if git apply --reverse --check {PKG}/patches/opendoctrines-agent-door.patch 2>/dev/null; then
  echo "patch already applied"
else
  git apply -p1 {PKG}/patches/opendoctrines-agent-door.patch && echo "patch applied"
fi
# -include cstdint: Colab builds with GCC 13, which no longer brings <cstdint> in
# through <string> or <algorithm>. Open Doctrines headers that use uint8_t without
# including it built on CI (GCC 11) and stop here. Force-including it fixes the whole
# class at once and changes nothing about what the game does.
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-include cstdint" > /content/results/cmake-configure.log
time cmake --build build --target OpenDoctrinesServer -j"$(nproc)" > /content/results/cmake-build.log
ls -la build/OpenDoctrinesServer
"""))

cells.append(md("## 2. Check the agent door before any brain touches it"))
cells.append(code(f"""
import sys; sys.path.insert(0, "{PKG}")
from open_fly.driver import run_seat
from open_fly.players import AlwaysHold
BIN, DATA = "/content/od/build/OpenDoctrinesServer", "/content/od/data/"
r = run_seat(BIN, DATA, "{SEAT}", {SEED}, AlwaysHold(), label="door-check", turns=3, log_dir="/content/results")
print(r)
import subprocess; print(subprocess.run(["grep", "-m3", "budget\\\\|BENCH\\\\|seed", r["log"]], capture_output=True, text=True).stdout)
assert r["returncode"] == 0 and r["score"] is not None, "the door did not complete a 3-turn seat"
"""))

cells.append(md("## 3. Download the connectome and build the brain"))
cells.append(code("""
%%bash
set -e
pip -q install "brian2==2.10.1" pyarrow
mkdir -p /content/fly && cd /content/fly
B=https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/main
[ -f Completeness_783.csv ] || curl -sSLO $B/Completeness_783.csv
[ -f Connectivity_783.parquet ] || curl -sSLO $B/Connectivity_783.parquet
[ -f neuron_annotations.tsv ] || curl -sSL -o neuron_annotations.tsv https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv
ls -la
"""))
cells.append(code(f"""
import json, time
from open_fly.brain import FlyBrain, peak_rss_mb
from open_fly import decode
from open_fly.encode import Encoder
from open_fly.players import FlyPlayer, RandomLegal

PARTITION_SEED, BRAIN_SEED, WINDOW_MS = 783, 20240922, 200.0   # fixed in PREREGISTRATION.md
brain = FlyBrain("/content/fly/Completeness_783.csv", "/content/fly/Connectivity_783.parquet")
ids = json.load(open("{PKG}/open_fly/sensory_ids.json"))
sizes = {{ch: brain.add_channel(ch, ids[ch]) for ch in ("sugar", "bitter", "water", "jon")}}
units = decode.descending_units("/content/fly/neuron_annotations.tsv", brain.index)
groups = decode.make_groups(units, PARTITION_SEED)
print(f"neurons {{brain.n}}, synapses {{brain.n_synapses}}, built in {{brain.build_seconds:.0f}} s, peak RSS {{peak_rss_mb():.0f}} MB")
print("sensory channels:", sizes, "| descending cell types:", len(units))
"""))

cells.append(md("## 4. Stage 0 and 1: speed, and does the output respond at all?"))
cells.append(code("""
import numpy as np
dn_all = np.unique(np.concatenate([g for m in decode.MODULES for g in groups[m]]))
probes = {"rest": {}, "sugar": {"sugar": 200}, "bitter": {"bitter": 200},
          "water": {"water": 200}, "jon": {"jon": 200},
          "crisis": {"bitter": 200, "jon": 130}}
report = {}
for name, rates in probes.items():
    t0 = time.time()
    c = brain.run_window(rates, WINDOW_MS, rng_seed=1)
    report[name] = {"wall_s": round(time.time() - t0, 1), "active": int((c > 0).sum()),
                    "dn_spikes": int(c[dn_all].sum())}
    print(name, report[name])
responsive = any(v["dn_spikes"] > 0 for k, v in report.items() if k != "rest")
print("descending neurons respond to input:", responsive)
assert responsive, "STOP: the output neurons never fire, so the fly could only ever hold."
"""))

cells.append(md("## 5. The fly plays a full seat"))
cells.append(code(f"""
fly = FlyPlayer(brain, groups, Encoder(), window_ms=WINDOW_MS, seed=BRAIN_SEED)
result = run_seat(BIN, DATA, "{SEAT}", {SEED}, fly, label="fly", turns=120, log_dir="/content/results")
print(result)
assert result["returncode"] == 0 and result["score"] is not None
assert result["counts"]["did"] > 0, "the fly never took an action"
print("The fly played Open Doctrines:", result["counts"]["did"], "actions over 120 turns, final share", result["score"])
"""))
cells.append(code(f"""
# Context only, same door, same seat and seed. Not the benchmark: see PREREGISTRATION.md.
for label, player in (("hold", AlwaysHold()), ("random", RandomLegal(seed=BRAIN_SEED))):
    print(run_seat(BIN, DATA, "{SEAT}", {SEED}, player, label=label, turns=120, log_dir="/content/results"))
"""))
cells.append(code("""
!cd /content && zip -qr open_fly_results.zip results && ls -la open_fly_results.zip
"""))

nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks" / "open_fly_colab.ipynb"
out.write_text(json.dumps(nb, indent=1))
print("wrote", out, len(cells), "cells")
