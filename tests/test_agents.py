import unittest

from src.runner.agents import is_known_model, normalize_model_name


class AgentModelTests(unittest.TestCase):
    def test_normalize_model_alias(self) -> None:
        self.assertEqual(normalize_model_name("claude-sonnet-4-6"), "claude-sonnet-46")

    def test_known_models_include_aliases(self) -> None:
        self.assertTrue(is_known_model("claude-sonnet-46"))
        self.assertTrue(is_known_model("claude-sonnet-4-6"))
        self.assertFalse(is_known_model("unknown-model"))
