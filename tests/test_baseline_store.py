import json
import tempfile
import unittest
from pathlib import Path

from sim_plane.baseline_store import (
    ARTIFACT_BASELINE_FILES,
    ARTIFACT_BASELINE_KIND,
    BASELINE_SCHEMA_VERSION,
    REPORT_BASELINE_KIND,
    sha256_file,
    verify_artifact_baseline,
    verify_report_baseline,
)
from sim_plane.paths import get_platform_paths


def write_metadata(root, kind, files, source_key, source_value):
    payload = {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "kind": kind,
        source_key: source_value,
        "source_commit": None,
        "source_commit_recorded": False,
        "frozen_at_commit": "a" * 40,
        "files": {name: sha256_file(root / name) for name in files},
    }
    (root / "baseline.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


class BaselineStoreTest(unittest.TestCase):
    def test_missing_artifact_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name in ARTIFACT_BASELINE_FILES:
                (root / name).write_text("{}\n", encoding="utf-8")

            issues = verify_artifact_baseline(root)

            self.assertTrue(any("metadata is missing" in issue for issue in issues))

    def test_incomplete_checksum_set_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name in ARTIFACT_BASELINE_FILES:
                (root / name).write_text("{}\n", encoding="utf-8")
            payload = write_metadata(
                root,
                ARTIFACT_BASELINE_KIND,
                ARTIFACT_BASELINE_FILES,
                "source_artifact",
                "runs/probe",
            )
            payload["files"].pop("result.json")
            (root / "baseline.json").write_text(json.dumps(payload), encoding="utf-8")

            issues = verify_artifact_baseline(root)

            self.assertTrue(any("required checksum entries are missing" in issue for issue in issues))

    def test_unknown_source_commit_is_explicit_and_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "report.json").write_text("{}\n", encoding="utf-8")
            write_metadata(
                root,
                REPORT_BASELINE_KIND,
                {"report.json"},
                "source_report",
                "runs/suites/probe/report.json",
            )

            self.assertEqual(verify_report_baseline(root / "report.json"), [])

    def test_matrix_source_identity_must_match_baseline_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for name in ARTIFACT_BASELINE_FILES:
                (root / name).write_text("{}\n", encoding="utf-8")
            write_metadata(
                root,
                ARTIFACT_BASELINE_KIND,
                ARTIFACT_BASELINE_FILES,
                "source_artifact",
                "runs/right_source",
            )

            issues = verify_artifact_baseline(
                root,
                expected_source_artifact="runs/wrong_source",
            )

            self.assertTrue(any("source_artifact mismatch" in issue for issue in issues))

    def test_checked_in_baseline_bundles_are_strictly_valid(self):
        paths = get_platform_paths()
        artifact_issues = {
            path.name: verify_artifact_baseline(path)
            for path in sorted((paths.baselines / "artifacts").iterdir())
            if path.is_dir()
        }
        report_issues = {
            path.name: verify_report_baseline(path / "report.json")
            for path in sorted((paths.baselines / "reports").iterdir())
            if path.is_dir()
        }

        self.assertTrue(artifact_issues)
        self.assertTrue(report_issues)
        self.assertEqual(
            {name: issues for name, issues in artifact_issues.items() if issues},
            {},
        )
        self.assertEqual(
            {name: issues for name, issues in report_issues.items() if issues},
            {},
        )


if __name__ == "__main__":
    unittest.main()
