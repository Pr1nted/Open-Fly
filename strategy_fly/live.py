"""Strategy Fly Live: the fly plays new games for as long as this runs.

    .venv/bin/python -m strategy_fly.live \
        --binary <OpenDoctrinesServer built with the agent-door patch> \
        --game-data <Open Doctrines data/ folder> \
        --fly-data <folder with Completeness_783.csv, Connectivity_783.parquet, neuron_annotations.tsv> \
        --scene <scene.gltf> [--port 8766]

Then open http://localhost:8766.

Each game is a random 1914 seat with a fresh seed, played through the same agent
door and per-module budget as the benchmark, one brain window per turn. The
browser gets every turn as it is decided: the orders, the spikes of every neuron
that fired, and who owns every province. A game's save and logs are deleted when
it ends, and games run in a private copy of data/ whose saves/ is its own, so
nothing accumulates in the game's folders.
"""
import argparse
import base64
import io
import json
import os
import queue
import random
import re
import shutil
import tempfile
import threading
import time
import traceback
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np

from . import decode
from .brain import FlyBrain
from .driver import run_seat
from .encode import Encoder
from .players import FlyPlayer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "live_web")
MAP_W, MAP_H = 1600, 800
PARTITION_SEED, BRAIN_SEED, WINDOW_MS = 783, 20240922, 200.0   # as in PREREGISTRATION.md
MODULE_TITLE = {"e": "Economy", "p": "Politics", "w": "War", "n": "Navy"}


class Hub:
    """What the browser can ask for: the current game, its turns so far, past games."""

    def __init__(self):
        self.lock = threading.Lock()
        self.seq = 0
        self.status = "Building the brain"
        self.game = None
        self.events = []
        self.results = []
        self.maps = {}
        self.subscribers = []

    def publish(self, kind, payload):
        with self.lock:
            self.seq += 1
            ev = {"seq": self.seq, "kind": kind, **payload}
            if kind == "game_start":
                self.game = ev
                self.events = []
            elif kind in ("turn", "game_over"):
                self.events.append(ev)
            if kind == "status":
                self.status = payload["text"]
            data = json.dumps(ev, separators=(",", ":"))
            for q in list(self.subscribers):
                try:
                    q.put_nowait((self.seq, data))
                except queue.Full:
                    pass
        return ev

    def snapshot(self):
        with self.lock:
            return {"seq": self.seq, "status": self.status, "game": self.game,
                    "events": list(self.events), "results": list(self.results[-30:])}


class WorldMap:
    """The 1914 map's own province raster, cropped around each game's seat."""

    def __init__(self, odmap_path):
        from PIL import Image
        z = zipfile.ZipFile(odmap_path)
        img = np.asarray(Image.open(io.BytesIO(z.read("provinces.png"))).convert("RGB"))
        ids = (img[..., 0].astype(np.int32) << 16) | (img[..., 1].astype(np.int32) << 8) | img[..., 2]
        self.provinces = json.loads(z.read("provinces.json"))
        self.countries = json.loads(z.read("countries.json"))
        max_pid = max(int(k) for k in self.provinces)
        ids[ids > max_pid] = 0
        self.ids = ids.astype(np.uint16)
        self.H, self.W = self.ids.shape
        self.max_pid = max_pid

    def whole(self, w=2048, h=1024):
        """The entire world at wall-map size, for the map on the room's back wall."""
        xs = np.minimum(((np.arange(w) + 0.5) * self.W / w).astype(int), self.W - 1)
        ys = np.minimum(((np.arange(h) + 0.5) * self.H / h).astype(int), self.H - 1)
        return self.ids[np.ix_(ys, xs)].astype("<u2").tobytes()

    def seats(self, min_provinces):
        count = {}
        for p in self.provinces.values():
            count[p["country_id"]] = count.get(p["country_id"], 0) + 1
        out = []
        for c in self.countries.values():
            if c["id"] < 60000 and count.get(c["id"], 0) >= min_provinces:
                out.append(c["iso_a3"])
        return sorted(out)

    def country(self, iso):
        return next(c for c in self.countries.values() if c["iso_a3"] == iso)

    def crop(self, cid):
        pids = np.array(sorted(int(k) for k, p in self.provinces.items() if p["country_id"] == cid), np.uint16)
        mask = np.isin(self.ids, pids)
        rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
        if len(rows) == 0:
            cx, cy, w = self.W / 2, self.H / 2, float(self.W)
        else:
            cx, cy = (cols[0] + cols[-1]) / 2, (rows[0] + rows[-1]) / 2
            w = max((cols[-1] - cols[0]) * 1.9, (rows[-1] - rows[0]) * 1.9 * 2, self.W * 0.14)
        w = min(w, float(self.W), self.H * 2.0)
        h = w / 2
        x0 = min(max(cx - w / 2, 0), self.W - w)
        y0 = min(max(cy - h / 2, 0), self.H - h)
        xs = np.minimum((x0 + (np.arange(MAP_W) + 0.5) * w / MAP_W).astype(int), self.W - 1)
        ys = np.minimum((y0 + (np.arange(MAP_H) + 0.5) * h / MAP_H).astype(int), self.H - 1)
        return self.ids[np.ix_(ys, xs)].astype("<u2").tobytes()


def brain_bin(brain, groups, tsv):
    """Neuron positions and kinds in the viewer's SFB1 layout, with no turns."""
    import pandas as pd
    import struct
    ann = pd.read_csv(tsv, sep="\t", usecols=["root_id", "pos_x", "pos_y", "pos_z", "super_class"],
                      dtype={"root_id": str}, low_memory=False).drop_duplicates("root_id").set_index("root_id")
    m = ann.reindex(brain.flyids)
    pos = m[["pos_x", "pos_y", "pos_z"]].to_numpy(dtype=np.float64)
    sc = m["super_class"].fillna("").to_numpy().astype(str)
    missing = np.isnan(pos).any(axis=1)
    nm = pos * np.array([4.0, 4.0, 40.0])            # FlyWire voxels are 4 x 4 x 40 nm
    lo, hi = np.nanmin(nm, 0), np.nanmax(nm, 0)
    c, s = (lo + hi) / 2, 0.9 / (hi[0] - lo[0])
    xyz = np.stack([(nm[:, 0] - c[0]) * s, -(nm[:, 1] - c[1]) * s, (nm[:, 2] - c[2]) * s], 1)
    xyz[missing] = 0
    kind = np.full(len(pos), 2, np.uint8)
    kind[np.isin(sc, ["optic", "visual_projection", "visual_centrifugal"])] = 1
    kind[np.isin(sc, ["sensory", "sensory_ascending"])] = 3
    kind[np.isin(sc, ["ascending"])] = 5
    kind[np.unique(np.concatenate([g for mod in decode.MODULES for g in groups[mod]]))] = 4
    kind[missing] = 255
    out = bytearray(b"SFB1" + struct.pack("<III", 1, len(pos), 0))
    out += xyz.astype("<f4").tobytes() + kind.tobytes()
    out += b"\0" * ((-len(out)) % 4)
    return bytes(out)


def private_data_dir(game_data):
    """data/ with every entry linked except saves/, which is this program's own."""
    root = os.path.join(tempfile.gettempdir(), "strategy_fly_live_data")
    saves = os.path.join(root, "saves")
    shutil.rmtree(saves, ignore_errors=True)
    os.makedirs(saves, exist_ok=True)
    src = os.path.abspath(game_data)
    for name in os.listdir(src):
        if name == "saves":
            continue
        link = os.path.join(root, name)
        if not os.path.lexists(link):
            os.symlink(os.path.join(src, name), link)
    return root + os.sep


class LiveFly:
    """The fly, plus a broadcast of everything it saw and did this turn."""

    def __init__(self, fly, brain, hub, game_id, pace):
        self.fly, self.brain, self.hub, self.game_id, self.pace = fly, brain, hub, game_id, pace
        self.last_info = None
        self.first_share = None
        self.landless = 0
        self.eliminated_turn = None

    def __call__(self, state):
        # A country with no land left has nothing to play. Two turns without a
        # province (so a one-turn gap before a counter-attack does not end it)
        # and the game stops; the next one starts instead of 90 empty turns.
        self.landless = self.landless + 1 if state["mine"] == 0 else 0
        if self.landless >= 2:
            self.eliminated_turn = state["turn"]
            return ["quit"]
        t0 = time.time()
        tokens = self.fly(state)
        self.last_info = self.fly.last_info
        counts = self.brain.last_counts
        nz = np.nonzero(counts)[0]
        spikes = nz.astype("<u4").tobytes() + np.minimum(np.asarray(counts)[nz], 255).astype(np.uint8).tobytes()
        names = {mod: dict(state["legal"][mod]) for mod in "epwn"}
        orders = []
        for tok in tokens:
            mod, _, a = tok.partition(":")
            if a == "0":
                continue
            orders.append([MODULE_TITLE[mod], names[mod].get(int(a), a)])
        think = time.time() - t0
        if self.first_share is None:
            self.first_share = state["share"]
        wait = self.pace - think
        if wait > 0:
            time.sleep(wait)
        info = self.fly.last_info or {}
        self.hub.publish("turn", {
            "game": self.game_id, "turn": state["turn"], "turns": state["turns"],
            "share": state["share"], "army": state["army"], "treasury": round(state["treasury"]),
            "war": state["war"], "orders": orders, "tokens": tokens,
            "dn": info.get("dn_spikes", 0), "active": info.get("active_neurons", 0),
            "rates": {k: round(v, 1) for k, v in (info.get("rates") or {}).items()},
            "think": round(think, 2), "spikes": base64.b64encode(spikes).decode(), "fired": int(len(nz)),
            "owners": state.get("owners"),
            "colors": {str(k): v["hex"] for k, v in (state.get("colors") or {}).items()},
        })
        return tokens


def game_loop(args, hub, brain, groups, world, data_dir):
    rng = random.Random()
    seats = [s for s in (args.seats.split(",") if args.seats else world.seats(args.min_provinces))]
    logs = tempfile.mkdtemp(prefix="strategy_fly_live_logs_")
    game_id, last = 0, None
    while True:
        game_id += 1
        iso = rng.choice([s for s in seats if s != last] or seats)
        last = iso
        seed = rng.randrange(1, 2**31 - 1)
        country = world.country(iso)
        hub.maps[game_id] = world.crop(country["id"])
        for old in [k for k in hub.maps if k < game_id - 2]:
            del hub.maps[old]
        hub.publish("game_start", {"game": game_id, "iso": iso, "name": country["name"],
                                   "cid": country["id"], "seed": seed, "turns": args.turns,
                                   "map": {"url": f"/map/{game_id}", "w": MAP_W, "h": MAP_H}})
        hub.publish("status", {"text": f"Game {game_id}: {country['name']}"})
        fly = FlyPlayer(brain, groups, Encoder(), window_ms=WINDOW_MS, seed=BRAIN_SEED)
        player = LiveFly(fly, brain, hub, game_id, args.min_turn_seconds)
        result = {"game": game_id, "iso": iso, "name": country["name"], "seed": seed}
        try:
            r = run_seat(args.binary, data_dir, f"1914:{iso}:rung", seed, player,
                         label=f"live{game_id}", turns=args.turns, log_dir=logs, turn_timeout=900)
            if player.eliminated_turn is not None:
                result.update(ok=True, start=player.first_share, end=0.0, orders=r["counts"]["did"],
                              eliminated_turn=player.eliminated_turn)
            else:
                result.update(ok=r["returncode"] == 0 and r["score"] is not None,
                              start=player.first_share, end=r["score"], orders=r["counts"]["did"])
            log_path = r["log"]
        except Exception as e:
            traceback.print_exc()
            result.update(ok=False, start=player.first_share, end=None, error=str(e))
            log_path = None
        with hub.lock:
            hub.results.append(result)
        hub.publish("game_over", {**result, "next_in": args.intermission})
        # This game's save and logs go now; nothing is kept between games.
        if log_path and os.path.exists(log_path):
            with open(log_path, errors="replace") as f:
                for line in f:
                    m = re.search(r"Auto-created save: (.+\.odsv)", line)
                    if m and os.path.exists(m[1].strip()):
                        os.remove(m[1].strip())
        for name in os.listdir(logs):
            os.remove(os.path.join(logs, name))
        for name in os.listdir(os.path.join(data_dir, "saves")):
            os.remove(os.path.join(data_dir, "saves", name))
        time.sleep(args.intermission)


def make_handler(hub, assets):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send_bytes(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            path = url.path
            try:
                if path in ("/", "/index.html"):
                    with open(os.path.join(WEB, "index.html"), "rb") as f:
                        return self.send_bytes(f.read(), "text/html; charset=utf-8")
                if path == "/scene.gltf":
                    with open(assets["scene"], "rb") as f:
                        return self.send_bytes(f.read(), "application/json")
                if path == "/brain.bin":
                    if assets.get("brain") is None:
                        self.send_error(503, "the brain is still being built")
                        return
                    return self.send_bytes(assets["brain"], "application/octet-stream")
                if path == "/world.bin":
                    if assets.get("world") is None:
                        self.send_error(503, "the map is still being read")
                        return
                    return self.send_bytes(assets["world"], "application/octet-stream")
                if path == "/state":
                    return self.send_bytes(json.dumps(hub.snapshot()).encode(), "application/json")
                if path.startswith("/map/"):
                    body = hub.maps.get(int(path.rsplit("/", 1)[1]))
                    if body is None:
                        self.send_error(404, "that game's map is gone")
                        return
                    return self.send_bytes(body, "application/octet-stream")
                if path == "/events":
                    return self.stream(int(parse_qs(url.query).get("since", ["0"])[0]))
                self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def stream(self, since):
            q = queue.Queue(maxsize=2000)
            with hub.lock:
                hub.subscribers.append(q)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                snap = hub.snapshot()
                backlog = []
                if snap["game"] and snap["game"]["seq"] > since:
                    backlog.append(snap["game"])
                backlog += [e for e in snap["events"] if e["seq"] > since]
                sent = since
                self.wfile.write(b"retry: 2000\n\n")
                for ev in backlog:
                    self.wfile.write(f"data: {json.dumps(ev, separators=(',', ':'))}\n\n".encode())
                    sent = ev["seq"]
                self.wfile.flush()
                while True:
                    try:
                        seq, data = q.get(timeout=15)
                    except queue.Empty:
                        self.wfile.write(b": still here\n\n")
                        self.wfile.flush()
                        continue
                    if seq <= sent:
                        continue
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                    sent = seq
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with hub.lock:
                    if q in hub.subscribers:
                        hub.subscribers.remove(q)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--binary", required=True)
    ap.add_argument("--game-data", required=True)
    ap.add_argument("--fly-data", required=True)
    ap.add_argument("--scene", required=True)
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--turns", type=int, default=120)
    ap.add_argument("--min-turn-seconds", type=float, default=1.2,
                    help="slow a turn down to at least this, so a person can follow it")
    ap.add_argument("--intermission", type=float, default=10.0)
    ap.add_argument("--seats", default=None, help="comma-separated ISO codes; default every 1914 country")
    ap.add_argument("--min-provinces", type=int, default=12,
                    help="only seat countries that start with at least this many provinces")
    args = ap.parse_args()
    os.environ["OD_AGENT_OWNERS"] = "1"

    hub = Hub()
    assets = {"scene": os.path.abspath(args.scene), "brain": None}
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(hub, assets))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Strategy Fly Live: http://localhost:{args.port}", flush=True)

    fd = args.fly_data
    brain = FlyBrain(os.path.join(fd, "Completeness_783.csv"), os.path.join(fd, "Connectivity_783.parquet"))
    ids = json.load(open(os.path.join(HERE, "sensory_ids.json")))
    for ch in ("sugar", "bitter", "water", "jon"):
        brain.add_channel(ch, ids[ch])
    units = decode.descending_units(os.path.join(fd, "neuron_annotations.tsv"), brain.index)
    groups = decode.make_groups(units, PARTITION_SEED)
    run_window = brain.run_window

    def recording(*a, **k):
        counts = run_window(*a, **k)
        brain.last_counts = counts
        return counts

    brain.run_window = recording
    brain.last_counts = np.zeros(brain.n)
    print(f"brain built: {brain.n} neurons in {brain.build_seconds:.0f} s", flush=True)
    hub.publish("status", {"text": "Placing the neurons"})
    assets["brain"] = brain_bin(brain, groups, os.path.join(fd, "neuron_annotations.tsv"))
    hub.publish("status", {"text": "Reading the 1914 map"})
    world = WorldMap(os.path.join(args.game_data, "STDmaps", "1914.odmap"))
    assets["world"] = world.whole()
    data_dir = private_data_dir(args.game_data)
    print("playing", flush=True)
    game_loop(args, hub, brain, groups, world, data_dir)


if __name__ == "__main__":
    main()
