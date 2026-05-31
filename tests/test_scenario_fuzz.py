import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.scenario_fuzz import build_fuzz_suite, run_scenario_fuzz


class ScenarioFuzzTest(unittest.TestCase):
    def test_build_fuzz_suite_is_seed_reproducible(self):
        scenario = {"name": "basic_takeoff", "backend": "demo", "target_altitude_m": 10.0}

        first = build_fuzz_suite(scenario, seed=123, variants=3)
        second = build_fuzz_suite(scenario, seed=123, variants=3)

        self.assertEqual(first, second)
        self.assertEqual(len(first["variants"]), 4)
        self.assertEqual(first["variants"][0]["name"], "baseline")
        self.assertIn("degradations", first["variants"][1]["overrides"])

    def test_build_fuzz_suite_rejects_non_demo_profile(self):
        with self.assertRaises(ValueError):
            build_fuzz_suite({"backend": "px4_sih"}, profile="demo_fast")

    def test_run_scenario_fuzz_writes_report_with_worst_cases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario = root / "scenario.json"
            scenario.write_text(
                '{"name":"basic_takeoff","backend":"demo","vehicle":"quadrotor","duration_s":8,"update_hz":5,"target_altitude_m":8,"realtime_factor":0,"waypoints":[]}\n',
                encoding="utf-8",
            )

            report = run_scenario_fuzz(
                scenario,
                seed=321,
                variants=2,
                artifact_root=root / "runs",
                report_root=root / "scenario_fuzz",
            )

            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["worst_cases"])
            self.assertTrue(Path(report["saved_report"]["report_json"]).exists())
            self.assertTrue(Path(report["saved_report"]["generated_suite_json"]).exists())


if __name__ == "__main__":
    unittest.main()
