# Security

Please report vulnerabilities privately through GitHub's **Report a vulnerability** button on this repo's Security tab. Don't open a public issue.

We take these especially seriously:

- anything that lets an agent edit a frozen path, an evaluator, the gates, the budget or `loopy.yml`
- anything that lets an agent merge its own change, publish a package or read a secret
- a way to make `tools/decide.py` return `keep` for a change that should fail a gate
- a way to exceed a budget cap

Loopy releases are signed and published by a human. No loop, including Loopy's own, ever publishes a package.
