import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "freeze_acceptance_baselines.py"
SPEC = importlib.util.spec_from_file_location("sim_plane_freeze_baselines", SCRIPT_PATH)
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)


class FreezeAcceptanceBaselinesTest(unittest.TestCase):
    def make_artifact(self, root, source_control):
        artifact = root / "runs" / "artifact"
        artifact.mkdir(parents=True)
        (artifact / "manifest.json").write_text(
            json.dumps({"source_control": source_control}),
            encoding="utf-8",
        )
        (artifact / "result.json").write_text(
            json.dumps({"written_at_utc": "2026-01-01T00:00:00Z"}),
            encoding="utf-8",
        )
        (artifact / "events.jsonl").write_text("{}\n", encoding="utf-8")
        return artifact

    def test_clean_recorded_source_commit_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            commit = "a" * 40
            self.make_artifact(
                root,
                {"kind": "git", "recorded": True, "commit": commit, "dirty": False},
            )
            with mock.patch.object(FREEZE, "REPO_ROOT", root):
                frozen = FREEZE.freeze_artifact(
                    "runs/artifact",
                    frozen_at_commit="b" * 40,
                    source_commit=commit,
                )

            metadata = json.loads((root / frozen / "baseline.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_commit"], commit)
            self.assertTrue(metadata["source_commit_recorded"])

    def test_dirty_or_missing_source_evidence_cannot_claim_a_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_artifact(
                root,
                {"kind": "git", "recorded": True, "commit": "a" * 40, "dirty": True},
            )
            with mock.patch.object(FREEZE, "REPO_ROOT", root):
                frozen = FREEZE.freeze_artifact(
                    "runs/artifact",
                    frozen_at_commit="b" * 40,
                )
                with self.assertRaisesRegex(ValueError, "cannot be verified"):
                    FREEZE.freeze_artifact(
                        "runs/artifact",
                        frozen_at_commit="b" * 40,
                        source_commit="a" * 40,
                    )

            metadata = json.loads((root / frozen / "baseline.json").read_text(encoding="utf-8"))
            self.assertIsNone(metadata["source_commit"])
            self.assertFalse(metadata["source_commit_recorded"])


if __name__ == "__main__":
    unittest.main()
