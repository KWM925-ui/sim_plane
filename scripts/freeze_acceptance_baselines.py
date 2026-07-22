#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_FILES = ("manifest.json", "result.json", "events.jsonl")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root):
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        text=True,
    ).strip()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def repo_path(value):
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def relative_repo_path(path):
    return str(Path(path).resolve().relative_to(REPO_ROOT.resolve()))


def verified_source_commit(payload, expected_commit=None):
    source_control = payload.get("source_control")
    commit = None
    if (
        isinstance(source_control, dict)
        and source_control.get("kind") == "git"
        and source_control.get("recorded") is True
        and source_control.get("dirty") is False
        and isinstance(source_control.get("commit"), str)
        and re.fullmatch(r"[0-9a-fA-F]{40}", source_control["commit"])
    ):
        commit = source_control["commit"].lower()

    if expected_commit is not None:
        expected = str(expected_commit).lower()
        if commit is None:
            raise ValueError(
                "source commit cannot be verified from clean source-control evidence"
            )
        if commit != expected:
            raise ValueError(
                "source commit mismatch: expected {0}, recorded {1}".format(
                    expected,
                    commit,
                )
            )
    return commit


def freeze_artifact(source_value, frozen_at_commit, source_commit=None):
    source_dir = repo_path(source_value)
    if not source_dir.is_dir():
        raise FileNotFoundError("reference artifact is missing: {0}".format(source_dir))

    source_manifest = load_json(source_dir / "manifest.json")
    verified_commit = verified_source_commit(source_manifest, source_commit)
    destination = REPO_ROOT / "baselines" / "artifacts" / source_dir.name
    destination.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for name in ARTIFACT_FILES:
        source_file = source_dir / name
        if not source_file.is_file():
            raise FileNotFoundError("reference artifact file is missing: {0}".format(source_file))
        destination_file = destination / name
        shutil.copyfile(str(source_file), str(destination_file))
        checksums[name] = sha256_file(destination_file)

    result = load_json(destination / "result.json")
    write_json(
        destination / "baseline.json",
        {
            "schema_version": 2,
            "kind": "sim_plane_acceptance_artifact",
            "source_artifact": relative_repo_path(source_dir),
            "source_commit": verified_commit,
            "source_commit_recorded": verified_commit is not None,
            "frozen_at_commit": frozen_at_commit,
            "source_written_at_utc": result.get("written_at_utc"),
            "files": checksums,
        },
    )
    return relative_repo_path(destination)


def freeze_report(source_value, frozen_at_commit, source_commit=None):
    source_file = repo_path(source_value)
    if not source_file.is_file():
        raise FileNotFoundError("reference report is missing: {0}".format(source_file))

    source_report = load_json(source_file)
    verified_commit = verified_source_commit(source_report, source_commit)
    destination = REPO_ROOT / "baselines" / "reports" / source_file.parent.name
    destination.mkdir(parents=True, exist_ok=True)
    destination_file = destination / source_file.name
    shutil.copyfile(str(source_file), str(destination_file))
    report = load_json(destination_file)
    write_json(
        destination / "baseline.json",
        {
            "schema_version": 2,
            "kind": "sim_plane_acceptance_report",
            "source_report": relative_repo_path(source_file),
            "source_commit": verified_commit,
            "source_commit_recorded": verified_commit is not None,
            "frozen_at_commit": frozen_at_commit,
            "source_written_at_utc": report.get("written_at_utc") or report.get("created_at_utc"),
            "files": {source_file.name: sha256_file(destination_file)},
        },
    )
    return relative_repo_path(destination_file)


def freeze_artifact_matrix(matrix_path, frozen_at_commit, source_commit=None, nested_modes=False):
    payload = load_json(matrix_path)
    for row in payload.get("rows", []):
        specs = [row.get("headless", {}), row.get("visual", {})] if nested_modes else [row]
        for spec in specs:
            source = spec.get("source_artifact") or spec.get("reference_artifact")
            if not source:
                raise ValueError("matrix reference artifact is missing in {0}".format(matrix_path))
            if not spec.get("source_artifact"):
                spec["source_artifact"] = source
            spec["reference_artifact"] = freeze_artifact(
                spec["source_artifact"],
                frozen_at_commit=frozen_at_commit,
                source_commit=source_commit,
            )
    write_json(matrix_path, payload)


def freeze_exam_matrix(matrix_path, frozen_at_commit, source_commit=None):
    payload = load_json(matrix_path)
    source = payload.get("source_reference_report") or payload.get("reference_report")
    if not source:
        raise ValueError("matrix reference report is missing in {0}".format(matrix_path))
    if not payload.get("source_reference_report"):
        payload["source_reference_report"] = source
    payload["reference_report"] = freeze_report(
        payload["source_reference_report"],
        frozen_at_commit=frozen_at_commit,
        source_commit=source_commit,
    )
    write_json(matrix_path, payload)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Freeze compact, version-controlled acceptance baselines from retained run evidence."
    )
    parser.add_argument(
        "--source-commit",
        help="Expected artifact-producing commit; it must match clean source evidence and never creates provenance",
    )
    args = parser.parse_args(argv)
    frozen_at_commit = git_head(REPO_ROOT)
    source_commit = args.source_commit

    freeze_artifact_matrix(
        REPO_ROOT / "configs" / "planner_acceptance_matrix.json",
        frozen_at_commit,
        source_commit=source_commit,
        nested_modes=True,
    )
    freeze_artifact_matrix(
        REPO_ROOT / "configs" / "platform_acceptance_matrix.json",
        frozen_at_commit,
        source_commit=source_commit,
    )
    freeze_artifact_matrix(
        REPO_ROOT / "configs" / "px4_failure_injection_acceptance_matrix.json",
        frozen_at_commit,
        source_commit=source_commit,
    )
    freeze_exam_matrix(
        REPO_ROOT / "configs" / "quadrotor_exam_acceptance_matrix.json",
        frozen_at_commit,
        source_commit=source_commit,
    )
    print("acceptance baselines frozen under {0}".format(REPO_ROOT / "baselines"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
