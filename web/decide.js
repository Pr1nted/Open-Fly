// The fly's side of a turn, in the browser: game state -> sensory rates, and
// descending-neuron spikes -> orders. Ports of strategy_fly/encode.py,
// decode.choose and players.turn_seed, unchanged in what they compute.

export const MODULES = ["e", "p", "w", "n"];
const REFS = { land_pp: 0.5, reserve_turns: 12.0, wars: 3.0 };
const MAX_HZ = 200.0, FLOOR_HZ = 10.0;
export const BRAIN_SEED = 20240922;
export const WINDOW_MS = 200.0;

export class Encoder {
  constructor() { this.prev = null; }
  signals(s) {
    const share = +s.share || 0, gross = +s.gross || 0, net = +s.net || 0, treasury = +s.treasury || 0;
    const wars = s.war || [];
    let dLand = 0, newWars = 0;
    if (this.prev) {
      dLand = share - this.prev.share;
      const before = new Set(this.prev.war);
      newWars = new Set(wars.filter((w) => !before.has(w))).size;
    }
    const ratio = gross > 1e-9 ? net / gross : 0;
    const sig = {
      sugar: Math.max(0, dLand) / REFS.land_pp + Math.max(0, ratio),
      bitter: Math.max(0, -dLand) / REFS.land_pp + Math.max(0, -ratio) + 0.5 * newWars,
      water: gross > 1e-9 ? treasury / (REFS.reserve_turns * gross) : 0,
      jon: wars.length / REFS.wars,
    };
    this.prev = { share, war: [...wars] };
    return sig;
  }
  rates(s) {
    const out = {};
    for (const [k, v] of Object.entries(this.signals(s))) {
      const r = MAX_HZ * Math.min(1, Math.max(0, v));
      out[k] = r >= FLOOR_HZ ? r : 0;
    }
    return out;
  }
}

// zlib.crc32, so a turn's seed is the number the Python fly would use.
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
  return t;
})();
export function crc32(str) {
  const bytes = new TextEncoder().encode(str);
  let c = 0xffffffff;
  for (const b of bytes) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
export const turnSeed = (base, iso, turn) => crc32(`${base}|${iso}|${turn}`) & 0x7fffffff;

function seededRandom(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// Up to the module's budget of the most active legal actions, per menu. Score =
// mean spikes per neuron in the action's group; silent actions are not taken; a
// silent menu holds (action 0); nothing after a 0 is sent. Ties go to a
// per-turn seeded draw.
export function choose(counts, groups, position, seed) {
  const rand = seededRandom(seed);
  const tokens = [], picksByModule = {};
  for (const m of MODULES) {
    const legal = (position.legal[m] || []).map((x) => x.a);
    if (!legal.length) continue;
    const budget = position.budget[m] | 0;
    const score = new Map();
    for (const a of legal) {
      const g = groups[m][a];
      let s = 0;
      for (const i of g) s += counts[i];
      score.set(a, s / g.length);
    }
    const tie = new Map(legal.map((a) => [a, rand()]));
    const order = [...legal].sort((x, y) => (score.get(y) - score.get(x)) || (tie.get(x) - tie.get(y)));
    let picks = order.filter((a) => score.get(a) > 0).slice(0, budget);
    if (!picks.length) picks = legal.includes(0) ? [0] : [];
    const zero = picks.indexOf(0);
    if (zero >= 0) picks = picks.slice(0, zero + 1);
    picksByModule[m] = picks;
    for (const a of picks) tokens.push(`${m}:${a}`);
  }
  return { tokens, picks: picksByModule };
}
