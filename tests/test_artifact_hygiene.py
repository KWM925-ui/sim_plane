import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.artifact_hygiene import (
    apply_artifact_hygiene,
    apply_manual_probe_hygiene,
    scan_artifact_root,
    scan_manual_probe_root,
)


def write_complete_artifact(path, scenario_name="demo"):
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(
        json.dumps({"backend": "demo", "scenario_name": scenario_name}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (path / "result.json").write_text(
        json.dumps({"status": "passed", "scenario_name": scenario_name}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (path / "events.jsonl").write_text(
        json.dumps({"level": "info"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


class ArtifactHygieneTest(unittest.TestCase):
    def test_scan_marks_referenced_manual_probe_and_prunable_stale_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_root = root / "runs"
            docs_root = root / "docs"
            docs_root.mkdir(parents=True, exist_ok=True)
            (docs_root / "evidence.md").write_text(
                "manual evidence: retained_probe_20260428_000001\n",
                encoding="utf-8",
            )
            write_complete_artifact(runs_root / "demo_20260428_000001")
            (runs_root / "acceptance").mkdir(parents=True, exist_ok=True)
            retained = runs_root / "retained_probe_20260428_000001"
            retained.mkdir(parents=True, exist_ok=True)
            (retained / "telemetry.jsonl").write_text("", encoding="utf-8")
            stale = runs_root / "stale_probe_20260428_000002"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "telemetry.jsonl").write_text("", encoding="utf-8")

            report = scan_artifact_root(
                artifact_root=runs_root,
                reference_search_paths=(docs_root,),
            )

            self.assertEqual(report["status"], "attention_needed")
            self.assertEqual(report["summary"]["complete_artifact_count"], 1)
            self.assertEqual(report["summary"]["reserved_root_count"], 1)
            self.assertEqual(report["summary"]["retained_manual_probe_count"], 1)
            self.assertEqual(report["summary"]["stale_manual_probe_count"], 1)
            entries = {entry["name"]: entry for entry in report["entries"]}
            self.assertEqual(entries["retained_probe_20260428_000001"]["category"], "retained_manual_probe")
            self.assertEqual(entries["stale_probe_20260428_000002"]["category"], "stale_manual_probe")
            self.assertTrue(entries["stale_probe_20260428_000002"]["safe_to_prune"])

    def test_scan_keeps_formal_acceptance_report_roots_reserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_root = Path(tmpdir) / "runs"
            report_roots = [
                "acceptance",
                "algorithm_ingress",
                "autotest",
                "console_commands",
                "flight_log_analysis",
                "live_smoke",
                "manual_probes",
                "platform_acceptance",
                "platform_health",
                "px4_failure_injection_acceptance",
                "quadrotor_exam_acceptance",
                "scenario_fuzz",
                "suites",
            ]
            for root_name in report_roots:
                (runs_root / root_name).mkdir(parents=True, exist_ok=True)
                (runs_root / root_name / "latest_latest.json").write_text("{}", encoding="utf-8")

            report = scan_artifact_root(artifact_root=runs_root)
            entries = {entry["name"]: entry for entry in report["entries"]}

            for root_name in report_roots:
                self.assertEqual(entries[root_name]["category"], "reserved_root")
                self.assertFalse(entries[root_name]["safe_to_prune"])
            self.assertEqual(report["summary"]["reserved_root_count"], len(report_roots))
            self.assertEqual(report["summary"]["attention_count"], 0)

    def test_apply_hygiene_migrates_retained_manual_and_prunes_safe_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_root = root / "runs"
            docs_root = root / "docs"
            docs_root.mkdir(parents=True, exist_ok=True)
            (docs_root / "evidence.md").write_text(
                "manual evidence: retained_probe_20260428_000001\n",
                encoding="utf-8",
            )
            write_complete_artifact(runs_root / "demo_20260428_000001")
            retained = runs_root / "retained_probe_20260428_000001"
            retained.mkdir(parents=True, exist_ok=True)
            (retained / "telemetry.jsonl").write_text("", encoding="utf-8")
            stale = runs_root / "stale_probe_20260428_000002"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "telemetry.jsonl").write_text("", encoding="utf-8")

            report = apply_artifact_hygiene(
                artifact_root=runs_root,
                migrate_retained_manual=True,
                prune_safe=True,
                reference_search_paths=(docs_root,),
            )

            self.assertEqual(report["status"], "clean")
            self.assertFalse((runs_root / "retained_probe_20260428_000001").exists())
            self.assertFalse((runs_root / "stale_probe_20260428_000002").exists())
            self.assertTrue((runs_root / "manual_probes" / "retained_probe_20260428_000001").exists())
            self.assertEqual(report["after"]["summary"]["attention_count"], 0)
            self.assertEqual(len(report["actions"]["migrated"]), 1)
            self.assertEqual(len(report["actions"]["pruned"]), 1)

    def test_scan_manual_probe_root_marks_unreferenced_entries_as_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_root = root / "runs"
            docs_root = root / "docs"
            docs_root.mkdir(parents=True, exist_ok=True)
            manual_root = runs_root / "manual_probes"
            manual_root.mkdir(parents=True, exist_ok=True)
            retained = manual_root / "retained_probe_20260429_000001"
            retained.mkdir(parents=True, exist_ok=True)
            (retained / "summary.json").write_text("{}", encoding="utf-8")
            stale = manual_root / "stale_probe_20260429_000002"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "summary.json").write_text("{}", encoding="utf-8")
            (docs_root / "evidence.md").write_text(
                "keep retained_probe_20260429_000001\n",
                encoding="utf-8",
            )

            report = scan_manual_probe_root(
                artifact_root=runs_root,
                reference_search_paths=(docs_root,),
            )

            self.assertEqual(report["status"], "attention_needed")
            self.assertEqual(report["summary"]["retained_manual_probe_count"], 1)
            self.assertEqual(report["summary"]["stale_manual_probe_count"], 1)
            entries = {entry["name"]: entry for entry in report["entries"]}
            self.assertEqual(entries["retained_probe_20260429_000001"]["category"], "retained_manual_probe")
            self.assertEqual(entries["stale_probe_20260429_000002"]["category"], "stale_manual_probe")
            self.assertTrue(entries["stale_probe_20260429_000002"]["safe_to_prune"])

    def test_apply_manual_probe_hygiene_prunes_unreferenced_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_root = root / "runs"
            docs_root = root / "docs"
            docs_root.mkdir(parents=True, exist_ok=True)
            manual_root = runs_root / "manual_probes"
            manual_root.mkdir(parents=True, exist_ok=True)
            retained = manual_root / "retained_probe_20260429_000001"
            retained.mkdir(parents=True, exist_ok=True)
            (retained / "summary.json").write_text("{}", encoding="utf-8")
            stale = manual_root / "stale_probe_20260429_000002"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "summary.json").write_text("{}", encoding="utf-8")
            (docs_root / "evidence.md").write_text(
                "keep retained_probe_20260429_000001\n",
                encoding="utf-8",
            )

            report = apply_manual_probe_hygiene(
                artifact_root=runs_root,
                prune_safe=True,
                reference_search_paths=(docs_root,),
            )

            self.assertEqual(report["status"], "clean")
            self.assertTrue(retained.exists())
            self.assertFalse(stale.exists())
            self.assertEqual(len(report["actions"]["pruned"]), 1)

    def test_scan_manual_probe_root_keeps_latest_successful_canonical_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_root = root / "runs"
            manual_root = runs_root / "manual_probes"
            manual_root.mkdir(parents=True, exist_ok=True)
            older = manual_root / "visplanner_tracking_20260429_010101"
            older.mkdir(parents=True, exist_ok=True)
            (older / "probe_meta.json").write_text(
                json.dumps(
                    {
                        "probe_name": "visplanner_tracking",
                        "retention": "keep_latest_success",
                        "status": "passed",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            newer = manual_root / "visplanner_tracking_20260429_020202"
            newer.mkdir(parents=True, exist_ok=True)
            (newer / "probe_meta.json").write_text(
                json.dumps(
                    {
                        "probe_name": "visplanner_tracking",
                        "retention": "keep_latest_success",
                        "status": "passed",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = scan_manual_probe_root(artifact_root=runs_root)

            entries = {entry["name"]: entry for entry in report["entries"]}
            self.assertEqual(entries["visplanner_tracking_20260429_010101"]["category"], "stale_manual_probe")
            self.assertEqual(entries["visplanner_tracking_20260429_020202"]["category"], "retained_manual_probe")


if __name__ == "__main__":
    unittest.main()
