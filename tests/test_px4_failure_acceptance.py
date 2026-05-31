import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.px4_failure_acceptance import validate_matrix, write_report


def write_failure_artifact(
    artifact_dir,
    metrics,
    notes=None,
    event_levels=None,
    backend="px4_sih",
    scenario_name="px4_sih_quadx_mavsdk_failure_motor",
    vehicle="quadrotor",
):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backend": backend,
                "scenario_name": scenario_name,
                "vehicle": vehicle,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "backend": backend,
                "vehicle": vehicle,
                "scenario_name": scenario_name,
                "metrics": metrics,
                "notes": notes or [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (artifact_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for level in event_levels or ["info"]:
            handle.write(json.dumps({"level": level}, ensure_ascii=False) + "\n")


def base_metrics():
    return {
        "telemetry_count": 11,
        "mode_changes": 2,
        "algorithm_adapter_name": "mavsdk_failure_injection",
        "algorithm_adapter_connected": True,
        "algorithm_adapter_completed_successfully": True,
        "failure_injection_backend": "px4_mavsdk_failure_plugin",
        "failure_injection_command": "MAV_CMD_INJECT_FAILURE",
        "failure_injection_unit": "SYSTEM_MOTOR",
        "failure_injection_type": "OFF",
        "failure_injection_instance": 1,
        "failure_injection_accepted": True,
        "failure_injection_reset_type": "OK",
        "failure_injection_reset_accepted": True,
        "failure_injection_health_changed_count": 0,
    }


def notes():
    return [
        "This run uses PX4-native MAV_CMD_INJECT_FAILURE through the MAVSDK failure plugin.",
        "Demo backend disturbances are not treated as PX4-native failures.",
    ]


def write_matrix(matrix_path, artifact_root):
    payload = {
        "matrix_name": "test_px4_failure_injection_acceptance",
        "required_event_levels": ["info"],
        "metric_regression_budgets": {
            "telemetry_count": {"max_drop": 5},
            "mode_changes": {"max_drop": 0},
        },
        "rows": [
            {
                "name": "px4_sih_motor_failure_injection",
                "backend": "px4_sih",
                "surface": "PX4 native failure",
                "scenario_name": "px4_sih_quadx_mavsdk_failure_motor",
                "reference_artifact": str(
                    artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001"
                ),
                "required_metrics": {
                    "algorithm_adapter_name": "mavsdk_failure_injection",
                    "algorithm_adapter_connected": True,
                    "algorithm_adapter_completed_successfully": True,
                    "failure_injection_backend": "px4_mavsdk_failure_plugin",
                    "failure_injection_command": "MAV_CMD_INJECT_FAILURE",
                    "failure_injection_unit": "SYSTEM_MOTOR",
                    "failure_injection_type": "OFF",
                    "failure_injection_instance": 1,
                    "failure_injection_accepted": True,
                    "failure_injection_reset_type": "OK",
                    "failure_injection_reset_accepted": True,
                },
                "metric_thresholds": {
                    "telemetry_count": {"min": 1},
                    "mode_changes": {"min": 1},
                    "failure_injection_health_changed_count": {"min": 0},
                },
                "notes_must_contain": [
                    "PX4-native MAV_CMD_INJECT_FAILURE",
                    "Demo backend disturbances are not treated as PX4-native failures.",
                ],
            }
        ],
    }
    matrix_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PX4FailureAcceptanceTest(unittest.TestCase):
    def test_reference_acceptance_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001",
                metrics=base_metrics(),
                notes=notes(),
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["rows"][0]["status"], "passed")

    def test_latest_acceptance_uses_newest_matching_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001",
                metrics=base_metrics(),
                notes=notes(),
            )
            newer = dict(base_metrics())
            newer["telemetry_count"] = 12
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000002",
                metrics=newer,
                notes=notes(),
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["rows"][0]["artifact_dir"].endswith("20260528_000002"))

    def test_warning_event_fails_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001",
                metrics=base_metrics(),
                notes=notes(),
                event_levels=["info", "warning"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("non-accepted values", " ".join(report["rows"][0]["issues"]))

    def test_metric_mismatch_fails_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            bad = dict(base_metrics())
            bad["failure_injection_accepted"] = False
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001",
                metrics=bad,
                notes=notes(),
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("failure_injection_accepted", " ".join(report["rows"][0]["issues"]))

    def test_write_report_persists_latest_and_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "reports"
            matrix_path = root / "matrix.json"
            write_failure_artifact(
                artifact_root / "px4_sih_quadx_mavsdk_failure_motor_20260528_000001",
                metrics=base_metrics(),
                notes=notes(),
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path)
            saved = write_report(report, report_root=report_root, keep_last=1)

            self.assertTrue(Path(saved["report_dir"]).exists())
            self.assertTrue(Path(saved["latest_report_json"]).exists())
            self.assertTrue(Path(saved["latest_delta_json"]).exists())
            self.assertTrue(Path(saved["history_jsonl"]).exists())


if __name__ == "__main__":
    unittest.main()
