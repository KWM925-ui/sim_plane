import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.cli import main
from sim_plane.run_suite import run_suite


def write_base_scenario(path):
    path.write_text(
        json.dumps(
            {
                "name": "suite_demo",
                "backend": "demo",
                "vehicle": "quadrotor",
                "duration_s": 7.0,
                "update_hz": 4.0,
                "target_altitude_m": 5.0,
                "realtime_factor": 0.0,
                "waypoints": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 5.0, "y": 0.0},
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


class RunSuiteTest(unittest.TestCase):
    def test_run_suite_writes_variant_artifacts_and_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            suite_path = root / "suite.json"
            write_base_scenario(scenario_path)
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "test_disturbance_suite",
                        "variants": [
                            {"name": "baseline", "overrides": {}},
                            {
                                "name": "wind",
                                "overrides": {
                                    "disturbances": {
                                        "seed": 3,
                                        "wind": {"x_mps": 0.2, "y_mps": 0.1},
                                    }
                                },
                            },
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            report = run_suite(
                scenario_path=scenario_path,
                suite_path=suite_path,
                artifact_root=root / "runs",
                report_root=root / "suites",
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["rows"]), 2)
            for row in report["rows"]:
                self.assertTrue(Path(row["artifact_dir"]).exists())
                self.assertEqual(row["status"], "passed")
            wind_row = {row["name"]: row for row in report["rows"]}["wind"]
            self.assertTrue(wind_row["metrics"]["disturbance_enabled"])
            self.assertGreater(wind_row["metrics"]["max_horizontal_error_m"], 0.0)
            self.assertIn("max_horizontal_error_m", report["metric_summary"])
            self.assertTrue(Path(report["saved_report"]["report_json"]).exists())

    def test_cli_run_suite_returns_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            write_base_scenario(scenario_path)

            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "run-suite",
                        str(scenario_path),
                        "--artifact-root",
                        str(root / "runs"),
                        "--report-root",
                        str(root / "suites"),
                        "--json",
                    ]
                )

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(len(payload["rows"]), 3)


if __name__ == "__main__":
    unittest.main()
