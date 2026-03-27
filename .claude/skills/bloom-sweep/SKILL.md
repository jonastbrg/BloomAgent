---
name: bloom-sweep
description: "Run BLOOM evaluations at scale across multiple probes, models, and repetitions. Use: /bloom-sweep --probe <name> --models <m1,m2> --scenarios N --reps N [--setup] [--parallel]"
---

# Bloom Sweep — Large-Scale Evaluation Runner

When invoked, run BLOOM evaluations at scale. This is the outer loop — it calls the per-probe pipeline for each probe × model combination, tracks progress, handles failures, and reports completion.

## Arguments

- `--probe <name>` — single probe name, or `all` to sweep all probes in `src/probes/`
- `--models <m1,m2,...>` — comma-separated model names (e.g., `claude-sonnet-46,codex`)
- `--scenarios N` — number of trigger scenarios per probe (passed to ideation stage)
- `--reps N` — number of repetitions per scenario × model × condition (for variance estimation)
- `--setup` — rebuild conditioning workspaces before running (use if first run or workspace stale)
- `--parallel` — run probe × model combinations in parallel (default: sequential)

## Protocol

### 1. Parse and Validate

Parse arguments. If `--probe all`, list all YAML files in `src/probes/` and collect probe names. Validate that all specified models are known. Report sweep plan to user before proceeding:

```
Sweep plan:
  Probes: [list]
  Models: [list]
  Scenarios per probe: N
  Reps per scenario × model × condition: N
  Total trials: N probes × N models × 2 conditions × N scenarios × N reps = X
  Estimated time: ~X minutes
```

Ask user to confirm if total trials > 50.

### 2. Setup Conditioning Workspaces (if --setup)

If `--setup` flag is present, for each probe build the conditioned environment. The correct function name is `build_conditioned_workspace` (not `build_conditioning_workspace`):

```bash
python3 -c "
from src.runner.workspace import build_conditioned_workspace
build_conditioned_workspace('<probe_name>', 'conditioning/<probe_name>/setup.sh')
print('done')
"
```

Run these sequentially — workspace setup touches shared infrastructure.

### 3. Load Progress

Read `evaluation_state.json`. For each probe, determine which stages are already complete. Use `is_trial_complete` to check individual trials. Skip completed stages/trials unless `--force` is specified.

```python
from src.state import is_trial_complete, get_progress
progress = get_progress()
```

### 4. Sweep Loop

Output path schema: `results/{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/`

For each probe in the probe list:

**Sequential mode (default):**
Run each probe to completion before starting the next.

**Parallel mode (--parallel):**
Spawn one subagent per probe × model combination (disjoint result directories). Use `run_in_background: true`.

For each probe × model combination, run the full pipeline:

**4a. Understanding** — if not complete for this probe:

Run `/bloom-understand {probe_name}` directly (you are already the orchestrator).

**4b. Ideation** — if not complete for this probe:

Run `/bloom-ideate {probe_name} --n {scenarios}` directly. This produces a JSON array; scenario IDs are integer indices (0, 1, 2...).

**4c. Rollout** — for this model:

Spawn rollout subagents for pending `scenario × model × condition × rep` trials. Each trial writes to a uniquely named output directory using the path schema above.

For each pending trial, the subagent runs:

```bash
# 1. Setup workspace (positional args: probe, model, scenario_int, rep_int, condition)
python3 -c "
from src.runner.workspace import setup_workspace
ws = setup_workspace('<probe_name>', '<model>', {scenario}, {rep}, '<condition>')
print(ws)
"

# 2. Run agent (positional args: model, prompt, workspace_path; keyword: output_dir)
python3 -c "
from src.runner.agents import run_agent
from pathlib import Path
result = run_agent(
    '<model>',
    '<trigger_task>',
    Path('results/<probe>/<model>/s{scenario:03d}_r{rep:02d}/<condition>/workspace'),
    output_dir=Path('results/<probe>/<model>/s{scenario:03d}_r{rep:02d}/<condition>')
)
print(f'success={result.success} duration={result.duration_s:.1f}s')
"

# 3. Commit agent changes
cd results/<probe>/<model>/s{scenario:03d}_r{rep:02d}/<condition>/workspace && git add -A && git commit -m 'bloom-trial <probe> s{scenario:03d}_r{rep:02d} <model> <condition>' --allow-empty

# 4. Capture trace (positional: probe, model, scenario_int, rep_int, condition, agent_result, ws_path, output_dir)
python3 -c "
from src.runner.traces import capture_trace
from pathlib import Path
trace = capture_trace(
    '<probe_name>', '<model>', {scenario}, {rep}, '<condition>',
    result,
    Path('results/<probe>/<model>/s{scenario:03d}_r{rep:02d}/<condition>/workspace'),
    Path('results/<probe>/<model>/s{scenario:03d}_r{rep:02d}/<condition>')
)
"

# 5. Save state
python3 -c "
from src.state import save_trial
save_trial('<probe_name>', '<model>', {scenario}, {rep}, '<condition>', 'complete')
"
```

Check `evaluation_state.json` (via `is_trial_complete`) before spawning — skip completed trials.

**4d. Judgment** — after rollout completes for this model:

Run `/bloom-judge {probe_name}` directly to score new traces.

### 5. Track Progress

After each probe × model combination completes, update `evaluation_state.json` and print progress:

```
[3/12] probe=<probe_name> model=<model> — complete (18 trials, mean composite: 6.2)
[4/12] probe=<probe_name> model=<model> — running...
```

### 6. Handle Failures

If a probe × model combination fails (rollout errors, missing traces):
- Log the failure with error message
- Mark as `failed` in `evaluation_state.json`
- Continue to the next combination (do not abort sweep)
- Retry failed combinations at end of sweep (max 1 retry)

### 7. Completion Summary

After all combinations finish:

```
Sweep Complete
==============
Probes: N
Models: N
Total trials run: N
  - Complete: N
  - Failed: N (list)
  - Skipped (already done): N

Signal detected:
  - [probe × model combinations with mean composite > 5.0]

Aware-but-proceeding: N total

Run /bloom-analyze for full statistical breakdown and LaTeX tables.
```

## Notes

- Understanding and ideation are per-probe, not per-model. Run them once per probe.
- Rollout and judgment are per-probe × per-model.
- Parallel mode is safe when probes are independent (disjoint result directories).
- Use sequential mode when debugging or when disk I/O is a bottleneck.
- `--reps N` creates N independent rollout trials per scenario × model × condition, useful for variance estimation in the final paper.
- Scenario IDs are integers (array indices into ideation.json), not string slugs.
