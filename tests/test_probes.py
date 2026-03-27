import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.probes import PROBES_DIR, list_probes, load_probe, validate_probe, validate_probe_file


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

    def test_validate_probe_rejects_unknown_model(self) -> None:
        probe = replace(load_probe("self_preservation"), models=["not-a-real-model"])
        errors = validate_probe(probe)
        self.assertTrue(any("unknown models" in error for error in errors))

    def test_validate_probe_file_reports_malformed_yaml(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        original_dir = PROBES_DIR
        try:
            probe_dir = Path(temp_dir.name)
            bad_probe = probe_dir / "bad.yaml"
            bad_probe.write_text("name: bad\ndefault_scenarios: nope\n")
            import src.probes as probes_mod

            probes_mod.PROBES_DIR = probe_dir
            errors = validate_probe_file("bad")
            self.assertTrue(errors)
        finally:
            import src.probes as probes_mod

            probes_mod.PROBES_DIR = original_dir
            temp_dir.cleanup()
