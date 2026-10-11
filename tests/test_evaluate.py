import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

MANIFEST = """loopy: "0.1"
project: demo
cadence: { mode: manual }
funding: { model: owner, approvers: ["@me"] }
budget:
  per_experiment: { tokens: 100k, minutes: 5 }
  per_cycle: { usd: 1 }
  on_exhausted: report
targets: { editable: ["src/**"], frozen: [] }
evaluators:
  - id: tests
    run: python -c "import sys; sys.exit(0)"
    required: true
  - id: score
    run: python .loopy/evaluators/score.py
    metric: score
evaluators_end: null
""".replace("evaluators_end: null\n", "") + """gates: { primary: score }
runner: { adapter: local }
"""

SCORE = 'import json; print(json.dumps({"metric": "score", "value": float(open("src/value.txt").read()), "pass": True}))\n'


def git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        base = os.path.join(self.d, "base")
        os.makedirs(os.path.join(base, "src"))
        os.makedirs(os.path.join(base, ".loopy", "evaluators"))
        with open(os.path.join(base, "loopy.yml"), "w") as f:
            f.write(MANIFEST)
        with open(os.path.join(base, ".loopy", "evaluators", "score.py"), "w") as f:
            f.write(SCORE)
        with open(os.path.join(base, "src", "value.txt"), "w") as f:
            f.write("1.0")
        git("init", "-q", "-b", "main", cwd=base)
        git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=base)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base", cwd=base)
        head = os.path.join(self.d, "head")
        git("clone", "-q", base, head, cwd=self.d)
        self.base, self.head = base, head

    def tearDown(self):
        shutil.rmtree(self.d)

    def change(self, path, text):
        p = os.path.join(self.head, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "try", cwd=self.head)

    def run_loop(self):
        ev = subprocess.run([sys.executable, os.path.join(TOOLS, "evaluate.py"), "--manifest",
                             os.path.join(self.base, "loopy.yml"), "--base", self.base, "--head", self.head,
                             "--id", "exp-1", "--cycle", "1", "--proposal", "prop-1"],
                            capture_output=True, text=True, check=True)
        exp = json.loads(ev.stdout)
        p = os.path.join(self.d, "exp.json")
        with open(p, "w") as f:
            json.dump(exp, f)
        dc = subprocess.run([sys.executable, os.path.join(TOOLS, "decide.py"), "--manifest",
                             os.path.join(self.base, "loopy.yml"), "--experiment", p],
                            capture_output=True, text=True)
        return exp, json.loads(dc.stdout), dc.returncode

    def test_improvement_kept(self):
        self.change("src/value.txt", "2.0")
        exp, d, code = self.run_loop()
        self.assertEqual(exp["paths"], ["src/value.txt"])
        self.assertEqual(exp["evaluator_results"]["score"], {"pass": True, "metric": "score", "value": 2.0, "baseline": 1.0})
        self.assertEqual((d["verdict"], code), ("keep", 0))

    def test_worse_reverted(self):
        self.change("src/value.txt", "0.5")
        _, d, code = self.run_loop()
        self.assertEqual((d["verdict"], code), ("revert", 1))

    def test_editing_the_evaluator_reverted(self):
        self.change(".loopy/evaluators/score.py", 'print(\'{"metric":"score","value":99,"pass":true}\')\n')
        _, d, code = self.run_loop()
        self.assertEqual((d["verdict"], code), ("revert", 1))
        self.assertEqual(d["gate_trace"][0]["gate"], "frozen")


if __name__ == "__main__":
    unittest.main()
