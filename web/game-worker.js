// Open Doctrines, off the page's thread: the OpenDoctrinesAgent WebAssembly
// module (built from Open Doctrines' own src/web/AgentWeb.cpp). The page asks
// for a seat, a position, orders and the end of a turn; this module resolves
// them with the game's own rules.
import createOpenDoctrinesAgent from "./agent/OpenDoctrinesAgent.mjs";

let od = null, api = null;
const ready = createOpenDoctrinesAgent({
  locateFile: (path) => new URL(`./agent/${path}`, import.meta.url).href,
  print: (line) => self.postMessage({ type: "log", line }),
  printErr: (line) => self.postMessage({ type: "log", line }),
}).then((m) => {
  od = m;
  api = {
    begin: m.cwrap("od_agent_begin", "number", ["string", "number", "number"]),
    position: m.cwrap("od_agent_position", "string", ["number"]),
    play: m.cwrap("od_agent_play", "string", ["string"]),
    endTurn: m.cwrap("od_agent_end_turn", "number", []),
    mapSeed: m.cwrap("od_agent_map_seed", "number", []),
  };
  try { m.FS.mkdir("/maps"); } catch (_) { /* already there */ }
  self.postMessage({ type: "ready" });
});

function listMaps() {
  const out = [];
  for (const dir of ["/data/STDmaps", "/maps"]) {
    let names = [];
    try { names = od.FS.readdir(dir); } catch (_) { continue; }
    for (const name of names) if (name.endsWith(".odmap")) out.push({ path: `${dir}/${name}`, name: name.replace(/\.odmap$/, ""), imported: dir === "/maps" });
  }
  return out;
}

self.onmessage = async (e) => {
  const msg = e.data;
  await ready;
  let reply;
  try {
    switch (msg.type) {
      case "maps": reply = { maps: listMaps() }; break;
      case "readMap": {
        const bytes = od.FS.readFile(msg.path);
        self.postMessage({ type: "reply", id: msg.id, bytes }, [bytes.buffer]);
        return;
      }
      case "import": {
        const safe = msg.name.replace(/[^A-Za-z0-9_. -]/g, "_");
        const path = `/maps/${safe.endsWith(".odmap") ? safe : safe + ".odmap"}`;
        od.FS.writeFile(path, new Uint8Array(msg.bytes));
        reply = { path, maps: listMaps() };
        break;
      }
      case "begin": {
        const t0 = performance.now();
        const ok = api.begin(msg.seat, msg.seed >>> 0, msg.turns | 0) === 1;
        reply = { ok, mapSeed: ok ? api.mapSeed() >>> 0 : 0, ms: performance.now() - t0 };
        break;
      }
      case "position": reply = { position: JSON.parse(api.position(msg.withMap ? 1 : 0)) }; break;
      case "play": reply = { moves: JSON.parse(api.play(msg.tokens)) }; break;
      case "endTurn": {
        const t0 = performance.now();
        reply = { more: api.endTurn() === 1, ms: performance.now() - t0 };
        break;
      }
      default: reply = { error: `unknown request ${msg.type}` };
    }
  } catch (err) {
    reply = { error: String(err && err.message || err) };
  }
  self.postMessage({ type: "reply", id: msg.id, ...reply });
};
