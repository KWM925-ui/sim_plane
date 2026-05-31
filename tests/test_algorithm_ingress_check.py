import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.algorithm_ingress_check import build_ingress_report, run_algorithm_ingress_check


class AlgorithmIngressCheckTest(unittest.TestCase):
    def test_ingress_check_reports_adapter_and_kpi_health(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "demo_external_ingress",
                        "description": "external command ingress check on demo backend",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 7.0,
                        "update_hz": 4.0,
                        "target_altitude_m": 4.0,
                        "realtime_factor": 0.0,
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 4.0, "y": 0.0},
                        ],
                        "algorithm_adapter": {
                            "type": "external_command",
                            "command": [
                                "python3",
                                "-c",
                                (
                                    "import json, os; "
                                    "path=os.environ['SIM_PLANE_ADAPTER_RESULT_JSON']; "
                                    "json.dump({'success': True, 'metrics': {'position_cmd_seen': True}}, open(path, 'w'))"
                                ),
                            ],
                            "max_runtime_s": 3.0,
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            report = run_algorithm_ingress_check(
                scenario_path=scenario_path,
                artifact_root=root / "runs",
                report_root=root / "ingress",
            )

            self.assertEqual(report["status"], "passed")
            checks = {check["name"]: check for check in report["checks"]}
            self.assertEqual(checks["adapter_success"]["status"], "passed")
            self.assertEqual(checks["control_or_command_observed"]["status"], "passed")
            self.assertEqual(checks["kpi_present"]["status"], "passed")
            self.assertTrue(Path(report["artifact_dir"]).exists())

    def test_ingress_check_rejects_missing_source(self):
        with self.assertRaisesRegex(ValueError, "requires --scenario"):
            run_algorithm_ingress_check()

    def test_ingress_check_accepts_external_command_effect_when_px4_reaches_target(self):
        report = build_ingress_report(
            {"type": "existing_scenario", "path": "scenario.json"},
            "scenario.json",
            {
                "artifact_dir": "runs/example",
                "result": {
                    "status": "passed",
                    "metrics": {
                        "algorithm_adapter_name": "external_command",
                        "algorithm_adapter_completed_successfully": True,
                        "target_altitude_reached": True,
                        "ever_armed": True,
                        "telemetry_count": 100,
                        "template_reached_altitude_m": 3.8,
                        "kpi_sample_count": 100,
                    },
                },
            },
        )

        self.assertEqual(report["status"], "passed")
        checks = {check["name"]: check for check in report["checks"]}
        self.assertEqual(checks["control_or_command_observed"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
