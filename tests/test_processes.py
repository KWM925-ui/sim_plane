import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from sim_plane.processes import terminate_process


class RecordingSink:
    def __init__(self):
        self.events = []

    def emit_event(self, level, message, details=None):
        self.events.append((level, message, details or {}))


class ProcessTerminationTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
