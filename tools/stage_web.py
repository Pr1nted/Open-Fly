"""Copy what the site serves into a deploy folder, and nothing Pages would refuse.

    python3 tools/stage_web.py --out dist

Everything under web/ except: the originals that a *.pack.json manifest stands
in for (the page only ever fetches their parts), notes, and anything that would
still break the 25 MiB limit -- which fails the stage rather than the deploy, so
the error names the file instead of arriving as an upload failure.
"""
import argparse
import glob
import json
import os
import shutil
import sys

LIMIT = 25 * 1024 * 1024
SKIP_NAMES = {"README.md", ".DS_Store"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default=os.path.join(os.path.dirname(__file__), "..", "web"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    web = os.path.abspath(args.web)
    out = os.path.abspath(args.out)

    packed = set()
    for manifest in glob.glob(os.path.join(web, "**", "*.pack.json"), recursive=True):
        m = json.load(open(manifest))
        packed.add(os.path.join(os.path.dirname(manifest), m["name"]))
        for part in m["parts"]:
            if not os.path.exists(os.path.join(os.path.dirname(manifest), part)):
                sys.exit(f"{manifest} names {part}, which is not there -- run tools/pack_web.py again")

    shutil.rmtree(out, ignore_errors=True)
    too_big, copied, total = [], 0, 0
    for root, _, files in os.walk(web):
        for name in files:
            src = os.path.join(root, name)
            if name in SKIP_NAMES or src in packed:
                continue
            size = os.path.getsize(src)
            if size >= LIMIT:
                too_big.append((src, size))
                continue
            dst = os.path.join(out, os.path.relpath(src, web))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
            total += size
    if too_big:
        for src, size in too_big:
            print(f"too big for Pages: {os.path.relpath(src, web)} ({size / 1e6:.1f} MB) -- pack it", file=sys.stderr)
        sys.exit(1)
    print(f"staged {copied} files, {total / 1e6:.1f} MB, into {out}")


if __name__ == "__main__":
    main()
