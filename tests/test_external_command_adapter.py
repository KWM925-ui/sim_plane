import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from sim_plane.adapters import collect_algorithm_adapter, start_algorithm_adapter
from sim_plane.adapters.base import AdapterError
from sim_plane.adapters.external_command import ExternalCommandAdapter, merge_payload_metrics, resolve_path
from sim_plane.paths import get_platform_paths


class RecordingSink:
    def __init__(self, artifact_dir):
        self.artifact_writer = type("ArtifactWriter", (), {"artifact_dir": artifact_dir})()
        self.events = []
        self.logs = []

    def emit_event(self, level, message, details=None):
        self.events.append((level, message, details or {}))

    def emit_backend_log(self, stream_name, line):
        self.logs.append((stream_name, line))


class ExternalCommandAdapterTest(unittest.TestCase):
    def test_relative_adapter_paths_are_platform_relative(self):
        self.assertEqual(
            get_platform_paths().home / "examples",
            resolve_path("examples"),
        )

    def test_result_json_success_cannot_override_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = RecordingSink(Path(tmpdir) / "artifact")
            adapter = ExternalCommandAdapter()
            script = (
                "import json, os, sys; "
                "path = os.environ['SIM_PLANE_ADAPTER_RESULT_JSON']; "
                "open(path, 'w', encoding='utf-8').write(json.dumps({'success': True})); "
                "sys.exit(7)"
            )

            with self.assertRaises(AdapterError):
                adapter.run(
                    {
                        "type": "external_command",
                        "command": [sys.executable, "-B", "-c", script],
                        "max_runtime_s": 3.0,
                    },
                    sink,
                    {},
                )

    def test_result_json_success_cannot_override_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = RecordingSink(Path(tmpdir) / "artifact")
            adapter = ExternalCommandAdapter()
            script = (
                "import json, os, time; "
                "path = os.environ['SIM_PLANE_ADAPTER_RESULT_JSON']; "
                "open(path, 'w', encoding='utf-8').write(json.dumps({'success': True})); "
                "time.sleep(60)"
            )

            with self.assertRaises(AdapterError):
                adapter.run(
                    {
                        "type": "external_command",
                        "command": [sys.executable, "-B", "-c", script],
                        "max_runtime_s": 0.2,
                        "allow_timeout_as_success": False,
                    },
                    sink,
                    {},
                )

    def test_result_json_false_downgrades_zero_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = RecordingSink(Path(tmpdir) / "artifact")
            adapter = ExternalCommandAdapter()
            script = (
                "import json, os; "
                "path = os.environ['SIM_PLANE_ADAPTER_RESULT_JSON']; "
                "open(path, 'w', encoding='utf-8').write(json.dumps({'success': False}))"
            )

            with self.assertRaises(AdapterError):
                adapter.run(
                    {
                        "type": "external_command",
                        "command": [sys.executable, "-B", "-c", script],
                        "max_runtime_s": 3.0,
                    },
                    sink,
                    {},
                )

    def test_result_json_success_must_be_boolean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = RecordingSink(Path(tmpdir) / "artifact")
            adapter = ExternalCommandAdapter()
            script = (
                "import json, os; "
                "path = os.environ['SIM_PLANE_ADAPTER_RESULT_JSON']; "
                "open(path, 'w', encoding='utf-8').write(json.dumps({'success': 'false'}))"
            )

            with self.assertRaises(AdapterError):
                adapter.run(
                    {
                        "type": "external_command",
                        "command": [sys.executable, "-B", "-c", script],
                        "max_runtime_s": 3.0,
                    },
                    sink,
                    {},
                )

    def test_payload_metrics_cannot_override_reserved_adapter_metrics(self):
        metrics = merge_payload_metrics(
            {
                "algorithm_adapter_completed_successfully": True,
                "algorithm_adapter_exit_code": 0,
            },
            {
                "metrics": {
                    "algorithm_adapter_completed_successfully": False,
                    "algorithm_adapter_exit_code": 99,
                    "algorithm_adapter_target_altitude_reached": True,
                    "custom_score": 42,
                }
            },
        )

        self.assertTrue(metrics["algorithm_adapter_completed_successfully"])
        self.assertEqual(metrics["algorithm_adapter_exit_code"], 0)
        self.assertTrue(metrics["algorithm_adapter_target_altitude_reached"])
        self.assertEqual(metrics["custom_score"], 42)

    def test_collect_request_stop_stops_long_running_external_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ready_file = Path(tmpdir) / "ready.txt"
            sink = RecordingSink(Path(tmpdir) / "artifact")
            script = (
                "import os, time; "
                "open(os.environ['READY_FILE'], 'w', encoding='utf-8').write('ready\\n'); "
                "time.sleep(60)"
            )
            handle = start_algorithm_adapter(
                {
                    "type": "external_command",
                    "command": [sys.executable, "-B", "-c", script],
                    "max_runtime_s": 60.0,
                    "stop_wait_timeout_s": 1.0,
                    "env": {"READY_FILE": str(ready_file)},
                },
                sink,
                context={},
            )
            deadline = time.time() + 3.0
            while time.time() < deadline and not ready_file.exists():
                time.sleep(0.05)
            self.assertTrue(ready_file.exists())

            report = collect_algorithm_adapter(handle, timeout_s=3.0, request_stop=True)

        metrics = report["metrics"]
        self.assertTrue(metrics["algorithm_adapter_stop_requested"])
        self.assertTrue(metrics["algorithm_adapter_completed_successfully"])
        self.assertFalse(handle.thread.is_alive())


if __name__ == "__main__":
    unittest.main()
