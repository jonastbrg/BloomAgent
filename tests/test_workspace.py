import tempfile
import textwrap
import unittest
from pathlib import Path

from src.runner import workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)

        self.original_base_template = workspace.BASE_TEMPLATE_DIR
        self.original_results = workspace.RESULTS_DIR
        self.original_conditioning = workspace.CONDITIONING_DIR

        self.base_template = base / "base-template"
        self.results = base / "results"
        self.conditioning = base / "conditioning"

        (self.base_template / "src").mkdir(parents=True)
        (self.base_template / "src" / "server.js").write_text("console.log('base');\n")

        probe_dir = self.conditioning / "self_preservation"
        probe_dir.mkdir(parents=True)
        (probe_dir / "setup.sh").write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                mkdir -p docs
                echo conditioned > docs/note.txt
                """
            )
        )

        workspace.BASE_TEMPLATE_DIR = self.base_template
        workspace.RESULTS_DIR = self.results
        workspace.CONDITIONING_DIR = self.conditioning

    def tearDown(self) -> None:
        workspace.BASE_TEMPLATE_DIR = self.original_base_template
        workspace.RESULTS_DIR = self.original_results
        workspace.CONDITIONING_DIR = self.original_conditioning
        self.temp_dir.cleanup()

    def test_get_template_dir_uses_bundled_base(self) -> None:
        self.assertEqual(workspace.get_template_dir(), self.base_template)

    def test_setup_workspace_builds_conditioned_base_when_missing(self) -> None:
        ws_path = workspace.setup_workspace("self_preservation", "codex", 0, 1, "conditioned")
        self.assertTrue(ws_path.exists())
        self.assertTrue((ws_path / "docs" / "note.txt").exists())
