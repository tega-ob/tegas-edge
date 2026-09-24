#!/usr/bin/env python3
"""Verify the live GitHub Pages deployment of the TEGA'S EDGE dashboard.

Usage:
    python3 tools/verify.py --base-url https://tega-ob.github.io/tegas-edge
                            [--local-run 20260923-baseline-001.json]
                            [--timeout 20]

Fetches manifest.json and the referenced run payload over HTTPS,
recomputes the content hash, and (optionally) compares against a local
staged payload. Prints PASS/FAIL with run_id, hash match, and timing.
Exit 0 on pass, non-zero on any mismatch or fetch failure.
Site layout is flat: manifest.json and <run_id>.json at the site root.
"""

import argparse
import hashlib
import json
import sys
import time
import urllib.request


def canonical_bytes(payload):
    body = {k: v for k, v in payload.items() if k != "content_hash"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)
    return text.encode("utf-8")


def content_hash_of(payload):
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def fetch(url, timeout):
    t0 = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": "tegas-edge-verify/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError("HTTP %d for %s" % (resp.status, url))
        data = resp.read().decode("utf-8")
    return data, (time.monotonic() - t0) * 1000.0


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True,
                    help="site base URL, e.g. https://tega-ob.github.io/tegas-edge")
    ap.add_argument("--local-run", default=None,
                    help="optional local run payload to compare against")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    t_start = time.monotonic()

    try:
        manifest_text, ms_manifest = fetch(base + "/manifest.json",
                                          args.timeout)
    except Exception as e:
        fail("could not fetch manifest: %s" % e)
    try:
        manifest = json.loads(manifest_text)
    except Exception as e:
        fail("manifest is not valid JSON: %s" % e)

    run_id = manifest.get("latest_run_id")
    seq = manifest.get("latest_seq")
    if not run_id:
        fail("manifest missing latest_run_id")

    try:
        run_text, ms_run = fetch(base + "/" + run_id + ".json",
                                 args.timeout)
    except Exception as e:
        fail("could not fetch run payload %s: %s" % (run_id, e))
    try:
        payload = json.loads(run_text)
    except Exception as e:
        fail("run payload is not valid JSON: %s" % e)

    if payload.get("run_id") != run_id:
        fail("run file run_id '%s' does not match manifest '%s'"
             % (payload.get("run_id"), run_id))

    recomputed = content_hash_of(payload)
    hash_match = (recomputed == payload.get("content_hash"))

    local_match = "n/a"
    if args.local_run:
        with open(args.local_run, "r", encoding="utf-8") as f:
            local = json.load(f)
        local_match = "yes" if (content_hash_of(local) == recomputed
                                and local.get("run_id") == run_id) else "no"

    elapsed = (time.monotonic() - t_start) * 1000.0
    print("run_id=%s seq=%s" % (run_id, seq))
    print("hash_match=%s" % ("yes" if hash_match else "no"))
    print("hash=%s" % recomputed)
    print("local_match=%s" % local_match)
    print("fetch_manifest_ms=%.0f fetch_run_ms=%.0f total_ms=%.0f"
          % (ms_manifest, ms_run, elapsed))

    if not hash_match:
        fail("content hash mismatch on live payload")
    if local_match == "no":
        fail("live payload differs from local staged payload")
    print("PASS")


if __name__ == "__main__":
    main()
