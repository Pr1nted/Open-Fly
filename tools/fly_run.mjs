// One whole game, headless, with the page's own brain and the page's own game.
//
//   node tools/fly_run.mjs [--map /data/STDmaps/1914.odmap] [--iso SWE] [--seed 20260801]
//                          [--turns 120] [--out run.json]
//
// The release workflow runs this against every new Open Doctrines version and
// puts the result in that version's devlog, so "Open Fly now plays vX" comes
// with what the fly actually did in it. Reads web/agent (unpacked .data) and
// web/data (unpacked connectome.bin), the files tools/pack_web.py cuts up.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { FlyBrain } from "../web/brain.js";
import { Encoder, choose, turnSeed, BRAIN_SEED, WINDOW_MS } from "../web/decide.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.join(here, "..", "web");
const arg = (name, dflt) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : dflt; };
const map = arg("map", "/data/STDmaps/1914.odmap"), iso = arg("iso", "SWE");
const seed = +arg("seed", "20260801"), turns = +arg("turns", "120"), out = arg("out", null);

const { default: createOpenDoctrinesAgent } = await import(path.join(web, "agent", "OpenDoctrinesAgent.mjs"));
const od = await createOpenDoctrinesAgent({ locateFile: (p) => path.join(web, "agent", p), print: () => {}, printErr: () => {} });
const begin = od.cwrap("od_agent_begin", "number", ["string", "number", "number"]);
const position = od.cwrap("od_agent_position", "string", ["number"]);
const play = od.cwrap("od_agent_play", "string", ["string"]);
const endTurn = od.cwrap("od_agent_end_turn", "number", []);

const meta = JSON.parse(readFileSync(path.join(web, "data", "brain.json"), "utf8"));
const c = readFileSync(path.join(web, "data", "connectome.bin"));
const brain = new FlyBrain(c.buffer.slice(c.byteOffset, c.byteOffset + c.byteLength), meta);
const dn = Int32Array.from(meta.dn);

const t0 = Date.now();
if (begin(`${map}:${iso}:rung`, seed, turns) !== 1) { console.error(`could not load ${map}:${iso}`); process.exit(1); }
const enc = new Encoder();
let start = null, last = null, orders = 0, dnTotal = 0, landless = 0, wipedOutTurn = null, wars = 0;
for (;;) {
  const p = JSON.parse(position(0));
  last = p;
  if (start === null) start = p.share;
  if (p.over) break;
  landless = p.mine === 0 ? landless + 1 : 0;
  if (landless >= 2) { wipedOutTurn = p.turn; break; }
  if (p.war.length) wars++;
  const s = turnSeed(BRAIN_SEED, p.iso, p.turn);
  const counts = brain.runWindow(enc.rates(p), WINDOW_MS, s);
  for (const i of dn) dnTotal += counts[i];
  const { tokens } = choose(counts, meta.groups, p, s);
  orders += JSON.parse(play(tokens.join(","))).filter((m) => m.outcome === "did" && !m.token.endsWith(":0")).length;
  if (endTurn() !== 1) { last = JSON.parse(position(0)); break; }
}
// `last.turn` IS the count. This has now been "fixed" twice from reading the
// loop instead of running it, so the evidence lives here.
//
// p.turn is zero-based -- Game.h has `m_turnNumber = 0`, incremented at the END
// of processTurn -- which makes it look one short. It is not, because of where
// each exit sits relative to the work:
//
//   normal end  od_agent_end_turn returns !agentOver(), so the iteration that
//               plays turn N-1 leaves m_turnNumber == N and exits. last.turn is
//               N, and N turns ran.
//   wiped out   the break is BEFORE brain.runWindow, so the turn named by
//               p.turn contributes no spikes and no orders. last.turn is the
//               number of turns that did.
//
// Measured, not argued: with a counter next to runWindow, --turns 5 gives 5 and
// --turns 12 gives 12, and the 1914:SWE wipeout gives 47 iterations to 46 brain
// turns with last.turn == 46. It divides dn_spikes_per_turn below, so an
// off-by-one "correction" here silently restates a published figure.
const played = Math.max(1, last.turn);
const result = {
  open_doctrines: (() => { try { return readFileSync(path.join(web, "agent", "VERSION"), "utf8").trim(); } catch { return "unknown"; } })(),
  seat: `${map}:${iso}`, country: last.name, seed, turns,
  start_share: start, end_share: wipedOutTurn === null ? last.share : 0, wiped_out_turn: wipedOutTurn,
  turns_played: played, turns_at_war: wars, orders, dn_spikes_per_turn: Math.round(dnTotal / played),
  seconds: Math.round((Date.now() - t0) / 1000),
};
console.log(JSON.stringify(result));
if (out) writeFileSync(out, JSON.stringify(result, null, 1));
