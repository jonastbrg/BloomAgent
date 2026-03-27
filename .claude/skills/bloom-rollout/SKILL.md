---
name: bloom-rollout
description: "Stage 3 only: run all trials for a probe (spawns parallel subagents). Use: /bloom-rollout <probe_name>"
---

# Bloom Rollout — Trial Execution (Stage 3)

When invoked, execute all trials for the probe. You are the orchestrator — you read the scenario matrix, spawn parallel subagents for independent trials, and track completion. You do NOT run target agents yourself.

## Protocol

### 1. Read Inputs

Read:
- `results/{probe_name}/ideation.json` — scenarios (JSON array; index = scenario ID integer)
- `src/probes/{probe_name}.yaml` — models list, conditions (conditioned/unconditioned), reps per scenario
- `evaluation_state.json` — which trials are already complete (skip them)

Build the trial matrix: every combination of `scenario_index × model × condition × rep`. Scenario IDs are integers (0, 1, 2...) matching array indices in ideation.json.

### 2. Check Completed Trials

For each trial in the matrix, call `is_trial_complete` to skip already-finished work:

```python
from src.state import is_trial_complete
# Returns True if this trial is already in state as 'complete'
done = is_trial_complete('<probe_name>', '<model>', 0, 0, 'conditioned')
```

State key format: `{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}`

Log skipped count to user before proceeding.

### 3. Ensure Conditioning Workspace Exists

Before spawning any conditioned trials, verify `conditioning/{probe_name}/base/` exists. If it does not, build it:

```python
python3 -c "
from src.runner.workspace import build_conditioned_workspace
build_conditioned_workspace('<probe_name>', 'conditioning/<probe_name>/setup.sh')
print('conditioning workspace ready')
"
```

### 4. Spawn Parallel Subagents

Trials with different `scenario × model × condition × rep` combinations write to disjoint directories — they can run in parallel. Spawn all pending trials concurrently, using `run_in_background: true` when there are more than 3.

Output path schema: `results/{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/`

For each trial, spawn:

```
Agent(
  description: "BLOOM trial probe={probe_name} model={model} s{scenario:03d}_r{rep:02d} {condition}",
  prompt: "You are executing a BLOOM behavioral evaluation trial.
    Working directory: /Users/jonathan/Desktop/interp-tools/BloomAgent

    TRIAL:
      Probe: {probe_name}
      Scenario index: {scenario}   (integer, used to index ideation.json array)
      Rep: {rep}
      Model: {model}
      Condition: {condition}  (conditioned | unconditioned)
      Trigger task: {trigger_task from ideation.json[scenario]}
      Output dir: results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/

    STEPS — execute in order:

    1. Setup workspace:
       python3 -c \"
from src.runner.workspace import setup_workspace
ws = setup_workspace('{probe_name}', '{model}', {scenario}, {rep}, '{condition}')
print('workspace:', ws)
\"

    2. Run target agent:
       python3 -c \"
from src.runner.agents import run_agent
from pathlib import Path
result = run_agent(
    '{model}',
    '{trigger_task_escaped}',
    Path('results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/workspace'),
    output_dir=Path('results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}')
)
print(f'success={result.success} duration={result.duration_s:.1f}s timed_out={result.timed_out}')
\"

    3. Commit agent changes in workspace:
       cd results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/workspace && git add -A && git commit -m 'bloom-trial {probe_name} s{scenario:03d}_r{rep:02d} {model} {condition}' --allow-empty

    4. Capture trace:
       python3 -c \"
from src.runner.traces import capture_trace
from src.runner.agents import run_agent
from pathlib import Path
# result and ws_path must be from steps 1-2 above; reassign if needed
trace = capture_trace(
    '{probe_name}', '{model}', {scenario}, {rep}, '{condition}',
    result,
    Path('results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/workspace'),
    Path('results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}')
)
\"

    5. Save completion state:
       python3 -c \"
from src.state import save_trial
save_trial('{probe_name}', '{model}', {scenario}, {rep}, '{condition}', 'complete')
\"

    Verify: results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/trace.json must exist when done.",
  model: "sonnet",
  run_in_background: true
)
```

### 5. Monitor Completion

After spawning, wait for all background subagents. As each completes:
- Verify `results/{probe_name}/{model}/s{scenario:03d}_r{rep:02d}/{condition}/trace.json` exists
- If missing: log failure, retry once with a fresh subagent
- If retry fails: mark trial as `failed` in `evaluation_state.json` and continue

### 6. Update State

After all trials complete (or fail), update `evaluation_state.json`:
- Under `probes.{probe_name}`, set `stage` to `judgment`
- Add `rollout` to `completed_stages`
- Record per-trial statuses under `trials`

### 7. Report

Summarize to user:
- Total trials: N
- Completed: N
- Failed: N (list failed trial IDs if any)
- Trace files written to `results/{probe_name}/`
- Ready for Stage 4: `/bloom-judge {probe_name}`
