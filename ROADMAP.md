# BloomAgent Roadmap

BloomAgent is intentionally narrower than upstream BLOOM today: it focuses on
real coding-agent behavior in local workspaces. The next capabilities to add
should preserve that focus while borrowing mature ideas from BLOOM.

## Near-Term

- Expand the new `bloomagent` CLI beyond `init`, `list-probes`, and
  `show-probe` into probe validation, rollout setup, and state inspection.
- Add probe validation so malformed YAML fails early before a long rollout.
- Add a first-class `irrelevant_context` builder instead of relying on static
  directories only.
- Add end-to-end smoke tests that verify one miniature rollout path without
  requiring external model APIs.
- Add a sample result bundle under `results/examples/` for documentation and
  regression tests.

## Bloom-Like Capabilities

- Config initialization similar to `bloom init`, but specialized for coding
  agents and the bundled base workspace template.
- Variation dimensions for ideation so one base scenario can spawn multiple
  perturbations, closer to upstream BLOOM's ideation model.
- Multiple rollout modalities:
  local coding-agent CLI,
  API conversation rollout,
  simulated tool environment.
- Transcript export adapters so BloomAgent traces can be converted into a
  BLOOM-like transcript schema for downstream analysis.
- Meta-judgment across multiple traces, not only per-trial scoring.
- Resume and sweep orchestration with explicit retry budgets and failure
  bookkeeping.

## Coding-Agent-Specific Extensions

- Richer trace capture: shell history, file access inventory, permission
  requests, and structured command timelines.
- Workspace snapshots before and after rollout to make behavioral diffs easier
  to inspect.
- Judge-side deception checks that explicitly compare summary claims against
  actual commands and file modifications.
- Support for more coding-agent runtimes beyond Claude, Codex, and Gemini.
- Built-in benchmark templates for webapps, data pipelines, infra repos, and
  monorepo maintenance tasks.

## Sharing Strategy

- Keep BloomAgent as a sibling project while the runtime model is Claude Code
  plus local agent CLIs.
- If upstream collaboration is desired, extract smaller upstreamable pieces:
  probe schema ideas,
  result adapters,
  variation generation logic,
  or analysis improvements.
