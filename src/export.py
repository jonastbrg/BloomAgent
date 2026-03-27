"""Export BloomAgent artifacts into a BLOOM-like bundle."""

from __future__ import annotations

import json
from pathlib import Path

from src.runtime import get_exports_dir, get_results_dir, get_runtime_root


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text())


def _collect_trials(probe: str) -> list[dict]:
    repo_root = get_runtime_root()
    results_dir = get_results_dir()
    trials: list[dict] = []
    for trace_path in sorted((results_dir / probe).rglob("trace.json")):
        trial_dir = trace_path.parent
        judgment_path = trial_dir / "judgment.json"
        trace = _load_json(trace_path)
        judgment = _load_json(judgment_path) if judgment_path.exists() else None
        trials.append(
            {
                "trial_id": f"{trace.get('probe')}/{trace.get('model')}/s{int(trace.get('scenario', 0)):03d}_r{int(trace.get('rep', 0)):02d}/{trace.get('condition')}",
                "probe": trace.get("probe"),
                "model": trace.get("model"),
                "scenario": trace.get("scenario"),
                "rep": trace.get("rep"),
                "condition": trace.get("condition"),
                "trace_path": str(trace_path.relative_to(repo_root)),
                "judgment_path": str(judgment_path.relative_to(repo_root)) if judgment_path.exists() else None,
                "success": trace.get("success"),
                "transcript": {
                    "metadata": {
                        "source": "BloomAgent export adapter",
                        "probe": trace.get("probe"),
                        "model": trace.get("model"),
                        "condition": trace.get("condition"),
                    },
                    "events": [
                        {
                            "type": "artifact",
                            "name": "trigger_prompt",
                            "content": trace.get("trigger_prompt", ""),
                        },
                        {
                            "type": "artifact",
                            "name": "agent_summary",
                            "content": trace.get("agent_summary", ""),
                        },
                        {
                            "type": "artifact",
                            "name": "git_diff",
                            "content": trace.get("git_diff", ""),
                        },
                    ],
                },
                "judgment": judgment,
            }
        )
    return trials


def export_probe_bundle(probe: str, output_dir: str | Path | None = None) -> Path:
    source_dir = get_results_dir() / probe
    if not source_dir.exists():
        raise FileNotFoundError(f"No results found for probe: {probe}")

    destination = Path(output_dir) if output_dir else get_exports_dir() / probe
    destination.mkdir(parents=True, exist_ok=True)

    understanding_path = source_dir / "understanding.json"
    ideation_path = source_dir / "ideation.json"
    if understanding_path.exists():
        (destination / "understanding.json").write_text(json.dumps(_load_json(understanding_path), indent=2))
    if ideation_path.exists():
        (destination / "ideation.json").write_text(json.dumps(_load_json(ideation_path), indent=2))

    trials = _collect_trials(probe)
    bundle = {
        "probe": probe,
        "source": "BloomAgent",
        "trial_count": len(trials),
        "trials": trials,
    }
    (destination / "rollout.json").write_text(json.dumps(bundle, indent=2))
    return destination
