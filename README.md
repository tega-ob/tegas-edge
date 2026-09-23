# TEGA'S EDGE — GitHub Pages dashboard

Static, dependency-free dashboard (pure HTML + vanilla JS + JSON, no build step).
Deployed to GitHub Pages from this repo.

## How the pipeline works

**Immutable run payloads.** Every board update is a brand-new JSON file under
`<run_id>.json`. A run file is written once and never modified.
Each payload carries:

- `run_id` (e.g. `20260923-baseline-001`) and `seq` (monotonic integer; baseline = 1)
- `generated_at_et` / `generated_at_utc`
- `clusters`: per-cluster `last_checked_et`, `last_changed_et`,
  `changed_basis` (`baseline` = tracking baseline, not fingerprint-verified;
  `verified` = fingerprint-verified change), plus `last_checked_utc`
  (ISO-8601, used for newness comparisons)
- `plays`: the card (MLB pitcher-strikeout props, earliest game first)
- `records`: combined / NFL / WNBA / MLB-live / MLB-validation
- `content_hash`: sha256 hex of the canonical JSON of the payload
  **excluding** the `content_hash` field itself
  (`json.dumps(..., sort_keys=True, separators=(",",":"), ensure_ascii=True)`)

**Manifest pointer.** `manifest.json` is the ONLY mutable file. It holds
`latest_run_id`, `latest_seq`, a per-cluster freshness map, and update
timestamps. The page (`index.html`) fetches the manifest first, then the
referenced run payload — so the rendered board always shows exactly one
immutable run.

**Newness guard (`tools/publish.py`).** Staging a run enforces, in order:

1. Schema validation (required keys, clusters mlb/nfl/wnba, play fields).
2. `content_hash` recomputation — mismatch aborts.
3. `seq` must be **strictly greater** than the manifest's `latest_seq`.
4. For every cluster the payload covers, `last_checked_utc` must be **>=**
   the manifest's per-cluster value — an older snapshot can never replace
   newer data.
5. The run file is copied to `<run_id>.json` at the site root (flat layout —
   refuses to overwrite an existing file; runs are immutable).
6. The manifest is rewritten **atomically** (tmp file + rename).

Any violation exits non-zero and touches nothing. There is deliberately no
"MISMATCH → retry" logic: a superseded worker must never re-assert older data.

## Deploying (GitHub web upload)

The repo `tega-ob/tegas-edge` is public and empty. GitHub Pages serves the
default branch.

1. Stage the next run locally:
   `python3 tools/publish.py --run-file /path/to/new_run.json`
   (prints `STAGED run_id=... seq=... hash=...`).
2. On GitHub.com, open the repo → **Add file → Upload files** and upload:
   - the new `<run_id>.json`
   - the updated `manifest.json`
   (`index.html` only needs re-uploading if the page itself changed.)
3. Commit directly to the main branch.
4. Enable Pages (first time only): **Settings → Pages → Deploy from a branch
   → main / root → Save.** The site appears at
   `https://tega-ob.github.io/tegas-edge`.

## Verifying a deployment

```bash
python3 tools/verify.py --base-url https://tega-ob.github.io/tegas-edge \
    --local-run <run_id>.json
```

Expected output ends with `PASS` and shows `hash_match=yes`,
`local_match=yes`, plus fetch timings. Any mismatch prints `FAIL` and exits
non-zero. The footer of the rendered page also displays the run ID and
content hash for manual cross-checking.

## File layout

```
index.html                  dashboard page (fetches manifest → run payload)
manifest.json          mutable pointer to the latest run (ONLY mutable file)
<run_id>.json     immutable per-run payloads (never edited)
tools/publish.py            stage a new run (validate → hash → newness guard → stage)
tools/verify.py             verify the live site against a local payload
README.md                   this file
BUILD_NOTES.md              build log, baseline values, discrepancies
```
