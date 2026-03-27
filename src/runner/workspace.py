"""Workspace setup with deterministic conditioning."""
import os
import shutil
import subprocess
from pathlib import Path

from src.runtime import get_package_root, get_results_dir

PACKAGE_ROOT = get_package_root()
BASE_TEMPLATE_DIR = PACKAGE_ROOT / "templates" / "base-workspace"
CONDITIONING_DIR = PACKAGE_ROOT / "conditioning"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@test.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@test.com",
}

VALID_CONDITIONS = {"conditioned", "unconditioned", "irrelevant_context"}


def get_template_dir() -> Path:
    """Return the bundled base workspace template."""
    if BASE_TEMPLATE_DIR.exists():
        return BASE_TEMPLATE_DIR
    raise FileNotFoundError(f"Workspace template not found: {BASE_TEMPLATE_DIR}")


def setup_workspace(probe: str, model: str, scenario: int, rep: int, condition: str) -> Path:
    """Create workspace for a trial. Returns workspace path."""
    if condition not in VALID_CONDITIONS:
        raise ValueError(f"Unsupported condition: {condition}")

    results_dir = get_results_dir()
    trial_dir = results_dir / probe / model / f"s{scenario:03d}_r{rep:02d}" / condition
    ws_path = trial_dir / "workspace"
    if ws_path.exists():
        return ws_path

    template_dir = get_template_dir()
    if condition == "conditioned":
        source = CONDITIONING_DIR / probe / "base"
        if not source.exists():
            script_path = CONDITIONING_DIR / probe / "setup.sh"
            if script_path.exists():
                build_conditioned_workspace(probe, str(script_path))
    else:  # unconditioned
        source = template_dir

    if condition == "irrelevant_context":
        source = template_dir
    if not source.exists():
        raise FileNotFoundError(f"Source directory not found: {source}")

    shutil.copytree(source, ws_path)
    if condition == "irrelevant_context":
        _overlay_irrelevant_context(probe, ws_path)

    # If source isn't already a git repo, initialize
    if not (ws_path / ".git").exists():
        env = {**os.environ, **GIT_ENV}
        subprocess.run(["git", "init"], cwd=ws_path, capture_output=True, env=env, check=True)
        subprocess.run(["git", "add", "."], cwd=ws_path, capture_output=True, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=ws_path, capture_output=True, env=env, check=True,
        )

    return ws_path


def build_conditioned_workspace(probe: str, conditioning_script: str):
    """One-time: deterministically build the conditioned workspace for a probe.

    Runs a script that applies conditioning changes to the template.
    Result is committed and stored in conditioning/{probe}/base/.
    Run ONCE per probe, not per trial.

    conditioning_script may be relative to the package root or an absolute path.
    """
    base_dir = CONDITIONING_DIR / probe / "base"
    if base_dir.exists():
        shutil.rmtree(base_dir)

    try:
        shutil.copytree(get_template_dir(), base_dir)
        env = {**os.environ, **GIT_ENV}
        subprocess.run(["git", "init"], cwd=base_dir, capture_output=True, env=env, check=True)
        subprocess.run(["git", "add", "."], cwd=base_dir, capture_output=True, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial template"],
            cwd=base_dir, capture_output=True, env=env, check=True,
        )

        script_path = Path(conditioning_script)
        if not script_path.is_absolute():
            script_path = PACKAGE_ROOT / script_path
        if not script_path.exists():
            raise FileNotFoundError(f"Conditioning script not found: {script_path}")

        result = subprocess.run(
            ["bash", str(script_path)], cwd=base_dir,
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Conditioning script failed (rc={result.returncode}):\n{result.stderr}"
            )

        subprocess.run(["git", "add", "-A"], cwd=base_dir, capture_output=True, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Applied conditioning"],
            cwd=base_dir, capture_output=True, env=env, check=True,
        )
        print(f"  Built conditioned workspace: {base_dir}")
    except Exception:
        if base_dir.exists():
            shutil.rmtree(base_dir)
        raise


def _overlay_irrelevant_context(probe: str, ws_path: Path) -> None:
    junk_dir = CONDITIONING_DIR / probe / "junk"
    if not junk_dir.exists():
        return
    for source in junk_dir.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(junk_dir)
        destination = ws_path / "irrelevant_context" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
