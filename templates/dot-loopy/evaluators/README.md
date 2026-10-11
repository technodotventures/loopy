# Evaluators

Scripts that score the project. Each one prints a JSON line as its last line of output:

```json
{"metric": "recall@10", "value": 0.734, "pass": true}
```

`pass` is false if the run is broken. A non-zero exit code also counts as a failure.

This folder is frozen. Agents can read these scripts but can never change them. Keep sealed data out of the repo entirely; a sealed evaluator should fetch it from somewhere the agents can't reach.
