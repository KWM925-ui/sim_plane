import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.platform_acceptance import validate_platform_matrix, write_platform_acceptance_report


def write_surface_artifact(
    artifact_dir,
    backend,
    scenario_name,
    metrics,
    notes=None,
    event_levels=None,
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


def write_planner_artifact(
    artifact_dir,
    backend,
    scenario_name,
    min_goal_distance_m,
    launch_rviz,
):
    write_surface_artifact(
        artifact_dir,
        backend=backend,
        scenario_name=scenario_name,
        metrics={
            "goal_reached": True,
            "min_goal_distance_m": min_goal_distance_m,
            "launch_rviz": launch_rviz,
            "cloud_only": True,
        },
        notes=[],
        event_levels=["info"],
    )


def write_planner_matrix(matrix_path, artifact_root):
    payload = {
        "matrix_name": "test_planner_matrix",
        "goal_distance_threshold_m": 0.1,
        "max_goal_distance_regression_m": 0.01,
        "required_event_levels": ["info"],
        "rows": [
            {
                "backend": "ego_planner_marsim",
                "surface": "legacy planner on scene",
                "odom_source": "/odom",
                "obstacle_source": "/cloud",
                "requires_cloud_only": True,
                "headless": {
                    "scenario_name": "ego_planner_marsim",
                    "reference_artifact": str(artifact_root / "ego_planner_marsim_20260428_010101"),
                    "expected_launch_rviz": False,
                    "baseline_min_goal_distance_m": 0.064,
                },
                "visual": {
                    "scenario_name": "ego_planner_marsim_visual",
                    "reference_artifact": str(artifact_root / "ego_planner_marsim_visual_20260428_010201"),
                    "expected_launch_rviz": True,
                    "baseline_min_goal_distance_m": 0.066,
                },
            }
        ],
    }
    matrix_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_platform_matrix(
    matrix_path,
    artifact_root,
    planner_matrix_path,
    metric_regression_budgets=None,
    row_metric_regression_budgets=None,
):
    payload = {
        "matrix_name": "test_platform_matrix",
        "required_event_levels": ["info"],
        "metric_regression_budgets": metric_regression_budgets
        or {
            "telemetry_count": {"max_drop": 10},
            "mode_changes": {"max_drop": 0},
        },
        "planner_acceptance_matrix": str(planner_matrix_path),
        "rows": [
            {
                "name": "px4_sih_headless",
                "backend": "px4_sih",
                "surface": "light takeoff",
                "scenario_name": "px4_sih_quadx_headless",
                "reference_artifact": str(artifact_root / "px4_sih_quadx_headless_20260428_000101"),
                "required_metrics": {
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                "metric_thresholds": {
                    "telemetry_count": {"min": 1},
                    "mode_changes": {"min": 1},
                },
                "metric_regression_budgets": row_metric_regression_budgets or {},
                "notes_must_contain": ["pymavlink"],
            }
        ],
    }
    matrix_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PlatformAcceptanceTest(unittest.TestCase):
    def test_reference_platform_acceptance_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["The px4_sih backend uses pymavlink to feed the local dashboard from live MAVLink telemetry."],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(path=platform_matrix_path)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["rows"][0]["status"], "passed")
            self.assertEqual(report["planner_acceptance"]["status"], "passed")

    def test_latest_platform_acceptance_uses_newest_matching_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000201",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 101,
                    "mode_changes": 4,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(
                path=platform_matrix_path,
                artifact_root=artifact_root,
                use_latest=True,
            )

            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["rows"][0]["artifact_dir"].endswith("px4_sih_quadx_headless_20260428_000201"))
            self.assertEqual(report["rows"][0]["metric_regressions"]["telemetry_count"], 2)

    def test_latest_platform_acceptance_fails_on_telemetry_regression_beyond_budget(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000201",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 80,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(
                path=platform_matrix_path,
                artifact_root=artifact_root,
                use_latest=True,
            )

            self.assertEqual(report["status"], "failed")
            self.assertIn(
                "metric telemetry_count regressed by 19 beyond allowed drop 10",
                " ".join(report["rows"][0]["issues"]),
            )

    def test_latest_platform_acceptance_fails_on_row_specific_max_increase_budget(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                    "max_altitude_m": 0.02,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000201",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                    "max_altitude_m": 0.09,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(
                platform_matrix_path,
                artifact_root,
                planner_matrix_path,
                row_metric_regression_budgets={"max_altitude_m": {"max_increase": 0.05}},
            )

            report = validate_platform_matrix(
                path=platform_matrix_path,
                artifact_root=artifact_root,
                use_latest=True,
            )

            self.assertEqual(report["status"], "failed")
            self.assertIn(
                "metric max_altitude_m increased by 0.07 beyond allowed 0.05",
                " ".join(report["rows"][0]["issues"]),
            )

    def test_warning_event_fails_platform_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info", "warning"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(path=platform_matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("non-accepted values", " ".join(report["rows"][0]["issues"]))

    def test_missing_required_note_fails_platform_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["missing keyword"],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(path=platform_matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("missing required note substring", " ".join(report["rows"][0]["issues"]))

    def test_write_platform_acceptance_report_persists_reports_and_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "platform_acceptance"
            planner_matrix_path = root / "planner_matrix.json"
            platform_matrix_path = root / "platform_matrix.json"
            write_surface_artifact(
                artifact_root / "px4_sih_quadx_headless_20260428_000101",
                backend="px4_sih",
                scenario_name="px4_sih_quadx_headless",
                metrics={
                    "telemetry_count": 99,
                    "mode_changes": 3,
                    "target_altitude_reached": True,
                    "ever_armed": True,
                },
                notes=["pymavlink"],
                event_levels=["info"],
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
            )
            write_planner_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
            )
            write_planner_matrix(planner_matrix_path, artifact_root)
            write_platform_matrix(platform_matrix_path, artifact_root, planner_matrix_path)

            report = validate_platform_matrix(path=platform_matrix_path)
            first = write_platform_acceptance_report(report, report_root=report_root)

            report2 = json.loads(json.dumps(report))
            report2["rows"][0]["metrics"]["telemetry_count"] = 101
            report2["rows"][0]["status"] = "failed"
            report2["rows"][0]["issues"] = ["synthetic issue"]
            report2["issues"] = ["synthetic top issue"]
            report2["status"] = "failed"
            second = write_platform_acceptance_report(report2, report_root=report_root)

            latest_delta = json.loads(Path(second["latest_delta_json"]).read_text(encoding="utf-8"))
            self.assertTrue(Path(first["report_dir"]).exists())
            self.assertTrue(Path(second["report_dir"]).exists())
            self.assertTrue(Path(second["latest_report_json"]).exists())
            self.assertTrue(Path(second["history_jsonl"]).exists())
            self.assertTrue(latest_delta["has_previous_report"])
            self.assertEqual(latest_delta["previous_report_dir"], first["report_dir"])
            self.assertEqual(latest_delta["changed_rows_count"], 1)
            self.assertTrue(latest_delta["status_changed"])


if __name__ == "__main__":
    unittest.main()
