"""The --bench-agent pipe protocol spoken by OpenDoctrinesServer.

Server side: Game::runBenchAgent in src/Game_AITrain.cpp of Open Doctrines.
Every turn the server prints the position, the legal actions of four menus and
the per-module budget, then `[AGENT] waiting`. It then opens the FIFO and reads
ONE line of comma-separated `module:action` tokens, or `quit`. An empty line is
a turn in which the player does nothing.
"""
import errno
import os
import re
import time

MODULES = "epwn"
MENU_LETTER = {"economy": "e", "politics": "p", "war": "w", "navy": "n"}
DEFAULT_BUDGET = {"e": 8, "p": 3, "w": 8, "n": 8}

_TURN = re.compile(r"^\[AGENT\] ===== turn (\d+)/(\d+)\s+(.*) \(([A-Z0-9]+)\) =====")
_LAND = re.compile(r"^\[AGENT\] land (\d+)/(\d+) \(([\d.]+)% of the world\)\s+army (-?\d+)\s+treasury (-?[\d.]+)")
_INCOME = re.compile(r"^\[AGENT\] gross (-?[\d.]+) net (-?[\d.]+)")
_WARS = re.compile(r"^\[AGENT\] at war with: (.*)$")
_MENU = re.compile(r"^\[AGENT\] (economy|politics|war|navy)\s+(.*)$")
_ACTION = re.compile(r"([epwn]):(\d+) (.+?)(?=\s{2}[epwn]:\d|\s*$)")
_BUDGET = re.compile(r"^\[AGENT\] budget e:(\d+) p:(\d+) w:(\d+) n:(\d+)")
_BENCH = re.compile(r"^\[BENCH\] seat (\S+)\s+score (-?[\d.]+)")


def new_state():
    return {"turn": 0, "turns": 0, "country": "", "iso": "", "share": 0.0,
            "mine": 0, "owned": 0, "army": 0, "treasury": 0.0,
            "gross": 0.0, "net": 0.0, "war": [],
            "legal": {m: [] for m in MODULES}, "budget": dict(DEFAULT_BUDGET),
            "bench_score": None}


def parse_line(line, state):
    """Update `state` from one server line. Returns an event name or None."""
    m = _TURN.match(line)
    if m:
        state.update(turn=int(m[1]), turns=int(m[2]), country=m[3], iso=m[4],
                     legal={k: [] for k in MODULES}, war=[])
        return "turn"
    m = _LAND.match(line)
    if m:
        state.update(mine=int(m[1]), owned=int(m[2]), share=float(m[3]),
                     army=int(m[4]), treasury=float(m[5]))
        return None
    m = _INCOME.match(line)
    if m:
        state.update(gross=float(m[1]), net=float(m[2]))
        return None
    m = _WARS.match(line)
    if m:
        rest = m[1].strip()
        state["war"] = [] if rest == "(nobody)" else rest.split()
        return None
    m = _MENU.match(line)
    if m:
        state["legal"][MENU_LETTER[m[1]]] = [(int(a), n.strip()) for _, a, n in _ACTION.findall(m[2])]
        return None
    m = _BUDGET.match(line)
    if m:
        state["budget"] = dict(zip(MODULES, (int(m[1]), int(m[2]), int(m[3]), int(m[4]))))
        return None
    m = _BENCH.match(line)
    if m:
        state["bench_score"] = float(m[2])
        return "bench"
    if line == "[AGENT] waiting":
        return "waiting"
    if line.startswith("[AGENT] did "):
        return "did"
    if line.startswith("[AGENT] REFUSED"):
        return "refused"
    if line.startswith("[AGENT] OVER BUDGET"):
        return "over_budget"
    if line.startswith("[AGENT] SKIPPED"):
        return "skipped"
    if line.startswith("[AGENT] stopped early"):
        return "stopped"
    return None


def send_line(fifo, line, proc, timeout=60.0):
    """Write one line to the FIFO without ever hanging on a dead server.

    The server prints `waiting` BEFORE it opens the FIFO for reading, so the
    first attempt can find no reader (ENXIO). Retry until it appears, and give
    up if the process has exited.
    """
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
            break
        except OSError as e:
            if e.errno != errno.ENXIO:
                raise
            if proc.poll() is not None:
                raise RuntimeError("server exited before reading the turn's choices")
            if time.time() > deadline:
                raise TimeoutError("server never opened the FIFO for reading")
            time.sleep(0.01)
    try:
        os.write(fd, (line + "\n").encode())
    finally:
        os.close(fd)
