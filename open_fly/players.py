"""The players: the simulated fly, and the baselines that play the same door."""
import random
import zlib

import numpy as np

from . import decode


def turn_seed(base, iso, turn):
    return zlib.crc32(f"{base}|{iso}|{turn}".encode()) & 0x7FFFFFFF


class FlyPlayer:
    """The brain decides every turn. `blind_rates` gives the input-blind control."""

    def __init__(self, brain, groups, encoder, *, window_ms=200.0, seed=0, blind_rates=None):
        self.brain, self.groups, self.encoder = brain, groups, encoder
        self.window_ms, self.seed, self.blind_rates = window_ms, seed, blind_rates
        self.dn_all = np.unique(np.concatenate([g for m in decode.MODULES for g in groups[m]]))
        self.last_info = None

    def __call__(self, state):
        rates = dict(self.blind_rates) if self.blind_rates is not None else self.encoder.rates(state)
        s = turn_seed(self.seed, state["iso"], state["turn"])
        counts = self.brain.run_window(rates, self.window_ms, s)
        tokens, info = decode.choose(counts, self.groups, state, random.Random(s))
        self.last_info = {"rates": rates,
                          "dn_spikes": int(counts[self.dn_all].sum()),
                          "active_neurons": int((counts > 0).sum()),
                          "picks": {m: v["picks"] for m, v in info.items()}}
        return tokens


class AlwaysHold:
    """Never does anything. Action 0 is legal in every menu."""
    last_info = None

    def __call__(self, state):
        return [f"{m}:0" for m in decode.MODULES if any(a == 0 for a, _ in state["legal"][m])]


class RandomLegal:
    """Uniformly random legal actions, a random number of them up to the budget."""

    def __init__(self, seed=0):
        self.seed = seed
        self.last_info = None

    def __call__(self, state):
        rng = random.Random(turn_seed(self.seed, state["iso"], state["turn"]))
        tokens = []
        for m in decode.MODULES:
            legal = [a for a, _ in state["legal"][m]]
            if not legal:
                continue
            for _ in range(rng.randint(1, int(state["budget"][m]))):
                a = rng.choice(legal)
                tokens.append(f"{m}:{a}")
                if a == 0:
                    break
        return tokens
