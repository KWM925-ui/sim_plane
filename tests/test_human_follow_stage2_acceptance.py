import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.human_follow_stage2_acceptance import validate_matrix, write_report


def write_stage2_artifact(
    artifact_dir,
    metrics,
    notes=None,
    event_levels=None,
    backend="px4_sih",
    scenario_name="px4_sih_quadx_human_follow_stage2_real_ego",
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


def write_matrix(matrix_path, artifact_root):
    payload = {
        "matrix_name": "test_human_follow_stage2_acceptance",
        "required_event_levels": ["info"],
        "metric_regression_budgets": {
            "telemetry_count": {"max_drop": 10},
            "mode_changes": {"max_drop": 0},
            "algorithm_adapter_stage2_goal_count": {"max_drop": 2},
            "algorithm_adapter_stage2_ego_cmd_count": {"max_drop": 5},
            "algorithm_adapter_stage2_nonzero_mavros_setpoint_count": {"max_drop": 10},
        },
        "rows": [
            {
                "name": "hf_stage2_real_ego_managed",
                "backend": "px4_sih",
                "surface": "stage2 real ego",
                "scenario_name": "px4_sih_quadx_human_follow_stage2_real_ego",
                "reference_artifact": str(
                    artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640"
                ),
                "required_metrics": {
                    "ever_armed": True,
                    "algorithm_adapter_name": "human_follow_ros_stage2",
                    "algorithm_adapter_completed_successfully": True,
                    "algorithm_adapter_connected": True,
                    "algorithm_adapter_arm_requested": True,
                    "algorithm_adapter_arm_command_sent": True,
                    "algorithm_adapter_armed": True,
                    "algorithm_adapter_estimator_valid": True,
                    "algorithm_adapter_offboard_requested": False,
                    "algorithm_adapter_offboard_mode_reached": True,
                    "algorithm_adapter_cleanup_mode": "AUTO.LOITER",
                    "algorithm_adapter_cleanup_mode_requested": True,
                    "algorithm_adapter_cleanup_mode_reached": True,
                    "algorithm_adapter_stage2_gate_owned_offboard_inferred": True,
                    "algorithm_adapter_stage2_search_goal_observed": True,
                    "algorithm_adapter_stage2_real_ego_path_observed": True,
                    "algorithm_adapter_stage2_variant": "real_ego",
                    "algorithm_adapter_stage2_launch_name": "human_follow_stage2_real_ego_managed.launch",
                },
                "metric_thresholds": {
                    "telemetry_count": {"min": 1},
                    "mode_changes": {"min": 1},
                    "max_altitude_m": {"max": 0.6},
                    "max_speed_mps": {"max": 0.6},
                    "algorithm_adapter_stage2_goal_count": {"min": 2},
                    "algorithm_adapter_stage2_ego_cmd_count": {"min": 2},
                    "algorithm_adapter_stage2_waypoint_count": {"min": 1},
                    "algorithm_adapter_stage2_distinct_goal_count": {"min": 2},
                    "algorithm_adapter_stage2_distinct_ego_cmd_count": {"min": 2},
                    "algorithm_adapter_stage2_nonzero_mavros_setpoint_count": {"min": 10},
                },
                "notes_must_contain": [
                    "real Stage2 chain",
                    "not a sim-plane independent ego_planner baseline",
                ],
            }
        ],
    }
    matrix_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def base_metrics():
    return {
        "telemetry_count": 52,
        "mode_changes": 4,
        "max_altitude_m": 0.206,
        "max_speed_mps": 0.333,
        "ever_armed": True,
        "algorithm_adapter_name": "human_follow_ros_stage2",
        "algorithm_adapter_completed_successfully": True,
        "algorithm_adapter_connected": True,
        "algorithm_adapter_arm_requested": True,
        "algorithm_adapter_arm_command_sent": True,
        "algorithm_adapter_armed": True,
        "algorithm_adapter_estimator_valid": True,
        "algorithm_adapter_offboard_requested": False,
        "algorithm_adapter_offboard_mode_reached": True,
        "algorithm_adapter_cleanup_mode": "AUTO.LOITER",
        "algorithm_adapter_cleanup_mode_requested": True,
        "algorithm_adapter_cleanup_mode_reached": True,
        "algorithm_adapter_stage2_goal_count": 12,
        "algorithm_adapter_stage2_ego_cmd_count": 376,
        "algorithm_adapter_stage2_waypoint_count": 14,
        "algorithm_adapter_stage2_distinct_goal_count": 6,
        "algorithm_adapter_stage2_distinct_ego_cmd_count": 8,
        "algorithm_adapter_stage2_nonzero_mavros_setpoint_count": 113,
        "algorithm_adapter_stage2_gate_owned_offboard_inferred": True,
        "algorithm_adapter_stage2_search_goal_observed": True,
        "algorithm_adapter_stage2_real_ego_path_observed": True,
        "algorithm_adapter_stage2_variant": "real_ego",
        "algorithm_adapter_stage2_launch_name": "human_follow_stage2_real_ego_managed.launch",
    }


class HumanFollowStage2AcceptanceTest(unittest.TestCase):
    def test_reference_acceptance_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            notes = [
                "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
                "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
            ]
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640",
                metrics=base_metrics(),
                notes=notes,
                event_levels=["info"],
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
            notes = [
                "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
                "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
            ]
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640",
                metrics=base_metrics(),
                notes=notes,
                event_levels=["info"],
            )
            newer_metrics = dict(base_metrics())
            newer_metrics["algorithm_adapter_stage2_ego_cmd_count"] = 378
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_070000",
                metrics=newer_metrics,
                notes=notes,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["rows"][0]["artifact_dir"].endswith("20260508_070000"))

    def test_warning_event_fails_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            notes = [
                "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
                "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
            ]
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640",
                metrics=base_metrics(),
                notes=notes,
                event_levels=["info", "warning"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("non-accepted values", " ".join(report["rows"][0]["issues"]))

    def test_metric_regression_beyond_budget_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            notes = [
                "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
                "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
            ]
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640",
                metrics=base_metrics(),
                notes=notes,
                event_levels=["info"],
            )
            regressed = dict(base_metrics())
            regressed["algorithm_adapter_stage2_nonzero_mavros_setpoint_count"] = 80
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_070000",
                metrics=regressed,
                notes=notes,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "failed")
            self.assertIn("regressed by", " ".join(report["rows"][0]["issues"]))

    def test_write_report_persists_latest_and_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "reports"
            matrix_path = root / "matrix.json"
            notes = [
                "This proof consumes the project-side stage2_real_ego.launch contract, including rolling follow goals, search goals after target loss, real EGO waypoint/path generation, PositionCommand bridge, and OFFBOARD gate.",
                "This is sim-plane managed evidence for the project-side real Stage2 chain, not a sim-plane independent ego_planner baseline.",
            ]
            write_stage2_artifact(
                artifact_root / "px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640",
                metrics=base_metrics(),
                notes=notes,
                event_levels=["info"],
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
