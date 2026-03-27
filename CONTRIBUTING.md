# Contributing

BloomAgent is a coding-agent-native adaptation of BLOOM concepts. Contributions
should preserve that focus: real coding-agent rollouts in local workspaces,
disk-backed artifacts, and explicit behavioral judgment.

## Development

```bash
pip install -e .
python3 -m unittest discover -s tests -v
```

## Guidelines

- Keep the repo self-contained. Do not add dependencies on machine-specific
  paths or external benchmark checkouts.
- Prefer adding probe-agnostic infrastructure over hard-coding behavior into
  one probe.
- Keep trace capture and judgment artifacts explicit and disk-backed.
- When changing stage contracts, update the Claude skills, docs, and tests in
  the same change.
