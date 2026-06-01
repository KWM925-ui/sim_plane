import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from sim_plane.cli import main
from sim_plane.platform_health import (
    collect_platform_health,
    format_platform_health_report,
    write_platform_health_report,
)


def complete_hygiene_report(root):
    return {
        "status": "clean",
        "issues": [],
        "artifact_root": str(root),
        "manual_probe_root_name": "manual_probes",
        "before": {"summary": {"attention_count": 0}},
        "after": {
            "summary": {
                "attention_count": 0,
                "complete_artifact_count": 1,
                "reserved_root_count": 1,
                "retained_manual_probe_count": 0,
                "stale_manual_probe_count": 0,
            },
            "entries": [],
        },
        "actions": {"pruned": [], "migrated": []},
    }


def acceptance_report(name):
    return {
        "matrix_name": name,
        "status": "passed",
        "issues": [],
        "selection_mode": "latest",
        "artifact_root": "runs",
        "rows": [{"name": "row_a", "status": "passed"}],
    }


class PlatformHealthTest(unittest.TestCase):
    @mock.patch("sim_plane.platform_health.list_test_surface_reports")
    @mock.patch("sim_plane.platform_health.list_suite_reports")
    @mock.patch("sim_plane.platform_health.list_complete_artifacts")
    @mock.patch("sim_plane.platform_health.validate_quadrotor_exam_matrix")
    @mock.patch("sim_plane.platform_health.validate_px4_failure_matrix")
    @mock.patch("sim_plane.platform_health.validate_acceptance_matrix")
    @mock.patch("sim_plane.platform_health.validate_platform_matrix")
    @mock.patch("sim_plane.platform_health.apply_manual_probe_hygiene")
    @mock.patch("sim_plane.platform_health.apply_artifact_hygiene")
    @mock.patch("sim_plane.platform_health.collect_platform_doctor_report")
    @mock.patch("sim_plane.platform_health.collect_git_report")
    def test_collect_platform_health_passes_when_components_pass(
        self,
        git_report,
        doctor_report,
        artifact_hygiene,
        manual_hygiene,
        platform_acceptance,
        planner_acceptance,
        px4_failure_acceptance,
        exam_acceptance,
        artifacts,
        suites,
        surfaces,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            git_report.return_value = {
                "status": "passed",
                "issues": [],
                "summary": {"branch": "main", "commit": "abc123", "dirty": False},
            }
            doctor_report.return_value = {
                "summary": {"ready_backend_count": 2, "ready_adapter_count": 1},
                "backends": [],
                "adapters": [],
            }
            artifact_hygiene.return_value = complete_hygiene_report(root / "runs")
            manual_hygiene.return_value = complete_hygiene_report(root / "runs")
            platform_acceptance.return_value = acceptance_report("platform_acceptance")
            planner_acceptance.return_value = acceptance_report("planner_acceptance")
            px4_failure_acceptance.return_value = acceptance_report("px4_failure_acceptance")
            exam_acceptance.return_value = acceptance_report("quadrotor_exam_acceptance")
            artifacts.return_value = []
            suites.return_value = {"available": True, "items": []}
            surfaces.return_value = {"available": True, "items": []}

            report = collect_platform_health(artifact_root=root / "runs", repo_root=root)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["summary"]["passed_component_count"], 8)
            self.assertEqual(report["issues"], [])
            self.assertEqual(len(report["next_stage_plan"]), 4)
            rendered = format_platform_health_report(report)
            self.assertIn("platform health: passed", rendered)
            self.assertIn("PX4 ULog auto-collection closure", rendered)

    @mock.patch("sim_plane.platform_health.collect_git_report")
    @mock.patch("sim_plane.platform_health.collect_platform_doctor_report")
    @mock.patch("sim_plane.platform_health.apply_artifact_hygiene")
    @mock.patch("sim_plane.platform_health.apply_manual_probe_hygiene")
    @mock.patch("sim_plane.platform_health.validate_platform_matrix")
    @mock.patch("sim_plane.platform_health.validate_acceptance_matrix")
    @mock.patch("sim_plane.platform_health.validate_px4_failure_matrix")
    @mock.patch("sim_plane.platform_health.validate_quadrotor_exam_matrix")
    def test_collect_platform_health_fails_on_blocking_component(
        self,
        exam_acceptance,
        px4_failure_acceptance,
        planner_acceptance,
        platform_acceptance,
        manual_hygiene,
        artifact_hygiene,
        doctor_report,
        git_report,
    ):
        git_report.return_value = {"status": "passed", "issues": [], "summary": {}}
        doctor_report.return_value = {
            "summary": {"ready_backend_count": 1},
            "backends": [],
            "adapters": [],
        }
        artifact_hygiene.return_value = {"status": "attention_needed", "issues": ["stale artifact"], "before": {}, "after": {}, "actions": {}}
        manual_hygiene.return_value = {"status": "clean", "issues": [], "before": {}, "after": {}, "actions": {}}
        platform_acceptance.return_value = acceptance_report("platform_acceptance")
        planner_acceptance.return_value = acceptance_report("planner_acceptance")
        px4_failure_acceptance.return_value = acceptance_report("px4_failure_acceptance")
        exam_acceptance.return_value = acceptance_report("quadrotor_exam_acceptance")

        report = collect_platform_health(artifact_root="runs")

        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("artifact_hygiene" in issue for issue in report["issues"]))

    def test_write_platform_health_report_persists_latest_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = Path(tmpdir) / "platform_health"
            report = {
                "health_name": "sim_plane_platform_health",
                "status": "passed",
                "generated_at_utc": "2026-06-01T00:00:00Z",
                "repo_root": "/repo",
                "artifact_root": "runs",
                "summary": {
                    "passed_component_count": 1,
                    "warning_component_count": 0,
                    "failed_component_count": 0,
                },
                "issues": [],
                "warnings": [],
                "components": [],
                "latest_evidence": {},
                "objective_boundaries": [],
                "next_stage_plan": [],
            }

            saved = write_platform_health_report(report, report_root=report_root, keep_last=1)

            self.assertTrue(Path(saved["report_json"]).exists())
            self.assertTrue(Path(saved["latest_json"]).exists())
            self.assertTrue(Path(saved["history_jsonl"]).exists())
            latest = json.loads(Path(saved["latest_json"]).read_text(encoding="utf-8"))
            self.assertEqual(latest["status"], "passed")

    @mock.patch("sim_plane.cli.write_platform_health_report")
    @mock.patch("sim_plane.cli.collect_platform_health")
    def test_cli_platform_health_allows_warning_status(self, collect_health, write_health):
        collect_health.return_value = {
            "health_name": "sim_plane_platform_health",
            "status": "warning",
            "generated_at_utc": "2026-06-01T00:00:00Z",
            "repo_root": "/repo",
            "artifact_root": "runs",
            "summary": {
                "passed_component_count": 7,
                "warning_component_count": 1,
                "failed_component_count": 0,
            },
            "issues": [],
            "warnings": ["git: status=warning"],
            "components": [],
            "latest_evidence": {},
            "objective_boundaries": [],
            "next_stage_plan": [],
        }
        write_health.return_value = {"report_json": "/tmp/report.json", "latest_json": "/tmp/latest.json"}
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["platform-health", "--artifact-root", "runs", "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "warning")
        self.assertEqual(payload["saved_report"]["report_json"], "/tmp/report.json")


if __name__ == "__main__":
    unittest.main()
