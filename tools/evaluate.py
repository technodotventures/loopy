#!/usr/bin/env python3
"""Run a project's non-sealed evaluators on the current version and on a candidate,
and write the Experiment record that tools/decide.py reads.

This is the trusted half of Prove: the agent writes the change, CI scores it.
The evaluator commands always come from the base checkout's loopy.yml.

Usage:
  python tools/evaluate.py --manifest base/loopy.yml --base base --head head \
      --id exp-12-3 --cycle 12 --proposal prop-12-1 [--usage usage.json] > exp.json
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loopylib import last_json_line, load_manifest  # noqa: E402


def run_one(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"pass": False, "error": "timeout"}
    out = last_json_line(p.stdout)
    if out is None:
        # No JSON: fall back to the exit code, which is how plain test runners report.
        return {"pass": p.returncode == 0}
    res = {"pass": bool(out.get("pass", p.returncode == 0)) and p.returncode == 0}
    if "metric" in out:
        res["metric"] = out["metric"]
    if isinstance(out.get("value"), (int, float)):
        res["value"] = out["value"]
    return res


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--base", required=True, help="Checkout of the current version")
    ap.add_argument("--head", required=True, help="Checkout of the candidate")
    ap.add_argument("--id", required=True)
    ap.add_argument("--cycle", type=int, required=True)
    ap.add_argument("--proposal", required=True)
    ap.add_argument("--usage", help="JSON file with tokens, usd, minutes, pool from the runner")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args(argv)

    m = load_manifest(a.manifest)
    results = {}
    for e in m["evaluators"]:
        if e.get("sealed"):
            continue  # sealed evaluators only run at report time
        head = run_one(e["run"], a.head, a.timeout)
        if "value" in head:
            base = run_one(e["run"], a.base, a.timeout)
            if "value" in base:
                head["baseline"] = base["value"]
        results[e["id"]] = head

    base_sha, head_sha = git(["rev-parse", "HEAD"], a.base), git(["rev-parse", "HEAD"], a.head)
    paths = [p for p in git(["diff", "--name-only", f"{base_sha}...{head_sha}"], a.head).splitlines() if p]
    usage = {"tokens": 0, "minutes": 0}
    if a.usage:
        with open(a.usage, encoding="utf-8") as f:
            usage.update(json.load(f))

    exp = {
        "type": "experiment",
        "id": a.id,
        "cycle": a.cycle,
        "proposal": a.proposal,
        "commit": head_sha,
        "base_commit": base_sha,
        "paths": paths,
        "evaluator_results": results,
        "usage": usage,
        "status": "done",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    print(json.dumps(exp, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
