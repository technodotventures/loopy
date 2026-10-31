# Loopy Protocol

**Version 0.1 (draft)** · Apache-2.0 · [loopy.systems](https://loopy.systems) · [technodotventures/loopy](https://github.com/technodotventures/loopy)

Loopy is an open protocol from [Techno Ventures](https://techno.ventures) that gives any project an end-to-end autoresearch loop. Signals come in, agents propose changes, a fixed evaluator proves them, gates decide, and what survives ships.

A project adopts Loopy by adding one manifest (`loopy.yml`) and a `.loopy/` folder to its repo. It picks a cadence (always on, hourly, daily, every few days, weekly), who pays, and hard budgets in tokens and dollars. The core needs nothing but a git repo and a machine to run on. Every outside product, GitHub included, is an optional adapter. GitHub Agentic Workflows is the first runner binding.

Loopy generalises [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) loop (edit, run a fixed evaluation, keep or revert) from one training file to a whole project. It adds what a project needs on top: community and research inputs, governance, budgets and a public record.

The key words MUST, MUST NOT, SHOULD and MAY are used as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Principles

Seven rules shape every other part of the spec.

1. **Files first.** The manifest, ledger, proposals and reports are plain files in the repo. Anyone can read, diff and replay a loop without Loopy installed.
2. **Humans own the scorer.** Agents can edit the code they are improving. They can never edit the evaluator, the gates, the budget or the manifest.
3. **Keep or revert.** A change survives only if it beats the current version on the evaluator and passes every required check.
4. **Budgets are hard limits.** Every loop has a cap per experiment, per cycle and per day. When a cap is hit, work stops and the loop writes a report.
5. **Every change has a reason.** Each proposal links the signals that caused it. Each shipped change links its proposal and its experiment runs.
6. **Bring your own everything.** Runner, model, sources, evaluators and boards are adapters. A plain repo, the local runner and the files in `.loopy/` are enough to run a full loop.
7. **Agents never grade themselves.** The keep-or-revert decision is made by deterministic code, not by the agent that wrote the change.

**What Loopy does not do:** it doesn't host compute, train models, choose your metric or publish packages.

---

## 2. The loop

Each cycle runs six stages. Only one of them, **Decide**, can ship anything. Agents run Listen, Propose, Prove and Report; Decide is plain code.

```
   ┌──────────► Listen ──► Propose ──► Prove ──┐
   │                                  ▲    │   │
   │                        edit, score, log   │
   │                                           ▼
 Report ◄────────── Ship ◄──────────── Decide (code, not an agent)
```

Inside Prove, an agent edits, scores and logs repeatedly until it beats the current version or runs out of budget. This is the autoresearch inner loop. Report scores the cycle on sealed data and writes lessons that the next Listen reads.

| Stage | Takes in | Produces |
| --- | --- | --- |
| Listen + triage | New issues, papers, releases, feedback | Signals, merged and scored, each with a label and a source |
| Propose | Top-scoring signals and lessons | Proposals with a hypothesis, the paths they touch and an estimated cost |
| Prove | One proposal | Draft PRs with evaluator results, logged to the ledger |
| Decide | Evaluator results and the diff | A verdict: `keep`, `revert` or `needs-human` |
| Ship | Kept PRs | Merged changes, or a review request to a code owner |
| Report | The cycle's ledger | Sealed scores, the cycle report, new lessons, the public feed |

---

## 3. The manifest: `loopy.yml`

One file at the repo root declares the whole loop. Humans own it; any agent edit to it fails the gates. The schema is [`schema/loopy.schema.json`](schema/loopy.schema.json).

```yaml
loopy: "0.1"
project: acme-memory

cadence:
  mode: scheduled            # always-on | scheduled | manual
  every: 1w                  # 1h, 1d, 3d, 1w ...
  start: 2026-10-12          # cycle 1 begins here
  timezone: Australia/Sydney

funding:
  model: owner               # owner | sponsored | pooled
  approvers: ["@acme/maintainers"]
  pools:
    - id: core-team
      cap: { usd_per_month: 1500 }

budget:
  per_experiment: { tokens: 400k, minutes: 20 }
  per_cycle:      { tokens: 20M, usd: 150 }
  per_day:        { usd: 60 }
  on_exhausted: report       # report | pause

sources:
  - id: community
    adapter: intake          # public form or task-card creation
    with: { identity: github, types: [feature, feedback, research, integration] }
  - id: feedback
    adapter: github-issues
    with: { labels: [bug, feedback] }
  - id: research
    adapter: arxiv
    with: { query: "long-term memory for LLM agents", max: 20 }

targets:
  editable: ["src/**", "docs/**"]
  frozen:   ["bench/**", "tests/conformance/**", "loopy.yml", ".loopy/evaluators/**"]

evaluators:
  - id: recall-dev
    run: python -m bench.run --split dev --json
    metric: recall@10
    direction: up
    tolerance: 0.5
  - id: conformance
    run: python -m unittest discover -s tests
    required: true
  - id: recall-sealed        # scored once per cycle, never shown to agents
    run: python -m bench.run --split sealed --json
    metric: recall@10
    sealed: true

gates:
  primary: recall-dev
  keep_if: required_pass and primary_improves
  human_signoff: ["spec/**"]
  max_prs_per_cycle: 5
  auto_merge: false

runner:
  adapter: gh-aw             # or: local, claude-code, codex
  engine: claude

sinks:
  - adapter: feed
    with: { publish: pages }
  - adapter: github-projects
    with: { project: 4 }
```

| Block | What it sets |
| --- | --- |
| `cadence` | When cycles start and how long they last |
| `funding` | Who pays, from which pools, and who may change the money and the rules |
| `budget` | Hard caps per experiment, cycle and day, and what happens when one is hit |
| `sources` | Where signals come from: public intake, feedback, research, market, or anything custom |
| `targets` | Which paths agents may change and which are frozen |
| `evaluators` | The commands that score a change, their metric, direction and tolerance |
| `gates` | The keep-or-revert rule, paths that need a human, and per-cycle limits |
| `runner` | What executes the agent stages |
| `sinks` | Where progress is published: the feed, boards, chat |

A conforming implementation MUST reject a manifest that does not validate against the schema. It MUST treat `loopy.yml`, `.loopy/evaluators/`, `.loopy/tools/`, `.loopy/stages/`, `.loopy/shared/`, the ledger, CI workflows and `CODEOWNERS` as frozen even if the project forgets to list them, and MUST revert any experiment that touches a path outside `targets.editable`.

---

## 4. Records and the ledger

Five record types carry a loop, and each is linked to the record before it. Together they answer "why did this change ship?" for any line of code. Schemas live in [`schema/records/`](schema/records/).

| Record | Stored at | Key fields | Written by |
| --- | --- | --- | --- |
| Signal | GitHub issue or `.loopy/signals/` | `id`, `source`, `url`, `author`, `title`, `votes`, `score`, `dup_of` | Source adapters, triage agent |
| Proposal | Issue labelled `loopy:proposal`, or `.loopy/proposals/` | `id`, `signals[]`, `hypothesis`, `change_plan`, `touches[]`, `needs_signoff`, `est_tokens` | Propose agent |
| Experiment | `.loopy/ledger.jsonl` + draft PR | `id`, `proposal`, `commit`, `evaluator_results{}`, `tokens`, `usd`, `minutes`, `pool`, `status` | Prove agent, evaluators |
| Decision | `.loopy/ledger.jsonl` + PR label | `experiment`, `verdict`, `gate_trace[]`, `decided_by` | Decide job (deterministic code) |
| Cycle report | `.loopy/cycles/<n>/report.md` + feed | `cycle`, `window`, `budget_used`, `shipped[]`, `rejected[]`, `sealed_scores{}`, `lessons[]` | Report agent |

**The ledger** (`.loopy/ledger.jsonl`) is append-only: one JSON line per experiment and per decision, never rewritten. A loop can be replayed or audited from the ledger alone.

**Lessons** (`.loopy/lessons.md`) carry what earlier cycles learned ("query splitting helps temporal questions", "index sharding broke determinism"). Every agent reads it at the start of a stage; only the report agent appends to it. It is how the loop remembers between cycles.

The `.loopy/` folder:

```
.loopy/
  ledger.jsonl        append-only experiments and decisions
  lessons.md          what the loop has learned
  shared/rules.md     rules every agent stage imports
  stages/             the stage prompts: listen, propose, prove, report
  tools/              decide.py and evaluate.py (frozen)
  signals/            signals not stored as issues
  proposals/          proposals not stored as issues
  cycles/<n>/         report.md and sealed scores per cycle
  evaluators/         evaluator scripts (frozen)
  adapters/<name>/    custom adapters
```

---

## 5. Adapters: how anyone plugs in

Everything outside the core is an adapter, and an adapter is just a command. It reads JSON on stdin and writes JSON lines on stdout, so it can be written in any language, wrap any app or call any API.

| Kind | Contract | Built-in adapters (v0.1) |
| --- | --- | --- |
| Source | `pull --since <cursor>` → Signal lines | `intake`, `files`, `webhook`, `rss`, `arxiv`, `github-issues`, `github-discussions`, `github-releases` |
| Evaluator | runs, then prints `{"metric": …, "value": …, "pass": …}` | `command` (any script), `pytest`, `unittest`, `benchmark-json` |
| Runner | executes a stage prompt with an agent, within a budget | `local` (cron + any model key, no third party), `gh-aw`, `claude-code`, `codex` |
| Sink | receives each record as it is written | `feed`, `files`, `github-projects`, `slack`, `discord` |

A custom adapter is a folder in `.loopy/adapters/<name>/` with an `adapter.yml` (kind, command, inputs) and the executable:

```yaml
# .loopy/adapters/helpdesk/adapter.yml
kind: source
command: ./pull.py
inputs:
  api_url: { required: true }
  token_env: HELPDESK_TOKEN
```

To plug in a whole app, such as a support desk as a source or a load test as an evaluator, wrap its API in one adapter.

---

## 6. Cadence and budgets

Cadence sets when work starts; the budget sets when it must stop. A loop never spends past its cap, whatever the cadence.

| Mode | How it runs | Good for |
| --- | --- | --- |
| Always on | Every new signal triggers triage straight away; experiments run from a queue until the day's budget is spent | Busy projects with steady community input |
| Scheduled, `1h` to `1d` | A cycle starts on the clock and runs every stage once | Fast-moving code with cheap evaluators |
| Scheduled, `3d` to `1w` | Same, with time for longer benchmarks and human sign-off inside the cycle | Protocols, specs and anything slow to evaluate |
| Manual | A maintainer starts a cycle by hand or with a `/loopy run` comment | Trying Loopy out, or a project on a tight budget |

Cycle numbers come from `cadence.start` and the cycle length, so every viewer and runner agrees which cycle it is. Schedulers that can't express the cadence directly (GitHub's cron has no "every 3 days") fire daily and start a new cycle only when the cycle clock rolls over.

**Budget levels.** Caps nest: an experiment can't outspend its cycle, and a cycle can't outspend the day.

- `per_experiment`: tokens and minutes for one attempt. Hitting it ends that attempt as `revert`.
- `per_cycle`: tokens and dollars for the whole cycle. Hitting it skips the remaining experiments and goes straight to the report.
- `per_day` and `per_month`: dollar ceilings across cycles, which matter most in always-on mode.

Dollars are estimated from token counts using a `prices` table in the manifest, which the project keeps up to date. When a budget runs out, `on_exhausted: report` writes the cycle report and carries unfinished proposals to the next cycle. `pause` also stops future cycles until a human resumes them.

**Community-triggered runs** have their own rate limit per user, so a flood of requests can't drain the budget. Triage is cheap and runs for everyone; experiments only run for proposals the propose stage has picked.

---

## 7. Ownership and funding

Every loop has an owner who pays for it and holds the keys to its manifest. The `funding` block lets a loop add sponsors or move to public configuration later without changing anything else.

| Model | Who pays | Who can change budgets, gates and evaluators | Fits |
| --- | --- | --- | --- |
| `owner` | One team, from its own model keys | The owner's approvers | Most projects, private projects |
| `sponsored` | The owner plus named sponsors, each with a capped pool | The owner's approvers; sponsors fund but can't reconfigure | Open-source projects with backers |
| `pooled` | A shared public pool | A public governance body, such as a DAO or a community vote | Community-run projects |

```yaml
funding:
  model: sponsored
  approvers: ["@acme/maintainers"]
  pools:
    - id: core-team
      cap: { usd_per_month: 1500 }
    - id: sponsor-globex
      cap: { usd_per_month: 300 }
      only: [prove]          # this pool pays for experiments only
```

- Pools are drawn on in the order listed, and every ledger entry records which pool paid.
- Changing `funding`, `budget`, `gates` or `evaluators` is a manifest change. It always needs the named approvers, never an agent.
- Each cycle report shows spend per pool, so every funder sees what they paid for.
- New funding models plug in as adapters. The core only needs each pool's cap and what it has spent.

**Pooled loops are governed publicly.** Approvers are an adapter, like everything else. In an `owner` loop they are the repo's code owners. In a `pooled` loop they are a public governance body, and a manifest change only merges once that body's decision is recorded against the PR. Loopy checks that the decision exists and matches the change; it doesn't run the vote.

---

## 8. Gates and governance

The decide job runs after every experiment and applies the gates in order; the first one that fails decides the verdict. It MUST be plain, deterministic code in a normal workflow, not an agent. A reference implementation is [`tools/decide.py`](tools/decide.py).

1. **Frozen paths untouched.** If the diff touches a `frozen` path, the verdict is `revert`.
2. **Budget respected.** If the experiment went over `per_experiment`, the verdict is `revert`.
3. **Required evaluators pass.** Any failing `required: true` evaluator means `revert`.
4. **No regression.** If any evaluator with a `tolerance` drops by more than it allows, the verdict is `revert`.
5. **Primary improves.** If the primary metric does not beat the current version, the verdict is `revert`. In pareto mode this gate is replaced by the trade-off rule below.
6. **Human sign-off.** If the diff touches a `human_signoff` path, the verdict is `needs-human` and the PR waits for a code owner's approval.
7. Otherwise the verdict is `keep`.

**Trading quality for cost.** Some loops, such as choosing which model runs each agent, are judged on two numbers at once. A cheaper model that is almost as good can be the right pick, and a single primary metric can't say so. Setting `keep_if: required_pass and pareto_improves` turns gate 5 into a trade-off rule against a second, cost evaluator:

```yaml
gates:
  primary: judge-dev
  keep_if: required_pass and pareto_improves
  pareto:
    cost: cost-per-task        # an evaluator, usually dollars or tokens per task
    max_primary_loss: 0.3      # in primary metric units
    min_cost_saving: 0.4       # as a fraction of the current cost
```

The change is kept if it is better on the primary and no worse on cost, cheaper and no worse on the primary, or gives up no more than `max_primary_loss` for a saving of at least `min_cost_saving`. Anything else is `revert`. The cost evaluator is re-run by the decide job like any other; the runner's own token count is never used. Gate 4 still applies first, so a `tolerance` on the primary caps every trade. Cost evaluators SHOULD average over enough runs that noise can't pass as a saving.

**LLM judges are evaluators, so humans own them.** When a loop is scored by a model grading outputs against a rubric, the judge's model, version, prompt and rubric MUST sit inside a frozen evaluator. Otherwise agents learn to please the judge, and scores move whenever the judge changes. Upgrading the judge is a manifest change for the approvers, and the sealed set should be scored with both judges for one cycle so the trend line holds.

**Sealed evaluators fight overfitting.** A loop that tests the same dev set thousands of times will learn that set rather than improve. Sealed evaluators run once per cycle, at report time, on data the agents never see. If the sealed score falls while the dev score rises, the report flags it and the next cycle starts from the last version that held up.

**Sealed sets are retired on a schedule.** Every sealed score leaks a little information, even to a loop that never sees the data. Each sealed set is retired after 10 scorings, or at once if a leak is suspected. Its replacement comes from a reserve no agent has ever been shown. For one cycle, both sets are scored side by side so the trend line doesn't jump.

**Defaults that stay on:**

- Agents work in draft PRs; `auto_merge` is off by default. When it's on, it only ever applies to `keep` verdicts on non-protected paths.
- Agents can never merge their own changes to `frozen` or `human_signoff` paths. Branch protection and `CODEOWNERS` enforce this, so it holds even if Loopy has a bug.
- Agents never publish packages, cut releases or touch secrets. A release is always a human action.
- Network access is an allowlist per stage. The prove stage gets package registries only.
- Every agent action goes through the runner's restricted write channel (safe outputs in gh-aw), never a raw write token.

**Recipes.** [`examples/`](examples/) holds manifests for common loops. Two cover software factories: [`self-improve-skills.yml`](examples/self-improve-skills.yml) has agents score past conversations with a pinned judge and edit only their own skills, and [`model-benchmark.yml`](examples/model-benchmark.yml) replays past conversations against different model selections and keeps a swap with the pareto gate. Self-improvement raises quality; benchmarking lowers cost.

---

## 9. Running on GitHub Agentic Workflows

The GitHub binding maps `loopy.yml` onto five workflow files: four agent stages in [GitHub Agentic Workflows](https://github.github.com/gh-aw/) (gh-aw) and one deterministic decide job in plain Actions. Reference templates live in [`templates/gh-aw/`](templates/gh-aw/). gh-aw is in public preview, so check the templates against the gh-aw version you run and pin it.

| Loopy stage | Workflow | Trigger | Allowed writes (safe outputs) | Limits from the manifest |
| --- | --- | --- | --- | --- |
| Listen + triage | `loopy-listen.md` | cycle clock; issues labelled `loopy:request` (always on) | `add-labels`, `add-comment`, `create-issue` | `max-turns`, per-user rate limit |
| Propose | `loopy-propose.md` | dispatched by listen | `create-issue` (proposal), `dispatch-workflow` | per-cycle share |
| Prove | `loopy-prove.md` | dispatched once per picked proposal | `create-pull-request` (draft), `add-comment` | `per_experiment` → `timeout-minutes` |
| Decide | `loopy-decide.yml` (plain Actions, no agent) | a `loopy/*` PR labelled `loopy:experiment` opens or updates | labels `loopy:keep` / `loopy:revert` / `loopy:needs-human`, closes reverted PRs | none: no model calls |
| Report | `loopy-report.md` | cycle clock, or budget exhausted | `create-discussion` (cycle report), `create-pull-request` (ledger, lessons, feed) | small fixed share |

**Decide runs in two jobs.** The first checks out the current version and the candidate with a read-only token and no secrets, and re-runs the non-sealed evaluators on both; the agent's own numbers are never used. The second never runs candidate code: it works out the diff from git itself, so a candidate can't hide a frozen path, applies the gates with `tools/decide.py`, and labels the PR. Evaluators still execute the candidate's code, so keep them free of secrets and network access they don't need.

**Labels are the state machine.** `loopy:signal` → `loopy:proposal` → `loopy:experiment` → `loopy:keep` or `loopy:revert` → `loopy:shipped`, plus `loopy:needs-human`, `loopy:request` for public intake and `loopy:source/<id>` on every signal. The full set is in [`templates/labels.yml`](templates/labels.yml). A GitHub Projects board with one column per stage mirrors the labels, and any other board can be built from them.

**Pinned versions.** Each Loopy release pins one gh-aw version and is tested against it. The compiled `.lock.yml` files are committed, so a gh-aw update never silently changes a running loop. Projects can pin an older one in `runner.version`.

---

## 10. Public intake and boards

The public reaches a loop through intake, and watches it through a board. Both are adapters; the core needs neither, and a day-one loop runs on the files and the feed.

1. **Intake.** People submit a feature request, feedback, a paper or an integration through an intake form, a GitHub issue form, or by creating a task card. They sign in first, so every request has a real author and a per-person rate limit.
2. **Triage.** The intake adapter turns each submission into a Signal. The triage agent merges duplicates, scores it, replies to the author and adds it to the next cycle.
3. **Board.** Every signal, proposal and experiment appears on a read-only public board, one column per stage: Listen, Propose, Prove, Ship. On day one that board is drawn from the feed on the project's own site.

Intake can come from anywhere that can create a record: a form on the site, a task card in any board tool, an email address, or a GitHub issue form. Each is a source adapter writing the same Signal.

---

## 11. The public feed

The report stage publishes one JSON file per project, the Loopy feed ([`schema/feed.schema.json`](schema/feed.schema.json)). Any website can draw a live loop, a cycle board, a changelog or a request list from it.

| Field | Holds |
| --- | --- |
| `cycle` | Number, start, end, current stage, budget used against cap |
| `signals` | Counts by source this cycle, plus the latest few signals |
| `events` | Recent agent and maintainer actions, newest first |
| `board` | Every open item with its stage, source, links and progress |
| `changelog` | Every shipped change: cycle, title, source, PR, proposal |
| `metrics` | Primary and sealed evaluator scores per cycle |
| `requests` | Top community requests with votes and status |

The feed is regenerated at the end of each stage and published to GitHub Pages or a data branch. It MUST hold only public data: nothing from private issues and no token or cost detail beyond the budget totals.

Projects that run Loopy can show it with a badge: **Autonomously improving with loopy**, or the compact **In the loop**. See [`brand/`](brand/).

---

## 12. Conformance

A project can say it runs Loopy at a level once it meets every requirement for that level.

| Level | Name | Requires |
| --- | --- | --- |
| L1 | Loop | Valid manifest, append-only ledger, at least one evaluator, deterministic keep-or-revert, hard budget caps |
| L2 | Governed | Frozen paths enforced, required evaluators, human sign-off paths, every change linked to its signals |
| L3 | Open | Public feed, community intake, a public board |
| L4 | Learning | Lessons file, sealed evaluators, a cycle review that tunes the loop's own prompts within budget (never its evaluators) |

---

## 13. Roadmap

1. **v0.1** (this spec): manifest and record schemas, reference decide gate, gh-aw templates, brand kit. First deployments: Smartware and expresso, both weekly.
2. **v0.2**: the `loopy` CLI (`init`, `validate`, `cycle`), built-in adapters and the feed generator.
3. **v0.3**: sealed-set rotation tooling and lessons review, taking first deployments to L4.
4. **v0.4**: Claude Code and Codex runners, sponsored and pooled funding, read-only public board sinks.

Releases of Loopy itself are signed and published by a human, never by a loop. The first approvers on this repo are the Techno Ventures team.
