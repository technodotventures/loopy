"""Shared helpers for the Loopy reference tools. Standard library plus PyYAML."""
import json
import re

# Paths an experiment may never change, whatever loopy.yml says (SPEC.md sections 3 and 8).
ALWAYS_FROZEN = [
    "loopy.yml",
    ".loopy/evaluators/**",
    ".loopy/tools/**",
    ".loopy/stages/**",
    ".loopy/shared/**",
    ".loopy/ledger.jsonl",
    ".github/workflows/**",
    "CODEOWNERS",
    ".github/CODEOWNERS",
]


def load_manifest(path):
    import yaml  # PyYAML
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a mapping")
    return _stringify_dates(data)


def _stringify_dates(obj):
    """YAML turns 2026-10-12 into a date; the schema wants strings."""
    import datetime
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    return obj


def parse_tokens(v):
    """400k -> 400000, 20M -> 20000000, 1500 -> 1500."""
    if isinstance(v, (int, float)):
        return int(v)
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([kM]?)", str(v).strip())
    if not m:
        raise ValueError(f"bad token count: {v!r}")
    n = float(m.group(1)) * {"": 1, "k": 1_000, "M": 1_000_000}[m.group(2)]
    return int(n)


def glob_to_regex(pattern):
    """Gitignore-style globs: ** crosses folders, * and ? stay inside one."""
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(path, patterns):
    if path.startswith("./"):
        path = path[2:]
    return [p for p in patterns if glob_to_regex(p).match(path)]


def last_json_line(text):
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None
