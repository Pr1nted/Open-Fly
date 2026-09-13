#!/usr/bin/env bash
# Build the Open Doctrines game module the browser fly plays through.
#
#   tools/build_web_agent.sh [path/to/Open-Doctrines] [git ref]
#
# The module is Open Doctrines' own OpenDoctrinesAgent target (src/web/AgentWeb.cpp
# over the agent session in src/Game_Agent.cpp), so a new version of the game is
# a new build of this, nothing else: pass the tag or commit to build from and
# web/agent/ is replaced, with the ref it came from in web/agent/VERSION.
# Needs Emscripten (emcmake) on PATH.
set -euo pipefail

OD="${1:-$(cd "$(dirname "$0")/../.." && pwd)/OpenDoctrines}"
REF="${2:-}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -n "$REF" ]; then
  git -C "$OD" worktree add --detach "$WORK/od" "$REF" >/dev/null
  SRC="$WORK/od"
  trap 'git -C "$OD" worktree remove --force "$WORK/od" >/dev/null 2>&1 || true; rm -rf "$WORK"' EXIT
else
  SRC="$OD"
fi

emcmake cmake -S "$SRC" -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$WORK/build" --target OpenDoctrinesAgent -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"

mkdir -p "$HERE/web/agent"
cp "$WORK/build/OpenDoctrinesAgent.mjs" "$WORK/build/OpenDoctrinesAgent.wasm" "$WORK/build/OpenDoctrinesAgent.data" "$HERE/web/agent/"
git -C "$SRC" describe --tags --always > "$HERE/web/agent/VERSION"
echo "web/agent: OpenDoctrinesAgent from $(cat "$HERE/web/agent/VERSION")"
