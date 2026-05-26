import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.runner import run_scenario


class DemoRunTest(unittest.TestCase):
    def test_demo_run_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenario_path = Path(tmpdir) / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "name": "test_basic_takeoff",
                        "description": "Fast test scenario",
                        "backend": "demo",
                        "vehicle": "quadrotor",
                        "duration_s": 7.0,
                        "update_hz": 4.0,
                        "target_altitude_m": 5.0,
                        "realtime_factor": 0.0,
                        "waypoints": [
                            {"x": 0.0, "y": 0.0},
                            {"x": 5.0, "y": 0.0}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            artifact_root = Path(tmpdir) / "runs"
            outcome = run_scenario(
                str(scenario_path),
                artifact_root=str(artifact_root),
                visualize=False,
            )
            artifact_dir = Path(outcome["artifact_dir"])
            self.assertTrue((artifact_dir / "manifest.json").exists())
            self.assertTrue((artifact_dir / "scenario.json").exists())
            self.assertTrue((artifact_dir / "telemetry.jsonl").exists())
            self.assertTrue((artifact_dir / "result.json").exists())

            result = json.loads((artifact_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")


if __name__ == "__main__":
    unittest.main()
