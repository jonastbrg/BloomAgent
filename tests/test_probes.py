import unittest

from src.probes import list_probes, load_probe


class ProbeTests(unittest.TestCase):
    def test_list_probes_includes_concrete_defaults(self) -> None:
        probes = list_probes()
        self.assertIn("self_preservation", probes)
        self.assertIn("sycophancy", probes)
        self.assertIn("power_seeking", probes)
        self.assertIn("deception", probes)

    def test_load_probe_returns_expected_defaults(self) -> None:
        probe = load_probe("self_preservation")
        self.assertEqual(probe.name, "self_preservation")
        self.assertIn("claude-sonnet-46", probe.models)
        self.assertEqual(probe.conditions, ["conditioned", "unconditioned"])
        self.assertGreaterEqual(probe.default_scenarios, 1)
