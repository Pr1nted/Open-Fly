"""Everything the browser brain needs, from the same files the Python brain reads.

    .venv/bin/python tools/export_web_brain.py --fly-data <folder> --out web/data

Writes:
  connectome.bin  SFC1: n, synapse count, then a CSR by presynaptic neuron --
                  row pointers (uint32, n+1), postsynaptic indices (uint32) and
                  signed synapse counts (int16). The browser multiplies a count
                  by w_syn = 0.275 mV, exactly as brain.py does.
  brain.bin       SFB1: neuron positions and kinds for the 3D view (see live.py).
  brain.json      the decoder's 39 action groups and the four sensory channels,
                  as brain indices. Groups are dealt by numpy's generator with the
                  preregistered seed, so they are computed HERE and shipped, not
                  re-dealt in JavaScript with a different generator.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from open_fly import decode  # noqa: E402

PARTITION_SEED = 783
PARAMS = {"v_0": -52.0, "v_rst": -52.0, "v_th": -45.0, "t_mbr": 20.0, "tau": 5.0,
          "t_rfc": 2.2, "t_dly": 1.8, "w_syn": 0.275, "f_poi": 250, "dt": 0.1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fly-data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    fd, out = args.fly_data, args.out
    os.makedirs(out, exist_ok=True)

    comp = pd.read_csv(os.path.join(fd, "Completeness_783.csv"), index_col=0)
    flyids = [str(x) for x in comp.index]
    index = {f: i for i, f in enumerate(flyids)}
    n = len(flyids)

    con = pd.read_parquet(os.path.join(fd, "Connectivity_783.parquet"),
                          columns=["Presynaptic_Index", "Postsynaptic_Index", "Excitatory x Connectivity"])
    pre = con["Presynaptic_Index"].to_numpy(np.int64)
    post = con["Postsynaptic_Index"].to_numpy(np.int64)
    w = con["Excitatory x Connectivity"].to_numpy(np.int64)
    del con
    if np.abs(w).max() > 32767:
        raise SystemExit(f"a synapse count of {np.abs(w).max()} does not fit int16")
    order = np.lexsort((post, pre))
    pre, post, w = pre[order], post[order], w[order]
    indptr = np.zeros(n + 1, np.uint32)
    np.add.at(indptr, pre + 1, 1)
    indptr = np.cumsum(indptr, dtype=np.uint64).astype(np.uint32)
    with open(os.path.join(out, "connectome.bin"), "wb") as f:
        f.write(b"SFC1" + struct.pack("<II", n, len(post)))
        f.write(indptr.astype("<u4").tobytes())
        f.write(post.astype("<u4").tobytes())
        f.write(w.astype("<i2").tobytes())
    print(f"connectome.bin: {n} neurons, {len(post)} synapses, "
          f"{os.path.getsize(os.path.join(out, 'connectome.bin')) / 1e6:.0f} MB")

    tsv = os.path.join(fd, "neuron_annotations.tsv")
    groups = decode.make_groups(decode.descending_units(tsv, index), PARTITION_SEED)
    sensory_ids = json.load(open(os.path.join(os.path.dirname(HERE), "open_fly", "sensory_ids.json")))
    sensory = {ch: [index[f] for f in sensory_ids[ch] if f in index] for ch in ("sugar", "bitter", "water", "jon")}
    dn = sorted(set(int(i) for m in decode.MODULES for g in groups[m] for i in g))
    json.dump({"n": n, "params": PARAMS, "partition_seed": PARTITION_SEED,
               "groups": {m: [[int(i) for i in g] for g in groups[m]] for m in decode.MODULES},
               "sensory": sensory, "dn": dn},
              open(os.path.join(out, "brain.json"), "w"), separators=(",", ":"))
    print("brain.json: groups", {m: len(groups[m]) for m in decode.MODULES},
          "sensory", {k: len(v) for k, v in sensory.items()}, "dn", len(dn))

    ann = pd.read_csv(tsv, sep="\t", usecols=["root_id", "pos_x", "pos_y", "pos_z", "super_class"],
                      dtype={"root_id": str}, low_memory=False).drop_duplicates("root_id").set_index("root_id")
    m = ann.reindex(flyids)
    pos = m[["pos_x", "pos_y", "pos_z"]].to_numpy(dtype=np.float64)
    sc = m["super_class"].fillna("").to_numpy().astype(str)
    missing = np.isnan(pos).any(axis=1)
    nm = pos * np.array([4.0, 4.0, 40.0])
    lo, hi = np.nanmin(nm, 0), np.nanmax(nm, 0)
    c, s = (lo + hi) / 2, 0.9 / (hi[0] - lo[0])
    xyz = np.stack([(nm[:, 0] - c[0]) * s, -(nm[:, 1] - c[1]) * s, (nm[:, 2] - c[2]) * s], 1)
    xyz[missing] = 0
    kind = np.full(n, 2, np.uint8)
    kind[np.isin(sc, ["optic", "visual_projection", "visual_centrifugal"])] = 1
    kind[np.isin(sc, ["sensory", "sensory_ascending"])] = 3
    kind[np.isin(sc, ["ascending"])] = 5
    kind[dn] = 4
    kind[missing] = 255
    blob = bytearray(b"SFB1" + struct.pack("<III", 1, n, 0))
    blob += xyz.astype("<f4").tobytes() + kind.tobytes()
    blob += b"\0" * ((-len(blob)) % 4)
    open(os.path.join(out, "brain.bin"), "wb").write(bytes(blob))
    print(f"brain.bin: {len(blob) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
