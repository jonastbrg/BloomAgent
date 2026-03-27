"""Probe loading utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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
    data = yaml.safe_load(path.read_text()) or {}
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
