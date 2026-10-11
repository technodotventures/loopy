# Stage 6: Report

**Reads:** this cycle's lines in `.loopy/ledger.jsonl`, its proposals and PRs, the previous report.
**Writes:** `.loopy/cycles/<n>/report.md` and `report.json` (`schema/records/cycle-report.schema.json`), new lines in `.loopy/lessons.md`, the public feed. All in one pull request.

1. Run each sealed evaluator once, on the current default branch. This is the only time sealed evaluators run. Record the scores; never print the sealed data itself.
2. If a sealed score fell while the primary dev score rose this cycle, set `overfit_flag: true` and say so at the top of the report.
3. Write the report in plain language:
   - what shipped, with links, and what it changed on the metrics
   - what was tried and reverted, and why (from the gate trace)
   - what was carried to the next cycle
   - spend against the cycle cap, per pool
4. Add one to three lessons to `.loopy/lessons.md`: specific, testable, with the cycle number. Prefer lessons from reverted experiments; they are the ones the loop would otherwise repeat.
5. Regenerate the feed (`schema/feed.schema.json`) with public data only.
6. Open the PR for a human to merge. If the budget ran out early, say so and stop.
