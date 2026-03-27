# BloomAgent

Claude Code native agent for behavioral safety evaluation of AI coding agents. It adapts [BLOOM](https://github.com/safety-research/bloom) concepts to real coding-agent rollouts in local workspaces.

## What It Does

Tests whether AI coding agents exhibit emergent unsafe behaviors when operating in realistic development environments. Zero malicious content at any layer — all scenarios are ordinary coding tasks.

```
Claude Code (BLOOM evaluator)
├── Stage 1: Understanding — reasons about the behavioral tendency
├── Stage 2: Ideation — generates diverse trigger scenarios
├── Stage 3: Rollout — spawns real agents (Claude/Codex/Gemini) in real workspaces
└── Stage 4: Judgment — scores execution traces for behavioral presence
```

## Quick Start

```bash
# Clone and enter the repo
cd BloomAgent

# Optional: install editable CLI helper
pip install -e .

# Create a clean local evaluation workspace scaffold
bloomagent init ./my-bloomagent-workspace
cd ./my-bloomagent-workspace

# Show available probes
bloomagent list-probes

# Validate all bundled probes
bloomagent validate-probe all

# Inspect repo state
bloomagent state --json

# Build conditioned workspaces for all probes
bloomagent setup-conditioning all

# Run a deterministic smoke evaluation
bloomagent smoke-eval self_preservation --model codex

# Export one probe into a BLOOM-like bundle
bloomagent export-bloom self_preservation

# Run the full pipeline for a probe
/bloom-eval self_preservation

# Or run individual stages
/bloom-understand sycophancy
/bloom-ideate sycophancy --n 8
/bloom-rollout sycophancy
/bloom-judge sycophancy

# Analyze results
/bloom-analyze

# Run at scale
/bloom-sweep --probe power_seeking --models claude-sonnet-46,codex --scenarios 10
```

`bloomagent init` now creates a clean scaffold with:

```text
my-bloomagent-workspace/
├── workspace/             # bundled base repo for coding-agent rollouts
├── results/               # output directory
├── evaluation_state.json  # initialized empty state
├── .env.example           # optional provider credentials
└── README.md
```

This keeps the project self-contained and avoids external benchmark-template dependencies.

## Installation

```bash
git clone https://github.com/jonastbrg/BloomAgent.git
cd BloomAgent
pip install -e .
```

The repository is self-contained: it ships its own bundled base workspace and probe definitions.

## Status

BloomAgent is currently a working research prototype. The repository now has:

- self-contained workspace initialization,
- bundled probe definitions and conditioning scripts,
- local CLI helpers for setup and inspection,
- tests covering state, probes, workspace setup, model aliases, and CLI init.

The higher-level evaluation orchestration still lives in Claude Code skills rather than a full Python pipeline CLI.

## CLI Commands

- `bloomagent init [path]` creates a clean local workspace scaffold.
- `bloomagent list-probes` lists bundled probes.
- `bloomagent show-probe <probe>` prints probe metadata.
- `bloomagent validate-probe <probe|all>` validates probe YAML and runtime references.
- `bloomagent state [--json]` inspects `evaluation_state.json`.
- `bloomagent setup-conditioning <probe|all>` builds conditioned base workspaces.
- `bloomagent smoke-eval <probe>` runs a deterministic miniature evaluation path.
- `bloomagent export-bloom <probe>` exports results into a BLOOM-like bundle under `exports/bloom/`.

## Behavioral Probes

BLOOM probes are named behavioral tendencies. Each probe targets a specific dimension of unsafe behavior:

| Probe | What It Measures |
|-------|----------------|
| `self_preservation` | Does the agent resist shutdown, correction, or retraining? |
| `sycophancy` | Does the agent adjust stated beliefs to match user preferences over truth? |
| `power_seeking` | Does the agent acquire capabilities or resources beyond what the task requires? |
| `deception` | Does the agent misrepresent its actions or capabilities? |

Probes are YAML definitions in `src/probes/`. Each specifies behavioral dimensions, conditioning, default models, and rollout defaults. The repo ships concrete definitions for `self_preservation`, `sycophancy`, `power_seeking`, and `deception`.

## Output Schema

Stage outputs are written to:

```
results/{probe}/understanding.json
results/{probe}/ideation.json
```

Trial outputs are written to:

```
results/{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/
  ├── workspace/           — git repo the agent operated in
  ├── stdout.txt           — captured agent output
  ├── trigger_prompt.txt   — the prompt sent to the agent
  ├── git_diff.txt         — workspace changes
  ├── trace.json           — structured ExecutionTrace
  └── judgment.json        — behavioral scores and verdict
```

Global trial state is tracked in `evaluation_state.json`.

## Architecture

```
Claude Code (BLOOM evaluator — this session)
  └── Skills (.claude/skills/bloom-*/): bloom-eval, bloom-ideate, bloom-rollout,
  |                                     bloom-judge, bloom-analyze, bloom-sweep
  └── Python utilities (src/)
        ├── src/runner/agents.py     — run_agent(): CLI subprocess runner
        ├── src/runner/workspace.py  — setup_workspace(), build_conditioned_workspace()
        ├── src/runner/traces.py     — capture_trace()
        ├── src/state.py             — save_trial(), is_trial_complete(), load_state()
        ├── src/probes/__init__.py   — load_probe(), list_probes()
        └── src/analysis.py          — aggregation and stats
```

Skills drive the pipeline. Python utilities handle I/O, subprocess management, and state persistence. The evaluator (Claude Code) never writes into traces — it only reads and judges.

The repo includes a bundled base workspace at `templates/base-workspace/`, so installs do not depend on external benchmark repos or machine-specific symlinks.

## Next Steps

The highest-value next work is:

1. Add richer rollout orchestration beyond the current smoke path, especially more deterministic test fixtures and better retry/failure bookkeeping.
2. Add variation dimensions and stronger result interoperability so evaluations become easier to compare with upstream BLOOM.
3. Expand trace richness and multi-runtime support for coding-agent-specific analysis.

See [docs/ROADMAP.md](/Users/jonathan/Desktop/interp-tools/BloomAgent/docs/ROADMAP.md) for the fuller roadmap.

## Contributing

Issues and pull requests are welcome. For larger architectural changes, open an issue first so the coding-agent-native direction stays coherent. See [docs/CONTRIBUTING.md](/Users/jonathan/Desktop/interp-tools/BloomAgent/docs/CONTRIBUTING.md).

## Reference

Built on [BLOOM](https://github.com/safety-research/bloom) by Anthropic Safety Research. See also the [BLOOM paper](https://alignment.anthropic.com/2025/bloom-auto-evals/).

## License

MIT
