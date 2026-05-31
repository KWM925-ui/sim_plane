import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.runner import run_scenario


class DemoRunTest(unittest.TestCase):
    def test_demo_run_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "test_basic_takeoff",
                        "description": "Fast test scenario",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 7.0,
                        "update_hz": 4.0,
                        "target_altitude_m": 5.0,
                        "realtime_factor": 0.0,
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 5.0, "y": 0.0}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            artifact_root = Path(tmpdir) / "runs"
            outcome = run_scenario(
                str(scenario_path),
                artifact_root=str(artifact_root),
                visualize=False,
            )
            artifact_dir = Path(outcome["artifact_dir"])
            self.assertTrue((artifact_dir / "manifest.json").exists())
            self.assertTrue((artifact_dir / "scenario.json").exists())
            self.assertTrue((artifact_dir / "telemetry.jsonl").exists())
            self.assertTrue((artifact_dir / "result.json").exists())

            result = json.loads((artifact_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["metrics"]["kpi_sample_count"], result["metrics"]["telemetry_count"])
            self.assertIn("kpi_altitude_mae_m", result["metrics"])

    def test_demo_run_supports_deterministic_degradations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "test_degraded_takeoff",
                        "description": "Fast degradation scenario",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 8.0,
                        "update_hz": 4.0,
                        "target_altitude_m": 4.0,
                        "realtime_factor": 0.0,
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 4.0, "y": 0.0}
                        ],
                        "degradations": {
                            "seed": 19,
                            "sensor_dropout": {
                                "windows": [
                                    {
                                        "start_s": 6.0,
                                        "end_s": 6.5
                                    }
                                ]
                            },
                            "measurement_bias": {
                                "x_m": 0.5,
                                "z_m": -0.2
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            artifact_root = Path(tmpdir) / "runs"
            outcome = run_scenario(
                str(scenario_path),
                artifact_root=str(artifact_root),
                visualize=False,
            )

            result = json.loads((Path(outcome["artifact_dir"]) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["metrics"]["degradation_enabled"])
            self.assertGreater(result["metrics"]["sensor_dropout_count"], 0)
            self.assertGreater(result["metrics"]["kpi_sensor_dropout_ratio"], 0.0)
            self.assertGreater(result["metrics"]["kpi_measurement_horizontal_error_mae_m"], 0.0)

    def test_demo_run_supports_target_loss_comm_interrupt_and_control_saturation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "test_fault_pack_takeoff",
                        "description": "Fast fault pack scenario",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 10.0,
                        "update_hz": 5.0,
                        "target_altitude_m": 4.0,
                        "realtime_factor": 0.0,
                        "control_limits": {
                            "max_speed_mps": 3.0
                        },
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 4.0, "y": 0.0}
                        ],
                        "degradations": {
                            "target_loss": {
                                "windows": [
                                    {"start_s": 6.0, "end_s": 6.4}
                                ]
                            },
                            "communication_interruption": {
                                "windows": [
                                    {"start_s": 6.0, "end_s": 6.4}
                                ]
                            },
                            "control_saturation": {
                                "max_speed_mps": 3.0
                            },
                            "sensor_noise": {
                                "position_std_m": 0.01
                            },
                            "measurement_bias_drift": {
                                "x_mps": 0.01
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            artifact_root = Path(tmpdir) / "runs"
            outcome = run_scenario(
                str(scenario_path),
                artifact_root=str(artifact_root),
                visualize=False,
            )

            result = json.loads((Path(outcome["artifact_dir"]) / "result.json").read_text(encoding="utf-8"))
            metrics = result["metrics"]
            self.assertEqual(result["status"], "passed")
            self.assertTrue(metrics["degradation_enabled"])
            self.assertGreater(metrics["target_loss_count"], 0)
            self.assertGreater(metrics["communication_interruption_count"], 0)
            self.assertGreater(metrics["control_saturation_count"], 0)
            self.assertEqual(metrics["kpi_speed_limit_violation_count"], 0)
            self.assertGreaterEqual(metrics["kpi_target_lost_count"], 1)
            self.assertGreaterEqual(metrics["kpi_target_reacquire_count"], 1)

    def test_demo_run_supports_data_stream_sensor_faults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "test_sensor_stream_faults",
                        "description": "Fast data-stream sensor fault scenario",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 10.0,
                        "update_hz": 5.0,
                        "target_altitude_m": 4.0,
                        "realtime_factor": 0.0,
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 5.0, "y": 0.0},
                        ],
                        "degradations": {
                            "seed": 71,
                            "sensor_stream_faults": {
                                "gps_dropout": {
                                    "windows": [
                                        {"start_s": 6.0, "end_s": 6.4}
                                    ]
                                },
                                "vio_scale_drift": {
                                    "start_s": 5.0,
                                    "scale_rate_per_s": 0.08,
                                    "max_scale_error": 0.2
                                },
                                "imu_noise_burst": {
                                    "windows": [
                                        {"start_s": 7.0, "end_s": 7.4}
                                    ],
                                    "position_std_m": 0.2,
                                    "altitude_std_m": 0.1
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            outcome = run_scenario(
                str(scenario_path),
                artifact_root=str(Path(tmpdir) / "runs"),
                visualize=False,
            )

            result = json.loads((Path(outcome["artifact_dir"]) / "result.json").read_text(encoding="utf-8"))
            metrics = result["metrics"]
            self.assertEqual(result["status"], "passed")
            self.assertTrue(metrics["sensor_stream_fault_enabled"])
            self.assertGreater(metrics["gps_dropout_count"], 0)
            self.assertGreater(metrics["vio_scale_drift_count"], 0)
            self.assertGreater(metrics["vio_scale_drift_max_scale_error"], 0.0)
            self.assertGreater(metrics["imu_noise_burst_count"], 0)
            self.assertGreater(metrics["kpi_sensor_dropout_count"], 0)


if __name__ == "__main__":
    unittest.main()
