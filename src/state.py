"""Evaluation state. Disk-based, resumable."""
import json
from datetime import datetime
from typing import Any

from src.runtime import get_state_file


def _now() -> str:
    return datetime.now().isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "phase": "init",
        "active_probe": None,
        "probes": {},
        "trials": {},
        "pending_judgments": [],
        "last_updated": None,
    }


def _ensure_probe_record(state: dict[str, Any], probe: str) -> dict[str, Any]:
    probes = state.setdefault("probes", {})
    record = probes.setdefault(probe, {})
    if not isinstance(record, dict):
        record = {}
        probes[probe] = record
    record.setdefault("stage", "understanding")
    record.setdefault("completed_stages", [])
    record.setdefault("scenario_count", 0)
    record.setdefault("models", [])
    record.setdefault("conditions", [])
    record.setdefault("reps", 1)
    record.setdefault("last_updated", None)
    return record


def load_state() -> dict:
    state_file = get_state_file()
    if state_file.exists():
        raw = json.loads(state_file.read_text())
        state = _default_state()
        state.update(raw)
        state.setdefault("probes", {})
        state.setdefault("trials", {})
        state.setdefault("pending_judgments", [])
        for probe_name in list(state["probes"].keys()):
            _ensure_probe_record(state, probe_name)
        return state
    return _default_state()


def save_state(state: dict[str, Any]) -> None:
    state["last_updated"] = _now()
    state_file = get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


def initialize_probe(
    probe: str,
    *,
    scenario_count: int = 0,
    models: list[str] | None = None,
    conditions: list[str] | None = None,
    reps: int = 1,
) -> dict[str, Any]:
    state = load_state()
    state["active_probe"] = probe
    probe_state = _ensure_probe_record(state, probe)
    probe_state["scenario_count"] = scenario_count
    probe_state["models"] = models or []
    probe_state["conditions"] = conditions or []
    probe_state["reps"] = reps
    probe_state["last_updated"] = _now()
    save_state(state)
    return state


def get_probe_state(probe: str) -> dict[str, Any]:
    state = load_state()
    return _ensure_probe_record(state, probe)


def mark_stage_complete(probe: str, stage: str) -> dict[str, Any]:
    state = load_state()
    state["active_probe"] = probe
    probe_state = _ensure_probe_record(state, probe)
    if stage not in probe_state["completed_stages"]:
        probe_state["completed_stages"].append(stage)
    probe_state["stage"] = _next_stage(stage)
    probe_state["last_updated"] = _now()
    state["phase"] = probe_state["stage"]
    save_state(state)
    return state


def set_probe_metadata(
    probe: str,
    *,
    scenario_count: int | None = None,
    models: list[str] | None = None,
    conditions: list[str] | None = None,
    reps: int | None = None,
) -> dict[str, Any]:
    state = load_state()
    probe_state = _ensure_probe_record(state, probe)
    if scenario_count is not None:
        probe_state["scenario_count"] = scenario_count
    if models is not None:
        probe_state["models"] = models
    if conditions is not None:
        probe_state["conditions"] = conditions
    if reps is not None:
        probe_state["reps"] = reps
    probe_state["last_updated"] = _now()
    save_state(state)
    return state


def register_pending_judgment(trial_id: str) -> dict[str, Any]:
    state = load_state()
    pending = state.setdefault("pending_judgments", [])
    if trial_id not in pending:
        pending.append(trial_id)
    save_state(state)
    return state


def clear_pending_judgment(trial_id: str) -> dict[str, Any]:
    state = load_state()
    state["pending_judgments"] = [item for item in state.get("pending_judgments", []) if item != trial_id]
    save_state(state)
    return state


def _next_stage(stage: str) -> str:
    order = {
        "understanding": "ideation",
        "ideate": "rollout",
        "ideation": "rollout",
        "rollout": "judgment",
        "judgment": "complete",
        "complete": "complete",
    }
    return order.get(stage, stage)


def save_trial(probe, model, scenario, rep, condition, status):
    state = load_state()
    state["active_probe"] = probe
    probe_state = _ensure_probe_record(state, probe)
    key = f"{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}"
    state["trials"][key] = {
        "status": status,
        "timestamp": _now(),
    }
    probe_state["last_updated"] = _now()
    if status == "complete":
        register = False
    else:
        register = status in {"needs_judgment", "judging"}
    if register:
        pending = state.setdefault("pending_judgments", [])
        if key not in pending:
            pending.append(key)
    elif key in state.get("pending_judgments", []):
        state["pending_judgments"] = [item for item in state["pending_judgments"] if item != key]
    save_state(state)


def is_trial_complete(probe, model, scenario, rep, condition) -> bool:
    state = load_state()
    key = f"{probe}/{model}/s{scenario:03d}_r{rep:02d}/{condition}"
    return state.get("trials", {}).get(key, {}).get("status") == "complete"


def get_progress() -> dict:
    state = load_state()
    trials = state.get("trials", {})
    complete = sum(1 for t in trials.values() if t["status"] == "complete")
    return {"total": len(trials), "complete": complete, "remaining": len(trials) - complete}
