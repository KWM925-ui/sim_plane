import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.baselines import get_baseline, list_baselines
from sim_plane.cli import main


class BaselinesTest(unittest.TestCase):
    def test_list_baselines_hides_planned_by_default(self):
        rows = list_baselines()
        names = {row["name"] for row in rows}

        self.assertIn("pid_position_demo", names)
        self.assertIn("mavsdk_takeoff_mission", names)
        self.assertNotIn("a_star_minimum_snap", names)

    def test_list_baselines_can_include_planned(self):
        rows = list_baselines(include_planned=True)
        names = {row["name"] for row in rows}

        self.assertIn("a_star_minimum_snap", names)
        self.assertEqual(get_baseline("a_star_minimum_snap")["status"], "planned")

    def test_run_baseline_demo_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "run-baseline",
                        "pid_position_demo",
                        "--artifact-root",
                        str(Path(tmpdir) / "runs"),
                        "--json",
                    ]
                )

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["baseline"]["name"], "pid_position_demo")
            self.assertEqual(payload["outcome"]["result"]["status"], "passed")

    def test_planned_baseline_is_not_runnable(self):
        with self.assertRaises(SystemExit):
            main(["run-baseline", "a_star_minimum_snap"])


if __name__ == "__main__":
    unittest.main()
