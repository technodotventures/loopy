# Setting up Loopy: instructions for agents

You've been asked to set up a Loopy loop in a project. This file is for you, the agent doing the setup. Read [SPEC.md](SPEC.md) first if you haven't; it is short and every rule below comes from it.

The goal: by the end, the project has a `loopy.yml`, a `.loopy/` folder and a runner, all in **one pull request for a human to review**. You set the loop up. You do not start it, and you never merge your own setup PR.

## Ground rules

- **Humans own the scorer.** You may suggest evaluators, gates, budgets and approvers. A human must confirm each of them before you write them into `loopy.yml`. If you can't ask, write your best suggestion and mark it `# TODO(human): confirm` so the PR can't be mistaken for a finished decision.
- **Ask before spending.** Budgets are real money. Never pick a budget above the conservative defaults below without a human saying so.
- **No secrets in files.** Model keys and tokens go in the runner's secret store, never in `loopy.yml` or `.loopy/`.
- **Don't change the project's code** during setup, apart from adding evaluator scripts the human has agreed to.

## Steps

### 1. Understand what "better" means here

Look at the project before writing anything:

- What does it do, and how is it built and tested? Find the test command, any benchmarks, linters, type checks or performance scripts.
- What could improve? Speed, accuracy, recall, bundle size, test coverage, docs quality, conformance to a spec.
- Which of those can a script measure and print as a number?

Propose to the human:

- **One primary evaluator**: a command that prints `{"metric": "<name>", "value": <number>, "pass": true}` and gets better in a known direction. If nothing suitable exists, propose a small script in `.loopy/evaluators/` that wraps the existing tests or benchmarks.
- **Required evaluators**: checks that must always pass (the test suite, type check, build).
- **A sealed evaluator** if the project has enough data to hold some back. Say plainly if it doesn't; L1 and L2 don't need one.

### 2. Write `loopy.yml`

Copy [`templates/loopy.yml`](templates/loopy.yml) to the project root and fill it in:

- `project`: the repo name.
- `cadence`: default to `mode: scheduled`, `every: 1w`, `start:` next Monday. Weekly is the right first cadence for almost every project.
- `budget`: use these defaults unless the human gives others:
  - `per_experiment: { tokens: 300k, minutes: 20 }`
  - `per_cycle: { tokens: 5M, usd: 25 }`
  - `per_day: { usd: 10 }`
  - `on_exhausted: report`
- `funding`: `model: owner`, and `approvers` set to the people or team the human names.
- `sources`: start with `github-issues` (labels `loopy:request`, `bug`, `feedback`). Add research or release sources only if the human wants them.
- `targets.editable`: the source and docs folders. `targets.frozen`: tests used by evaluators, benchmark data, `loopy.yml`, `.loopy/evaluators/**`, CI config and anything security-sensitive.
- `evaluators` and `gates`: from step 1. Keep `auto_merge: false`.
- `runner`: `gh-aw` if the project is on GitHub and the human agrees, otherwise `local`.

Then validate it from a clone of this repo:

```bash
pip install pyyaml jsonschema
python tools/validate.py path/to/loopy.yml
```

### 3. Add the `.loopy/` folder

Copy [`templates/dot-loopy/`](templates/dot-loopy/) to `.loopy/` in the project. It holds an empty ledger, a lessons file, the shared rules every stage follows, and the stage prompts in `.loopy/stages/`.

Then copy `tools/decide.py`, `tools/evaluate.py` and `tools/loopylib.py` from this repo into `.loopy/tools/`. The decide workflow runs them, and they are always frozen.

### 4. Add the runner

**GitHub Agentic Workflows** (`runner.adapter: gh-aw`):

1. Copy the files in [`templates/gh-aw/`](templates/gh-aw/) to `.github/workflows/`.
2. Set `timeout-minutes` in `loopy-prove.md` to `budget.per_experiment.minutes`, and the schedules to match `cadence`.
3. Compile them with `gh aw compile` and commit both the `.md` files and the generated `.lock.yml` files.
4. Create the labels in [`templates/labels.yml`](templates/labels.yml).
5. Tell the human which secret the engine needs (for example `ANTHROPIC_API_KEY` for `engine: claude`) and that they must add it themselves.

**Local** (`runner.adapter: local`): the stage prompts in `.loopy/stages/` work with any coding agent. Write a short `.loopy/RUNNING.md` explaining how the human runs a cycle with their agent of choice, on a cron job or by hand.

### 5. Protect what must stay human

Add a `CODEOWNERS` entry for every frozen and `human_signoff` path, owned by the approvers. Then tell the human to turn on branch protection for the default branch with "Require review from Code Owners". This is what makes the gates hold even if something goes wrong.

### 6. Open the pull request

One PR, titled `Set up Loopy`, containing everything above. In the description:

- what the loop will try to improve, and the primary metric
- the cadence and the budget caps, in plain numbers
- every `TODO(human)` left in the files
- what the human must do outside the PR: add the model secret, turn on branch protection, merge

Optionally offer to add a badge to the README (see [`brand/`](brand/)): **Autonomously improving with loopy**.

## After setup

The first cycle starts on the `cadence.start` date. Each cycle ends with a report in `.loopy/cycles/<n>/report.md`. If the human asks you to run a cycle by hand, follow `.loopy/stages/` in order: listen, propose, prove, then run `tools/decide.py` on each experiment, then report. Never skip decide, and never decide yourself.
