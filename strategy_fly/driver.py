"""Plays one benchmark seat through OpenDoctrinesServer --bench-agent."""
import json
import os
import queue
import re
import subprocess
import threading
import time

from . import protocol


def run_seat(binary, data_dir, seat, seed, player, *, label, turns=120,
             log_dir="results", turn_timeout=3600.0, world_seed=None):
    """Run one seat to the end with `player(state) -> list of tokens`.

    OD_WORLD_SEED is pinned: without it the world seed is drawn from entropy
    and every country's political compass is jittered before the agent door
    applies its own seed (Game::chooseWorldSeed, jitterStartingPolitics), so
    two runs of one seed would not be the same world.
    """
    os.makedirs(log_dir, exist_ok=True)
    # A seat can name its map by path ("/maps/x.odmap:SWE"): file-name-safe.
    tag = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{label}__{seat}__{seed}")[-120:]
    fifo = f"/tmp/strategy_fly_{os.getpid()}_{tag}.fifo"
    if os.path.exists(fifo):
        os.unlink(fifo)
    os.mkfifo(fifo)

    env = dict(os.environ)
    env["OD_WORLD_SEED"] = str(world_seed if world_seed is not None else seed)
    cmd = [binary, "--bench-agent", seat, fifo, "--until", str(turns),
           "--seed", str(seed), "--data", data_dir]
    log_path = os.path.join(log_dir, tag + ".log")
    turns_path = os.path.join(log_dir, tag + ".turns.jsonl")
    counts = {"did": 0, "refused": 0, "over_budget": 0, "skipped": 0}

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, env=env)
    lines = queue.Queue()
    log = open(log_path, "w")

    def pump():
        # Drained continuously: a full stdout pipe would block the server mid-turn.
        for ln in proc.stdout:
            log.write(ln)
            lines.put(ln.rstrip("\n"))
        lines.put(None)

    threading.Thread(target=pump, daemon=True).start()
    state = protocol.new_state()
    started = time.time()
    try:
        with open(turns_path, "w") as tl:
            while True:
                try:
                    ln = lines.get(timeout=turn_timeout)
                except queue.Empty:
                    raise TimeoutError(f"{tag}: no output for {turn_timeout}s")
                if ln is None:
                    break
                ev = protocol.parse_line(ln, state)
                if ev in counts:
                    counts[ev] += 1
                if ev == "waiting":
                    t0 = time.time()
                    tokens = list(player(state))
                    think = time.time() - t0
                    protocol.send_line(fifo, ", ".join(tokens), proc)
                    rec = {k: state[k] for k in ("turn", "share", "army", "treasury", "gross", "net", "war", "budget")}
                    rec.update(tokens=tokens, think_s=round(think, 3),
                               info=getattr(player, "last_info", None))
                    tl.write(json.dumps(rec) + "\n")
                    tl.flush()
        proc.wait(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
        log.close()
        if os.path.exists(fifo):
            os.unlink(fifo)
    return {"label": label, "seat": seat, "seed": seed, "turns": turns,
            "score": state["bench_score"], "returncode": proc.returncode,
            "counts": counts, "wall_s": round(time.time() - started, 1),
            "log": log_path, "turns_log": turns_path}
