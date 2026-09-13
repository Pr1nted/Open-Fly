"""Descending-neuron spikes -> actions, under the model's own budget.

The 1,303 descending neurons (FlyWire super_class "descending") are the
brain's output to the body. They carry no annotation that says "declare war",
so any assignment of neurons to actions is arbitrary. This one is at least
not chosen by hand: whole cell types (so left and right homologues move
together) are dealt into 39 balanced groups by a committed seed, and each
group is one action. The shuffled-connectome control uses the same groups.
"""
import csv

import numpy as np

MENU_SIZES = {"e": 12, "p": 12, "w": 8, "n": 7}
MODULES = "epwn"


def descending_units(annotations_tsv, flyid_to_index):
    """Lists of brain indices, one per descending cell type."""
    units = {}
    with open(annotations_tsv, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["super_class"] != "descending":
                continue
            i = flyid_to_index.get(row["root_id"])
            if i is None:
                continue
            key = row["cell_type"] or row["hemibrain_type"] or ("root:" + row["root_id"])
            units.setdefault(key, []).append(i)
    return [sorted(units[k]) for k in sorted(units)]


def make_groups(units, seed):
    """Deal units into one balanced group per action. Deterministic in `seed`."""
    rng = np.random.default_rng(seed)
    n_groups = sum(MENU_SIZES.values())
    order = list(rng.permutation(len(units)))
    order.sort(key=lambda u: -len(units[u]))          # stable: seed breaks size ties
    bins = [[] for _ in range(n_groups)]
    totals = [0] * n_groups
    for u in order:
        low = min(totals)
        candidates = [b for b in range(n_groups) if totals[b] == low]
        b = candidates[int(rng.integers(len(candidates)))]
        bins[b].extend(units[u])
        totals[b] += len(units[u])
    slots = list(rng.permutation(n_groups))
    groups, k = {}, 0
    for m in MODULES:
        groups[m] = [np.array(sorted(bins[slots[k + a]]), dtype=np.int64) for a in range(MENU_SIZES[m])]
        k += MENU_SIZES[m]
    return groups


def choose(counts, groups, state, rng):
    """Up to the module's budget of the most active legal actions, per menu.

    Score = mean spikes per neuron in the action's group. Actions with no
    spikes are not taken. A menu where nothing fired holds (action 0). The
    server ends a module when it takes action 0, so nothing ranked after it
    is sent. Ties are broken by `rng`, seeded per turn.
    """
    tokens, info = [], {}
    for m in MODULES:
        legal = [a for a, _ in state["legal"][m]]
        if not legal:
            continue
        budget = int(state["budget"][m])
        scores = {a: float(counts[groups[m][a]].sum()) / len(groups[m][a]) for a in legal}
        order = sorted(legal, key=lambda a: (-scores[a], rng.random()))
        picks = [a for a in order if scores[a] > 0][:budget]
        if not picks:
            picks = [0] if 0 in legal else []
        if 0 in picks:
            picks = picks[:picks.index(0) + 1]
        tokens += [f"{m}:{a}" for a in picks]
        info[m] = {"picks": picks, "best": max(scores.values())}
    return tokens, info
