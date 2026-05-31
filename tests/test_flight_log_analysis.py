import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.flight_log_analysis import analyze_flight_log, write_flight_log_report


def write_artifact(root):
    artifact = root / "px4_sih_quadx_headless_20260528_000000"
    artifact.mkdir(parents=True)
    (artifact / "manifest.json").write_text(
        json.dumps(
            {
                "created_at_utc": "2026-05-28T00:00:00Z",
                "backend": "px4_sih",
                "scenario_name": "px4_sih_quadx_headless",
                "vehicle": "quadrotor",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "scenario.json").write_text(
        json.dumps(
            {
                "name": "px4_sih_quadx_headless",
                "backend": "px4_sih",
                "vehicle": "quadrotor",
                "target_altitude_m": 2.0,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "backend": "px4_sih",
                "vehicle": "quadrotor",
                "scenario_name": "px4_sih_quadx_headless",
                "metrics": {"telemetry_count": 3, "target_altitude_reached": True},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"level": "info", "message": "started"}, ensure_ascii=False),
                json.dumps({"level": "warning", "message": "test warning"}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with (artifact / "telemetry.jsonl").open("w", encoding="utf-8") as handle:
        for sample in [
            {"t": 0.0, "mode": "INIT", "armed": False, "position": {"x_m": 0.0, "y_m": 0.0, "z_m": 0.0}, "altitude_m": 0.0, "speed_mps": 0.0},
            {"t": 1.0, "mode": "TAKEOFF", "armed": True, "position": {"x_m": 0.0, "y_m": 0.0, "z_m": -1.0}, "altitude_m": 1.0, "speed_mps": 1.0},
            {"t": 2.0, "mode": "LOITER", "armed": True, "position": {"x_m": 1.0, "y_m": 0.0, "z_m": -2.0}, "altitude_m": 2.0, "speed_mps": 1.5},
        ]:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return artifact


class FlightLogAnalysisTest(unittest.TestCase):
    def test_analyze_artifact_replays_metrics_and_timelines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = write_artifact(Path(tmpdir))

            report = analyze_flight_log(artifact, save_report=False)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["source_type"], "artifact")
            self.assertEqual(report["metrics"]["telemetry_count"], 3)
            self.assertEqual(report["metrics"]["mode_change_count"], 2)
            self.assertEqual(report["metrics"]["armed_transition_count"], 1)
            self.assertEqual(report["metrics"]["anomaly_event_count"], 1)
            self.assertIn("replay_kpi_sample_count", report["metrics"])

    def test_write_report_persists_latest_and_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact = write_artifact(root)
            report = analyze_flight_log(artifact, save_report=False)

            saved = write_flight_log_report(report, report_root=root / "reports", keep_last=1)

            self.assertTrue(Path(saved["report_json"]).exists())
            self.assertTrue(Path(saved["latest_json"]).exists())
            self.assertTrue(Path(saved["history_jsonl"]).exists())


if __name__ == "__main__":
    unittest.main()
