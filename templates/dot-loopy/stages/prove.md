# Stage 3: Prove

**Reads:** one picked proposal and its signals, `.loopy/lessons.md`, the code under `targets.editable`.
**Writes:** one draft pull request on a branch named `loopy/<proposal-id>`, labelled `loopy:experiment`.

This is the autoresearch inner loop. Repeat until the primary evaluator beats the current version or you reach `budget.per_experiment`:

1. Make one focused change to editable paths only.
2. Run the non-sealed evaluators from `loopy.yml` exactly as written. Never edit them, the tests they run, or their data.
3. Note what you tried and the numbers, including attempts that made things worse.

Then open a **draft** PR with:

- the final diff (one idea, not a bundle)
- a table of evaluator results you saw: before and after
- links to the proposal and its signals
- tokens and minutes used
- what didn't work, in one or two lines each, so the report stage can turn it into lessons

Your numbers are for humans to read. CI re-runs the evaluators itself and `tools/decide.py` makes the call. Do not merge, approve or label your own PR beyond `loopy:experiment`.
