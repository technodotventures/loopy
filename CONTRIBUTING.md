# Contributing to Loopy

Loopy improves itself with Loopy, so there are two ways in.

## File a request

Open an issue with the **Loopy request** form. Ideas, feedback, papers and integration requests all count. The triage stage reads every one, merges duplicates, replies, and adds it to the next cycle. You'll see it move across the board as it goes.

## Send a pull request

Small fixes (typos, broken links, schema bugs) are welcome as normal PRs. For anything that changes the protocol itself, open a request first so it can be discussed.

Before you send a PR:

```bash
python tools/validate.py templates/loopy.yml examples/*.yml
python -m unittest discover -s tests
```

## What stays human

Changes to `SPEC.md`, `schema/`, `tools/decide.py` and the `brand/` assets need a review from the Techno Ventures team, whoever (or whatever) wrote them. Releases are always cut and signed by a person.

## Licence

By contributing you agree that your contributions are licensed under [Apache-2.0](LICENSE).
