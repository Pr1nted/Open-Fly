// Does the browser brain behave like the Brian2 brain?
//
//   node tools/validate_brain.mjs web/data <brian2 probes.json>
//
// Runs the stage-1 probes (the same stimuli, five seeds each) through
// web/brain.js and compares, per probe, the mean total spikes, active neurons
// and descending-neuron spikes with Brian2's -- and, for the decoder, how well
// the 39 action groups' mean activity agrees (Pearson r and rank of the top
// group). The random draws differ between the two, so the bar is the same
// process, not the same numbers: every mean within the Brian2 seeds' own
// spread or 20%, and group profiles that correlate.
import { readFileSync } from "node:fs";
import { FlyBrain } from "../web/brain.js";

const [dataDir, refPath] = process.argv.slice(2);
const buf = readFileSync(`${dataDir}/connectome.bin`);
const connectome = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
const meta = JSON.parse(readFileSync(`${dataDir}/brain.json`, "utf8"));
const ref = JSON.parse(readFileSync(refPath, "utf8"));
const probes = {
  rest: {}, sugar: { sugar: 200 }, bitter: { bitter: 200 }, water: { water: 200 },
  jon: { jon: 200 }, crisis: { bitter: 200, jon: 130 }, mild: { sugar: 60, water: 110, jon: 70 },
};
const groups = ["e", "p", "w", "n"].flatMap((m) => meta.groups[m]);
const dnSet = Int32Array.from(meta.dn);

const t0 = performance.now();
const brain = new FlyBrain(connectome, meta);
console.log(`built in ${((performance.now() - t0) / 1000).toFixed(1)} s`);

const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const sd = (a) => { const m = mean(a); return Math.sqrt(mean(a.map((x) => (x - m) ** 2))); };
function pearson(a, b) {
  const ma = mean(a), mb = mean(b);
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < a.length; i++) { num += (a[i] - ma) * (b[i] - mb); da += (a[i] - ma) ** 2; db += (b[i] - mb) ** 2; }
  return da && db ? num / Math.sqrt(da * db) : NaN;
}

let failures = 0;
const walls = [];
for (const [name, rates] of Object.entries(probes)) {
  const rows = [];
  for (const seed of [1, 2, 3, 4, 5]) {
    const t = performance.now();
    const c = brain.runWindow(rates, 200, seed);
    walls.push(performance.now() - t);
    let total = 0, active = 0, dn = 0;
    for (let i = 0; i < c.length; i++) { total += c[i]; if (c[i]) active++; }
    for (const i of dnSet) dn += c[i];
    rows.push({ total, active, dn, gm: groups.map((g) => g.reduce((s, i) => s + c[i], 0) / g.length) });
  }
  const r = ref[name];
  const line = [name.padEnd(7)];
  for (const k of ["total", "active", "dn"]) {
    const js = mean(rows.map((x) => x[k])), br = mean(r.map((x) => x[k])), spread = sd(r.map((x) => x[k]));
    const ok = br === 0 ? js === 0 : Math.abs(js - br) <= Math.max(2 * spread, 0.2 * br);
    if (!ok) failures++;
    line.push(`${k} js ${js.toFixed(0).padStart(5)} brian ${br.toFixed(0).padStart(5)} ${ok ? "ok " : "OFF"}`);
  }
  if (name !== "rest") {
    const gj = groups.map((_, gi) => mean(rows.map((x) => x.gm[gi])));
    const gb = groups.map((_, gi) => mean(r.map((x) => x.group_means[gi])));
    const rr = pearson(gj, gb);
    const topJ = gj.indexOf(Math.max(...gj)), topB = gb.indexOf(Math.max(...gb));
    if (!(rr > 0.8)) failures++;
    line.push(`groups r ${rr.toFixed(2)} top ${topJ === topB ? "same" : `${topJ} vs ${topB}`}`);
  }
  console.log(line.join(" | "));
}
console.log(`window wall time: mean ${(mean(walls) / 1000).toFixed(2)} s, max ${(Math.max(...walls) / 1000).toFixed(2)} s`);
console.log(failures ? `${failures} check(s) OFF` : "ALL CHECKS PASS");
process.exit(failures ? 1 : 0);
