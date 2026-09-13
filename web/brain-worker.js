// The brain, off the page's thread: loads the connectome once, then runs one
// 200 ms decision window per request and sends back every neuron's spike count.
import { FlyBrain } from "./brain.js";

let brain = null;

self.onmessage = async (e) => {
  const msg = e.data;
  try {
    if (msg.type === "load") {
      const meta = await (await fetch(msg.metaUrl)).json();
      const res = await fetch(msg.connectomeUrl);
      const total = +res.headers.get("Content-Length") || 0;
      const reader = res.body.getReader();
      const chunks = [];
      let got = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        got += value.length;
        self.postMessage({ type: "progress", got, total });
      }
      const buf = new Uint8Array(got);
      let at = 0;
      for (const c of chunks) { buf.set(c, at); at += c.length; }
      brain = new FlyBrain(buf.buffer, meta);
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
