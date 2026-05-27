import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.cli import main
from sim_plane.run_suite import load_suite_definition, run_suite


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

    def test_variant_required_metric_and_threshold_failures_are_reported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            suite_path = root / "suite.json"
            write_base_scenario(scenario_path)
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "strict_suite",
                        "variants": [
                            {
                                "name": "too_strict",
                                "overrides": {},
                                "required_metrics": {
                                    "target_altitude_reached": True
                                },
                                "metric_thresholds": {
                                    "max_altitude_m": {
                                        "min": 50.0
                                    }
                                },
                            }
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
                report_root=None,
            )

            self.assertEqual(report["status"], "failed")
            self.assertIn("below min", report["issues"][0])

    def test_invalid_metric_threshold_shape_fails_before_running(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            suite_path = root / "suite.json"
            write_base_scenario(scenario_path)
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "bad_suite",
                        "variants": [
                            {
                                "name": "bad_threshold",
                                "overrides": {},
                                "metric_thresholds": {
                                    "max_altitude_m": {
                                        "minimum": 3.0
                                    }
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported key minimum"):
                run_suite(
                    scenario_path=scenario_path,
                    suite_path=suite_path,
                    artifact_root=root / "runs",
                    report_root=None,
                )

    def test_sweep_suite_expands_axes_and_runs_variants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            suite_path = root / "suite.json"
            write_base_scenario(scenario_path)
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "sweep_suite",
                        "base_overrides": {
                            "realtime_factor": 0.0,
                            "disturbances": {
                                "seed": 17
                            },
                        },
                        "sweep": {
                            "axes": [
                                {
                                    "name": "alt",
                                    "path": "target_altitude_m",
                                    "values": [3.0, 4.0],
                                },
                                {
                                    "name": "wind_y",
                                    "path": "disturbances.wind.y_mps",
                                    "values": [0.0, -0.1],
                                },
                            ]
                        },
                        "required_metrics": {
                            "target_altitude_reached": True
                        },
                        "metric_thresholds": {
                            "max_altitude_m": {
                                "min": 2.8
                            }
                        },
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
                report_root=None,
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(
                [row["name"] for row in report["rows"]],
                [
                    "alt_3_0_wind_y_0_0",
                    "alt_3_0_wind_y_-0_1",
                    "alt_4_0_wind_y_0_0",
                    "alt_4_0_wind_y_-0_1",
                ],
            )
            self.assertIn("max_horizontal_error_m", report["metric_summary"])

    def test_sweep_suite_rejects_variants_and_sweep_together(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "suite.json"
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "bad_mix",
                        "variants": [{"name": "baseline", "overrides": {}}],
                        "sweep": {
                            "axes": [
                                {
                                    "name": "alt",
                                    "path": "target_altitude_m",
                                    "values": [3.0],
                                }
                            ]
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "either variants or sweep"):
                load_suite_definition(suite_path)

    def test_suite_rejects_duplicate_variant_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "suite.json"
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "duplicate_suite",
                        "variants": [
                            {"name": "same", "overrides": {}},
                            {"name": "same", "overrides": {}},
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicated"):
                load_suite_definition(suite_path)

    def test_suite_rejects_sanitized_variant_name_collisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "suite.json"
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "collision_suite",
                        "variants": [
                            {"name": "a b", "overrides": {}},
                            {"name": "a_b", "overrides": {}},
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "collides after sanitizing"):
                load_suite_definition(suite_path)


if __name__ == "__main__":
    unittest.main()
