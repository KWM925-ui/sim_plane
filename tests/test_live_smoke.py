import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.cli import main
from sim_plane.live_smoke import (
    load_live_smoke_matrix,
    run_live_smoke_suite,
    select_rows,
)


class LiveSmokeTest(unittest.TestCase):
    def test_select_rows_uses_named_profile_order(self):
        matrix = load_live_smoke_matrix()

        rows = select_rows(matrix, "fast")

        self.assertEqual([row["name"] for row in rows], ["demo_basic_takeoff"])

    def test_unknown_profile_raises_clear_error(self):
        matrix = load_live_smoke_matrix()

        with self.assertRaises(ValueError) as context:
            select_rows(matrix, "missing")

        self.assertIn("Unknown live smoke profile", str(context.exception))

    def test_fast_profile_runs_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_root = root / "runs"
            report_root = root / "live_smoke"

            report = run_live_smoke_suite(
                profile="fast",
                artifact_root=artifact_root,
                report_root=report_root,
                keep_last=10,
            )

            self.assertEqual(report["status"], "passed")
            self.assertEqual(len(report["rows"]), 1)
            row = report["rows"][0]
            self.assertEqual(row["name"], "demo_basic_takeoff")
            self.assertEqual(row["status"], "passed")
            self.assertTrue(Path(row["artifact_dir"]).exists())
            self.assertEqual(row["metrics"]["target_altitude_reached"], True)
            saved = report["saved_report"]
            self.assertTrue(Path(saved["report_json"]).exists())
            self.assertTrue((report_root / "latest_fast.json").exists())
            history_lines = (report_root / "history_fast.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(history_lines), 1)

    def test_cli_fast_profile_returns_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "live-smoke",
                        "--profile",
                        "fast",
                        "--artifact-root",
                        str(root / "runs"),
                        "--report-root",
                        str(root / "live_smoke"),
                        "--json",
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn('"status": "passed"', stdout.getvalue())
            latest = root / "live_smoke" / "latest_fast.json"
            self.assertTrue(latest.exists())
            report = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")


if __name__ == "__main__":
    unittest.main()
