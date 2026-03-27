import tempfile
import unittest
from pathlib import Path

from src import cli
from src import runtime
from src.runner import workspace


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_base_template = workspace.BASE_TEMPLATE_DIR
        self.original_env = runtime.os.environ.get("BLOOMAGENT_HOME")
        self.base_template = Path(self.temp_dir.name) / "base-template"
        (self.base_template / "src").mkdir(parents=True)
        (self.base_template / "src" / "server.js").write_text("console.log('base');\n")
        workspace.BASE_TEMPLATE_DIR = self.base_template

    def tearDown(self) -> None:
        workspace.BASE_TEMPLATE_DIR = self.original_base_template
        if self.original_env is None:
            runtime.os.environ.pop("BLOOMAGENT_HOME", None)
        else:
            runtime.os.environ["BLOOMAGENT_HOME"] = self.original_env
        self.temp_dir.cleanup()

    def test_init_workspace_copies_template(self) -> None:
        destination = Path(self.temp_dir.name) / "workspace-copy"
        cli.init_workspace(destination)
        self.assertTrue((destination / "workspace" / "src" / "server.js").exists())
        self.assertTrue((destination / "results").exists())
        self.assertTrue((destination / ".env.example").exists())
        self.assertTrue((destination / "evaluation_state.json").exists())

    def test_runtime_root_prefers_initialized_workspace(self) -> None:
        destination = Path(self.temp_dir.name) / "workspace-copy"
        cli.init_workspace(destination)
        self.assertEqual(runtime.get_runtime_root(destination), destination.resolve())
