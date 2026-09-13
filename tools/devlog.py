"""The devlog for one Open Doctrines version: written once, published four ways.

    python3 tools/devlog.py --tag v1.2.1a --run release/run.json

  devlogs/<date>-<tag>.md    the entry, kept in the repository
  web/devlog/index.html      every entry, newest first, on the Open Fly site
  web/devlog/feed.xml        the same as RSS, for anything that follows feeds
  release/itch-devlog.md     the text to paste into itch.io (it has no devlog API)
  release/discord.json       the webhook message the release workflow posts
  release/history.json       every version's run, so the next entry can compare

The entry says the thing a follower needs -- Open Fly now plays this version of
Open Doctrines -- and what the fly did in it, measured the same way every time:
1914 Sweden, seed 20260801, 120 turns (tools/fly_run.mjs). The game's own
release notes are linked, not rewritten.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLAY_URL = "https://open-fly.pages.dev/"
ITCH_URL = "https://pr1nted.itch.io/open-fly"
OD_REPO = "Pr1nted/Open-Doctrines"


def od_release(tag):
    url = f"https://api.github.com/repos/{OD_REPO}/releases/tags/{tag}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.load(r)
        return j.get("html_url") or f"https://github.com/{OD_REPO}/releases/tag/{tag}"
    except Exception:
        return f"https://github.com/{OD_REPO}/releases/tag/{tag}"


def describe(run):
    who = run.get("country", "the fly's country")
    if run.get("wiped_out_turn") is not None:
        how = (f"started with {run['start_share']:.2f}% of the world and was wiped out on turn "
               f"{run['wiped_out_turn'] + 1}, after {run['turns_at_war']} turns at war")
    else:
        how = (f"went from {run['start_share']:.2f}% to {run['end_share']:.2f}% of the world in "
               f"{run['turns_played']} turns, {run['turns_at_war']} of them at war")
    return (f"As {who} in 1914 (seed {run['seed']}), the fly {how}. It gave {run['orders']} orders, "
            f"from an average of {run['dn_spikes_per_turn']} descending-neuron spikes a turn.")


def compare(run, previous):
    if not previous:
        return "This is the first version the fly has played, so there is nothing to compare it with yet."
    was, tag = previous["run"], previous["tag"]
    if run.get("wiped_out_turn") is not None or was.get("wiped_out_turn") is not None:
        def lasted(r):
            return f"was wiped out on turn {r['wiped_out_turn'] + 1}" if r.get("wiped_out_turn") is not None \
                else f"survived all {r['turns_played']} turns with {r['end_share']:.2f}%"
        text = f"Under {tag} it {lasted(was)}."
    else:
        before, now = was["end_share"], run["end_share"]
        if abs(now - before) < 0.005:
            text = f"That is the same share it ended with under {tag}."
        else:
            text = f"Under {tag} it ended with {before:.2f}%."
    return f"{text} One seat and one seed: a change in the game, not a verdict on it."


def render_markdown(entry):
    return (f"---\ntitle: {entry['title']}\ndate: {entry['date']}\ntag: {entry['tag']}\n---\n\n"
            f"{entry['lead']}\n\n## What the fly did\n\n{entry['did']}\n\n{entry['compare']}\n\n"
            f"## Links\n\n- Watch it play: {PLAY_URL}\n- Open Fly on itch.io: {ITCH_URL}\n"
            f"- What changed in Open Doctrines {entry['tag']}: {entry['od_url']}\n")


def parse_markdown(text):
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta = dict(line.split(": ", 1) for line in m[1].splitlines()) if m else {}
    return meta, (m[2] if m else text)


def body_html(md):
    out, in_list = [], False
    for line in md.strip().splitlines():
        line = html.escape(line)
        line = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', line)
        if line.startswith("## "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h3>{line[3:]}</h3>")
        elif line.startswith("- "):
            if not in_list: out.append("<ul>"); in_list = True
            out.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<p>{line}</p>")
    if in_list: out.append("</ul>")
    return "\n".join(out)


def site(entries):
    items = "\n".join(
        f'<article id="{html.escape(e["tag"])}"><header><span class="prompt">$ cat devlog/{html.escape(e["date"])}-{html.escape(e["tag"])}.md</span>'
        f'<h2>{html.escape(e["title"])}</h2><time datetime="{e["date"]}">{e["date"]}</time></header>{body_html(e["body"])}</article>'
        for e in entries)
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Open Fly devlog</title>
<link rel="icon" href="../favicon.ico" sizes="16x16 32x32 48x48">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="alternate" type="application/rss+xml" title="Open Fly devlog" href="feed.xml">
<style>
  :root {{ --void:#030806; --panel:#06120d; --line:#1a4d33; --dim:#2e8f5c; --green:#4dff9b; --gold:#ffd700; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--void); color:#b8f5d2; font:15px/1.7 "JetBrains Mono", ui-monospace, Menlo, monospace; }}
  body::before {{ content:""; position:fixed; inset:0; pointer-events:none; background:repeating-linear-gradient(#0000 0 2px,#0006 2px 4px); }}
  main {{ max-width: 760px; margin: 0 auto; padding: 32px 20px 80px; }}
  .bar {{ background:var(--green); color:var(--void); padding:8px 12px; font-weight:700; letter-spacing:.08em; }}
  h1 {{ font-size: 26px; margin: 28px 0 4px; color: var(--gold); }}
  h1 span {{ color: var(--green); }}
  .sub {{ color: var(--dim); margin: 0 0 32px; }}
  article {{ border:1px solid var(--line); background:var(--panel); padding:18px 20px; margin:0 0 20px; }}
  .prompt {{ color: var(--dim); font-size: 12px; }}
  h2 {{ color: var(--green); font-size: 18px; margin: 6px 0 2px; }}
  h3 {{ color: var(--gold); font-size: 13px; letter-spacing: .12em; text-transform: uppercase; margin: 18px 0 4px; }}
  time {{ color: var(--dim); font-size: 12px; }}
  a {{ color: var(--green); }}
  a:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
</style>
<main>
  <div class="bar">&#9608; OPEN-FLY // DEVLOG</div>
  <h1>Open <span>Fly</span> devlog</h1>
  <p class="sub">Every time Open Doctrines releases, the fly plays the new version and writes here. <a href="../">Watch it play</a> &middot; <a href="feed.xml">RSS</a></p>
  {items or "<p>No entries yet.</p>"}
</main>
"""


def feed(entries):
    items = "".join(
        f"<item><title>{html.escape(e['title'])}</title><link>{PLAY_URL}devlog/#{html.escape(e['tag'])}</link>"
        f"<guid>{PLAY_URL}devlog/#{html.escape(e['tag'])}</guid>"
        f"<pubDate>{dt.datetime.strptime(e['date'], '%Y-%m-%d').strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>"
        f"<description>{html.escape(e['lead'])}</description></item>"
        for e in entries)
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Open Fly devlog</title>'
            f"<link>{PLAY_URL}devlog/</link><description>A fruit fly brain plays each new Open Doctrines release.</description>{items}</channel></rss>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    run = json.load(open(args.run))

    hist_path = os.path.join(ROOT, "release", "history.json")
    history = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    previous = next((h for h in reversed(history) if h["tag"] != args.tag), None)

    od_url = od_release(args.tag)
    entry = {
        "tag": args.tag, "date": args.date,
        "title": f"Open Fly now plays Open Doctrines {args.tag}",
        "lead": (f"Open Doctrines {args.tag} is out, and the simulated fruit fly brain -- the FlyWire "
                 f"connectome, 138,639 neurons -- is playing it now, in the browser."),
        "did": describe(run), "compare": compare(run, previous), "od_url": od_url,
    }
    os.makedirs(os.path.join(ROOT, "devlogs"), exist_ok=True)
    md_path = os.path.join(ROOT, "devlogs", f"{args.date}-{args.tag}.md")
    open(md_path, "w").write(render_markdown(entry))

    history = [h for h in history if h["tag"] != args.tag] + [{"tag": args.tag, "date": args.date, "run": run}]
    os.makedirs(os.path.dirname(hist_path), exist_ok=True)
    json.dump(history, open(hist_path, "w"), indent=1)

    entries = []
    for name in sorted(os.listdir(os.path.join(ROOT, "devlogs")), reverse=True):
        if not name.endswith(".md"):
            continue
        meta, body = parse_markdown(open(os.path.join(ROOT, "devlogs", name)).read())
        lead = body.strip().split("\n\n")[0]
        entries.append({"tag": meta.get("tag", name), "date": meta.get("date", name[:10]),
                        "title": meta.get("title", name), "body": body, "lead": lead})
    os.makedirs(os.path.join(ROOT, "web", "devlog"), exist_ok=True)
    open(os.path.join(ROOT, "web", "devlog", "index.html"), "w").write(site(entries))
    open(os.path.join(ROOT, "web", "devlog", "feed.xml"), "w").write(feed(entries))

    itch = (f"{entry['title']}\n\n{entry['lead']}\n\n{entry['did']} {entry['compare']}\n\n"
            f"Watch it play: {PLAY_URL}\nWhat changed in Open Doctrines {args.tag}: {od_url}\n")
    open(os.path.join(ROOT, "release", "itch-devlog.md"), "w").write(itch)
    json.dump({"username": "Open Fly",
               "embeds": [{"title": entry["title"], "url": f"{PLAY_URL}devlog/#{args.tag}",
                           "description": f"{entry['lead']}\n\n{entry['did']}", "color": 0x4DFF9B,
                           "fields": [{"name": "Watch it play", "value": PLAY_URL, "inline": True},
                                      {"name": f"Open Doctrines {args.tag}", "value": od_url, "inline": True}]}]},
              open(os.path.join(ROOT, "release", "discord.json"), "w"), indent=1)
    print(f"devlog: {md_path}")


if __name__ == "__main__":
    main()
