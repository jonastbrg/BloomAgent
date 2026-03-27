"""Small CLI for local BloomAgent repo setup and inspection."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from src.probes import list_probes, load_probe
from src.runner.workspace import get_template_dir


ENV_TEMPLATE = """# Optional CLI credentials for local coding-agent rollouts
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=
# GEMINI_API_KEY=
"""

WORKSPACE_README = """# BloomAgent Workspace

This directory was initialized by `bloomagent init`.

- `workspace/` is the bundled base repository template that target coding agents operate on.
- `results/` stores stage outputs and per-trial artifacts.
- `.env.example` lists optional provider credentials for local agent CLIs.
"""


def init_workspace(destination: str | Path = "bloomagent-workspace", force: bool = False) -> Path:
    """Create a self-contained evaluation workspace scaffold."""
    src = get_template_dir()
    dst = Path(destination)

    if dst.exists():
        if not force:
            raise FileExistsError(f"Destination already exists: {dst}")
        shutil.rmtree(dst)

    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst / "workspace")
    (dst / "results").mkdir()
    (dst / ".env.example").write_text(ENV_TEMPLATE)
    (dst / "README.md").write_text(WORKSPACE_README)
    (dst / "evaluation_state.json").write_text(
        json.dumps(
            {
                "version": 1,
                "phase": "init",
                "active_probe": None,
                "probes": {},
                "trials": {},
                "pending_judgments": [],
                "last_updated": None,
            },
            indent=2,
        )
    )
    return dst


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bloomagent", description="BloomAgent repository helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a clean BloomAgent workspace scaffold")
    init_parser.add_argument("destination", nargs="?", default="bloomagent-workspace")
    init_parser.add_argument("--force", action="store_true", help="Overwrite the destination if it exists")

    subparsers.add_parser("list-probes", help="List bundled behavioral probes")

    show_probe = subparsers.add_parser("show-probe", help="Show probe metadata")
    show_probe.add_argument("probe", help="Probe name")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        dst = init_workspace(args.destination, force=args.force)
        print(f"Initialized BloomAgent workspace at: {dst}")
        print(f"  workspace: {dst / 'workspace'}")
        print(f"  results:   {dst / 'results'}")
        print(f"  env file:  {dst / '.env.example'}")
        return 0

    if args.command == "list-probes":
        for probe in list_probes():
            print(probe)
        return 0

    if args.command == "show-probe":
        probe = load_probe(args.probe)
        print(f"name: {probe.name}")
        print(f"models: {', '.join(probe.models)}")
        print(f"conditions: {', '.join(probe.conditions)}")
        print(f"default_scenarios: {probe.default_scenarios}")
        print(f"conditioning_script: {probe.conditioning_script}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
