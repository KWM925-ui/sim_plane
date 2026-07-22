import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from sim_plane.artifacts import (
    ArtifactWriter,
    allocate_artifact_dir,
    append_jsonl,
    artifact_lifecycle_state,
    atomic_write_json,
    is_active_artifact_dir,
    is_complete_artifact_dir,
    read_jsonl,
)


def scenario(name="artifact_probe"):
    return {
        "name": name,
        "backend": "demo",
        "vehicle": "quadrotor",
    }


class ArtifactLifecycleTest(unittest.TestCase):
    def test_writer_records_git_commit_and_dirty_state(self):
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch(
            "sim_plane.artifacts.capture_git_state",
            return_value={
                "kind": "git",
                "recorded": True,
                "commit": "a" * 40,
                "dirty": True,
            },
        ):
            artifact_dir = Path(tmpdir) / "probe"
            writer = ArtifactWriter(artifact_dir, scenario(), "demo")
            writer.initialize()
            writer.write_result(
                {
                    "status": "passed",
                    "backend": "demo",
                    "vehicle": "quadrotor",
                    "scenario_name": "artifact_probe",
                }
            )

            manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(
            manifest["source_control"],
            {
                "kind": "git",
                "recorded": True,
                "commit": "a" * 40,
                "dirty": True,
            },
        )

    def test_writer_exposes_running_then_complete_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "probe"
            writer = ArtifactWriter(artifact_dir, scenario(), "demo")

            writer.initialize()

            self.assertTrue((artifact_dir / ".running").is_file())
            self.assertTrue(is_active_artifact_dir(artifact_dir))
            self.assertFalse(is_complete_artifact_dir(artifact_dir))
            self.assertEqual(artifact_lifecycle_state(artifact_dir), "active")

            writer.append_event({"level": "info"})
            writer.write_result(
                {
                    "status": "passed",
                    "backend": "demo",
                    "vehicle": "quadrotor",
                    "scenario_name": "artifact_probe",
                }
            )

            self.assertFalse((artifact_dir / ".running").exists())
            self.assertTrue((artifact_dir / ".complete").is_file())
            self.assertTrue(is_complete_artifact_dir(artifact_dir))
            self.assertEqual(artifact_lifecycle_state(artifact_dir), "complete")
            manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["lifecycle"]["state"], "complete")

    def test_released_running_marker_is_stale_not_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "probe"
            writer = ArtifactWriter(artifact_dir, scenario(), "demo")
            writer.initialize()
            writer.close()

            self.assertFalse(is_active_artifact_dir(artifact_dir))
            self.assertEqual(artifact_lifecycle_state(artifact_dir), "stale_incomplete")

    def test_legacy_artifact_without_markers_remains_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "legacy"
            artifact_dir.mkdir()
            for name, content in (
                ("manifest.json", "{}\n"),
                ("result.json", "{}\n"),
                ("events.jsonl", "{}\n"),
            ):
                (artifact_dir / name).write_text(content, encoding="utf-8")

            self.assertEqual(artifact_lifecycle_state(artifact_dir), "legacy_complete")
            self.assertTrue(is_complete_artifact_dir(artifact_dir))

    def test_atomic_allocation_is_unique_under_threads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(lambda _: allocate_artifact_dir(tmpdir, "same/name"), range(40)))

            self.assertEqual(len(paths), len(set(paths)))
            self.assertTrue(all(path.is_dir() for path in paths))
            self.assertTrue(all(path.name.startswith("same_name_") for path in paths))

    def test_atomic_json_replace_never_leaves_temporary_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            for index in range(20):
                atomic_write_json(path, {"index": index})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"index": 19})
            self.assertEqual(list(Path(tmpdir).glob(".*.tmp")), [])

    def test_atomic_json_replace_preserves_private_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "private.json"
            path.write_text("{}\n", encoding="utf-8")
            path.chmod(0o600)

            atomic_write_json(path, {"secret": "retained"})

            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_new_atomic_json_is_not_group_or_world_readable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "private.json"

            atomic_write_json(path, {"secret": "new"})

            self.assertEqual(os.stat(path).st_mode & 0o077, 0)

    def test_completed_artifact_rejects_late_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "probe"
            writer = ArtifactWriter(artifact_dir, scenario(), "demo")
            writer.initialize()
            writer.append_event({"level": "info", "message": "before"})
            writer.write_result(
                {
                    "status": "passed",
                    "backend": "demo",
                    "vehicle": "quadrotor",
                    "scenario_name": "artifact_probe",
                }
            )
            before = {
                name: (artifact_dir / name).read_bytes()
                for name in ("telemetry.jsonl", "events.jsonl", "backend_stdout.log")
            }

            self.assertFalse(writer.append_telemetry({"time_s": 1.0}))
            self.assertFalse(writer.append_event({"level": "warning", "message": "late"}))
            self.assertFalse(writer.append_backend_log("stdout", "late"))
            after = {
                name: (artifact_dir / name).read_bytes()
                for name in before
            }
            self.assertEqual(after, before)

    def test_reserved_allocation_is_not_prunable_as_empty(self):
        from sim_plane.artifact_hygiene import scan_artifact_root

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = allocate_artifact_dir(tmpdir, "reserved")

            report = scan_artifact_root(artifact_root=tmpdir)
            entry = next(item for item in report["entries"] if item["path"] == str(artifact_dir))

            self.assertEqual(entry["lifecycle"], "stale_incomplete")
            self.assertFalse(entry["safe_to_prune"])

    def test_completed_artifact_can_be_classified_with_read_only_lock_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "probe"
            writer = ArtifactWriter(artifact_dir, scenario(), "demo")
            writer.initialize()
            writer.write_result(
                {
                    "status": "passed",
                    "backend": "demo",
                    "vehicle": "quadrotor",
                    "scenario_name": "artifact_probe",
                }
            )
            (artifact_dir / ".artifact.lock").chmod(0o400)

            self.assertEqual(artifact_lifecycle_state(artifact_dir), "complete")

    def test_jsonl_append_is_line_safe_under_threads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"

            def write_batch(worker):
                for index in range(50):
                    append_jsonl(path, {"worker": worker, "index": index})

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(write_batch, range(8)))

            entries = read_jsonl(path)
            self.assertEqual(len(entries), 400)
            self.assertEqual(len({(item["worker"], item["index"]) for item in entries}), 400)


if __name__ == "__main__":
    unittest.main()
