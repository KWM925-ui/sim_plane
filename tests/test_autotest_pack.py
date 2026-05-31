import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.autotest_pack import find_latest_artifact, is_success_status, run_autotest_pack, write_autotest_report


def write_artifact(root, name, backend, scenario_name, created_at):
    artifact = root / name
    artifact.mkdir(parents=True)
    (artifact / "manifest.json").write_text(
        json.dumps(
            {
                "created_at_utc": created_at,
                "backend": backend,
                "scenario_name": scenario_name,
                "vehicle": "quadrotor",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "scenario.json").write_text(
        json.dumps({"name": scenario_name, "backend": backend, "vehicle": "quadrotor"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (artifact / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "backend": backend,
                "vehicle": "quadrotor",
                "scenario_name": scenario_name,
                "metrics": {},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "events.jsonl").write_text('{"level":"info"}\n', encoding="utf-8")
    return artifact


class AutotestPackTest(unittest.TestCase):
    def test_success_status_accepts_clean_hygiene(self):
        self.assertTrue(is_success_status("passed"))
        self.assertTrue(is_success_status("clean"))
        self.assertFalse(is_success_status("failed"))

    def test_find_latest_artifact_prefers_px4_sih(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_artifact(root, "demo_latest", "demo", "basic_takeoff", "2026-05-28T00:00:00Z")
            first_px4 = write_artifact(root, "px4_old", "px4_sih", "px4_sih_quadx_headless", "2026-05-28T00:00:01Z")
            latest_px4 = write_artifact(root, "px4_new", "px4_sih", "px4_sih_quadx_headless", "2026-05-28T00:00:02Z")

            self.assertEqual(find_latest_artifact(root, backend_prefix="px4", preferred_scenario_prefix="px4_sih"), latest_px4)
            self.assertNotEqual(find_latest_artifact(root, backend_prefix="px4", preferred_scenario_prefix="px4_sih"), first_px4)

    def test_write_autotest_report_persists_latest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = {
                "pack_name": "sim_plane_autotest_fast",
                "profile": "fast",
                "artifact_root": "runs",
                "status": "passed",
                "issues": [],
                "steps": [],
            }

            saved = write_autotest_report(report, report_root=root / "autotest", keep_last=1)

            self.assertTrue(Path(saved["report_json"]).exists())
            self.assertTrue(Path(saved["latest_json"]).exists())
            self.assertTrue(Path(saved["history_jsonl"]).exists())

    @mock.patch("sim_plane.autotest_pack.validate_platform_matrix")
    @mock.patch("sim_plane.autotest_pack.write_platform_acceptance_report")
    @mock.patch("sim_plane.autotest_pack.validate_px4_failure_matrix")
    @mock.patch("sim_plane.autotest_pack.write_px4_failure_report")
    @mock.patch("sim_plane.autotest_pack.analyze_flight_log")
    @mock.patch("sim_plane.autotest_pack.run_scenario_fuzz")
    @mock.patch("sim_plane.autotest_pack.run_suite")
    @mock.patch("sim_plane.autotest_pack.run_live_smoke_suite")
    @mock.patch("sim_plane.autotest_pack.apply_artifact_hygiene")
    @mock.patch("sim_plane.autotest_pack.collect_platform_doctor_report")
    def test_run_autotest_pack_composes_fast_steps(
        self,
        doctor,
        hygiene,
        live_smoke,
        run_suite_mock,
        fuzz,
        flight_log,
        px4_write,
        px4_validate,
        platform_write,
        platform_validate,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_artifact(root / "runs", "px4_new", "px4_sih", "px4_sih_quadx_headless", "2026-05-28T00:00:02Z")
            doctor.return_value = {"summary": {"ready_backend_count": 1}}
            hygiene.return_value = {"status": "clean", "issues": []}
            live_smoke.return_value = {"status": "passed", "issues": [], "rows": []}
            run_suite_mock.return_value = {"status": "passed", "issues": [], "rows": []}
            fuzz.return_value = {"status": "passed", "issues": [], "rows": []}
            flight_log.return_value = {"status": "passed", "issues": [], "metrics": {}}
            px4_validate.return_value = {"status": "passed", "issues": [], "rows": []}
            px4_write.return_value = {"report_json": str(root / "px4.json"), "delta": {}}
            platform_validate.return_value = {"status": "passed", "issues": [], "rows": []}
            platform_write.return_value = {"report_json": str(root / "platform.json"), "delta": {}}

            report = run_autotest_pack(
                artifact_root=root / "runs",
                report_root=root / "autotest",
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["steps"]), 8)
            self.assertTrue(Path(report["saved_report"]["report_json"]).exists())


if __name__ == "__main__":
    unittest.main()
