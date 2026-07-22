import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from sim_plane.processes import start_log_threads, terminate_process


class RecordingSink:
    def __init__(self):
        self.events = []

    def emit_event(self, level, message, details=None):
        self.events.append((level, message, details or {}))

    def emit_backend_log(self, stream_name, line):
        pass

    def register_background_thread(self, thread):
        if not hasattr(self, "background_threads"):
            self.background_threads = []
        self.background_threads.append(thread)


class ProcessTerminationTest(unittest.TestCase):
    def test_log_threads_are_registered_and_can_be_drained(self):
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", "print('stdout line'); import sys; print('stderr line', file=sys.stderr)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        sink = RecordingSink()

        threads = start_log_threads(process, sink, "probe")
        process.wait(timeout=3.0)
        for thread in threads:
            thread.join(timeout=3.0)

        self.assertEqual(sink.background_threads, list(threads))
        self.assertTrue(all(not thread.is_alive() for thread in threads))

    def test_terminate_process_reaps_after_forced_kill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ready_file = Path(tmpdir) / "ready"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    (
                        "import pathlib, signal, sys, time; "
                        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                        "pathlib.Path(sys.argv[1]).write_text('ready', encoding='utf-8'); "
                        "time.sleep(60)"
                    ),
                    str(ready_file),
                ],
                preexec_fn=os.setsid,
            )
            deadline = time.time() + 3.0
            while time.time() < deadline and not ready_file.exists():
                time.sleep(0.02)
            self.assertTrue(ready_file.exists())
            sink = RecordingSink()

            terminate_process(
                process,
                sink,
                "stubborn_test_process",
                stop_signal=signal.SIGTERM,
                wait_timeout_s=0.1,
            )

            self.assertIsNotNone(process.poll())
            self.assertTrue(any(message == "forcing process kill" for _, message, _ in sink.events))

    def test_terminate_process_stops_group_after_parent_exits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            child_pid_path = Path(tmpdir) / "child.pid"
            process = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    "sleep 60 & echo $! > \"$1\"",
                    "bash",
                    str(child_pid_path),
                ],
                preexec_fn=os.setsid,
            )
            process.wait(timeout=3.0)
            child_pid = int(child_pid_path.read_text(encoding="utf-8").strip())
            sink = RecordingSink()
            try:
                terminate_process(
                    process,
                    sink,
                    "orphaned_group",
                    stop_signal=signal.SIGTERM,
                    wait_timeout_s=1.0,
                )
                deadline = time.time() + 2.0
                while time.time() < deadline and process_is_live(child_pid):
                    time.sleep(0.02)
                self.assertFalse(process_is_live(child_pid))
            finally:
                if process_is_live(child_pid):
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


def process_is_live(pid):
    stat_path = Path("/proc") / str(pid) / "stat"
    if not stat_path.exists():
        return False
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return len(fields) > 2 and fields[2] != "Z"


if __name__ == "__main__":
    unittest.main()
