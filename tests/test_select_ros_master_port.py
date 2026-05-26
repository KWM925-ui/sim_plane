import socket
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "select_ros_master_port.py"


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class SelectRosMasterPortTest(unittest.TestCase):
    def test_requested_busy_port_fails(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            busy_port = sock.getsockname()[1]
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--requested-port", str(busy_port)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("already in use", result.stderr)

    def test_base_port_selection_skips_busy_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            busy_port = sock.getsockname()[1]
            expected = None
            for candidate in range(busy_port + 1, busy_port + 21):
                if port_available(candidate):
                    expected = candidate
                    break
            self.assertIsNotNone(expected)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--base-port",
                    str(busy_port),
                    "--max-offset",
                    "20",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(int(result.stdout.strip()), expected)


if __name__ == "__main__":
    unittest.main()
