"""Small CLI for local BloomAgent repo setup and inspection."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from src.export import export_probe_bundle
from src.probes import list_probes, load_probe, validate_probe_file
from src.runner.workspace import build_conditioned_workspace, get_template_dir
from src.smoke import run_smoke_evaluation
from src.state import load_state


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

    validate_parser = subparsers.add_parser("validate-probe", help="Validate one probe or all bundled probes")
    validate_parser.add_argument("probe", nargs="?", default="all")

    state_parser = subparsers.add_parser("state", help="Inspect evaluation state")
    state_parser.add_argument("--json", action="store_true", help="Print raw JSON")

    setup_parser = subparsers.add_parser("setup-conditioning", help="Build conditioned workspaces for one probe or all")
    setup_parser.add_argument("probe", nargs="?", default="all")

    smoke_parser = subparsers.add_parser("smoke-eval", help="Run a deterministic smoke evaluation for one probe")
    smoke_parser.add_argument("probe", help="Probe name")
    smoke_parser.add_argument("--model", help="Optional model override")

    export_parser = subparsers.add_parser("export-bloom", help="Export probe artifacts into a BLOOM-like bundle")
    export_parser.add_argument("probe", help="Probe name")
    export_parser.add_argument("--output-dir", help="Optional export destination")

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

    if args.command == "validate-probe":
        probes = list_probes() if args.probe == "all" else [args.probe]
        failed = False
        for probe_name in probes:
            errors = validate_probe_file(probe_name)
            if errors:
                failed = True
                print(f"{probe_name}: INVALID")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"{probe_name}: OK")
        return 1 if failed else 0

    if args.command == "state":
        state = load_state()
        if args.json:
            print(json.dumps(state, indent=2))
        else:
            print(f"phase: {state.get('phase')}")
            print(f"active_probe: {state.get('active_probe')}")
            print(f"probes: {len(state.get('probes', {}))}")
            print(f"trials: {len(state.get('trials', {}))}")
            print(f"pending_judgments: {len(state.get('pending_judgments', []))}")
        return 0

    if args.command == "setup-conditioning":
        probes = list_probes() if args.probe == "all" else [args.probe]
        for probe_name in probes:
            probe = load_probe(probe_name)
            build_conditioned_workspace(probe.name, probe.conditioning_script)
            print(f"conditioned workspace ready: {probe.name}")
        return 0

    if args.command == "smoke-eval":
        result = run_smoke_evaluation(args.probe, model=args.model)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "export-bloom":
        destination = export_probe_bundle(args.probe, output_dir=args.output_dir)
        print(f"exported to: {destination}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
