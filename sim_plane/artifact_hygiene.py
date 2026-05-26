import json
import shutil
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "runs"
DEFAULT_REFERENCE_SEARCH_PATHS = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs",
    REPO_ROOT / ".agent",
    REPO_ROOT / ".supervisor",
)
DEFAULT_RESERVED_ROOT_NAMES = {
    "acceptance",
    "human_follow_stage1_acceptance",
    "human_follow_stage1_detector_tracker_acceptance",
    "human_follow_stage2_acceptance",
    "human_follow_stage2_integrated_acceptance",
    "live_smoke",
    "manual_probes",
    "platform_acceptance",
}
DEFAULT_MANUAL_PROBE_ROOT_NAME = "manual_probes"
REQUIRED_ARTIFACT_FILES = (
    "manifest.json",
    "result.json",
    "events.jsonl",
)
MANUAL_SIGNAL_FILES = {
    "telemetry.jsonl",
    "smoke_probe.json",
    "run_meta.txt",
    "roslaunch.log",
    "roslaunch.stdout.log",
    "roslaunch.stderr.log",
    "odom_sample.txt",
    "local_cloud_sample.txt",
    "global_cloud_sample.txt",
}
MANUAL_SIGNAL_DIRS = {
    "ros_home",
    "ros_logs",
}
MANUAL_PROBE_META_FILE = "probe_meta.json"


def scan_artifact_root(
    artifact_root=None,
    reference_search_paths=None,
    reserved_root_names=None,
):
    artifact_root_path = Path(artifact_root) if artifact_root is not None else DEFAULT_ARTIFACT_ROOT
    reserved_names = set(reserved_root_names or DEFAULT_RESERVED_ROOT_NAMES)
    search_paths = tuple(reference_search_paths or DEFAULT_REFERENCE_SEARCH_PATHS)
    entries = []
    if artifact_root_path.exists():
        for path in sorted(artifact_root_path.iterdir()):
            if not path.is_dir():
                continue
            entries.append(
                classify_artifact_directory(
                    path,
                    reference_search_paths=search_paths,
                    reserved_root_names=reserved_names,
                )
            )
    summary = build_scan_summary(entries)
    return {
        "artifact_root": str(artifact_root_path),
        "status": "clean" if summary["attention_count"] == 0 else "attention_needed",
        "summary": summary,
        "entries": entries,
    }


def classify_artifact_directory(
    path,
    reference_search_paths=None,
    reserved_root_names=None,
):
    directory_path = Path(path)
    reserved_names = set(reserved_root_names or DEFAULT_RESERVED_ROOT_NAMES)
    required_files = {
        name: (directory_path / name).exists()
        for name in REQUIRED_ARTIFACT_FILES
    }
    child_names = sorted(child.name for child in directory_path.iterdir())
    reference_hits = []
    if directory_path.name not in reserved_names and not all(required_files.values()):
        reference_hits = find_reference_hits(
            directory_path.name,
            reference_search_paths=reference_search_paths,
        )
    has_manual_signals = any(name in MANUAL_SIGNAL_FILES for name in child_names) or any(
        name in MANUAL_SIGNAL_DIRS for name in child_names
    )
    missing_required_files = [
        name
        for name, present in required_files.items()
        if not present
    ]
    category = "stale_incomplete_directory"
    clean = False
    safe_to_prune = True
    reason = "unreferenced incomplete directory"

    if directory_path.name in reserved_names:
        category = "reserved_root"
        clean = True
        safe_to_prune = False
        reason = "reserved non-artifact root"
    elif all(required_files.values()):
        category = "complete_artifact"
        clean = True
        safe_to_prune = False
        reason = "required artifact files present"
    elif reference_hits:
        category = "retained_manual_probe"
        clean = False
        safe_to_prune = False
        reason = "incomplete directory is referenced by repo docs or control files"
    elif not child_names:
        category = "empty_directory"
        clean = False
        safe_to_prune = True
        reason = "empty directory under artifact root"
    elif has_manual_signals:
        category = "stale_manual_probe"
        clean = False
        safe_to_prune = True
        reason = "manual probe directory is unreferenced and safe to prune"

    return {
        "name": directory_path.name,
        "path": str(directory_path),
        "category": category,
        "clean": clean,
        "safe_to_prune": safe_to_prune,
        "required_files": required_files,
        "missing_required_files": missing_required_files,
        "reference_hits": reference_hits,
        "reason": reason,
    }


def find_reference_hits(directory_name, reference_search_paths=None):
    hits = []
    search_paths = reference_search_paths or DEFAULT_REFERENCE_SEARCH_PATHS
    for search_path in search_paths:
        path = Path(search_path)
        if not path.exists():
            continue
        if path.is_file():
            candidate_paths = [path]
        else:
            candidate_paths = [item for item in path.rglob("*") if item.is_file()]
        for candidate_path in candidate_paths:
            try:
                text = candidate_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                display_path = candidate_path.relative_to(REPO_ROOT)
            except ValueError:
                display_path = candidate_path
            for line_number, line in enumerate(text.splitlines(), start=1):
                if directory_name in line:
                    hits.append("{0}:{1}".format(display_path, line_number))
    return hits


def build_scan_summary(entries):
    counts = Counter(entry["category"] for entry in entries)
    return {
        "reserved_root_count": counts.get("reserved_root", 0),
        "complete_artifact_count": counts.get("complete_artifact", 0),
        "retained_manual_probe_count": counts.get("retained_manual_probe", 0),
        "stale_manual_probe_count": counts.get("stale_manual_probe", 0),
        "stale_incomplete_directory_count": counts.get("stale_incomplete_directory", 0),
        "empty_directory_count": counts.get("empty_directory", 0),
        "attention_count": sum(0 if entry["clean"] else 1 for entry in entries),
    }


def scan_manual_probe_root(
    artifact_root=None,
    manual_probe_root_name=DEFAULT_MANUAL_PROBE_ROOT_NAME,
    reference_search_paths=None,
):
    artifact_root_path = Path(artifact_root) if artifact_root is not None else DEFAULT_ARTIFACT_ROOT
    manual_probe_root = artifact_root_path / manual_probe_root_name
    search_paths = tuple(reference_search_paths or DEFAULT_REFERENCE_SEARCH_PATHS)
    raw_entries = []
    if manual_probe_root.exists():
        for path in sorted(manual_probe_root.iterdir()):
            if not path.is_dir():
                continue
            raw_entries.append(
                read_manual_probe_directory(
                    path,
                    reference_search_paths=search_paths,
                )
            )
    latest_success_by_probe = {}
    for entry in raw_entries:
        probe_meta = entry["probe_meta"]
        if not probe_meta:
            continue
        if probe_meta.get("retention") != "keep_latest_success":
            continue
        if probe_meta.get("status") != "passed":
            continue
        probe_name = probe_meta.get("probe_name")
        if not probe_name:
            continue
        current = latest_success_by_probe.get(probe_name)
        if current is None or entry["name"] > current["name"]:
            latest_success_by_probe[probe_name] = entry
    entries = [
        classify_manual_probe_directory(
            entry,
            latest_success_by_probe=latest_success_by_probe,
        )
        for entry in raw_entries
    ]
    summary = build_manual_probe_summary(entries)
    return {
        "artifact_root": str(artifact_root_path),
        "manual_probe_root": str(manual_probe_root),
        "status": "clean" if summary["attention_count"] == 0 else "attention_needed",
        "summary": summary,
        "entries": entries,
    }


def read_manual_probe_directory(path, reference_search_paths=None):
    directory_path = Path(path)
    child_names = sorted(child.name for child in directory_path.iterdir())
    reference_hits = find_reference_hits(
        directory_path.name,
        reference_search_paths=reference_search_paths,
    )
    probe_meta = {}
    probe_meta_path = directory_path / MANUAL_PROBE_META_FILE
    if probe_meta_path.exists():
        try:
            probe_meta = json.loads(probe_meta_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            probe_meta = {}
    return {
        "name": directory_path.name,
        "path": str(directory_path),
        "reference_hits": reference_hits,
        "probe_meta": probe_meta,
        "file_count": len(child_names),
    }


def classify_manual_probe_directory(entry, latest_success_by_probe=None):
    latest_success_map = latest_success_by_probe or {}
    probe_meta = entry["probe_meta"]
    category = "retained_manual_probe"
    clean = True
    safe_to_prune = False
    reason = "manual probe is referenced by repo docs or control files"
    if entry["reference_hits"]:
        reason = "manual probe is referenced by repo docs or control files"
    elif probe_meta.get("retention") == "keep_latest_success":
        probe_name = probe_meta.get("probe_name")
        latest_entry = latest_success_map.get(probe_name)
        if probe_meta.get("status") == "passed" and latest_entry is not None and latest_entry["name"] == entry["name"]:
            reason = "manual probe is the latest successful canonical result for its probe name"
        else:
            category = "stale_manual_probe"
            clean = False
            safe_to_prune = True
            reason = "manual probe has been superseded by a newer canonical result"
    else:
        category = "stale_manual_probe"
        clean = False
        safe_to_prune = True
        reason = "manual probe is unreferenced and superseded"
    return {
        "name": entry["name"],
        "path": entry["path"],
        "category": category,
        "clean": clean,
        "safe_to_prune": safe_to_prune,
        "reference_hits": entry["reference_hits"],
        "probe_meta": probe_meta,
        "file_count": entry["file_count"],
        "reason": reason,
    }


def build_manual_probe_summary(entries):
    counts = Counter(entry["category"] for entry in entries)
    return {
        "retained_manual_probe_count": counts.get("retained_manual_probe", 0),
        "stale_manual_probe_count": counts.get("stale_manual_probe", 0),
        "attention_count": sum(0 if entry["clean"] else 1 for entry in entries),
    }


def apply_artifact_hygiene(
    artifact_root=None,
    migrate_retained_manual=False,
    prune_safe=False,
    manual_probe_root_name="manual_probes",
    reference_search_paths=None,
    reserved_root_names=None,
):
    artifact_root_path = Path(artifact_root) if artifact_root is not None else DEFAULT_ARTIFACT_ROOT
    reserved_names = set(reserved_root_names or DEFAULT_RESERVED_ROOT_NAMES)
    reserved_names.add(manual_probe_root_name)
    search_paths = tuple(reference_search_paths or DEFAULT_REFERENCE_SEARCH_PATHS)

    before = scan_artifact_root(
        artifact_root=artifact_root_path,
        reference_search_paths=search_paths,
        reserved_root_names=reserved_names,
    )
    actions = {
        "migrated": [],
        "pruned": [],
        "skipped": [],
    }

    if migrate_retained_manual:
        manual_probe_root = artifact_root_path / manual_probe_root_name
        for entry in before["entries"]:
            if entry["category"] != "retained_manual_probe":
                continue
            source = Path(entry["path"])
            destination = manual_probe_root / source.name
            if destination.exists():
                actions["skipped"].append(
                    {
                        "action": "migrate",
                        "path": str(source),
                        "reason": "destination already exists",
                    }
                )
                continue
            manual_probe_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            actions["migrated"].append(
                {
                    "from": str(source),
                    "to": str(destination),
                }
            )

    if prune_safe:
        after_migration = scan_artifact_root(
            artifact_root=artifact_root_path,
            reference_search_paths=search_paths,
            reserved_root_names=reserved_names,
        )
        for entry in after_migration["entries"]:
            if not entry["safe_to_prune"]:
                continue
            target = Path(entry["path"])
            shutil.rmtree(target)
            actions["pruned"].append(str(target))

    after = scan_artifact_root(
        artifact_root=artifact_root_path,
        reference_search_paths=search_paths,
        reserved_root_names=reserved_names,
    )
    return {
        "artifact_root": str(artifact_root_path),
        "manual_probe_root_name": manual_probe_root_name,
        "status": after["status"],
        "before": before,
        "after": after,
        "actions": actions,
    }


def apply_manual_probe_hygiene(
    artifact_root=None,
    manual_probe_root_name=DEFAULT_MANUAL_PROBE_ROOT_NAME,
    prune_safe=False,
    reference_search_paths=None,
):
    artifact_root_path = Path(artifact_root) if artifact_root is not None else DEFAULT_ARTIFACT_ROOT
    search_paths = tuple(reference_search_paths or DEFAULT_REFERENCE_SEARCH_PATHS)
    before = scan_manual_probe_root(
        artifact_root=artifact_root_path,
        manual_probe_root_name=manual_probe_root_name,
        reference_search_paths=search_paths,
    )
    actions = {
        "pruned": [],
    }
    if prune_safe:
        for entry in before["entries"]:
            if not entry["safe_to_prune"]:
                continue
            target = Path(entry["path"])
            shutil.rmtree(target)
            actions["pruned"].append(str(target))
    after = scan_manual_probe_root(
        artifact_root=artifact_root_path,
        manual_probe_root_name=manual_probe_root_name,
        reference_search_paths=search_paths,
    )
    return {
        "artifact_root": str(artifact_root_path),
        "manual_probe_root_name": manual_probe_root_name,
        "status": after["status"],
        "before": before,
        "after": after,
        "actions": actions,
    }


def format_artifact_hygiene_report(report):
    before = report["before"]
    after = report["after"]
    lines = [
        "artifact hygiene: {0}".format(report["status"]),
        "artifact_root: {0}".format(report["artifact_root"]),
        "before: attention={0} complete={1} reserved_roots={2}".format(
            before["summary"]["attention_count"],
            before["summary"]["complete_artifact_count"],
            before["summary"]["reserved_root_count"],
        ),
        "after: attention={0} complete={1} reserved_roots={2}".format(
            after["summary"]["attention_count"],
            after["summary"]["complete_artifact_count"],
            after["summary"]["reserved_root_count"],
        ),
    ]

    if report["actions"]["migrated"]:
        lines.append("migrated manual probes:")
        for item in report["actions"]["migrated"]:
            lines.append("- {0} -> {1}".format(item["from"], item["to"]))
    if report["actions"]["pruned"]:
        lines.append("pruned safe directories:")
        for item in report["actions"]["pruned"]:
            lines.append("- {0}".format(item))
    if report["actions"]["skipped"]:
        lines.append("skipped actions:")
        for item in report["actions"]["skipped"]:
            lines.append("- {0}: {1}".format(item["path"], item["reason"]))

    remaining_attention = [entry for entry in after["entries"] if not entry["clean"]]
    if remaining_attention:
        lines.append("remaining attention:")
        for entry in remaining_attention:
            lines.append(
                "- {0}: {1} ({2})".format(
                    entry["name"],
                    entry["category"],
                    entry["reason"],
                )
            )
            if entry["reference_hits"]:
                lines.append(
                    "  references: {0}".format(", ".join(entry["reference_hits"]))
                )
    return "\n".join(lines)


def format_manual_probe_hygiene_report(report):
    before = report["before"]
    after = report["after"]
    lines = [
        "manual probe hygiene: {0}".format(report["status"]),
        "artifact_root: {0}".format(report["artifact_root"]),
        "manual_probe_root: {0}".format(before["manual_probe_root"]),
        "before: attention={0} retained={1} stale={2}".format(
            before["summary"]["attention_count"],
            before["summary"]["retained_manual_probe_count"],
            before["summary"]["stale_manual_probe_count"],
        ),
        "after: attention={0} retained={1} stale={2}".format(
            after["summary"]["attention_count"],
            after["summary"]["retained_manual_probe_count"],
            after["summary"]["stale_manual_probe_count"],
        ),
    ]
    if report["actions"]["pruned"]:
        lines.append("pruned stale manual probes:")
        for item in report["actions"]["pruned"]:
            lines.append("- {0}".format(item))
    remaining_attention = [entry for entry in after["entries"] if not entry["clean"]]
    if remaining_attention:
        lines.append("remaining attention:")
        for entry in remaining_attention:
            lines.append(
                "- {0}: {1} ({2})".format(
                    entry["name"],
                    entry["category"],
                    entry["reason"],
                )
            )
    return "\n".join(lines)


def dump_artifact_hygiene_report(report):
    return json.dumps(report, indent=2, ensure_ascii=False)
