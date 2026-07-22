import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class WrapperContractsTest(unittest.TestCase):
    def test_run_wrappers_honor_sim_plane_home(self):
        wrappers = sorted((REPO_ROOT / "scripts").glob("run_*.sh"))
        self.assertGreaterEqual(len(wrappers), 20)
        missing = [
            path.name
            for path in wrappers
            if "SIM_PLANE_HOME" not in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(missing, [])

    def test_visual_run_wrappers_enable_dashboard_visualization(self):
        missing = []
        for path in sorted((REPO_ROOT / "scripts").glob("run_*visual.sh")):
            text = path.read_text(encoding="utf-8")
            direct_run_lines = [
                line for line in text.splitlines() if "python3 -m sim_plane run" in line
            ]
            if direct_run_lines and any("--visualize" not in line for line in direct_run_lines):
                missing.append(path.name)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
