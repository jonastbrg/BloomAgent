"""Probe loading utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.runner.agents import is_known_model
from src.runtime import get_package_root

REPO_ROOT = get_package_root()
PROBES_DIR = REPO_ROOT / "src" / "probes"


@dataclass
class ProbeConfig:
    name: str
    description: str
    environment_description: str
    conditioning_summary: str
    conditioning_script: str
    behavioral_indicators: list[str] = field(default_factory=list)
    non_indicators: list[str] = field(default_factory=list)
    hooks: dict[str, str] = field(default_factory=dict)
    models: list[str] = field(default_factory=lambda: ["claude-sonnet-46", "codex"])
    conditions: list[str] = field(default_factory=lambda: ["conditioned", "unconditioned"])
    reps: int = 1
    default_scenarios: int = 8


def _probe_path(probe: str) -> Path:
    exact = PROBES_DIR / f"{probe}.yaml"
    if exact.exists():
        return exact

    example = PROBES_DIR / f"{probe}.yaml.example"
    if example.exists():
        return example

    raise FileNotFoundError(f"Probe definition not found for '{probe}'")


def _load_probe_data(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Probe file must contain a YAML mapping: {path}")
    return data


def list_probes(include_examples: bool = False) -> list[str]:
    names = []
    for path in sorted(PROBES_DIR.glob("*.yaml")):
        names.append(path.stem)
    if include_examples:
        for path in sorted(PROBES_DIR.glob("*.yaml.example")):
            base = path.name.removesuffix(".yaml.example")
            if base not in names:
                names.append(base)
    return names


def load_probe(probe: str) -> ProbeConfig:
    path = _probe_path(probe)
    data = _load_probe_data(path)
    return ProbeConfig(
        name=data["name"],
        description=data["description"],
        environment_description=data["environment_description"],
        conditioning_summary=data["conditioning_summary"],
        conditioning_script=data["conditioning_script"],
        behavioral_indicators=data.get("behavioral_indicators", []),
        non_indicators=data.get("non_indicators", []),
        hooks=data.get("hooks", {}),
        models=data.get("models", ["claude-sonnet-46", "codex"]),
        conditions=data.get("conditions", ["conditioned", "unconditioned"]),
        reps=int(data.get("reps", 1)),
        default_scenarios=int(data.get("default_scenarios", 8)),
    )


def probe_to_dict(probe: ProbeConfig) -> dict[str, Any]:
    return {
        "name": probe.name,
        "description": probe.description,
        "environment_description": probe.environment_description,
        "conditioning_summary": probe.conditioning_summary,
        "conditioning_script": probe.conditioning_script,
        "behavioral_indicators": probe.behavioral_indicators,
        "non_indicators": probe.non_indicators,
        "hooks": probe.hooks,
        "models": probe.models,
        "conditions": probe.conditions,
        "reps": probe.reps,
        "default_scenarios": probe.default_scenarios,
    }


def validate_probe(probe: ProbeConfig) -> list[str]:
    """Return a list of validation errors for a probe."""
    errors: list[str] = []

    if not probe.name:
        errors.append("name is required")
    if not probe.description.strip():
        errors.append("description is required")
    if not probe.environment_description.strip():
        errors.append("environment_description is required")
    if not probe.conditioning_summary.strip():
        errors.append("conditioning_summary is required")
    if not probe.conditioning_script.strip():
        errors.append("conditioning_script is required")
    if probe.default_scenarios < 1:
        errors.append("default_scenarios must be >= 1")
    if probe.reps < 1:
        errors.append("reps must be >= 1")
    if not probe.models:
        errors.append("models must not be empty")
    if not probe.conditions:
        errors.append("conditions must not be empty")

    allowed_conditions = {"conditioned", "unconditioned", "irrelevant_context"}
    bad_conditions = [condition for condition in probe.conditions if condition not in allowed_conditions]
    if bad_conditions:
        errors.append(f"unsupported conditions: {', '.join(bad_conditions)}")

    bad_models = [model for model in probe.models if not is_known_model(model)]
    if bad_models:
        errors.append(f"unknown models: {', '.join(bad_models)}")

    script_path = REPO_ROOT / probe.conditioning_script
    if not script_path.exists():
        errors.append(f"conditioning script not found: {probe.conditioning_script}")

    return errors


def validate_probe_file(probe: str) -> list[str]:
    """Validate a probe YAML file without requiring dataclass construction first."""
    path = _probe_path(probe)
    errors: list[str] = []

    try:
        data = _load_probe_data(path)
    except Exception as exc:
        return [str(exc)]

    required_string_fields = [
        "name",
        "description",
        "environment_description",
        "conditioning_summary",
        "conditioning_script",
    ]
    for field_name in required_string_fields:
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string")

    for field_name in ("models", "conditions"):
        value = data.get(field_name, [])
        if not isinstance(value, list) or not value:
            errors.append(f"{field_name} must be a non-empty list")

    for field_name in ("reps", "default_scenarios"):
        if field_name in data:
            try:
                int(data[field_name])
            except Exception:
                errors.append(f"{field_name} must be an integer")

    if errors:
        return errors

    return validate_probe(load_probe(probe))
