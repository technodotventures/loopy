# GitHub Agentic Workflows binding

Reference workflows for running a Loopy loop on [GitHub Agentic Workflows](https://github.github.com/gh-aw/) (gh-aw). Four agent stages, plus one deterministic decide job in plain Actions.

| File | Stage | Agent? |
| --- | --- | --- |
| `loopy-listen.md` | Listen + triage | yes |
| `loopy-propose.md` | Propose | yes |
| `loopy-prove.md` | Prove | yes |
| `loopy-decide.yml` | Decide | **no**, plain code |
| `loopy-report.md` | Report | yes |

## Install

1. Copy these files into `.github/workflows/` in your project.
2. Match the schedules to `cadence` in `loopy.yml`, and `timeout-minutes` in `loopy-prove.md` to `budget.per_experiment.minutes`.
3. Run `gh aw compile` and commit the `.md` sources and the generated `.lock.yml` files together.
4. Create the labels in `../labels.yml`.
5. Add your engine's secret (for example `ANTHROPIC_API_KEY` for `engine: claude`) in the repo settings.
6. Protect the default branch and require Code Owner review for frozen paths.

## A note on versions

gh-aw is in public preview and its frontmatter still changes. These templates were written against the October 2026 reference. Pin the gh-aw version you compile with, commit the `.lock.yml` output, and check each key against the [frontmatter](https://github.github.com/gh-aw/reference/frontmatter/) and [safe outputs](https://github.github.com/gh-aw/reference/safe-outputs/) references when you upgrade. The v0.2 `loopy` CLI will generate these files from `loopy.yml` so this is done once, centrally.
