---
# Loopy stage 3: Prove. Reference template, see README.md.
# Set timeout-minutes to budget.per_experiment.minutes in loopy.yml.
on:
  workflow_dispatch:
    inputs:
      proposal:
        description: "Proposal issue number"
        required: true
permissions:
  contents: read
  issues: read
engine: claude
timeout-minutes: 20
network:
  allowed: [defaults, python, node]   # package registries only
tools:
  edit:
  bash: ["npm test", "npm run", "python -m", "node .loopy/evaluators/"]   # match your evaluator commands
imports:
  - .loopy/shared/rules.md
safe-outputs:
  create-pull-request:
    title-prefix: "[loopy] "
    labels: ["loopy:experiment"]
    draft: true
  add-comment:
    max: 3
---

Follow `.loopy/stages/prove.md` for proposal #${{ github.event.inputs.proposal }}.

Name the branch `loopy/prop-${{ github.event.inputs.proposal }}`. The decide workflow will re-run the evaluators itself and label the PR.
