import json
import shutil
from datetime import datetime
from pathlib import Path

from sim_plane.io_utils import atomic_write_json


DEFAULT_LOG_DIR_NAME = "px4_ulog"


def utc_timestamp():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_px4_ulog_files(config):
    snapshot = {}
    for path in discover_px4_ulog_files(config):
        stat = safe_stat(path)
        if stat is None:
            continue
        snapshot[str(path)] = {
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return snapshot


def discover_px4_ulog_files(config):
    paths = []
    for root in px4_ulog_search_roots(config):
        try:
            root_exists = root.is_dir()
        except OSError:
            continue
        if not root_exists:
            continue
        try:
            candidates = list(root.glob("**/*.ulg"))
        except OSError:
            continue
        paths.extend(candidates)
    discovered = set()
    for path in paths:
        try:
            if path.is_file():
                discovered.add(path.resolve())
        except OSError:
            continue
    return sorted(discovered)


def px4_ulog_search_roots(config):
    roots = []
    build_dir = config.get("build_dir")
    if build_dir:
        roots.extend(px4_ulog_roots_for_build_dir(Path(build_dir)))
    px4_dir = config.get("px4_dir")
    build_target = config.get("build_target")
    if px4_dir and build_target:
        roots.extend(px4_ulog_roots_for_build_dir(Path(px4_dir) / "build" / str(build_target)))
    deduped = []
    seen = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            deduped.append(root)
    return deduped


def px4_ulog_roots_for_build_dir(build_dir):
    return [
        build_dir / "rootfs" / "fs" / "microsd" / "log",
        build_dir / "rootfs" / "log",
    ]


def collect_px4_ulog_artifacts(config, artifact_dir, before_snapshot=None, sink=None, label="px4"):
    artifact_path = Path(artifact_dir)
    before_snapshot = before_snapshot or {}
    report = build_px4_ulog_report(config, label=label)
    if config.get("collect_ulog") is False:
        report["status"] = "disabled"
        report["issues"].append("PX4 ULog collection is disabled by backend_options.collect_ulog=false.")
        write_px4_ulog_index(artifact_path, report)
        update_manifest_with_px4_ulog(artifact_path, report)
        return report

    selected = select_new_or_changed_ulog_files(config, before_snapshot)
    if not selected:
        report["issues"].append("No new or changed PX4 .ulg file was found under the configured PX4 SITL rootfs log directories.")
        write_px4_ulog_index(artifact_path, report)
        update_manifest_with_px4_ulog(artifact_path, report)
        emit_px4_ulog_event(sink, "warning", "px4 ulog collection found no log", report)
        return report

    output_dir = artifact_path / DEFAULT_LOG_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in selected:
        try:
            copied_path = copy_ulog_file(source, output_dir)
            stat = copied_path.stat()
            report["files"].append(
                {
                    "source_path": str(source),
                    "artifact_path": str(copied_path.relative_to(artifact_path)),
                    "size_bytes": stat.st_size,
                    "modified_at_utc": datetime.utcfromtimestamp(copied_path.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
        except OSError as exc:
            report["issues"].append("failed to copy {0}: {1}".format(source, exc))

    report["count"] = len(report["files"])
    report["status"] = "collected" if report["files"] else "failed"
    write_px4_ulog_index(artifact_path, report)
    update_manifest_with_px4_ulog(artifact_path, report)
    event_level = "info" if report["status"] == "collected" else "warning"
    emit_px4_ulog_event(sink, event_level, "px4 ulog collection finished", report)
    return report


def collect_px4_ulog_artifacts_safely(config, artifact_dir, before_snapshot=None, sink=None, label="px4"):
    try:
        return collect_px4_ulog_artifacts(
            config,
            artifact_dir,
            before_snapshot=before_snapshot,
            sink=sink,
            label=label,
        )
    except Exception as exc:  # keep raw-log collection from changing the run verdict
        report = build_px4_ulog_report(config, label=label)
        report["status"] = "failed"
        report["issues"].append(
            "PX4 ULog collection failed without changing the simulation verdict: {0}".format(exc)
        )
        try:
            write_px4_ulog_index(artifact_dir, report)
            update_manifest_with_px4_ulog(artifact_dir, report)
        except Exception:
            pass
        try:
            emit_px4_ulog_event(sink, "warning", "px4 ulog collection failed", report)
        except Exception:
            pass
        return report


def build_px4_ulog_report(config, label="px4"):
    return {
        "status": "missing",
        "collected_at_utc": utc_timestamp(),
        "label": label,
        "search_roots": [str(root) for root in px4_ulog_search_roots(config)],
        "count": 0,
        "files": [],
        "issues": [],
    }


def select_new_or_changed_ulog_files(config, before_snapshot):
    selected = []
    stats_by_path = {}
    for path in discover_px4_ulog_files(config):
        stat = safe_stat(path)
        if stat is None:
            continue
        stats_by_path[path] = stat
        previous = before_snapshot.get(str(path))
        if previous is None or previous.get("size_bytes") != stat.st_size or previous.get("mtime_ns") != stat.st_mtime_ns:
            selected.append(path)
    selected.sort(key=lambda item: stats_by_path[item].st_mtime_ns, reverse=True)
    max_files = int(config.get("collect_ulog_max_files", 3))
    return selected[: max(max_files, 0)]


def copy_ulog_file(source, output_dir):
    source = Path(source)
    target = output_dir / source.name
    if target.exists():
        target = output_dir / "{0}_{1}{2}".format(source.stem, int(source.stat().st_mtime_ns), source.suffix)
    shutil.copy2(str(source), str(target))
    return target


def write_px4_ulog_index(artifact_dir, report):
    index_dir = Path(artifact_dir) / DEFAULT_LOG_DIR_NAME
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "index.json"
    atomic_write_json(index_path, report)
    return index_path


def read_px4_ulog_index(artifact_dir):
    index_path = Path(artifact_dir) / DEFAULT_LOG_DIR_NAME / "index.json"
    if not index_path.exists():
        return {
            "available": False,
            "status": "missing",
            "count": 0,
            "files": [],
            "index_path": str(index_path),
        }
    try:
        report = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "available": False,
            "status": "invalid",
            "count": 0,
            "files": [],
            "index_path": str(index_path),
        }
    summary = dict(report)
    summary["available"] = bool(report.get("files"))
    summary["index_path"] = str(index_path)
    return summary


def update_manifest_with_px4_ulog(artifact_dir, report):
    manifest_path = Path(artifact_dir) / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    files = dict(manifest.get("files") or {})
    files["px4_ulog_index"] = "{0}/index.json".format(DEFAULT_LOG_DIR_NAME)
    for index, item in enumerate(report.get("files", []), start=1):
        files["px4_ulog_{0}".format(index)] = item.get("artifact_path")
    manifest["files"] = files
    manifest["px4_ulog"] = {
        "status": report.get("status"),
        "count": report.get("count", 0),
        "index": "{0}/index.json".format(DEFAULT_LOG_DIR_NAME),
    }
    atomic_write_json(manifest_path, manifest)


def px4_ulog_metrics(report):
    files = report.get("files", []) if isinstance(report, dict) else []
    return {
        "px4_ulog_collected": bool(files),
        "px4_ulog_count": len(files),
        "px4_ulog_total_bytes": sum(int(item.get("size_bytes") or 0) for item in files),
    }


def px4_ulog_note(report):
    if not isinstance(report, dict):
        return "PX4 ULog collection did not produce a report."
    if report.get("files"):
        return "PX4 ULog collection copied {0} .ulg file(s) into {1}/.".format(
            len(report["files"]),
            DEFAULT_LOG_DIR_NAME,
        )
    return "PX4 ULog collection did not find a new .ulg file for this run; see {0}/index.json.".format(DEFAULT_LOG_DIR_NAME)


def safe_stat(path):
    try:
        return Path(path).stat()
    except OSError:
        return None


def emit_px4_ulog_event(sink, level, message, report):
    if sink is None:
        return
    sink.emit_event(
        level,
        message,
        {
            "status": report.get("status"),
            "count": report.get("count", 0),
            "issues": report.get("issues", []),
            "index": "{0}/index.json".format(DEFAULT_LOG_DIR_NAME),
        },
    )
