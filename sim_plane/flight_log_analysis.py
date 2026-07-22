import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from sim_plane.io_utils import atomic_write_json, atomic_write_text, append_jsonl, prune_directories, report_write_lock
from sim_plane.paths import get_platform_paths, resolve_platform_path

from sim_plane.artifacts import read_jsonl
from sim_plane.evaluation import compute_kpis


REPO_ROOT = get_platform_paths().home
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "flight_log_analysis"
DEFAULT_KEEP_LAST = 10


def analyze_flight_log(
    source,
    report_root=None,
    keep_last=DEFAULT_KEEP_LAST,
    save_report=True,
):
    source_path = resolve_platform_path(source)
    if not source_path.exists():
        raise ValueError("flight-log source does not exist: {0}".format(source))
    if source_path.is_dir():
        report = analyze_artifact_directory(source_path)
    elif source_path.suffix.lower() == ".ulg":
        report = analyze_ulog_file(source_path)
    else:
        raise ValueError("flight-log source must be a run artifact directory or .ulg file")
    if save_report:
        report["saved_report"] = write_flight_log_report(
            report,
            report_root=report_root,
            keep_last=keep_last,
        )
    return report


def analyze_artifact_directory(artifact_dir):
    artifact_path = Path(artifact_dir)
    manifest = load_json_or_empty(artifact_path / "manifest.json")
    scenario = load_json_or_empty(artifact_path / "scenario.json")
    result = load_json_or_empty(artifact_path / "result.json")
    telemetry = read_jsonl(artifact_path / "telemetry.jsonl")
    events = read_jsonl(artifact_path / "events.jsonl")
    metrics = dict(result.get("metrics") or {})
    kpis = compute_kpis(scenario, telemetry)
    mode_changes = count_field_changes(telemetry, "mode")
    armed_transitions = count_field_changes(telemetry, "armed")
    event_levels = Counter(str(event.get("level", "unknown")) for event in events)
    anomaly_events = [
        event
        for event in events
        if str(event.get("level", "")).lower() in {"warning", "error", "critical"}
    ]
    analysis_metrics = build_telemetry_metrics(telemetry)
    analysis_metrics.update(
        {
            "telemetry_count": len(telemetry),
            "event_count": len(events),
            "mode_change_count": mode_changes,
            "armed_transition_count": armed_transitions,
            "anomaly_event_count": len(anomaly_events),
            "kpi_count": len(kpis),
        }
    )
    analysis_metrics.update(prefix_mapping(kpis, "replay_"))
    return {
        "source_type": "artifact",
        "source": str(artifact_path),
        "status": "passed" if telemetry else "failed",
        "issues": [] if telemetry else ["artifact telemetry.jsonl is empty or missing"],
        "artifact": {
            "name": artifact_path.name,
            "backend": result.get("backend") or manifest.get("backend") or scenario.get("backend"),
            "vehicle": result.get("vehicle") or manifest.get("vehicle") or scenario.get("vehicle"),
            "scenario_name": result.get("scenario_name") or manifest.get("scenario_name") or scenario.get("name"),
            "run_status": result.get("status"),
        },
        "metrics": analysis_metrics,
        "event_levels": dict(event_levels),
        "mode_timeline": summarize_field_timeline(telemetry, "mode"),
        "armed_timeline": summarize_field_timeline(telemetry, "armed"),
        "result_metrics": metrics,
        "kpis": kpis,
        "anomaly_events": anomaly_events[:20],
        "notes": [
            "Artifact replay uses telemetry.jsonl/result.json/events.jsonl from a sim_plane run.",
            "This does not prove PX4 .ulg collection unless source_type is ulog.",
        ],
    }


def analyze_ulog_file(path):
    try:
        from pyulog import ULog
    except ImportError as exc:
        raise ValueError("pyulog is required to analyze .ulg files: {0}".format(exc))
    ulog_path = Path(path)
    ulog = ULog(
        str(ulog_path),
        message_name_filter_list=[
            "vehicle_local_position",
            "vehicle_status",
            "vehicle_land_detected",
            "failsafe_flags",
        ],
        disable_str_exceptions=True,
    )
    datasets = {dataset.name: dataset for dataset in ulog.data_list}
    local_position = dataset_data(datasets.get("vehicle_local_position"))
    vehicle_status = dataset_data(datasets.get("vehicle_status"))
    telemetry = telemetry_from_ulog(local_position)
    status_summary = summarize_vehicle_status(vehicle_status)
    kpis = compute_kpis({}, telemetry)
    logged_messages = [
        {
            "timestamp": jsonable_scalar(getattr(message, "timestamp", None)),
            "level": jsonable_scalar(getattr(message, "log_level", None)),
            "message": str(getattr(message, "message", "")),
        }
        for message in getattr(ulog, "logged_messages", [])
    ]
    warning_messages = [message for message in logged_messages if is_warning_log_message(message)]
    metrics = build_telemetry_metrics(telemetry)
    metrics.update(
        {
            "ulog_dataset_count": len(ulog.data_list),
            "ulog_start_timestamp_us": getattr(ulog, "start_timestamp", None),
            "ulog_last_timestamp_us": getattr(ulog, "last_timestamp", None),
            "ulog_duration_s": ulog_duration_s(ulog),
            "ulog_dropout_count": len(getattr(ulog, "dropouts", []) or []),
            "ulog_logged_message_count": len(logged_messages),
            "ulog_warning_message_count": len(warning_messages),
            "vehicle_status_sample_count": status_summary.get("sample_count", 0),
            "nav_state_change_count": status_summary.get("nav_state_change_count", 0),
            "arming_state_change_count": status_summary.get("arming_state_change_count", 0),
            "kpi_count": len(kpis),
        }
    )
    metrics.update(prefix_mapping(kpis, "replay_"))
    issues = []
    if not local_position:
        issues.append("vehicle_local_position dataset is missing")
    return {
        "source_type": "ulog",
        "source": str(ulog_path),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "artifact": {
            "name": ulog_path.name,
            "backend": "px4_ulog",
            "vehicle": None,
            "scenario_name": None,
            "run_status": None,
        },
        "metrics": metrics,
        "event_levels": {},
        "mode_timeline": status_summary.get("nav_state_timeline", []),
        "armed_timeline": status_summary.get("arming_state_timeline", []),
        "result_metrics": {},
        "kpis": kpis,
        "anomaly_events": warning_messages[:20],
        "notes": [
            "ULog replay is parsed through pyulog and is independent from sim_plane telemetry artifacts.",
            "Numeric nav_state and arming_state values are kept as PX4 enum integers unless a caller maps them.",
        ],
    }


def load_json_or_empty(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build_telemetry_metrics(telemetry):
    altitudes = numbers(sample.get("altitude_m") for sample in telemetry)
    speeds = numbers(sample.get("speed_mps") for sample in telemetry)
    positions = []
    for sample in telemetry:
        position = sample.get("position") or {}
        x = as_float(position.get("x_m"))
        y = as_float(position.get("y_m"))
        z = as_float(position.get("z_m"))
        if x is not None and y is not None and z is not None:
            positions.append((x, y, z))
    return {
        "duration_s": telemetry_duration_s(telemetry),
        "max_altitude_m": round(max(altitudes), 3) if altitudes else None,
        "min_altitude_m": round(min(altitudes), 3) if altitudes else None,
        "max_speed_mps": round(max(speeds), 3) if speeds else None,
        "mean_speed_mps": round(sum(speeds) / len(speeds), 3) if speeds else None,
        "path_distance_m": round(path_distance(positions), 3),
        "final_altitude_m": round(altitudes[-1], 3) if altitudes else None,
    }


def telemetry_duration_s(telemetry):
    times = numbers(sample.get("t") for sample in telemetry)
    if len(times) < 2:
        return 0.0 if times else None
    return round(max(times) - min(times), 3)


def path_distance(points):
    distance = 0.0
    for previous, current in zip(points, points[1:]):
        distance += math.sqrt(
            (current[0] - previous[0]) ** 2
            + (current[1] - previous[1]) ** 2
            + (current[2] - previous[2]) ** 2
        )
    return distance


def count_field_changes(telemetry, field_name):
    timeline = summarize_field_timeline(telemetry, field_name)
    return max(len(timeline) - 1, 0)


def summarize_field_timeline(telemetry, field_name):
    timeline = []
    sentinel = object()
    previous = sentinel
    for sample in telemetry:
        value = sample.get(field_name)
        if value is None or value == previous:
            continue
        timeline.append({"t": sample.get("t"), "value": value})
        previous = value
    return timeline


def dataset_data(dataset):
    if dataset is None:
        return {}
    return getattr(dataset, "data", {}) or {}


def telemetry_from_ulog(local_position):
    if not local_position:
        return []
    timestamps = list(local_position.get("timestamp", []))
    xs = list(local_position.get("x", []))
    ys = list(local_position.get("y", []))
    zs = list(local_position.get("z", []))
    vxs = list(local_position.get("vx", []))
    vys = list(local_position.get("vy", []))
    vzs = list(local_position.get("vz", []))
    if not timestamps:
        return []
    start = float(timestamps[0])
    count = min(len(timestamps), len(xs), len(ys), len(zs))
    telemetry = []
    for index in range(count):
        speed = None
        if index < len(vxs) and index < len(vys) and index < len(vzs):
            speed = math.sqrt(float(vxs[index]) ** 2 + float(vys[index]) ** 2 + float(vzs[index]) ** 2)
        z = float(zs[index])
        telemetry.append(
            {
                "t": round((float(timestamps[index]) - start) / 1_000_000.0, 3),
                "position": {
                    "x_m": round(float(xs[index]), 3),
                    "y_m": round(float(ys[index]), 3),
                    "z_m": round(z, 3),
                },
                "altitude_m": round(-z, 3),
                "speed_mps": round(speed, 3) if speed is not None else None,
            }
        )
    return telemetry


def summarize_vehicle_status(vehicle_status):
    if not vehicle_status:
        return {
            "sample_count": 0,
            "nav_state_change_count": 0,
            "arming_state_change_count": 0,
            "nav_state_timeline": [],
            "arming_state_timeline": [],
        }
    timestamps = list(vehicle_status.get("timestamp", []))
    nav_states = list(vehicle_status.get("nav_state", []))
    arming_states = list(vehicle_status.get("arming_state", []))
    start = float(timestamps[0]) if timestamps else 0.0
    return {
        "sample_count": max(len(timestamps), len(nav_states), len(arming_states)),
        "nav_state_change_count": count_sequence_changes(nav_states),
        "arming_state_change_count": count_sequence_changes(arming_states),
        "nav_state_timeline": build_ulog_timeline(timestamps, nav_states, start),
        "arming_state_timeline": build_ulog_timeline(timestamps, arming_states, start),
    }


def build_ulog_timeline(timestamps, values, start_timestamp):
    timeline = []
    sentinel = object()
    previous = sentinel
    count = min(len(timestamps), len(values))
    for index in range(count):
        value = scalar_value(values[index])
        if value == previous:
            continue
        timeline.append(
            {
                "t": round((float(timestamps[index]) - start_timestamp) / 1_000_000.0, 3),
                "value": value,
            }
        )
        previous = value
    return timeline


def count_sequence_changes(values):
    timeline_count = 0
    sentinel = object()
    previous = sentinel
    for value in values:
        scalar = scalar_value(value)
        if scalar == previous:
            continue
        timeline_count += 1
        previous = scalar
    return max(timeline_count - 1, 0)


def ulog_duration_s(ulog):
    start = getattr(ulog, "start_timestamp", None)
    end = getattr(ulog, "last_timestamp", None)
    if start is None or end is None:
        return None
    return round((float(end) - float(start)) / 1_000_000.0, 3)


def numbers(values):
    result = []
    for value in values:
        converted = as_float(value)
        if converted is not None:
            result.append(converted)
    return result


def as_float(value):
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def scalar_value(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def jsonable_scalar(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        if hasattr(value, "item"):
            return value.item()
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def is_warning_log_message(message):
    text = str(message.get("message", "")).lower()
    if any(marker in text for marker in ("warn", "fail", "error", "critical", "emergency")):
        return True
    level = message.get("level")
    return isinstance(level, int) and level <= 4


def prefix_mapping(mapping, prefix):
    return {"{0}{1}".format(prefix, key): value for key, value in mapping.items()}


def write_flight_log_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = resolve_platform_path(report_root) if report_root is not None else DEFAULT_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with report_write_lock(root):
        return _write_flight_log_report_locked(report, root, keep_last)


def _write_flight_log_report_locked(report, root, keep_last):
    root = root if hasattr(root, "joinpath") else resolve_platform_path(root)
    source_name = safe_name(Path(report.get("source", "source")).stem)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    report_dir = root / "{0}_{1}_{2}".format(report.get("source_type", "source"), source_name, stamp)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "report.json"
    report_txt = report_dir / "report.txt"
    latest_json = root / "latest_{0}.json".format(report.get("source_type", "source"))
    latest_txt = root / "latest_{0}.txt".format(report.get("source_type", "source"))
    history_jsonl = root / "history_{0}.jsonl".format(report.get("source_type", "source"))
    serializable = dict(report)
    serializable.pop("saved_report", None)
    serializable = make_jsonable(serializable)
    text_report = format_flight_log_report(serializable) + "\n"
    atomic_write_json(report_json, serializable)
    atomic_write_text(report_txt, text_report)
    atomic_write_json(latest_json, serializable)
    atomic_write_text(latest_txt, text_report)
    append_jsonl(
        history_jsonl,
        {
            "created_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_type": report.get("source_type"),
            "source": report.get("source"),
            "status": report.get("status"),
            "report_json": str(report_json),
        },
    )
    if keep_last and keep_last > 0:
        prune_reports(root, "{0}_{1}_*".format(report.get("source_type", "source"), source_name), keep_last)
    return {
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "report_text": str(report_txt),
        "latest_json": str(latest_json),
        "latest_text": str(latest_txt),
        "history_jsonl": str(history_jsonl),
    }


def prune_reports(root, pattern, keep_last):
    return prune_directories(root, pattern, keep_last)


def safe_name(value):
    safe = []
    for char in str(value):
        if char.isalnum() or char in ("_", "-", "."):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "source"


def format_flight_log_report(report):
    artifact = report.get("artifact", {})
    metrics = report.get("metrics", {})
    lines = [
        "flight log analysis: {0}".format(report.get("status")),
        "source_type: {0}".format(report.get("source_type")),
        "source: {0}".format(report.get("source")),
        "artifact: {0} backend={1} scenario={2}".format(
            artifact.get("name"),
            artifact.get("backend"),
            artifact.get("scenario_name"),
        ),
        "",
        "key metrics:",
        "- telemetry_count: {0}".format(metrics.get("telemetry_count") or metrics.get("ulog_dataset_count")),
        "- duration_s: {0}".format(metrics.get("duration_s") or metrics.get("ulog_duration_s")),
        "- max_altitude_m: {0}".format(metrics.get("max_altitude_m")),
        "- max_speed_mps: {0}".format(metrics.get("max_speed_mps")),
        "- mode/nav changes: {0}".format(metrics.get("mode_change_count") or metrics.get("nav_state_change_count")),
        "- armed transitions: {0}".format(
            metrics.get("armed_transition_count") or metrics.get("arming_state_change_count")
        ),
        "- anomalies: {0}".format(
            metrics.get("anomaly_event_count") if metrics.get("anomaly_event_count") is not None else metrics.get("ulog_warning_message_count")
        ),
    ]
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    return "\n".join(lines)


def make_jsonable(value):
    if isinstance(value, dict):
        return {str(key): make_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [make_jsonable(item) for item in value]
    return jsonable_scalar(value)
