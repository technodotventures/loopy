import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from decide import decide  # noqa: E402
from loopylib import glob_to_regex, parse_tokens  # noqa: E402

MANIFEST = {
    "budget": {"per_experiment": {"tokens": "300k", "minutes": 20}},
    "targets": {"editable": ["src/**", "docs/**"], "frozen": ["tests/**"]},
    "evaluators": [
        {"id": "tests", "run": "x", "required": True},
        {"id": "perf", "run": "x", "direction": "up", "tolerance": 2},
        {"id": "size", "run": "x", "direction": "down", "tolerance": 1},
        {"id": "sealed", "run": "x", "sealed": True},
    ],
    "gates": {"primary": "perf", "human_signoff": ["docs/spec/**"]},
}


def exp(**kw):
    e = {
        "id": "exp-1",
        "paths": ["src/a.py"],
        "usage": {"tokens": 1000, "minutes": 3},
        "status": "done",
        "evaluator_results": {
            "tests": {"pass": True},
            "perf": {"pass": True, "value": 110, "baseline": 100},
            "size": {"pass": True, "value": 50, "baseline": 50},
        },
    }
    e.update(kw)
    return e


def v(e, m=MANIFEST):
    return decide(m, e, now="2026-10-12T00:00:00+00:00")


class Gates(unittest.TestCase):
    def test_keep(self):
        d = v(exp())
        self.assertEqual(d["verdict"], "keep")
        self.assertEqual([g["gate"] for g in d["gate_trace"]],
                         ["frozen", "budget", "required", "regression", "primary", "signoff"])

    def test_frozen_path_reverts(self):
        self.assertEqual(v(exp(paths=["src/a.py", "tests/t.py"]))["verdict"], "revert")

    def test_manifest_always_frozen(self):
        m = dict(MANIFEST, targets={"editable": ["**"], "frozen": []})
        for p in ["loopy.yml", ".loopy/evaluators/e.py", ".loopy/tools/decide.py", ".github/workflows/ci.yml"]:
            self.assertEqual(v(exp(paths=[p]), m)["verdict"], "revert", p)

    def test_outside_editable_reverts(self):
        self.assertEqual(v(exp(paths=["README.md"]))["verdict"], "revert")

    def test_over_token_budget_reverts(self):
        self.assertEqual(v(exp(usage={"tokens": 300_001, "minutes": 1}))["verdict"], "revert")

    def test_timeout_reverts(self):
        self.assertEqual(v(exp(status="timeout"))["verdict"], "revert")

    def test_required_fail_reverts(self):
        e = exp()
        e["evaluator_results"]["tests"]["pass"] = False
        self.assertEqual(v(e)["verdict"], "revert")

    def test_required_missing_reverts(self):
        e = exp()
        del e["evaluator_results"]["tests"]
        self.assertEqual(v(e)["verdict"], "revert")

    def test_regression_beyond_tolerance_reverts(self):
        e = exp()
        e["evaluator_results"]["size"]["value"] = 51.5  # down is better, tolerance 1
        self.assertEqual(v(e)["verdict"], "revert")

    def test_regression_within_tolerance_keeps(self):
        e = exp()
        e["evaluator_results"]["size"]["value"] = 50.9
        self.assertEqual(v(e)["verdict"], "keep")

    def test_no_primary_gain_reverts(self):
        e = exp()
        e["evaluator_results"]["perf"]["value"] = 100
        self.assertEqual(v(e)["verdict"], "revert")

    def test_min_improvement(self):
        m = dict(MANIFEST, gates=dict(MANIFEST["gates"], min_improvement=15))
        self.assertEqual(v(exp(), m)["verdict"], "revert")

    def test_sealed_primary_reverts(self):
        m = dict(MANIFEST, gates={"primary": "sealed"})
        e = exp()
        e["evaluator_results"]["sealed"] = {"pass": True, "value": 9, "baseline": 1}
        self.assertEqual(v(e, m)["verdict"], "revert")

    def test_signoff_needs_human(self):
        self.assertEqual(v(exp(paths=["docs/spec/x.md"]))["verdict"], "needs-human")

    def test_deterministic(self):
        self.assertEqual(json.dumps(v(exp())), json.dumps(v(exp())))


PARETO = dict(MANIFEST,
              evaluators=MANIFEST["evaluators"] + [{"id": "cost", "run": "x", "direction": "down"}],
              gates={"primary": "perf", "keep_if": "required_pass and pareto_improves",
                     "pareto": {"cost": "cost", "max_primary_loss": 3, "min_cost_saving": 0.3}})


def pexp(perf, cost):
    e = exp()
    e["evaluator_results"]["perf"]["value"] = perf
    e["evaluator_results"]["cost"] = {"pass": True, "value": cost, "baseline": 1.0}
    return e


class Pareto(unittest.TestCase):
    def verdict(self, perf, cost):
        return v(pexp(perf, cost), PARETO)

    def test_better_quality_same_cost_keeps(self):
        d = self.verdict(105, 1.0)
        self.assertEqual(d["verdict"], "keep")
        self.assertIn("pareto", [g["gate"] for g in d["gate_trace"]])

    def test_cheaper_same_quality_keeps(self):
        self.assertEqual(self.verdict(100, 0.9)["verdict"], "keep")

    def test_big_saving_small_loss_keeps(self):
        self.assertEqual(self.verdict(98, 0.6)["verdict"], "keep")  # -2 quality, 40% cheaper

    def test_small_saving_small_loss_reverts(self):
        self.assertEqual(self.verdict(98, 0.8)["verdict"], "revert")  # only 20% cheaper

    def test_big_saving_big_loss_reverts(self):
        self.assertEqual(self.verdict(96, 0.2)["verdict"], "revert")  # -4 is past max_primary_loss

    def test_better_but_dearer_reverts(self):
        self.assertEqual(self.verdict(120, 1.1)["verdict"], "revert")

    def test_no_change_reverts(self):
        self.assertEqual(self.verdict(100, 1.0)["verdict"], "revert")

    def test_missing_cost_reverts(self):
        e = exp()
        self.assertEqual(v(e, PARETO)["verdict"], "revert")

    def test_regression_gate_still_applies(self):
        # perf has tolerance 2, so a 3-point trade is caught by the regression gate first.
        d = self.verdict(97, 0.1)
        self.assertEqual(d["verdict"], "revert")
        self.assertEqual(d["gate_trace"][-1]["gate"], "regression")


class Helpers(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(parse_tokens("400k"), 400_000)
        self.assertEqual(parse_tokens("20M"), 20_000_000)
        self.assertEqual(parse_tokens("1.5M"), 1_500_000)
        self.assertEqual(parse_tokens(1500), 1500)

    def test_globs(self):
        g = glob_to_regex
        self.assertTrue(g("src/**").match("src/a/b.py"))
        self.assertTrue(g("**/*.md").match("a/b/c.md"))
        self.assertTrue(g("**/*.md").match("c.md"))
        self.assertFalse(g("src/*").match("src/a/b.py"))
        self.assertFalse(g("src/**").match("srcx/a.py"))


class Validator(unittest.TestCase):
    def run_validate(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(text)
        try:
            return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "validate.py"), f.name],
                                  capture_output=True, text=True)
        finally:
            os.unlink(f.name)

    def test_examples_valid(self):
        examples = sorted(os.path.join("examples", f) for f in os.listdir(os.path.join(ROOT, "examples"))
                          if f.endswith(".yml"))
        for p in ["templates/loopy.yml", *examples]:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "validate.py"), os.path.join(ROOT, p)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_sealed_primary_rejected(self):
        with open(os.path.join(ROOT, "examples", "minimal.yml")) as f:
            t = f.read()
        t = t.replace("gates: { primary: speed }", "gates: { primary: speed }").replace(
            "    metric: seconds\n    direction: down", "    metric: seconds\n    direction: down\n    sealed: true")
        r = self.run_validate(t)
        self.assertEqual(r.returncode, 1)
        self.assertIn("sealed", r.stdout)

    def test_pareto_needs_a_cost_evaluator(self):
        with open(os.path.join(ROOT, "examples", "minimal.yml")) as f:
            t = f.read()
        t = t.replace("gates: { primary: speed }",
                      "gates:\n  primary: speed\n  keep_if: required_pass and pareto_improves\n"
                      "  pareto: { cost: nope }")
        r = self.run_validate(t)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pareto.cost", r.stdout)

    def test_pareto_block_needs_pareto_keep_if(self):
        with open(os.path.join(ROOT, "examples", "minimal.yml")) as f:
            t = f.read()
        t = t.replace("gates: { primary: speed }", "gates:\n  primary: speed\n  pareto: { cost: tests }")
        r = self.run_validate(t)
        self.assertEqual(r.returncode, 1)

    def test_unknown_key_rejected(self):
        with open(os.path.join(ROOT, "examples", "minimal.yml")) as f:
            t = f.read()
        r = self.run_validate(t + "\nyolo: true\n")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
