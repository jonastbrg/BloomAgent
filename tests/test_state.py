import tempfile
import unittest

from src import runtime
from src import state


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_env = runtime.os.environ.get("BLOOMAGENT_HOME")
        runtime.os.environ["BLOOMAGENT_HOME"] = self.temp_dir.name

    def tearDown(self) -> None:
        if self.original_env is None:
            runtime.os.environ.pop("BLOOMAGENT_HOME", None)
        else:
            runtime.os.environ["BLOOMAGENT_HOME"] = self.original_env
        self.temp_dir.cleanup()

    def test_initialize_probe_and_mark_stage_complete(self) -> None:
        state.initialize_probe(
            "sycophancy",
            scenario_count=8,
            models=["claude-sonnet-46", "codex"],
            conditions=["conditioned", "unconditioned"],
            reps=1,
        )
        probe_state = state.get_probe_state("sycophancy")
        self.assertEqual(probe_state["stage"], "understanding")
        self.assertEqual(probe_state["scenario_count"], 8)

        state.mark_stage_complete("sycophancy", "understanding")
        probe_state = state.get_probe_state("sycophancy")
        self.assertEqual(probe_state["stage"], "ideation")
        self.assertIn("understanding", probe_state["completed_stages"])

    def test_save_trial_updates_completion(self) -> None:
        state.save_trial("deception", "codex", 1, 1, "conditioned", "complete")
        self.assertTrue(state.is_trial_complete("deception", "codex", 1, 1, "conditioned"))
        progress = state.get_progress()
        self.assertEqual(progress["complete"], 1)

    def test_load_state_normalizes_partial_probe_records(self) -> None:
        state_file = runtime.get_state_file()
        state_file.write_text('{"probes":{"sycophancy":{"stage":"rollout"}}}')
        loaded = state.load_state()
        self.assertIn("completed_stages", loaded["probes"]["sycophancy"])
