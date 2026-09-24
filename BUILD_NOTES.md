# BUILD NOTES — TEGA'S EDGE GitHub Pages site

Built 2026-09-23 (~2:00 PM ET) as step 2 of the authorized GitHub migration.
Repo: https://github.com/tega-ob/tegas-edge (public, empty — awaiting upload).

## Files created

```
~/workspace/tegas-edge-site/
├── index.html                          dashboard page
├── data/
│   ├── manifest.json                   pointer → 20260923-baseline-001 (seq 1)
│   └── runs/
│       └── 20260923-baseline-001.json  immutable baseline payload
├── tools/
│   ├── publish.py                      stage new runs (validate/hash/newness guard)
│   └── verify.py                       verify live site vs local payload
├── README.md
└── BUILD_NOTES.md                      this file
```

## Baseline values used (last VERIFIED public state, 2026-09-23 12:30:17 PM ET)

- Run ID: `20260923-baseline-001`, seq 1
- Content hash (sha256, canonical JSON excl. content_hash):
  `644e29c4b1b951ac348182cb50a81d74d4e06db28eb7eb447bbe450a7b38284b`
- MLB: 16 pitcher-strikeout props, FanDuel lines, earliest game first,
  all pending. Last checked 12:12 PM ET, last changed 11:42 AM ET
  (changed_basis: `baseline` — tracking baseline, NOT fingerprint-verified).
- NFL: no active plays. Record 10–10.
- WNBA: no active plays. Record 6–6.
- MLB live record: 11–9 (+0.79u).
- MLB validation lane (Sep 21): 1–0, one void (Yesavage; post-surgery
  workload restriction). Separate lane, not in the live record.
- Combined live record: 27–25 (51.9%).

## Discrepancies found vs dashboard/data/latest.json (source of truth = verified values above)

1. `latest.json` MLB `last_checked_et` = **12:42 PM ET** vs verified **12:12 PM ET**.
   The 12:42 timestamp came from the 12:40 pull, whose public delivery was
   never verified (automatic fail). The baseline uses the verified 12:12 PM ET.
2. `latest.json` `generated_at_et` = 12:42 PM ET. Baseline payload uses the
   verification time, 12:30 PM ET, and is labeled "Baseline copied from the
   last manually verified public state — not a fresh scan."
3. `latest.json` NFL/WNBA sections carry fully graded historical cards
   (13-leg MNF card, 14-leg WNBA card). The board shows "no active plays" for
   both sports per the verified state; records (10–10 / 6–6) are in the
   records strip with explanatory notes. Graded-play detail lives in the
   pipeline archive, not on this board.
4. NFL/WNBA cluster freshness in the baseline is approximate: last checked =
   verification time (12:30 PM ET), last changed = 3:07 AM ET (nightly grading
   job that finalized the 9/21 cards), basis `baseline`. Documented here so a
   future run can replace them with exact values.

## Testing performed (2026-09-23, local sandbox)

- `tools/publish.py`:
  - re-submitting seq 1 → FAIL "superseded" (exit 1) ✓
  - tampered content_hash → FAIL "content_hash mismatch" (exit 1) ✓
  - seq 2 with older cluster `last_checked_utc` → FAIL "superseded: cluster 'mlb'…" (exit 1) ✓
  - valid seq 2 → STAGED, manifest rewritten atomically, baseline run file
    untouched (hash unchanged) ✓
- `tools/verify.py` against a local HTTP server:
  - matching local payload → PASS, hash_match=yes, local_match=yes (exit 0) ✓
  - tampered local payload → FAIL "live payload differs" (exit 1) ✓

## How to add the next run

1. Build the new payload JSON (same schema as
   `data/runs/20260923-baseline-001.json`): new `run_id`, `seq` = 2,
   updated clusters/plays/records, and a correct `content_hash`
   (sha256 of canonical JSON excluding `content_hash` itself:
   `json.dumps(body, sort_keys=True, separators=(",",":"), ensure_ascii=True)`).
2. `python3 tools/publish.py --run-file /path/to/new_run.json`
   → prints `STAGED run_id=… seq=… hash=…`.
3. Upload `data/runs/<new_run_id>.json` + `data/manifest.json` to the repo
   (GitHub web upload, commit to main).
4. `python3 tools/verify.py --base-url https://tega-ob.github.io/tegas-edge --local-run data/runs/<new_run_id>.json`
   → must print PASS.
5. Never edit a file under `data/runs/` after staging. Never upload a
   manifest pointing at a run file that isn't in the repo.

## 2026-09-23 ~13:55 ET — flattened layout for web upload
The GitHub web uploader cannot preserve nested folders (drops are filename-only),
so the site was flattened: `manifest.json` and `<run_id>.json` now live at the
site root (was `data/`). index.html, tools/publish.py, tools/verify.py, README.md
updated to the flat paths. All 4 publish.py guard tests re-run in a scratch copy
(superseded seq / tampered hash / older cluster ts -> FAIL; valid seq-2 -> STAGED,
baseline file untouched), and verify.py PASSed against a local HTTP server.
Real staging dir untouched: manifest still seq 1 -> 20260923-baseline-001.

## 2026-09-24 — frontend revamp (Worker B, dashboard-upgrade SPEC)

Full rewrite of `index.html` as a self-contained tabbed app (inline CSS + JS,
vanilla, zero external requests, system fonts only). Dark/gold identity kept.
The probability bar + edge treatment from the old board is preserved on pick
cards (thin bar, prob fill — green gradient for OVER, gold for UNDER — plus a
50% tick mark and the edge pill), now reading "+x.x pp" (percentage points)
instead of "%".

### New/changed files (all at the site root)
- `index.html` — rewritten. Tabs: Picks | Results | Performance | Settings
  (bottom tab bar, `role=tablist`, state in `location.hash`).
  Picks: sport chips, status filter (Upcoming / In progress / Finished / Live /
  All — Live shows an honest "no live feed" empty state), earliest-game-first
  sort, Reset filters, "View details" expander (model prob, edge pp,
  line-capture ts, model version, why, risk, change, price history or
  "Not yet captured"), "Share as image" (branded canvas PNG download).
  Game status is derived honestly: pending + passed start = "In progress —
  awaiting final result".
  Results: calendar (Today / Yesterday / Last 7 days / Custom date), Eastern /
  Device-local day grouping, lazy loading from `runs.json`, original
  line/odds/timestamps/versions/results per graded pick, Live vs Validation
  lane filter, withdrawn[] rendered as an audit trail, expandable
  "What happened" loss reviews (result_detail first, then why/risk; honest
  fallback sentence when no cause data — never invented).
  Performance: record cards (W-L-P-V, win rate WITH n, units or "Unavailable",
  validation lane labeled "not the official record"), headline re-check
  against the published counts, collapsed deeper analysis (prob-vs-observed
  buckets with n + "small samples" disclaimer, unit flow from published
  result notes). Labeled "Paper record — no real wagers."
  Settings: timezone (Eastern default / Device-local), alerts (badge always;
  system Notification only after user enables; quiet hours; honest "true push
  needs a service not yet connected" label), short glossary, "How it works",
  "System status" (run id, seq, content hash 12 chars + full in <details>,
  verified ids, per-cluster freshness, "Published via scheduled worker +
  browser upload" note, OK/Stale/Failed line), Reset to defaults.
  Refresh engine: labeled Refresh button, 60 s auto-poll only when visible,
  immediate refresh on return, in-flight guard + 15 s timeout, unchanged
  hash/run_id updates "Last checked" only, failure keeps last good data with
  inline warning + Retry, "Last checked" vs "Data updated", stale chip >6 h.
  Fetches ONLY ./manifest.json and ./*.json with cache:'no-store'.
- `manifest.webmanifest`, `icon-180.png`, `icon-192.png`, `icon-512.png`
  (PIL: near-black rounded square, gold ring, geometric "E"), `sw.js`
  (cache `edge-shell-v1`, cache-first shell, **network-only for *.json**,
  registers `./sw.js` scope `./`; everything works without SW).
- `runs.json` — built by `tools/build_runs_json.py` (idempotent scan of
  `YYYYMMDD-<slug>.json`, sorted by seq; 16 entries, seq 1–16).
- `tools/publish.py` — ADDITIVE ONLY: after a successful STAGED publish it
  rebuilds `runs.json` via `tools/build_runs_json.py`; failures warn to
  stderr and never change the publish outcome. All pre-existing guards
  (superseded seq, hash mismatch, stale cluster ts, immutable run files)
  re-verified in a scratch copy.
- `tools/gen_icons.py`, `tools/test_js_helpers.py`,
  `tools/test_data_contract.py`, `tools/test_render_smoke.py` — additive
  build/test tooling (not part of the publish pipeline).

### Data contracts (frontend reads only — never modified)
- `manifest.json`: `{latest_run_id, latest_seq, per_cluster.{mlb,nfl,wnba}:
  {run_id, seq, last_checked_et/utc, availability_status, validation_status,
  model_versions}, verified_at_utc, verified_run_id}` (+ `updated_at_*`).
- `<run_id>.json`: `run_id, seq, generated_at_et/utc, lanes, clusters,
  plays[], records{}, model_versions, availability_status, validation_status,
  verified_at_utc, withdrawn{}, note, content_hash, graded{}`.
  Play keys: `player, team, opp, market, line, side, game_start, prob (0-1),
  edge (fraction of pp — 0.089 = +8.9 pp), status, price_note ("@1.82 fanduel"
  or "@-113 fanduel"), line_src, model_version, line_captured_at, why, risk,
  change`. Current picks come from `clusters.*.plays` (superset, carries
  sport); old runs without cluster plays fall back to top-level `plays[]`.
  `withdrawn` is sport → list (rows = play fields + `withdraw_reason`,
  `withdrawn_at_et`; old rows lack the reason — rendered without it).
  `graded` is sport → list (play fields + `result_detail, graded_at_et/utc`).
  `records` keys vary (`combined, mlb_live, mlb_validation, nfl, wnba`):
  rendered generically; keys containing "validation" are labeled
  "Validation (not the official record)"; `units` is a string like "+2.27u"
  or absent ("Unavailable").
- Defensive rules: no "prizepicks" string anywhere in the frontend (a
  `line_src` containing it would render as "Board" — not present in any run
  file today); missing values render "Unknown"/"Unavailable", never zero.
- Untouched per spec: `records.json`, `login_status*.json`, `receipts/`,
  `raw/`, `audit_holds.json`, `lanes.json`, existing run files, `manifest.json`.

### How to publish frontend changes
Frontend files (`index.html`, `sw.js`, `manifest.webmanifest`, icons,
`runs.json`) deploy flat at the repo root via the existing browser-upload
flow (same as run files). After changing `index.html` JS, re-run:
`python3 tools/test_js_helpers.py`, `python3 tools/test_render_smoke.py`,
`python3 tools/test_data_contract.py`, and the TEST_REPORT.md curl checklist.
Bump the `sw.js` cache name (e.g. `edge-shell-v3`) when the shell changes so
installed clients pick it up. Since v3 the HTML shell document is
network-first (cache fallback offline) so UI fixes land on the next visit;
v2 was cache-first and served a stale shell indefinitely, which hid the
restored sort controls from returning visitors. Do NOT commit/push from here — the main agent
publishes via the browser flow.
