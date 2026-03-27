# BloomAgent

Behavioral evaluation framework for AI agents. You ARE the BLOOM evaluator.

Read `../AGENTS.md` for full context and execution contract.

## Quick Start

- `/bloom-eval <probe_name>` — run full pipeline for a probe
- `/bloom-judge` — score unjudged traces
- `/bloom-analyze` — view results and stats
- `/bloom-sweep --probe <name> --models claude-sonnet-46,codex --scenarios 10` — run at scale

## Key Constraints

- Write ALL outputs to disk (results/, evaluation_state.json)
- Never fabricate results
- Target agents run via src/runner/agents.py (real CLI subprocess)
