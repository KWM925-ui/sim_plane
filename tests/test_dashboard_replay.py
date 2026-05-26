import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.web import (
    ArtifactRootBrowser,
    compare_artifact_dirs,
    list_complete_artifacts,
    load_platform_acceptance_latest,
)


def write_artifact(root, name, scenario_name, backend, max_altitude, max_speed, points):
    artifact_dir = root / name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "manifest.json").write_text(
        json.dumps(
            {
                "created_at_utc": "2026-05-26T17:00:00Z",
                "backend": backend,
                "scenario_name": scenario_name,
                "vehicle": "quadrotor",
                "artifact_dir": str(artifact_dir),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "scenario.json").write_text(
        json.dumps(
            {
                "name": scenario_name,
                "description": "test scenario",
                "backend": backend,
                "vehicle": "quadrotor",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "backend": backend,
                "vehicle": "quadrotor",
                "scenario_name": scenario_name,
                "metrics": {
                    "telemetry_count": len(points),
                    "max_altitude_m": max_altitude,
                    "max_speed_mps": max_speed,
                    "target_altitude_reached": True,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "events.jsonl").write_text(
        json.dumps({"level": "info", "message": "ok"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with (artifact_dir / "telemetry.jsonl").open("w", encoding="utf-8") as handle:
        for index, point in enumerate(points):
            handle.write(
                json.dumps(
                    {
                        "t": float(index),
                        "phase": "mission",
                        "mode": "AUTO",
                        "armed": True,
                        "position": {"x_m": point[0], "y_m": point[1], "z_m": -point[2]},
                        "altitude_m": point[2],
                        "speed_mps": max_speed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return artifact_dir


class DashboardReplayTest(unittest.TestCase):
    def test_list_complete_artifacts_and_root_browser(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = write_artifact(root, "demo_20260526_170000", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            second = write_artifact(root, "demo_20260526_170100", "demo", "demo", 3.0, 1.5, [(0, 0, 0), (2, 0, 2)])
            (root / "incomplete").mkdir()

            rows = list_complete_artifacts(root)
            browser = ArtifactRootBrowser(root)

            self.assertEqual([row["name"] for row in rows], [second.name, first.name])
            self.assertEqual(len(browser.list_artifacts()), 2)
            self.assertEqual(browser.state()["status"], "passed")
            self.assertEqual(browser.meta()["mode"], "browser")

    def test_compare_artifacts_reports_metric_and_trajectory_deltas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            left = write_artifact(root, "left", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            right = write_artifact(root, "right", "demo", "demo", 3.0, 1.5, [(0, 0, 0), (2, 0, 2)])

            report = compare_artifact_dirs(left, right)

            self.assertTrue(report["same_scenario"])
            metric_deltas = {row["name"]: row for row in report["metric_deltas"]}
            trajectory_deltas = {row["name"]: row for row in report["trajectory_deltas"]}
            self.assertEqual(metric_deltas["max_altitude_m"]["delta"], 1.0)
            self.assertGreater(trajectory_deltas["distance_m"]["delta"], 0.0)
            self.assertEqual(len(report["left"]["track"]), 2)
            self.assertEqual(len(report["right"]["track"]), 2)

    def test_load_platform_acceptance_latest_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_root = root / "platform_acceptance"
            report_root.mkdir(parents=True)
            (report_root / "latest_latest.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "selection_mode": "latest",
                        "planner_acceptance": {"status": "passed"},
                        "rows": [
                            {
                                "name": "px4_sih_headless",
                                "backend": "px4_sih",
                                "status": "passed",
                                "artifact_dir": "runs/new",
                                "reference_artifact_dir": "runs/ref",
                                "metric_regressions": {"telemetry_count": 0},
                                "issues": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (report_root / "latest_latest_delta.json").write_text(
                json.dumps(
                    {
                        "changed_rows_count": 1,
                        "status_changed": False,
                        "row_deltas": [
                            {
                                "name": "px4_sih_headless",
                                "changed": True,
                                "changed_metric_names": ["max_altitude_m"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = load_platform_acceptance_latest(root)

            self.assertTrue(report["available"])
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["changed_rows_count"], 1)
            self.assertEqual(report["rows"][0]["name"], "px4_sih_headless")


if __name__ == "__main__":
    unittest.main()
