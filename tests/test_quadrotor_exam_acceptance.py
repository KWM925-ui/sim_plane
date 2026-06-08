import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.cli import main
from sim_plane.quadrotor_exam_acceptance import validate_matrix, write_report


SCENES = ["hover", "waypoint"]


def make_report(path, distance=10.0, status="passed", created_at_utc=None):
    rows = []
    for scene in SCENES:
        rows.append(
            {
                "name": scene,
                "status": status,
                "artifact_dir": "runs/{0}_artifact".format(scene),
                "metrics": {
                    "kpi_distance_m": distance,
                    "kpi_max_speed_mps": 4.0,
                    "kpi_max_acceleration_mps2": 8.0,
                    "kpi_speed_roughness_mps": 0.1,
                    "kpi_safety_violation_count": 0,
                    "kpi_final_goal_distance_m": 0.0,
                    "kpi_sensor_recovery_time_s": 1.0,
                    "kpi_measurement_horizontal_error_max_m": 0.0,
                },
                "issues": [],
            }
        )
    report = {
        "suite_name": "paper_quadrotor_exam_suite",
        "status": "passed" if status == "passed" else "failed",
        "rows": rows,
        "exam": {
            "scene_count": len(rows),
            "passed_scene_count": sum(1 for row in rows if row["status"] == "passed"),
            "success_rate": 1.0 if status == "passed" else 0.0,
        },
    }
    if created_at_utc is not None:
        report["created_at_utc"] = created_at_utc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_matrix(path, reference_report):
    payload = {
        "matrix_name": "test_quadrotor_exam_acceptance",
        "suite_name": "paper_quadrotor_exam_suite",
        "reference_report": str(reference_report),
        "required_scene_count": 2,
        "required_success_rate": 1.0,
        "required_row_status": "passed",
        "required_scene_names": SCENES,
        "exam_regression_budgets": {
            "success_rate": {"max_drop": 0.0},
            "passed_scene_count": {"max_drop": 0.0},
        },
        "row_metric_regression_budgets": {
            "kpi_distance_m": {"max_increase": 2.0},
            "kpi_safety_violation_count": {"max_increase": 0.0},
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class QuadrotorExamAcceptanceTest(unittest.TestCase):
    def test_reference_report_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            reference_report = root / "runs" / "suites" / "reference.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_matrix(matrix_path, reference_report)

            report = validate_matrix(path=matrix_path)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["rows"]), 2)
            self.assertEqual(report["summary"]["success_rate"], 1.0)

    def test_latest_report_uses_artifact_root_latest_suite_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            reference_report = artifact_root / "suites" / "reference.json"
            latest_report = artifact_root / "suites" / "latest_paper_quadrotor_exam_suite.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_report(latest_report, distance=11.0)
            make_matrix(matrix_path, reference_report)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["report_path"], str(latest_report))
            self.assertEqual(report["rows"][0]["metric_regressions"]["kpi_distance_m"], 1.0)

    def test_latest_report_prefers_newest_timestamped_suite_report_over_stale_latest_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            suites_root = artifact_root / "suites"
            reference_report = suites_root / "reference.json"
            stale_latest_report = suites_root / "latest_paper_quadrotor_exam_suite.json"
            newer_report = suites_root / "paper_quadrotor_exam_suite_20260608_090000" / "report.json"
            older_report_with_later_name = suites_root / "paper_quadrotor_exam_suite_20260608_100000" / "report.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_report(stale_latest_report, distance=14.0, created_at_utc="2026-06-08T08:00:00Z")
            make_report(newer_report, distance=11.0, created_at_utc="2026-06-08T10:00:00Z")
            make_report(
                older_report_with_later_name,
                distance=14.0,
                created_at_utc="2026-06-08T09:00:00Z",
            )
            make_matrix(matrix_path, reference_report)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["report_path"], str(newer_report))
            self.assertEqual(report["rows"][0]["metric_regressions"]["kpi_distance_m"], 1.0)

    def test_latest_report_falls_back_to_report_mtime_when_timestamp_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            suites_root = artifact_root / "suites"
            reference_report = suites_root / "reference.json"
            newer_by_name_but_older_mtime = suites_root / "paper_quadrotor_exam_suite_20260608_100000" / "report.json"
            older_by_name_but_newer_mtime = suites_root / "paper_quadrotor_exam_suite_20260608_090000" / "report.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_report(newer_by_name_but_older_mtime, distance=12.0, created_at_utc="not-a-time")
            make_report(older_by_name_but_newer_mtime, distance=11.0)
            os.utime(newer_by_name_but_older_mtime, (1000, 1000))
            os.utime(older_by_name_but_newer_mtime, (2000, 2000))
            make_matrix(matrix_path, reference_report)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["report_path"], str(older_by_name_but_newer_mtime))
            self.assertEqual(report["rows"][0]["metric_regressions"]["kpi_distance_m"], 1.0)

    def test_metric_regression_beyond_budget_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            reference_report = artifact_root / "suites" / "reference.json"
            latest_report = artifact_root / "suites" / "latest_paper_quadrotor_exam_suite.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_report(latest_report, distance=14.0)
            make_matrix(matrix_path, reference_report)

            report = validate_matrix(path=matrix_path, artifact_root=artifact_root, use_latest=True)

            self.assertEqual(report["status"], "failed")
            self.assertIn("kpi_distance_m", " ".join(report["issues"]))

    def test_write_report_persists_latest_history_and_delta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            reference_report = root / "runs" / "suites" / "reference.json"
            matrix_path = root / "matrix.json"
            report_root = root / "acceptance"
            make_report(reference_report, distance=10.0)
            make_matrix(matrix_path, reference_report)
            report = validate_matrix(path=matrix_path)

            saved = write_report(report, report_root=report_root)

            self.assertTrue(Path(saved["report_json"]).exists())
            self.assertTrue(Path(saved["latest_report_json"]).exists())
            self.assertTrue(Path(saved["history_jsonl"]).exists())
            self.assertFalse(saved["delta"]["has_previous_report"])

    def test_cli_acceptance_returns_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            reference_report = root / "runs" / "suites" / "reference.json"
            matrix_path = root / "matrix.json"
            make_report(reference_report, distance=10.0)
            make_matrix(matrix_path, reference_report)

            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "quadrotor-exam-acceptance",
                        "--matrix",
                        str(matrix_path),
                        "--report-root",
                        str(root / "acceptance"),
                        "--json",
                    ]
                )

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "passed")
            self.assertIn("saved_report", payload)


if __name__ == "__main__":
    unittest.main()
