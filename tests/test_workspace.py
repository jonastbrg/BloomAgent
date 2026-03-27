import tempfile
import textwrap
import unittest
from pathlib import Path

from src import runtime
from src.runner import workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)

        self.original_base_template = workspace.BASE_TEMPLATE_DIR
        self.original_conditioning = workspace.CONDITIONING_DIR
        self.original_env = runtime.os.environ.get("BLOOMAGENT_HOME")

        self.base_template = base / "base-template"
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
        workspace.CONDITIONING_DIR = self.conditioning
        runtime.os.environ["BLOOMAGENT_HOME"] = self.temp_dir.name

    def tearDown(self) -> None:
        workspace.BASE_TEMPLATE_DIR = self.original_base_template
        workspace.CONDITIONING_DIR = self.original_conditioning
        if self.original_env is None:
            runtime.os.environ.pop("BLOOMAGENT_HOME", None)
        else:
            runtime.os.environ["BLOOMAGENT_HOME"] = self.original_env
        self.temp_dir.cleanup()

    def test_get_template_dir_uses_bundled_base(self) -> None:
        self.assertEqual(workspace.get_template_dir(), self.base_template)

    def test_setup_workspace_builds_conditioned_base_when_missing(self) -> None:
        ws_path = workspace.setup_workspace("self_preservation", "codex", 0, 1, "conditioned")
        self.assertTrue(ws_path.exists())
        self.assertTrue((ws_path / "docs" / "note.txt").exists())

    def test_setup_workspace_rejects_unknown_condition(self) -> None:
        with self.assertRaises(ValueError):
            workspace.setup_workspace("self_preservation", "codex", 0, 1, "typo-condition")

    def test_irrelevant_context_overlays_extra_files(self) -> None:
        junk_dir = self.conditioning / "self_preservation" / "junk"
        junk_dir.mkdir(parents=True)
        (junk_dir / "README.md").write_text("irrelevant\n")
        ws_path = workspace.setup_workspace("self_preservation", "codex", 1, 1, "irrelevant_context")
        self.assertTrue((ws_path / "src" / "server.js").exists())
        self.assertTrue((ws_path / "irrelevant_context" / "README.md").exists())

    def test_failed_conditioning_build_cleans_partial_base(self) -> None:
        bad_probe = self.conditioning / "bad_probe"
        bad_probe.mkdir(parents=True)
        (bad_probe / "setup.sh").write_text("#!/usr/bin/env bash\nexit 1\n")
        with self.assertRaises(RuntimeError):
            workspace.build_conditioned_workspace("bad_probe", str((bad_probe / "setup.sh")))
        self.assertFalse((bad_probe / "base").exists())
