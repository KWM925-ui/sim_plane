import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sim_plane.artifacts import build_artifact_dir
from sim_plane.cli import main
import sim_plane.run_suite as run_suite_module
from sim_plane.run_suite import load_suite_definition, run_suite, write_suite_report
from sim_plane.quadrotor_exam import run_quadrotor_exam
from sim_plane.scenario import normalize_scenario


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
    def test_suite_waits_for_registered_output_threads_before_completion(self):
        class ThreadedBackend:
            def validate_environment(self, scenario):
                return []

            def run(self, scenario, sink):
                def emit_late_event():
                    time.sleep(0.02)
                    sink.emit_event("info", "late backend event")

                thread = threading.Thread(target=emit_late_event)
                sink.register_background_thread(thread)
                thread.start()
                return {
                    "status": "passed",
                    "backend": "demo",
                    "vehicle": "quadrotor",
                    "scenario_name": scenario["name"],
                    "metrics": {},
                }

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "sim_plane.runner.get_backend",
            return_value=ThreadedBackend(),
        ):
            outcome = run_suite_module.run_scenario_data(
                normalize_scenario({"name": "threaded_suite_probe"}),
                artifact_root=Path(tmpdir),
                runtime_options={},
            )
            events = [
                json.loads(line)
                for line in (Path(outcome["artifact_dir"]) / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]

        self.assertTrue(any(event["message"] == "late backend event" for event in events))

    def test_artifact_dir_uses_collision_resistant_stamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = build_artifact_dir(tmpdir, "same_name")
            first.mkdir(parents=True)
            second = build_artifact_dir(tmpdir, "same_name")

            self.assertNotEqual(first, second)
            self.assertRegex(first.name, r"same_name_\d{8}_\d{6}_\d{6}")

    def test_artifact_dir_sanitizes_path_separators(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = build_artifact_dir(tmpdir, "bad/name with spaces")

            self.assertEqual(artifact_dir.parent, Path(tmpdir))
            self.assertRegex(artifact_dir.name, r"bad_name_with_spaces_\d{8}_\d{6}_\d{6}")

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
            self.assertIn("kpi_altitude_mae_m", wind_row["metrics"])
            self.assertIn("max_horizontal_error_m", report["metric_summary"])
            self.assertIn("kpi_altitude_mae_m", report["kpi_rankings"])
            self.assertEqual(report["factor_analysis"], {})
            self.assertTrue(Path(report["saved_report"]["report_json"]).exists())

    def test_suite_report_pruning_preserves_protected_reference_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_root = root / "suites"
            protected_dir = report_root / "paper_quadrotor_exam_suite_20250101_000000_000000"
            stale_dir = report_root / "paper_quadrotor_exam_suite_20250101_000001_000000"
            newest_dir = report_root / "paper_quadrotor_exam_suite_20250101_000002_000000"
            for directory in (protected_dir, stale_dir, newest_dir):
                directory.mkdir(parents=True)
                (directory / "report.json").write_text("{}", encoding="utf-8")

            saved = write_suite_report(
                {
                    "suite_name": "paper_quadrotor_exam_suite",
                    "base_scenario": "scenario.json",
                    "artifact_root": str(root / "runs"),
                    "status": "passed",
                    "issues": [],
                    "rows": [],
                    "metric_summary": {},
                },
                report_root=report_root,
                keep_last=1,
                protected_report_dirs=[protected_dir],
            )

            self.assertTrue(protected_dir.exists())
            self.assertFalse(stale_dir.exists())
            self.assertFalse(newest_dir.exists())
            self.assertIn(str(protected_dir.resolve()), saved["protected_report_dirs"])
            self.assertIn(str(stale_dir), saved["pruned_report_dirs"])

    def test_suite_report_pruning_preserves_acceptance_matrix_reference_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            config_root = repo_root / "configs"
            report_root = repo_root / "runs" / "suites"
            protected_dir = report_root / "paper_quadrotor_exam_suite_20250101_000000_000000"
            stale_dir = report_root / "paper_quadrotor_exam_suite_20250101_000001_000000"
            config_root.mkdir(parents=True)
            for directory in (protected_dir, stale_dir):
                directory.mkdir(parents=True)
                (directory / "report.json").write_text("{}", encoding="utf-8")
            (config_root / "quadrotor_exam_acceptance_matrix.json").write_text(
                json.dumps(
                    {
                        "reference_report": (
                            "runs/suites/"
                            "paper_quadrotor_exam_suite_20250101_000000_000000/"
                            "report.json"
                        )
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(run_suite_module, "REPO_ROOT", repo_root):
                saved = write_suite_report(
                    {
                        "suite_name": "paper_quadrotor_exam_suite",
                        "base_scenario": "scenario.json",
                        "artifact_root": str(repo_root / "runs"),
                        "status": "passed",
                        "issues": [],
                        "rows": [],
                        "metric_summary": {},
                    },
                    report_root=report_root,
                    keep_last=1,
                )

            self.assertTrue(protected_dir.exists())
            self.assertFalse(stale_dir.exists())
            self.assertIn(str(protected_dir.resolve()), saved["protected_report_dirs"])
            self.assertIn(str(stale_dir), saved["pruned_report_dirs"])

    def test_suite_report_pruning_preserves_source_reference_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            config_root = repo_root / "configs"
            report_root = repo_root / "runs" / "suites"
            protected_dir = report_root / "paper_quadrotor_exam_suite_20250101_000000_000000"
            stale_dir = report_root / "paper_quadrotor_exam_suite_20250101_000001_000000"
            config_root.mkdir(parents=True)
            for directory in (protected_dir, stale_dir):
                directory.mkdir(parents=True)
                (directory / "report.json").write_text("{}", encoding="utf-8")
            (config_root / "quadrotor_exam_acceptance_matrix.json").write_text(
                json.dumps(
                    {
                        "reference_report": "baselines/reports/exam/report.json",
                        "source_reference_report": (
                            "runs/suites/"
                            "paper_quadrotor_exam_suite_20250101_000000_000000/"
                            "report.json"
                        ),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(run_suite_module, "REPO_ROOT", repo_root):
                saved = write_suite_report(
                    {
                        "suite_name": "paper_quadrotor_exam_suite",
                        "base_scenario": "scenario.json",
                        "artifact_root": str(repo_root / "runs"),
                        "status": "passed",
                        "issues": [],
                        "rows": [],
                        "metric_summary": {},
                    },
                    report_root=report_root,
                    keep_last=1,
                )

            self.assertTrue(protected_dir.exists())
            self.assertFalse(stale_dir.exists())
            self.assertIn(str(protected_dir.resolve()), saved["protected_report_dirs"])

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

    def test_suite_can_gate_on_kpi_metrics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            suite_path = root / "suite.json"
            write_base_scenario(scenario_path)
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "kpi_suite",
                        "variants": [
                            {
                                "name": "dropout",
                                "overrides": {
                                    "degradations": {
                                        "sensor_dropout": {
                                            "windows": [
                                                {
                                                    "start_s": 5.5,
                                                    "end_s": 6.0,
                                                }
                                            ]
                                        }
                                    }
                                },
                                "required_metrics": {
                                    "degradation_enabled": True
                                },
                                "metric_thresholds": {
                                    "kpi_sensor_dropout_count": {
                                        "min": 1
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

            self.assertEqual(report["status"], "passed")
            self.assertGreater(report["rows"][0]["metrics"]["kpi_sensor_dropout_count"], 0)

    def test_data_stream_sensor_fault_suite_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            write_base_scenario(scenario_path)

            report = run_suite(
                scenario_path=scenario_path,
                suite_path=Path.cwd() / "configs" / "demo_sensor_stream_fault_suite.json",
                artifact_root=root / "runs",
                report_root=root / "suites",
            )

            self.assertEqual(report["status"], "passed")
            rows = {row["name"]: row for row in report["rows"]}
            self.assertGreater(rows["gps_dropout_window"]["metrics"]["gps_dropout_count"], 0)
            self.assertGreater(rows["vio_scale_drift"]["metrics"]["vio_scale_drift_count"], 0)
            self.assertGreater(rows["imu_noise_burst"]["metrics"]["imu_noise_burst_count"], 0)

    def test_quadrotor_exam_writes_success_rate_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            write_base_scenario(scenario_path)

            report = run_quadrotor_exam(
                scenario_path=scenario_path,
                suite_path=Path.cwd() / "configs" / "paper_quadrotor_exam_suite.json",
                artifact_root=root / "runs",
                report_root=root / "suites",
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["exam"]["scene_count"], 8)
            self.assertEqual(report["exam"]["success_rate"], 1.0)

    def test_base_overrides_apply_to_hand_written_variants(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            suite_path = root / "suite.json"
            suite_path.write_text(
                json.dumps(
                    {
                        "name": "base_override_suite",
                        "base_overrides": {
                            "duration_s": 8.0,
                            "disturbances": {
                                "seed": 5
                            },
                        },
                        "variants": [
                            {
                                "name": "baseline",
                                "overrides": {
                                    "disturbances": {
                                        "wind": {
                                            "y_mps": 0.2
                                        }
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

            suite = load_suite_definition(suite_path)

            self.assertEqual(suite["variants"][0]["overrides"]["duration_s"], 8.0)
            self.assertEqual(suite["variants"][0]["overrides"]["disturbances"]["seed"], 5)
            self.assertEqual(suite["variants"][0]["overrides"]["disturbances"]["wind"]["y_mps"], 0.2)

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
            self.assertEqual(report["rows"][0]["factors"][0]["name"], "alt")
            self.assertEqual(report["rows"][0]["factors"][1]["name"], "wind_y")
            self.assertEqual(
                report["factor_analysis"]["alt"]["metric_effects"]["max_altitude_m"]["mean_spread"],
                1.0,
            )
            self.assertGreater(
                report["factor_analysis"]["wind_y"]["metric_effects"]["max_horizontal_error_m"]["mean_spread"],
                0.0,
            )
            self.assertIn(
                {
                    "factor": "wind_y",
                    "path": "disturbances.wind.y_mps",
                    "metric": "max_horizontal_error_m",
                    "mean_spread": 0.7,
                    "mean_min": 0.0,
                    "mean_max": 0.7,
                },
                report["top_metric_effects"],
            )
            self.assertIn("kpi_distance_m", report["kpi_rankings"])
            self.assertEqual(len(report["kpi_rankings"]["kpi_distance_m"]["worst_high"]), 4)

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
