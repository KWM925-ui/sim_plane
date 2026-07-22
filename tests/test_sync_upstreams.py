import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_upstreams.py"
SPEC = importlib.util.spec_from_file_location("sim_plane_sync_upstreams", SCRIPT_PATH)
SYNC_UPSTREAMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC_UPSTREAMS)


class SyncUpstreamsTest(unittest.TestCase):
    def write_manifest(self, root, workspace):
        path = root / "upstreams.json"
        path.write_text(
            json.dumps(
                {
                    "workspace_root": str(workspace),
                    "entries": [
                        {
                            "name": "PX4-Autopilot",
                            "path": "src/core/PX4-Autopilot",
                            "url": "https://example.invalid/PX4-Autopilot.git",
                            "branch": "main",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_status_only_does_not_create_workspace_or_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "missing" / "workspace"
            manifest = self.write_manifest(root, workspace)

            with contextlib.redirect_stdout(io.StringIO()):
                status = SYNC_UPSTREAMS.main(
                    ["--manifest", str(manifest), "--status-only"]
                )

            self.assertEqual(status, 0)
            self.assertFalse(workspace.exists())
            self.assertFalse((workspace / "src" / "core").exists())

    def test_unknown_requested_name_fails_before_writing_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            manifest = self.write_manifest(root, workspace)

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                SYNC_UPSTREAMS.main(
                    [
                        "--manifest",
                        str(manifest),
                        "--names",
                        "not-managed",
                        "--status-only",
                    ]
                )

            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(workspace.exists())


if __name__ == "__main__":
    unittest.main()
