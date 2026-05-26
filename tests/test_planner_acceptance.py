import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.planner_acceptance import validate_acceptance_matrix, write_acceptance_report


def write_artifact(
    artifact_dir,
    backend,
    scenario_name,
    min_goal_distance_m,
    launch_rviz,
    event_levels,
):
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backend": backend,
                "scenario_name": scenario_name,
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
                "scenario_name": scenario_name,
                "metrics": {
                    "goal_reached": True,
                    "min_goal_distance_m": min_goal_distance_m,
                    "launch_rviz": launch_rviz,
                    "cloud_only": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (artifact_dir / "events.jsonl").open("w", encoding="utf-8") as handle:
        for level in event_levels:
            handle.write(json.dumps({"level": level}, ensure_ascii=False) + "\n")


def write_matrix(matrix_path, artifact_root):
    payload = {
        "matrix_name": "test_matrix",
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


class PlannerAcceptanceTest(unittest.TestCase):
    def test_reference_acceptance_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info", "info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(path=matrix_path)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["rows"][0]["headless"]["status"], "passed")
            self.assertEqual(report["rows"][0]["visual"]["status"], "passed")

    def test_latest_acceptance_uses_newest_matching_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010301",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.05,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(
                path=matrix_path,
                artifact_root=artifact_root,
                use_latest=True,
            )

            self.assertEqual(report["status"], "passed")
            self.assertTrue(
                report["rows"][0]["headless"]["artifact_dir"].endswith("ego_planner_marsim_20260428_010301")
            )

    def test_warning_event_fails_acceptance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info", "warning"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(path=matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn("non-accepted values", report["rows"][0]["headless"]["issues"][0])

    def test_goal_distance_regression_beyond_tolerance_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010301",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.08,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(
                path=matrix_path,
                artifact_root=artifact_root,
                use_latest=True,
            )

            self.assertEqual(report["status"], "failed")
            self.assertIn(
                "regressed by",
                " ".join(report["rows"][0]["headless"]["issues"]),
            )

    def test_configured_baseline_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)
            payload = json.loads(matrix_path.read_text(encoding="utf-8"))
            payload["rows"][0]["headless"]["baseline_min_goal_distance_m"] = 0.05
            matrix_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            report = validate_acceptance_matrix(path=matrix_path)

            self.assertEqual(report["status"], "failed")
            self.assertIn(
                "does not match reference artifact value",
                " ".join(report["rows"][0]["headless"]["issues"]),
            )

    def test_write_acceptance_report_persists_timestamped_and_latest_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "acceptance"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(path=matrix_path)
            saved = write_acceptance_report(report, report_root=report_root)

            report_dir = Path(saved["report_dir"])
            latest_json = Path(saved["latest_report_json"])
            latest_text = Path(saved["latest_report_text"])
            delta_json = Path(saved["delta_json"])
            delta_text = Path(saved["delta_text"])
            latest_delta_json = Path(saved["latest_delta_json"])
            history_jsonl = Path(saved["history_jsonl"])
            self.assertTrue((report_dir / "report.json").exists())
            self.assertTrue((report_dir / "report.txt").exists())
            self.assertTrue((report_dir / "delta.json").exists())
            self.assertTrue((report_dir / "delta.txt").exists())
            self.assertTrue((report_dir / "manifest.json").exists())
            self.assertTrue(latest_json.exists())
            self.assertTrue(latest_text.exists())
            self.assertTrue(delta_json.exists())
            self.assertTrue(delta_text.exists())
            self.assertTrue(latest_delta_json.exists())
            self.assertTrue(history_jsonl.exists())

            payload = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
            latest_payload = json.loads(latest_json.read_text(encoding="utf-8"))
            delta_payload = json.loads(delta_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(latest_payload["status"], "passed")
            self.assertEqual(payload["selection_mode"], "reference")
            self.assertFalse(delta_payload["has_previous_report"])

    def test_write_acceptance_report_prunes_older_timestamped_reports_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "acceptance"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(path=matrix_path)
            first = write_acceptance_report(report, report_root=report_root, keep_last=1)
            second = write_acceptance_report(report, report_root=report_root, keep_last=1)

            first_dir = Path(first["report_dir"])
            second_dir = Path(second["report_dir"])
            history_jsonl = Path(second["history_jsonl"])
            self.assertFalse(first_dir.exists())
            self.assertTrue(second_dir.exists())
            self.assertEqual(len(history_jsonl.read_text(encoding="utf-8").strip().splitlines()), 2)
            self.assertIn(str(first_dir), second["pruned_report_dirs"])

    def test_write_acceptance_report_persists_delta_against_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "acceptance"
            matrix_path = root / "matrix.json"
            write_artifact(
                artifact_root / "ego_planner_marsim_20260428_010101",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim",
                min_goal_distance_m=0.064,
                launch_rviz=False,
                event_levels=["info"],
            )
            write_artifact(
                artifact_root / "ego_planner_marsim_visual_20260428_010201",
                backend="ego_planner_marsim",
                scenario_name="ego_planner_marsim_visual",
                min_goal_distance_m=0.066,
                launch_rviz=True,
                event_levels=["info"],
            )
            write_matrix(matrix_path, artifact_root)

            report = validate_acceptance_matrix(path=matrix_path)
            first = write_acceptance_report(report, report_root=report_root)

            report2 = json.loads(json.dumps(report))
            report2["rows"][0]["headless"]["metrics"]["min_goal_distance_m"] = 0.07
            report2["rows"][0]["headless"]["metrics"]["goal_distance_regression_m"] = 0.006
            report2["rows"][0]["headless"]["issues"] = ["synthetic issue"]
            report2["rows"][0]["headless"]["status"] = "failed"
            report2["rows"][0]["issues"] = ["synthetic row issue"]
            report2["rows"][0]["status"] = "failed"
            report2["issues"] = ["synthetic top issue"]
            report2["status"] = "failed"
            second = write_acceptance_report(report2, report_root=report_root)

            delta_payload = json.loads(Path(second["latest_delta_json"]).read_text(encoding="utf-8"))
            self.assertTrue(delta_payload["has_previous_report"])
            self.assertEqual(delta_payload["previous_report_dir"], first["report_dir"])
            self.assertTrue(delta_payload["status_changed"])
            self.assertEqual(delta_payload["issues_count_delta"], 1)
            self.assertEqual(delta_payload["changed_backends_count"], 1)
            self.assertEqual(delta_payload["changed_modes_count"], 1)
            headless_delta = delta_payload["row_deltas"][0]["mode_deltas"][0]
            self.assertEqual(headless_delta["mode"], "headless")
            self.assertEqual(headless_delta["min_goal_distance_delta_m"], 0.006)
            self.assertEqual(headless_delta["issues_count_delta"], 1)


if __name__ == "__main__":
    unittest.main()
