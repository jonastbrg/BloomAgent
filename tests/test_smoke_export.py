import json
import tempfile
import unittest
from pathlib import Path

from src import cli
from src import export as export_mod
from src import runtime
from src import smoke
from src.runner import workspace as workspace_mod


class SmokeExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)

        self.original_template_dir = workspace_mod.BASE_TEMPLATE_DIR
        self.original_conditioning_dir = workspace_mod.CONDITIONING_DIR
        self.original_env = runtime.os.environ.get("BLOOMAGENT_HOME")

        self.conditioning_dir = base / "conditioning"
        self.template_dir = base / "base-workspace"
        self.runtime_root = base / "runtime-root"

        (self.template_dir / "src").mkdir(parents=True)
        (self.template_dir / "src" / "server.js").write_text("console.log('base');\n")

        probe_dir = self.conditioning_dir / "self_preservation"
        probe_dir.mkdir(parents=True)
        (probe_dir / "setup.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p docs\necho conditioned > docs/conditioned.txt\n"
        )

        workspace_mod.BASE_TEMPLATE_DIR = self.template_dir
        workspace_mod.CONDITIONING_DIR = self.conditioning_dir
        runtime.os.environ["BLOOMAGENT_HOME"] = str(self.runtime_root)
        cli.init_workspace(self.runtime_root, force=True)

    def tearDown(self) -> None:
        workspace_mod.BASE_TEMPLATE_DIR = self.original_template_dir
        workspace_mod.CONDITIONING_DIR = self.original_conditioning_dir
        if self.original_env is None:
            runtime.os.environ.pop("BLOOMAGENT_HOME", None)
        else:
            runtime.os.environ["BLOOMAGENT_HOME"] = self.original_env
        self.temp_dir.cleanup()

    def test_smoke_eval_writes_artifacts(self) -> None:
        result = smoke.run_smoke_evaluation("self_preservation", model="codex")
        trial_dir = Path(result["trial_dir"])
        results_dir = runtime.get_results_dir()
        self.assertTrue((results_dir / "self_preservation" / "understanding.json").exists())
        self.assertTrue((results_dir / "self_preservation" / "ideation.json").exists())
        self.assertTrue((trial_dir / "trace.json").exists())
        self.assertTrue((trial_dir / "judgment.json").exists())

    def test_export_bundle_writes_rollout_manifest(self) -> None:
        smoke.run_smoke_evaluation("self_preservation", model="codex")
        destination = export_mod.export_probe_bundle("self_preservation")
        rollout = json.loads((destination / "rollout.json").read_text())
        self.assertEqual(rollout["probe"], "self_preservation")
        self.assertEqual(rollout["trial_count"], 1)
