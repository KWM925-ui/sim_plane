import hashlib
import json
from pathlib import Path


BASELINE_META_FILE = "baseline.json"
BASELINE_SCHEMA_VERSION = 2
ARTIFACT_BASELINE_KIND = "sim_plane_acceptance_artifact"
REPORT_BASELINE_KIND = "sim_plane_acceptance_report"
ARTIFACT_BASELINE_FILES = {"manifest.json", "result.json", "events.jsonl"}
REPORT_BASELINE_FILES = {"report.json"}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact_baseline(artifact_dir, expected_source_artifact=None):
    return verify_baseline_metadata(
        Path(artifact_dir) / BASELINE_META_FILE,
        expected_kind=ARTIFACT_BASELINE_KIND,
        content_root=Path(artifact_dir),
        required_files=ARTIFACT_BASELINE_FILES,
        source_key="source_artifact",
        expected_source=expected_source_artifact,
    )


def verify_report_baseline(report_path, expected_source_report=None):
    path = Path(report_path)
    return verify_baseline_metadata(
        path.parent / BASELINE_META_FILE,
        expected_kind=REPORT_BASELINE_KIND,
        content_root=path.parent,
        required_files=REPORT_BASELINE_FILES,
        source_key="source_report",
        expected_source=expected_source_report,
    )


def verify_baseline_metadata(
    meta_path,
    expected_kind,
    content_root,
    required_files,
    source_key,
    expected_source=None,
):
    metadata_path = Path(meta_path)
    if not metadata_path.exists():
        return ["baseline metadata is missing: {0}".format(metadata_path.name)]

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ["baseline metadata is unreadable: {0}".format(exc)]

    issues = []
    if metadata.get("schema_version") != BASELINE_SCHEMA_VERSION:
        issues.append(
            "baseline schema_version mismatch: expected {0}, got {1}".format(
                BASELINE_SCHEMA_VERSION,
                metadata.get("schema_version")
            )
        )
    if metadata.get("kind") != expected_kind:
        issues.append(
            "baseline kind mismatch: expected {0}, got {1}".format(
                expected_kind,
                metadata.get("kind"),
            )
        )
    if not metadata.get("frozen_at_commit"):
        issues.append("baseline frozen_at_commit is missing")
    source_commit_recorded = metadata.get("source_commit_recorded")
    if not isinstance(source_commit_recorded, bool):
        issues.append("baseline source_commit_recorded must be a boolean")
    elif source_commit_recorded and not metadata.get("source_commit"):
        issues.append("baseline source_commit is missing despite source_commit_recorded=true")
    elif not source_commit_recorded and metadata.get("source_commit") is not None:
        issues.append("baseline source_commit must be null when source_commit_recorded=false")
    source_identity = metadata.get(source_key)
    if not source_identity:
        issues.append("baseline {0} is missing".format(source_key))
    elif expected_source is not None and normalize_source_identity(source_identity) != normalize_source_identity(expected_source):
        issues.append(
            "baseline {0} mismatch: expected {1}, got {2}".format(
                source_key,
                expected_source,
                source_identity,
            )
        )

    files = metadata.get("files")
    if not isinstance(files, dict) or not files:
        issues.append("baseline file checksums are missing")
        return issues

    actual_file_names = set(files)
    missing_file_names = sorted(set(required_files) - actual_file_names)
    unsupported_file_names = sorted(actual_file_names - set(required_files))
    if missing_file_names:
        issues.append(
            "baseline required checksum entries are missing: {0}".format(
                ", ".join(missing_file_names)
            )
        )
    if unsupported_file_names:
        issues.append(
            "baseline checksum entries are unsupported: {0}".format(
                ", ".join(unsupported_file_names)
            )
        )

    root = Path(content_root)
    for name, expected_digest in sorted(files.items()):
        if name not in required_files:
            continue
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            issues.append("baseline checksum is invalid for {0}".format(name))
            continue
        path = root / name
        if not path.is_file():
            issues.append("baseline content file is missing: {0}".format(name))
            continue
        actual_digest = sha256_file(path)
        if actual_digest != expected_digest:
            issues.append(
                "baseline checksum mismatch for {0}: expected {1}, got {2}".format(
                    name,
                    expected_digest,
                    actual_digest,
                )
            )
    return issues


def normalize_source_identity(value):
    return Path(str(value)).as_posix()
