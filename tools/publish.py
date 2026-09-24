#!/usr/bin/env python3
"""Stage a new immutable run payload for the TEGA'S EDGE GitHub Pages site.

Usage:
    python3 tools/publish.py --run-file <payload.json>

Steps:
  1. Validate the payload schema (new optional enrichment fields are
     accepted when present; old payloads without them still validate —
     nothing new is required).
  2. Recompute content_hash (sha256 of canonical JSON excluding the
     content_hash field itself); fail if it does not match.
  3. Newness guard: payload seq must be > manifest latest_seq, and for every
     cluster the payload covers, its last_checked_utc must be >= the
     manifest's per-cluster value. Otherwise the payload is superseded and
     the run exits non-zero WITHOUT touching anything.
  4. Copy the run file to <run_id>.json at the site root (never modify an
     existing run file).
  5. Rewrite manifest.json atomically (tmp file + os.replace). The staged
     manifest carries verified_at_utc: null and verified_run_id: null
     (the post-verify stamp step fills them); per-cluster entries pass
     through the run's model_versions / availability_status /
     validation_status additively.

Repo root is resolved as the parent of this script's directory, and it is
also the site root: every file here deploys flat (index.html, manifest.json,
<run_id>.json) so the GitHub web uploader needs no folder structure.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

REQUIRED_CLUSTERS = ("mlb", "nfl", "wnba")

# Additive enrichment fields (all optional; old payloads still validate).
PLAY_CHANGE_VALUES = ("new", "changed", "same", "withdrawn")
AVAIL_VALUES = ("ok", "degraded", "unknown")
VALID_VALUES = ("approved", "unvalidated", "unknown")


def canonical_bytes(payload):
    """Deterministic serialization of a payload EXCLUDING content_hash."""
    body = {k: v for k, v in payload.items() if k != "content_hash"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)
    return text.encode("utf-8")


def content_hash_of(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def fail(msg):
    print("FAIL: " + msg, file=sys.stderr)
    sys.exit(1)


def _is_integer_line(line):
    """Mirror of the scanner's push-impossibility rule: a whole-number line
    can push, which the side-relative probability math cannot price."""
    try:
        return float(line).is_integer()
    except (TypeError, ValueError):
        return True  # fail closed: unreadable lines are unpriceable

def validate_play(p, where, integer_line_block=False):
    for k in ("player", "team", "opp", "market", "line", "side",
              "game_start"):
        if k not in p:
            fail("%s missing %s" % (where, k))
    if integer_line_block and _is_integer_line(p.get("line")):
        fail("%s: integer line %r is unpublishable (push possible; "
             "probability model cannot price it)" % (where, p.get("line")))
    # Optional enrichment fields: type-checked only when present.
    for k in ("why", "risk", "line_captured_at"):
        if k in p and p[k] is not None and not isinstance(p[k], str):
            fail("%s.%s must be a string or null" % (where, k))
    if "line_src" in p and not isinstance(p["line_src"], str):
        fail("%s.line_src must be a string" % where)
    if "model_version" in p:
        if p["model_version"] is not None and not isinstance(
                p["model_version"], str):
            fail("%s.model_version must be a string or null" % where)
    if "change" in p and p["change"] not in PLAY_CHANGE_VALUES:
        fail("%s.change must be one of %s" % (where, PLAY_CHANGE_VALUES))



def validate(payload):
    if not isinstance(payload, dict):
        fail("payload is not a JSON object")
    for key in ("run_id", "seq", "generated_at_et", "clusters", "plays",
                "records", "content_hash"):
        if key not in payload:
            fail("missing required key: %s" % key)
    if not isinstance(payload["run_id"], str) or not payload["run_id"]:
        fail("run_id must be a non-empty string")
    if not isinstance(payload["seq"], int) or payload["seq"] < 1:
        fail("seq must be a positive integer")
    clusters = payload["clusters"]
    if not isinstance(clusters, dict):
        fail("clusters must be an object")
    for c in REQUIRED_CLUSTERS:
        if c not in clusters:
            fail("clusters missing required cluster: %s" % c)
        cc = clusters[c]
        for k in ("last_checked_et", "last_changed_et", "changed_basis"):
            if k not in cc:
                fail("clusters.%s missing %s" % (c, k))
        if cc["changed_basis"] not in ("baseline", "verified"):
            fail("clusters.%s changed_basis must be baseline|verified" % c)
        for i, p in enumerate(cc.get("plays") or []):
            # Defense in depth (2026-09-23 audit): the NFL scanner rejects
            # integer lines at generation; the publishing layer rejects them
            # independently so a malformed scan payload can never publish one.
            # Scoped to NFL only — the demonstrated defect. MLB/WNBA scanners
            # have no such gate, so blocking them here could kill legitimate
            # plays; widen only when those scanners get their own gate.
            validate_play(p, "clusters.%s.plays[%d]" % (c, i),
                          integer_line_block=(c == "nfl"))
    if not isinstance(payload["plays"], list):
        fail("plays must be a list")
    for i, p in enumerate(payload["plays"]):
        validate_play(p, "plays[%d]" % i)
    if not isinstance(payload["records"], dict):
        fail("records must be an object")
    for r in ("combined", "nfl", "wnba", "mlb_live"):
        if r not in payload["records"]:
            fail("records missing %s" % r)
    # Optional run-level enrichment fields: accepted, never required.
    if "model_versions" in payload:
        mv = payload["model_versions"]
        if not isinstance(mv, dict):
            fail("model_versions must be an object")
        for s in REQUIRED_CLUSTERS:
            if s in mv and mv[s] is not None and not isinstance(mv[s], str):
                fail("model_versions.%s must be a string or null" % s)
    if "availability_status" in payload:
        av = payload["availability_status"]
        if not isinstance(av, dict):
            fail("availability_status must be an object")
        for s, v in av.items():
            if v not in AVAIL_VALUES:
                fail("availability_status.%s must be one of %s"
                     % (s, AVAIL_VALUES))
    if "validation_status" in payload:
        vv = payload["validation_status"]
        if not isinstance(vv, dict):
            fail("validation_status must be an object")
        for s, v in vv.items():
            if v not in VALID_VALUES:
                fail("validation_status.%s must be one of %s"
                     % (s, VALID_VALUES))
    if "verified_at_utc" in payload and payload["verified_at_utc"] is not None:
        if not isinstance(payload["verified_at_utc"], str):
            fail("verified_at_utc must be a string or null")
    if "withdrawn" in payload:
        w = payload["withdrawn"]
        if not isinstance(w, dict):
            fail("withdrawn must be an object")
        for s, lst in w.items():
            if not isinstance(lst, list):
                fail("withdrawn.%s must be a list" % s)
            for i, p in enumerate(lst):
                validate_play(p, "withdrawn.%s[%d]" % (s, i))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-file", required=True,
                    help="path to the new run payload JSON")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runs_dir = root  # run files live flat at the site root: <run_id>.json
    manifest_path = os.path.join(root, "manifest.json")

    with open(args.run_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    validate(payload)

    expected = content_hash_of(payload)
    if payload["content_hash"] != expected:
        fail("content_hash mismatch: payload says %s, recomputed %s"
             % (payload["content_hash"], expected))

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # --- newness guard: monotonic sequence ---
    if payload["seq"] <= manifest.get("latest_seq", 0):
        fail("superseded: payload seq %d is not > manifest latest_seq %d"
             % (payload["seq"], manifest.get("latest_seq", 0)))

    # --- newness guard: per-cluster freshness (no older snapshot replaces newer) ---
    per_cluster = manifest.get("per_cluster", {})
    for c, cc in payload["clusters"].items():
        old = per_cluster.get(c)
        if old is None:
            continue
        new_ts = cc.get("last_checked_utc") or ""
        old_ts = old.get("last_checked_utc") or ""
        if new_ts and old_ts and new_ts < old_ts:
            fail("superseded: cluster '%s' last_checked_utc %s is older than "
                 "published %s" % (c, new_ts, old_ts))

    # --- copy run file (immutable: never overwrite) ---
    dest = os.path.join(runs_dir, payload["run_id"] + ".json")
    if os.path.exists(dest):
        fail("run file already exists (immutable): %s" % dest)
    shutil.copyfile(args.run_file, dest)

    # --- rewrite manifest atomically ---
    # verified_at_utc / verified_run_id are null at staging; the post-verify
    # stamp step fills them after the rendered page is confirmed.
    new_manifest = {
        "latest_run_id": payload["run_id"],
        "latest_seq": payload["seq"],
        "per_cluster": {},
        "updated_at_et": payload.get("generated_at_et", ""),
        "updated_at_utc": payload.get("generated_at_utc", ""),
        "verified_at_utc": None,
        "verified_run_id": None,
    }
    model_versions = payload.get("model_versions") or {}
    availability_status = payload.get("availability_status") or {}
    validation_status = payload.get("validation_status") or {}
    for c, old in per_cluster.items():
        new_manifest["per_cluster"][c] = old
    for c, cc in payload["clusters"].items():
        entry = {
            "run_id": payload["run_id"],
            "seq": payload["seq"],
            "last_checked_et": cc["last_checked_et"],
            "last_checked_utc": cc.get("last_checked_utc", ""),
        }
        # Additive pass-through of run-level enrichment into per-cluster
        # entries (only when the payload carries them).
        if model_versions:
            entry["model_versions"] = dict(model_versions)
        if c in availability_status:
            entry["availability_status"] = availability_status[c]
        if c in validation_status:
            entry["validation_status"] = validation_status[c]
        new_manifest["per_cluster"][c] = entry
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(new_manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, manifest_path)

    print("STAGED run_id=%s seq=%d hash=%s"
          % (payload["run_id"], payload["seq"], expected))

    # --- maintain runs.json (frontend history index; display infrastructure,
    #     not a model change). Additive: rebuild idempotently from the run
    #     files on disk. Must never alter the publish outcome above, so any
    #     failure here is a warning, not a publish failure.
    # --- maintain runs.json (frontend history index; display infrastructure,
    #     not a model change). Additive: rebuild idempotently from the run
    #     files on disk. Must never alter the publish outcome above, so any
    #     failure here is a warning, not a publish failure.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build_runs_json
        entries = build_runs_json.build(root)
        print("runs.json rebuilt: %d runs indexed" % len(entries))
    except Exception as e:  # noqa: BLE001
        print("WARN: runs.json rebuild failed: %s" % e, file=sys.stderr)


if __name__ == "__main__":
    main()
