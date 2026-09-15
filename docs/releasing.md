# Releasing: Open Fly follows Open Doctrines

Every Open Doctrines release is an Open Fly release. Nobody has to remember it.

```
Open Doctrines tags vX  ─(dispatch, immediate)──┐
                        ─(poll, every 6 hours)──┤
                                                ▼
             .github/workflows/follow-open-doctrines.yml
   check:   is vX a release tag, is it new, does it contain the agent door, are we live?
   release: build OpenDoctrinesAgent at vX -> fetch FlyWire data -> export the brain
            -> fly_run.mjs plays 120 turns -> devlog.py writes the entry
            -> pack + stage dist/ -> Pages -> itch.io -> Discord
            -> commit release/ and devlogs/ back
```

## Going live (once)

Until the repository variable `OPEN_FLY_LIVE` is `true`, the poll and the dispatch do
nothing. A manual run (**Actions -> Follow Open Doctrines -> Run workflow**) still
builds everything as a dry run: it uploads `dist/` and the devlog as a workflow
artifact, and publishes and commits nothing.

1. **Cloudflare:** create a Pages project named `open-fly` (Direct Upload). Create
   an API token with *Account -> Cloudflare Pages -> Edit*.
2. **itch.io:** create the project as in `docs/itch/README.md`, and keep it in Draft.
3. **Open Fly repository secrets:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
   `BUTLER_API_KEY` (the same key Open Doctrines uses), and optionally
   `DISCORD_WEBHOOK_URL`.
4. **Open Doctrines repository secret** `OPEN_FLY_DISPATCH_TOKEN`, optional: a
   fine-grained token scoped to `Pr1nted/Open-Fly` only, with *Contents: Read and
   write*. Without it Open Fly still follows, just up to six hours later.
5. **Open Fly repository variable** `OPEN_FLY_LIVE=true`. Optional variables:
   `OPEN_FLY_PAGES_PROJECT` (default `open-fly`) and `OPEN_FLY_ITCH_TARGET`
   (default `pr1nted/open-fly:web`).
6. Run the workflow by hand once, with the current tag, to publish.

Each publishing step skips with a warning if its secret is missing, as the itch
step does in Open Doctrines. A missing Discord webhook never blocks a deploy.

## What gets committed back

- `release/open-doctrines-version`: the last tag built. The check compares against it.
- `release/history.json`: every version's `fly_run` result, so the next devlog can compare.
- `release/itch-devlog.md`: the post to paste into itch (itch has no devlog API).
- `devlogs/<date>-<tag>.md`: the entry.
- `web/devlog/`: the entry, published at `/devlog/` with `feed.xml`.

## Tags that are skipped, on purpose

- Anything not `v<digit>…`: `backup/…`, `gearbox-v…` and other SDK tags.
- Release tags from before the agent door existed (`src/web/AgentWeb.cpp`, added
  in 13b2cd5). That means everything up to and including v1.2.0a. The check says
  so in its log instead of failing the build.

## Rebuilding without a new game release

When the fly itself changes (brain, page, encoder), run the workflow by hand with
*force* ticked. It rebuilds the current tag and writes a new devlog entry for it.

## Costs

The repository is public, so Actions minutes on the standard runners are free.
The timings still buy wall-clock rather than money: the poll is a few seconds,
four times a day, and a release run takes 20-40 minutes -- the Emscripten build,
the brain export, then 120 turns of the fly.

## When it breaks

- **The brain step fails to download:** the FlyWire or model file URLs moved. They
  live only in the workflow's *The brain* step and in `tools/make_notebook.py`.
- **`fly_run` cannot load the map:** the game renamed `STDmaps/1914.odmap` or SWE.
  Pass `--map` and `--iso` in the workflow.
- **Pages deploys a preview instead of production:** wrangler guessed the branch.
  The step names `--branch main` for this reason. Keep it.
