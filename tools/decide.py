#!/usr/bin/env python3
"""Reference keep-or-revert gate for Loopy (SPEC.md section 8).

Deterministic: same manifest and experiment in, same decision out. No model calls,
no network. Gates run in order and the first failure decides the verdict.

Usage:
  python tools/decide.py --manifest loopy.yml --experiment exp.json [--out ledger.jsonl]

Prints the Decision record as JSON. Exit code: 0 keep, 1 revert, 2 needs-human, 3 bad input.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loopylib import ALWAYS_FROZEN, load_manifest, matches_any, parse_tokens  # noqa: E402

VERSION = "loopy-decide/0.1.0"
EXIT = {"keep": 0, "revert": 1, "needs-human": 2}


def decide(manifest, exp, now=None):
    trace = []

    def gate(name, ok, detail):
        trace.append({"gate": name, "ok": ok, "detail": detail})
        return ok

    def verdict(v):
        return {
            "type": "decision",
            "experiment": exp.get("id"),
            "verdict": v,
            "gate_trace": trace,
            "decided_by": VERSION,
            "at": now or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }

    paths = exp.get("paths", [])
    targets = manifest.get("targets", {})
    evals = {e["id"]: e for e in manifest.get("evaluators", []) if not e.get("sealed")}
    results = exp.get("evaluator_results", {})
    gates = manifest.get("gates", {})

    # 1. Frozen paths untouched (and nothing outside editable).
    frozen = list(targets.get("frozen", [])) + ALWAYS_FROZEN
    hit = [p for p in paths if matches_any(p, frozen)]
    outside = [p for p in paths if not matches_any(p, targets.get("editable", []))]
    if not gate("frozen", not hit and not outside,
                f"frozen: {hit}" if hit else (f"not editable: {outside}" if outside else f"{len(paths)} paths ok")):
        return verdict("revert")

    # 2. Budget respected.
    cap = manifest.get("budget", {}).get("per_experiment", {})
    use = exp.get("usage", {})
    over = []
    if "tokens" in cap and use.get("tokens", 0) > parse_tokens(cap["tokens"]):
        over.append(f"tokens {use.get('tokens')} > {cap['tokens']}")
    if "minutes" in cap and use.get("minutes", 0) > cap["minutes"]:
        over.append(f"minutes {use.get('minutes')} > {cap['minutes']}")
    if "usd" in cap and use.get("usd", 0) > cap["usd"]:
        over.append(f"usd {use.get('usd')} > {cap['usd']}")
    if exp.get("status") in ("timeout", "over_budget"):
        over.append(f"status {exp.get('status')}")
    if not gate("budget", not over, "; ".join(over) or "within per_experiment"):
        return verdict("revert")

    # 3. Required evaluators pass.
    failed = [i for i, e in evals.items() if e.get("required")
              and not results.get(i, {}).get("pass", False)]
    if not gate("required", not failed, f"failed or missing: {failed}" if failed else "all required passed"):
        return verdict("revert")

    # 4. No regression beyond tolerance.
    regressed = []
    for i, e in evals.items():
        if "tolerance" not in e:
            continue
        r = results.get(i, {})
        if "value" not in r or "baseline" not in r:
            regressed.append(f"{i}: missing value or baseline")
            continue
        sign = -1 if e.get("direction") == "down" else 1
        delta = (r["value"] - r["baseline"]) * sign
        if delta < -e["tolerance"]:
            regressed.append(f"{i}: {r['baseline']} -> {r['value']} (tolerance {e['tolerance']})")
    if not gate("regression", not regressed, "; ".join(regressed) or "no regression"):
        return verdict("revert")

    # 5. Primary improves.
    pid = gates.get("primary")
    p = results.get(pid, {})
    pe = evals.get(pid)
    if pe is None or "value" not in p or "baseline" not in p:
        gate("primary", False, f"primary {pid!r} missing, sealed, or has no value and baseline")
        return verdict("revert")
    sign = -1 if pe.get("direction") == "down" else 1
    gain = (p["value"] - p["baseline"]) * sign
    need = gates.get("min_improvement", 0)
    if not gate("primary", gain > need, f"{pid}: {p['baseline']} -> {p['value']} (gain {gain:+g}, need > {need:g})"):
        return verdict("revert")

    # 6. Human sign-off.
    signoff = [x for x in paths if matches_any(x, gates.get("human_signoff", []))]
    if not gate("signoff", not signoff, f"needs a code owner: {signoff}" if signoff else "no sign-off paths"):
        return verdict("needs-human")

    return verdict("keep")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--experiment", required=True, help="Experiment record as JSON")
    ap.add_argument("--out", help="Append the decision to this ledger file")
    a = ap.parse_args(argv)
    try:
        manifest = load_manifest(a.manifest)
        with open(a.experiment, encoding="utf-8") as f:
            exp = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 3
    d = decide(manifest, exp)
    line = json.dumps(d, separators=(",", ":"))
    print(json.dumps(d, indent=2))
    if a.out:
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return EXIT[d["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
