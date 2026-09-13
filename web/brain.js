// The FlyWire whole-brain model, in the browser.
//
// The same model brain.py runs in Brian2 -- Shiu et al., Nature 2024, model.py
// (MIT) -- with the same equations, constants and order of operations per step:
//
//   dv/dt = (v_0 - v + g) / t_mbr     (frozen while refractory)
//   dg/dt = -g / tau                   (frozen while refractory)
//   spike when v > v_th; then v = v_rst, g = 0, refractory for t_rfc
//   a spike adds w = count * w_syn to g of each target, t_dly later
//   a sensory input spike adds w_syn * f_poi to v of its neuron at once
//
// Brian2 integrates this linear system exactly; so does this, with the closed
// form below. Its schedule per 0.1 ms step is groups -> thresholds ->
// synapses -> resets, and so is this loop's. Random numbers come from a
// different generator, so a window here is a different draw from the same
// process as a Brian2 window -- which is what tools/validate_brain.mjs checks.
//
// EVENT-DRIVEN. Of 138,639 neurons, a 200 ms window moves a few thousand off
// rest. A neuron at rest stays at rest under these equations, so only neurons
// that have received input are integrated; the rest cost nothing. That is what
// makes 2,000 steps over the whole brain fit in a second or two of JavaScript.

export class FlyBrain {
  constructor(connectome, meta) {
    const dv = new DataView(connectome);
    const magic = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3));
    if (magic !== "SFC1") throw new Error("connectome.bin has the wrong header");
    const n = dv.getUint32(4, true), nsyn = dv.getUint32(8, true);
    let off = 12;
    this.n = n;
    this.indptr = new Uint32Array(connectome, off, n + 1); off += (n + 1) * 4;
    this.post = new Uint32Array(connectome, off, nsyn); off += nsyn * 4;
    this.count = new Int16Array(connectome.slice(off, off + nsyn * 2));
    const P = meta.params;
    this.P = P;
    this.dt = P.dt;
    this.em = Math.exp(-P.dt / P.t_mbr);
    this.es = Math.exp(-P.dt / P.tau);
    this.k = P.tau / (P.tau - P.t_mbr);          // v gets k*g of the g term
    this.delaySteps = Math.round(P.t_dly / P.dt);
    this.rfcSteps = Math.round(P.t_rfc / P.dt);
    this.wSyn = P.w_syn;
    this.wPoisson = P.w_syn * P.f_poi;
    // FLOAT64, as Brian2. With 32-bit state the two engines agreed on every
    // mechanism and still parted after ~55 ms of a stimulus, rounding near
    // threshold; in 64-bit the same scripted input gives the same 3,063 spikes
    // on the same steps from the same neurons. 2 MB is the price.
    this.v = new Float64Array(n).fill(P.v_0);
    this.g = new Float64Array(n);
    this.rfc = new Uint16Array(n);                // steps of refractoriness left
    this.noRfc = new Uint8Array(n);               // sensory inputs have none
    this.awake = new Uint8Array(n);
    this.awakeList = new Int32Array(n);
    this.awakeCount = 0;
    this.sensory = {};
    for (const [ch, idx] of Object.entries(meta.sensory)) {
      this.sensory[ch] = Int32Array.from(idx);
      for (const i of idx) this.noRfc[i] = 1;
    }
    // Spikes in flight: one bucket of (target, weight) per step of delay.
    this.ring = [];
    for (let s = 0; s <= this.delaySteps; s++) this.ring.push({ post: new Int32Array(1 << 16), w: new Float64Array(1 << 16), len: 0 });
    this.head = 0;
    this.spikesStep = new Int32Array(n);
  }

  wake(i) {
    if (!this.awake[i]) { this.awake[i] = 1; this.awakeList[this.awakeCount++] = i; }
  }

  push(bucket, target, w) {
    if (bucket.len === bucket.post.length) {
      const p = new Int32Array(bucket.post.length * 2); p.set(bucket.post); bucket.post = p;
      const ww = new Float64Array(bucket.w.length * 2); ww.set(bucket.w); bucket.w = ww;
    }
    bucket.post[bucket.len] = target; bucket.w[bucket.len] = w; bucket.len++;
  }

  // One 0.1 ms step. `rates` is Hz per channel; `counts` collects spikes (or null).
  step(rates, rand, counts) {
    const { v, g, rfc, noRfc, P, em, es, k } = this;
    const v0 = P.v_0, vth = P.v_th;
    // groups: integrate every awake, non-refractory neuron; retire the settled
    let live = 0, nSpk = 0;
    const list = this.awakeList, spk = this.spikesStep;
    for (let j = 0; j < this.awakeCount; j++) {
      const i = list[j];
      if (rfc[i] > 0) { list[live++] = i; continue; }
      const gi = g[i];
      const vi = v0 + (v[i] - v0 - k * gi) * em + k * gi * es;
      const gn = gi * es;
      v[i] = vi; g[i] = gn;
      if (vi > vth) spk[nSpk++] = i;
      if (Math.abs(vi - v0) < 1e-5 && Math.abs(gn) < 1e-6) { v[i] = v0; g[i] = 0; this.awake[i] = 0; }
      else list[live++] = i;
    }
    this.awakeCount = live;
    // thresholds of the Poisson inputs, and synapses: delayed deliveries land on
    // g, input spikes land on v -- both before the reset below, as in Brian2
    // A REFRACTORY TARGET IGNORES THE SPIKE. g is declared "(unless refractory)",
    // and in Brian2 that guards synaptic updates to it as well as its
    // integration: an input landing inside t_rfc is lost, not stored for later.
    // Storing it instead let a neuron fire again one input sooner -- an ISI of
    // 250 steps where Brian2 gives 300 -- which compounded into ~25% more
    // spikes downstream of a strong stimulus.
    const bucket = this.ring[this.head];
    for (let s = 0; s < bucket.len; s++) {
      const t = bucket.post[s];
      if (rfc[t] > 0) continue;
      g[t] += bucket.w[s];
      this.wake(t);
    }
    bucket.len = 0;
    for (const ch in this.sensory) {
      const r = rates[ch] || 0;
      if (r <= 0) continue;
      const p = r * this.dt * 1e-3;
      const idx = this.sensory[ch];
      for (let s = 0; s < idx.length; s++) {
        if (rand() < p) { const t = idx[s]; if (rfc[t] > 0) continue; v[t] += this.wPoisson; this.wake(t); }
      }
    }
    // resets, and each spike queued t_dly ahead
    const target = this.ring[(this.head + this.delaySteps) % this.ring.length];
    for (let s = 0; s < nSpk; s++) {
      const i = spk[s];
      v[i] = P.v_rst; g[i] = 0;
      // Brian2 frees a neuron once timestep(t - lastspike) >= timestep(t_rfc):
      // after a spike at step k it is frozen for steps k+1 .. k+21 and
      // integrates again at k+22. The counter runs down at the end of each
      // step, including this one, so 22 here freezes exactly those 21.
      rfc[i] = noRfc[i] ? 0 : this.rfcSteps;
      if (counts) counts[i]++;
      for (let e = this.indptr[i], end = this.indptr[i + 1]; e < end; e++) {
        this.push(target, this.post[e], this.count[e] * this.wSyn);
      }
    }
    // a refractory neuron's clock runs down whether or not it is integrated
    for (let j = 0; j < this.awakeCount; j++) { const i = list[j]; if (rfc[i] > 0) rfc[i]--; }
    this.head = (this.head + 1) % this.ring.length;
  }

  // Spike counts per neuron over one decision window, as brain.run_window.
  runWindow(rates, windowMs, seed, flushMs = 2.0) {
    const rand = mulberry32(seed >>> 0);
    const flushSteps = Math.round(flushMs / this.dt);
    for (let s = 0; s < flushSteps; s++) this.step({}, rand, null);
    for (let j = 0; j < this.awakeCount; j++) {
      const i = this.awakeList[j];
      this.v[i] = this.P.v_0; this.g[i] = 0;
    }
    const counts = new Uint16Array(this.n);
    const steps = Math.round(windowMs / this.dt);
    for (let s = 0; s < steps; s++) this.step(rates, rand, counts);
    return counts;
  }
}

export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
