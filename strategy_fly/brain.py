"""The whole-brain model, built once and run in short decision windows.

Neuron and synapse equations and every constant are copied unchanged from
model.py of philshiu/Drosophila_brain_model (MIT), which accompanies Shiu et
al., "A Drosophila computational brain model reveals sensorimotor processing",
Nature 2024. Two things differ, both for speed and neither for dynamics:

- The network is built ONCE. model.py rebuilds all 15 million synapses for
  every trial, which a game of 120 turns cannot afford.
- Stimulation uses a PoissonGroup per sensory channel instead of one
  PoissonInput per neuron. PoissonInput fixes its rate when it is created;
  a PoissonGroup's `rates` can change every turn. Each input spike adds
  w_syn * f_poi to the target's membrane, exactly as PoissonInput did, and
  the targets have no refractory period, as in model.py.
"""
import resource
import sys
import time
from textwrap import dedent

import numpy as np
import pandas as pd
from brian2 import (Hz, NeuronGroup, Network, PoissonGroup, SpikeMonitor,
                    Synapses, mV, ms, prefs)
from brian2 import seed as brian_seed

PARAMS = {
    "v_0": -52 * mV, "v_rst": -52 * mV, "v_th": -45 * mV,
    "t_mbr": 20 * ms, "tau": 5 * ms, "t_rfc": 2.2 * ms, "t_dly": 1.8 * ms,
    "w_syn": 0.275 * mV, "f_poi": 250,
}
EQS = dedent("""
    dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)
    dg/dt = -g / tau               : volt (unless refractory)
    rfc                            : second
    """)
THRESHOLD = "v > v_th"
RESET = "v = v_rst; w = 0; g = 0 * mV"


def peak_rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1024 if sys.platform.startswith("linux") else r / 1048576


class FlyBrain:
    def __init__(self, completeness_csv, connectivity_parquet, *,
                 shuffle_seed=None, codegen="cython"):
        t0 = time.time()
        prefs.codegen.target = codegen
        comp = pd.read_csv(completeness_csv, index_col=0)
        self.flyids = [str(x) for x in comp.index]
        self.index = {f: i for i, f in enumerate(self.flyids)}
        self.n = len(self.flyids)
        del comp

        con = pd.read_parquet(connectivity_parquet, columns=[
            "Presynaptic_Index", "Postsynaptic_Index", "Excitatory x Connectivity"])
        pre = con["Presynaptic_Index"].to_numpy(np.int32)
        post = con["Postsynaptic_Index"].to_numpy(np.int32)
        weights = con["Excitatory x Connectivity"].to_numpy(np.float64)
        self.n_synapses = len(pre)
        del con

        # THE SHUFFLED CONTROL. Permuting only the postsynaptic column keeps
        # every neuron's out-degree, in-degree and outgoing signs and weights,
        # and scrambles who talks to whom.
        self.shuffle_seed = shuffle_seed
        if shuffle_seed is not None:
            post = np.random.default_rng(shuffle_seed).permutation(post)

        self.neu = NeuronGroup(self.n, model=EQS, method="linear", threshold=THRESHOLD,
                               reset=RESET, refractory="rfc", name="neurons",
                               namespace=dict(PARAMS))
        self.neu.v = PARAMS["v_0"]
        self.neu.g = 0 * mV
        self.neu.rfc = PARAMS["t_rfc"]
        self.syn = Synapses(self.neu, self.neu, "w : volt", on_pre="g += w",
                            delay=PARAMS["t_dly"], name="synapses")
        self.syn.connect(i=pre, j=post)
        self.syn.w = weights * PARAMS["w_syn"]
        del pre, post, weights

        self.mon = SpikeMonitor(self.neu, record=False, name="spikes")
        self.net = Network(self.neu, self.syn, self.mon)
        self.channels = {}
        self.build_seconds = time.time() - t0

    def add_channel(self, name, flyids):
        """A sensory population driven by one Poisson rate. Returns its size."""
        idx = np.array([self.index[f] for f in flyids if f in self.index], dtype=np.int32)
        pg = PoissonGroup(len(idx), rates=0 * Hz, name=f"in_{name}")
        syn = Synapses(pg, self.neu, on_pre="v += w_in", name=f"in_{name}_syn",
                       namespace={"w_in": PARAMS["w_syn"] * PARAMS["f_poi"]})
        syn.connect(i=np.arange(len(idx)), j=idx)
        self.neu.rfc[idx] = 0 * ms
        self.net.add(pg, syn)
        self.channels[name] = (pg, idx)
        return len(idx)

    def run_window(self, rates_hz, window_ms, rng_seed, flush_ms=2.0):
        """Spike counts per neuron over one decision window.

        Inputs off and a short run first, longer than the 1.8 ms synaptic
        delay, so spikes still in flight from the previous turn land before
        the membrane is reset and counting starts.
        """
        brian_seed(int(rng_seed) & 0x7FFFFFFF)
        for pg, _ in self.channels.values():
            pg.rates = 0 * Hz
        if flush_ms > 0:
            self.net.run(flush_ms * ms)
        self.neu.v = PARAMS["v_0"]
        self.neu.g = 0 * mV
        for name, (pg, _) in self.channels.items():
            pg.rates = float(rates_hz.get(name, 0.0)) * Hz
        before = np.array(self.mon.count[:], dtype=np.int64)
        self.net.run(window_ms * ms)
        return np.array(self.mon.count[:], dtype=np.int64) - before
