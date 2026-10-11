---
# Loopy stage 2: Propose. Reference template, see README.md.
on:
  workflow_dispatch:
permissions:
  contents: read
  issues: read
engine: claude
timeout-minutes: 20
network:
  allowed: [defaults]
tools:
  github:
    toolsets: [issues, pull_requests]
imports:
  - .loopy/shared/rules.md
safe-outputs:
  create-issue:
    title-prefix: "[proposal] "
    labels: ["loopy:proposal"]
    max: 5
  add-comment:
    max: 10
---

Follow `.loopy/stages/propose.md`.

When you have picked proposals, list their issue numbers in your final comment so the maintainers (or a dispatch step) can start one Prove run per proposal.
