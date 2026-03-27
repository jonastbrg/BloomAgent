"""Runtime path helpers.

Package assets live in the installed repository. Runtime artifacts should live
in the current BloomAgent workspace when one is active.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def get_package_root() -> Path:
    return PACKAGE_ROOT


def get_runtime_root(cwd: str | Path | None = None) -> Path:
    env_root = os.environ.get("BLOOMAGENT_HOME")
    if env_root:
        return Path(env_root).resolve()

    candidate = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    if (candidate / "evaluation_state.json").exists():
        return candidate

    return PACKAGE_ROOT


def get_results_dir(cwd: str | Path | None = None) -> Path:
    return get_runtime_root(cwd) / "results"


def get_exports_dir(cwd: str | Path | None = None) -> Path:
    return get_runtime_root(cwd) / "exports" / "bloom"


def get_state_file(cwd: str | Path | None = None) -> Path:
    return get_runtime_root(cwd) / "evaluation_state.json"
