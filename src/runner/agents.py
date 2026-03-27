"""Agent CLI runners. Adapted from MOSAIC benchmark/runners/common.py."""
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

MODEL_CONFIGS = {
    "claude-sonnet-46": {"type": "claude", "model_id": "claude-sonnet-4-6"},
    "claude-opus":      {"type": "claude", "model_id": "claude-opus-4-6"},
    "codex":            {"type": "codex",  "model_id": "gpt-5.3-codex"},
    "gemini-pro":       {"type": "gemini", "model_id": "gemini-3.1-pro-preview"},
    "gemini-flash":     {"type": "gemini", "model_id": "gemini-3-flash-preview"},
}

MODEL_ALIASES = {
    "claude-sonnet-4-6": "claude-sonnet-46",
    "claude-opus-4-6": "claude-opus",
}

ALL_MODELS = sorted(set(MODEL_CONFIGS) | set(MODEL_ALIASES))

SUMMARY_INSTRUCTION = (
    "\n\n---\nAfter completing the task, create AGENT_SUMMARY.md documenting: "
    "(1) what you did step by step, (2) commands you ran, (3) files modified, "
    "(4) issues/blockers encountered, (5) decisions and rationale.\n"
)


@dataclass
class AgentResult:
    success: bool
    stdout: str
    stderr: str
    timed_out: bool
    duration_s: float
    return_code: int


def normalize_model_name(model: str) -> str:
    """Accept both canonical repo names and common human-readable aliases."""
    return MODEL_ALIASES.get(model, model)


def is_known_model(model: str) -> bool:
    return normalize_model_name(model) in MODEL_CONFIGS


def run_agent(model: str, prompt: str, workspace: Path, timeout: int = 600,
              output_dir: Path | None = None) -> AgentResult:
    """Run agent CLI, capture full output to files."""
    model = normalize_model_name(model)
    if model not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model: {model}")

    full_prompt = prompt + SUMMARY_INSTRUCTION
    cfg = MODEL_CONFIGS[model]
    runner = {"claude": _run_claude, "codex": _run_codex, "gemini": _run_gemini}[cfg["type"]]

    start = time.time()
    result = runner(full_prompt, workspace, cfg["model_id"], timeout)
    duration = time.time() - start

    agent_result = AgentResult(
        success=result["success"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        timed_out=result["timed_out"],
        duration_s=duration,
        return_code=result["rc"],
    )

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "stdout.txt").write_text(agent_result.stdout)
        (output_dir / "stderr.txt").write_text(agent_result.stderr)
        (output_dir / "trigger_prompt.txt").write_text(prompt)

    return agent_result


def _run_claude(prompt, workspace, model_id, timeout):
    cmd = ["claude", "--dangerously-skip-permissions", "--model", model_id, "-p", prompt]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        r = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout, env=env)
        return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr,
                "timed_out": False, "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "TIMEOUT", "timed_out": True, "rc": -1}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "claude CLI not found", "timed_out": False, "rc": -1}


def _run_codex(prompt, workspace, model_id, timeout):
    cmd = ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
           "-C", str(workspace), "-m", model_id, prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr,
                "timed_out": False, "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "TIMEOUT", "timed_out": True, "rc": -1}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "codex CLI not found", "timed_out": False, "rc": -1}


def _run_gemini(prompt, workspace, model_id, timeout):
    cmd = ["gemini", "-p", prompt, "-y", "-m", model_id]
    try:
        r = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout)
        return {"success": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr,
                "timed_out": False, "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "TIMEOUT", "timed_out": True, "rc": -1}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "gemini CLI not found", "timed_out": False, "rc": -1}
