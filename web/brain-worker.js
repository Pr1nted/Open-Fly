// The brain, off the page's thread: loads the connectome once, then runs one
// 200 ms decision window per request and sends back every neuron's spike count.
import { FlyBrain } from "./brain.js";
import { loadPacked } from "./packed.js";

let brain = null;

self.onmessage = async (e) => {
  const msg = e.data;
  try {
    if (msg.type === "load") {
      const meta = await (await fetch(msg.metaUrl)).json();
      const connectome = await loadPacked(msg.connectomeManifest,
        (got, total) => self.postMessage({ type: "progress", got, total }));
      brain = new FlyBrain(connectome, meta);
      self.postMessage({ type: "loaded", n: brain.n, meta });
    } else if (msg.type === "run") {
      const t0 = performance.now();
      const counts = brain.runWindow(msg.rates, msg.windowMs, msg.seed);
      self.postMessage({ type: "ran", id: msg.id, counts, ms: performance.now() - t0 }, [counts.buffer]);
    }
  } catch (err) {
    self.postMessage({ type: "error", id: msg.id, message: String(err && err.message || err) });
  }
};
