#!/usr/bin/env python3
"""Validate loopy.yml files against schema/loopy.schema.json, plus the rules a schema can't express.

Usage: python tools/validate.py loopy.yml [more.yml ...]
Needs PyYAML and jsonschema (pip install pyyaml jsonschema).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loopylib import load_manifest, parse_tokens  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema", "loopy.schema.json")


def extra_checks(m):
    errs = []
    ids = [e["id"] for e in m.get("evaluators", [])]
    if len(ids) != len(set(ids)):
        errs.append("evaluator ids must be unique")
    prim = m.get("gates", {}).get("primary")
    byid = {e["id"]: e for e in m.get("evaluators", [])}
    if prim not in byid:
        errs.append(f"gates.primary {prim!r} is not an evaluator id")
    elif byid[prim].get("sealed"):
        errs.append("gates.primary can't be a sealed evaluator; agents would never see their score")
    b = m.get("budget", {})
    try:
        pe, pc = b.get("per_experiment", {}), b.get("per_cycle", {})
        if "tokens" in pe and "tokens" in pc and parse_tokens(pe["tokens"]) > parse_tokens(pc["tokens"]):
            errs.append("budget.per_experiment.tokens is larger than budget.per_cycle.tokens")
    except ValueError as e:
        errs.append(str(e))
    if m.get("funding", {}).get("model") == "pooled" and isinstance(m["funding"].get("approvers"), list):
        errs.append("a pooled loop needs a governance adapter as approvers, not a list of people")
    if m.get("gates", {}).get("auto_merge") and not m.get("gates", {}).get("human_signoff"):
        errs.append("auto_merge needs human_signoff paths set, so protected work still waits for a person")
    src = [s.get("id") for s in m.get("sources", [])]
    if len(src) != len(set(src)):
        errs.append("source ids must be unique")
    return errs


def main(paths):
    import jsonschema
    with open(SCHEMA, encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    bad = 0
    for p in paths:
        try:
            m = load_manifest(p)
        except Exception as e:  # noqa: BLE001
            print(f"✗ {p}: {e}")
            bad += 1
            continue
        errs = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in validator.iter_errors(m)]
        if not errs:
            errs = extra_checks(m)
        if errs:
            bad += 1
            print(f"✗ {p}")
            for e in errs:
                print(f"    {e}")
        else:
            print(f"✓ {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
