---
# Loopy stage 1: Listen + triage. Reference template, see README.md.
on:
  schedule:
    - cron: "17 21 * * *"        # daily; the stage exits early unless a new cycle or new signals are due
  issues:
    types: [opened, labeled]     # always-on intake for issues labelled loopy:request
  workflow_dispatch:
permissions:
  contents: read
  issues: read
engine: claude
timeout-minutes: 15
network:
  allowed: [defaults]
tools:
  github:
    toolsets: [issues]
imports:
  - .loopy/shared/rules.md
safe-outputs:
  add-labels:
    allowed: ["loopy:signal", "loopy:needs-human", "loopy:source/requests", "loopy:source/feedback", "loopy:source/research", "loopy:source/market"]
  add-comment:
    max: 20
  create-issue:
    title-prefix: "[signal] "
    labels: ["loopy:signal"]
    max: 10
---

Follow `.loopy/stages/listen.md`.

Triggered by: ${{ github.event_name }}. If this run came from an issue, triage only issue #${{ github.event.issue.number }}, and only if it carries the `loopy:request` label. Respect `budget.per_user` in `loopy.yml` for its author.
