---
# Loopy stage 6: Report. Reference template, see README.md.
on:
  schedule:
    - cron: "47 20 * * 0"        # the night before each weekly cycle starts; match your cadence
  workflow_dispatch:
permissions:
  contents: read
  issues: read
  pull-requests: read
engine: claude
timeout-minutes: 30
network:
  allowed: [defaults]
tools:
  edit:
  bash: ["python -m", "node .loopy/evaluators/"]   # sealed evaluator commands
  github:
    toolsets: [issues, pull_requests]
imports:
  - .loopy/shared/rules.md
safe-outputs:
  create-pull-request:
    title-prefix: "[loopy report] "
    labels: ["loopy:report"]
  create-discussion:
    title-prefix: "Loopy cycle "
    category: "announcements"
---

Follow `.loopy/stages/report.md`.

Put the report, lessons and feed changes in one pull request. Post the plain-language summary as a discussion as well.
