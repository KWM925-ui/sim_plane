import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.artifacts import ArtifactWriter
from sim_plane.px4_ulog import (
    collect_px4_ulog_artifacts,
    collect_px4_ulog_artifacts_safely,
    discover_px4_ulog_files,
    px4_ulog_metrics,
    read_px4_ulog_index,
    snapshot_px4_ulog_files,
)


class PX4ULogTest(unittest.TestCase):
    def test_discover_snapshot_collect_and_manifest_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            build_dir = root / "PX4-Autopilot" / "build" / "px4_sitl_sih"
            log_dir = build_dir / "rootfs" / "fs" / "microsd" / "log" / "2026-06-06"
            log_dir.mkdir(parents=True)
            old_log = log_dir / "old.ulg"
            old_log.write_bytes(b"old")
            config = {
                "build_dir": build_dir,
                "collect_ulog": True,
                "collect_ulog_max_files": 2,
            }
            before = snapshot_px4_ulog_files(config)
            new_log = log_dir / "new.ulg"
            new_log.write_bytes(b"new-log")

            artifact_dir = root / "runs" / "px4_probe"
            writer = ArtifactWriter(
                artifact_dir,
                {"name": "px4_probe", "vehicle": "quadrotor"},
                "px4_sih",
            )
            writer.initialize()

            report = collect_px4_ulog_artifacts(config, artifact_dir, before_snapshot=before, label="px4_sih")
            manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
            index = read_px4_ulog_index(artifact_dir)
            metrics = px4_ulog_metrics(report)

            self.assertEqual([path.name for path in discover_px4_ulog_files(config)], ["new.ulg", "old.ulg"])
            self.assertEqual(report["status"], "collected")
            self.assertEqual(report["count"], 1)
            self.assertEqual(report["files"][0]["artifact_path"], "px4_ulog/new.ulg")
            self.assertTrue((artifact_dir / "px4_ulog" / "new.ulg").is_file())
            self.assertEqual(manifest["files"]["px4_ulog_index"], "px4_ulog/index.json")
            self.assertEqual(manifest["files"]["px4_ulog_1"], "px4_ulog/new.ulg")
            self.assertEqual(manifest["px4_ulog"]["status"], "collected")
            self.assertTrue(index["available"])
            self.assertEqual(index["count"], 1)
            self.assertTrue(metrics["px4_ulog_collected"])
            self.assertEqual(metrics["px4_ulog_count"], 1)
            self.assertEqual(metrics["px4_ulog_total_bytes"], len(b"new-log"))

    def test_collect_disabled_writes_index_without_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_dir = root / "runs" / "px4_probe"
            writer = ArtifactWriter(
                artifact_dir,
                {"name": "px4_probe", "vehicle": "quadrotor"},
                "px4_sih",
            )
            writer.initialize()

            report = collect_px4_ulog_artifacts(
                {"build_dir": root / "missing", "collect_ulog": False},
                artifact_dir,
            )
            index = read_px4_ulog_index(artifact_dir)
            manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(report["status"], "disabled")
            self.assertEqual(index["status"], "disabled")
            self.assertFalse(index["available"])
            self.assertEqual(manifest["px4_ulog"]["status"], "disabled")

    def test_missing_new_log_is_warning_style_report_not_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_dir = root / "runs" / "px4_probe"
            writer = ArtifactWriter(
                artifact_dir,
                {"name": "px4_probe", "vehicle": "quadrotor"},
                "px4_sih",
            )
            writer.initialize()

            report = collect_px4_ulog_artifacts(
                {"build_dir": root / "PX4-Autopilot" / "build" / "px4_sitl_sih"},
                artifact_dir,
            )
            index = read_px4_ulog_index(artifact_dir)

            self.assertEqual(report["status"], "missing")
            self.assertEqual(report["count"], 0)
            self.assertFalse(index["available"])
            self.assertTrue(report["issues"])

    def test_safe_collection_reports_failure_without_raising(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_dir = root / "runs" / "px4_probe"
            writer = ArtifactWriter(
                artifact_dir,
                {"name": "px4_probe", "vehicle": "quadrotor"},
                "px4_sih",
            )
            writer.initialize()

            report = collect_px4_ulog_artifacts_safely(
                {"build_dir": root, "collect_ulog_max_files": "not-an-int"},
                artifact_dir,
            )
            index = read_px4_ulog_index(artifact_dir)

            self.assertEqual(report["status"], "failed")
            self.assertEqual(index["status"], "failed")
            self.assertFalse(index["available"])
            self.assertTrue(any("without changing the simulation verdict" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
