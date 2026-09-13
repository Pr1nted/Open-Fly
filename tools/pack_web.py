"""Cut files too big for Cloudflare Pages into gzip parts the page reassembles.

    python3 tools/pack_web.py web/data/connectome.bin web/agent/OpenDoctrinesAgent.data

For each file F this writes F.gz.000, F.gz.001, ... (each under --part-mib,
default 20 MiB against Pages' 25 MiB limit) and F's manifest, named
<stem>.pack.json beside it, which web/packed.js reads. The original stays on disk
for local tools; tools/stage_web.py leaves it out of what gets deployed.

Deterministic: gzip without a timestamp, so rebuilding the same input gives
byte-identical parts and a deploy uploads nothing that did not change.
"""
import argparse
import gzip
import hashlib
import json
import os
import sys


def pack(path, part_bytes):
    raw = open(path, "rb").read()
    blob = gzip.compress(raw, compresslevel=9, mtime=0)
    folder, name = os.path.split(path)
    stem = name.rsplit(".", 1)[0]
    for old in os.listdir(folder or "."):
        if old.startswith(name + ".gz."):
            os.remove(os.path.join(folder, old))
    parts = []
    for k, at in enumerate(range(0, len(blob), part_bytes)):
        part = f"{name}.gz.{k:03d}"
        with open(os.path.join(folder, part), "wb") as f:
            f.write(blob[at:at + part_bytes])
        parts.append(part)
    manifest = {"name": name, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "gzip": True, "compressed": len(blob), "parts": parts}
    with open(os.path.join(folder, f"{stem}.pack.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"{name}: {len(raw) / 1e6:.1f} MB -> {len(blob) / 1e6:.1f} MB gzip in {len(parts)} part(s)")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--part-mib", type=float, default=20.0)
    args = ap.parse_args()
    part_bytes = int(args.part_mib * 1024 * 1024)
    if part_bytes >= 25 * 1024 * 1024:
        sys.exit("--part-mib must stay under Cloudflare Pages' 25 MiB file limit")
    for f in args.files:
        pack(f, part_bytes)


if __name__ == "__main__":
    main()
