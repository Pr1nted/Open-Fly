"""Game state -> stimulation rates of real sensory neuron populations.

Fixed before any real run; see PREREGISTRATION.md. Rates stay inside the
ranges Shiu et al. used (roughly 10-200 Hz).
"""
REFS = {"land_pp": 0.5, "reserve_turns": 12.0, "wars": 3.0}
MAX_HZ = 200.0
FLOOR_HZ = 10.0
CHANNELS = ("sugar", "bitter", "water", "jon")


class Encoder:
    def __init__(self):
        self.prev = None

    def signals(self, s):
        share = float(s.get("share", 0.0))
        gross = float(s.get("gross", 0.0))
        net = float(s.get("net", 0.0))
        treasury = float(s.get("treasury", 0.0))
        wars = list(s.get("war", []))
        if self.prev is None:
            d_land, new_wars = 0.0, 0
        else:
            d_land = share - self.prev["share"]
            new_wars = len(set(wars) - set(self.prev["war"]))
        ratio = net / gross if gross > 1e-9 else 0.0
        sig = {
            "sugar": max(0.0, d_land) / REFS["land_pp"] + max(0.0, ratio),
            "bitter": max(0.0, -d_land) / REFS["land_pp"] + max(0.0, -ratio) + 0.5 * new_wars,
            "water": treasury / (REFS["reserve_turns"] * gross) if gross > 1e-9 else 0.0,
            "jon": len(wars) / REFS["wars"],
        }
        self.prev = {"share": share, "war": wars}
        return sig

    def rates(self, s):
        out = {}
        for k, v in self.signals(s).items():
            r = MAX_HZ * min(1.0, max(0.0, v))
            out[k] = r if r >= FLOOR_HZ else 0.0
        return out
