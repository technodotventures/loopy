# Stage 2: Propose

**Reads:** the top-scoring open signals, `.loopy/lessons.md`, recent cycle reports, the code under `targets.editable`.
**Writes:** Proposals (`schema/records/proposal.schema.json`), as issues labelled `loopy:proposal` or files in `.loopy/proposals/`.

1. Group related signals. One proposal can answer several signals.
2. For each, write:
   - **hypothesis**: what will improve, on which evaluator, by roughly how much, and why you think so
   - **change_plan**: the smallest change that would test the hypothesis
   - **touches**: every path you expect to edit. If any path is outside `targets.editable`, drop the proposal.
   - **needs_signoff**: true if any path matches `gates.human_signoff`
   - **est_tokens**: your honest estimate
3. Check `.loopy/lessons.md`. Don't propose something a lesson says failed, unless you say what is different this time.
4. Pick up to `gates.max_prs_per_cycle` proposals whose estimates fit the cycle budget, best expected gain per token first. Mark them `picked`. Leave the rest `open`.
