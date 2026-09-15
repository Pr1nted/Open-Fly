// Files too big for a static host, fetched in parts and put back together.
//
// Cloudflare Pages refuses any single file over 25 MiB, and the two this page
// needs are 91 MB (the connectome) and 22 MB (the game's data). tools/pack_web.py
// gzips each one and cuts it into parts under that limit, with a manifest:
//
//   { "name": "connectome.bin", "size": 91106470, "sha256": "...",
//     "gzip": true, "compressed": 41000000, "parts": ["connectome.bin.part.000", ...] }
//
// Here the parts download in parallel, the stream is gunzipped by the browser's
// own DecompressionStream -- unless the host already did it. A host that sees a
// .gz name may answer with Content-Encoding: gzip, and the browser inflates it
// transparently; the parts are named .part for that reason, and the magic bytes
// are checked anyway, because no promise about a host's headers is worth the
// page failing to load.
// own DecompressionStream, and the result is checked against the manifest
// before anything uses it. To the page it is one fetch with one progress bar.

export async function loadPacked(manifestUrl, onProgress = () => {}) {
  const base = new URL(manifestUrl, self.location.href);
  const res = await fetch(base, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${base.pathname}: ${res.status}`);
  const m = await res.json();
  const total = m.compressed || 0;
  let got = 0;
  const parts = await Promise.all(m.parts.map(async (name) => {
    const r = await fetch(new URL(name, base));
    if (!r.ok) throw new Error(`${name}: ${r.status}`);
    const reader = r.body.getReader();
    const chunks = [];
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      got += value.length;
      // Clamped: if a host inflated the stream, got counts decompressed bytes
      // against a compressed total and the bar would read 194%.
      onProgress(Math.min(got, total) || got, total);
    }
    return new Blob(chunks);
  }));
  const blob = new Blob(parts);
  const head = new Uint8Array(await blob.slice(0, 2).arrayBuffer());
  const stillGzip = head[0] === 0x1f && head[1] === 0x8b;
  let stream = blob.stream();
  if (m.gzip && stillGzip) stream = stream.pipeThrough(new DecompressionStream("gzip"));
  const bytes = await new Response(stream).arrayBuffer();
  if (bytes.byteLength !== m.size) {
    throw new Error(`${m.name}: expected ${m.size} bytes, got ${bytes.byteLength} -- a part is missing or stale`);
  }
  if (m.sha256 && self.crypto && self.crypto.subtle) {
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    const hex = Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join("");
    if (hex !== m.sha256) throw new Error(`${m.name}: checksum does not match the manifest`);
  }
  return bytes;
}
