import json
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sim_plane.artifacts import read_jsonl


STATIC_DIR = Path(__file__).resolve().parent / "static"
REQUIRED_ARTIFACT_FILES = ("manifest.json", "result.json", "events.jsonl")


class LiveRunState:
    def __init__(self, scenario, artifact_dir):
        self.scenario = scenario
        self.artifact_dir = str(artifact_dir)
        self.started_at = time.time()
        self.telemetry = []
        self.events = []
        self.result = None
        self.status = "starting"
        self.lock = threading.Lock()

    def append_telemetry(self, sample):
        with self.lock:
            self.telemetry.append(sample)
            self.status = "running"

    def append_event(self, event):
        with self.lock:
            self.events.append(event)

    def finalize(self, result):
        with self.lock:
            self.result = result
            self.status = result.get("status", "finished")

    def meta(self):
        return {
            "mode": "live",
            "scenario": self.scenario,
            "artifact_dir": self.artifact_dir,
        }

    def state(self):
        with self.lock:
            telemetry_count = len(self.telemetry)
            events_count = len(self.events)
            latest = self.telemetry[-1] if self.telemetry else None
            return {
                "status": self.status,
                "telemetry_count": telemetry_count,
                "events_count": events_count,
                "latest": latest,
                "result": self.result,
                "uptime_wall_s": round(time.time() - self.started_at, 2),
            }

    def get_telemetry(self, after_index):
        with self.lock:
            items = self.telemetry[after_index:]
            return {"items": items, "next_index": len(self.telemetry)}

    def get_events(self, after_index):
        with self.lock:
            items = self.events[after_index:]
            return {"items": items, "next_index": len(self.events)}


class ArtifactReplay:
    def __init__(self, artifact_dir):
        self.artifact_dir = Path(artifact_dir)
        self.artifact_root = self.artifact_dir.parent
        self.manifest = load_json(self.artifact_dir / "manifest.json")
        self.scenario = load_json(self.artifact_dir / "scenario.json")
        self.result = load_json(self.artifact_dir / "result.json")
        self.telemetry = read_jsonl(self.artifact_dir / "telemetry.jsonl")
        self.events = read_jsonl(self.artifact_dir / "events.jsonl")

    def meta(self):
        return {
            "mode": "replay",
            "scenario": self.scenario,
            "artifact_dir": str(self.artifact_dir),
            "manifest": self.manifest,
        }

    def state(self):
        latest = self.telemetry[-1] if self.telemetry else None
        return {
            "status": self.result.get("status", "finished"),
            "telemetry_count": len(self.telemetry),
            "events_count": len(self.events),
            "latest": latest,
            "result": self.result,
            "uptime_wall_s": None,
        }

    def get_telemetry(self, after_index):
        return {"items": self.telemetry[after_index:], "next_index": len(self.telemetry)}

    def get_events(self, after_index):
        return {"items": self.events[after_index:], "next_index": len(self.events)}

    def list_artifacts(self, limit=100):
        return list_complete_artifacts(self.artifact_root, limit=limit, active_name=self.artifact_dir.name)

    def get_artifact_summary(self, artifact_name):
        artifact_dir = resolve_artifact_name(self.artifact_root, artifact_name)
        return summarize_artifact_dir(artifact_dir)

    def compare_artifacts(self, left_name, right_name):
        left_dir = resolve_artifact_name(self.artifact_root, left_name)
        right_dir = resolve_artifact_name(self.artifact_root, right_name)
        return compare_artifact_dirs(left_dir, right_dir)

    def platform_acceptance_latest(self):
        return load_platform_acceptance_latest(self.artifact_root)

    def list_suite_reports(self, limit=20):
        return list_suite_reports(self.artifact_root, limit=limit)

    def list_test_surface_reports(self, limit=20):
        return list_test_surface_reports(self.artifact_root, limit=limit)


class ArtifactRootBrowser:
    def __init__(self, artifact_root):
        self.artifact_root = Path(artifact_root)
        artifacts = list_complete_artifacts(self.artifact_root, limit=1)
        self.active_artifact_dir = Path(artifacts[0]["path"]) if artifacts else None
        self.active_replay = ArtifactReplay(self.active_artifact_dir) if self.active_artifact_dir else None

    def meta(self):
        if self.active_replay is None:
            scenario = {
                "name": "Artifact Browser",
                "description": "No complete artifacts found under {0}".format(self.artifact_root),
                "backend": "-",
                "vehicle": "-",
            }
            return {
                "mode": "browser",
                "scenario": scenario,
                "artifact_root": str(self.artifact_root),
                "active_artifact_dir": None,
            }
        meta = self.active_replay.meta()
        meta["mode"] = "browser"
        meta["artifact_root"] = str(self.artifact_root)
        meta["active_artifact_dir"] = str(self.active_artifact_dir)
        return meta

    def state(self):
        if self.active_replay is None:
            return {
                "status": "empty",
                "telemetry_count": 0,
                "events_count": 0,
                "latest": None,
                "result": None,
                "uptime_wall_s": None,
            }
        state = self.active_replay.state()
        state["browser_active_artifact"] = self.active_artifact_dir.name
        return state

    def get_telemetry(self, after_index):
        if self.active_replay is None:
            return {"items": [], "next_index": 0}
        return self.active_replay.get_telemetry(after_index)

    def get_events(self, after_index):
        if self.active_replay is None:
            return {"items": [], "next_index": 0}
        return self.active_replay.get_events(after_index)

    def list_artifacts(self, limit=100):
        active_name = self.active_artifact_dir.name if self.active_artifact_dir else None
        return list_complete_artifacts(self.artifact_root, limit=limit, active_name=active_name)

    def get_artifact_summary(self, artifact_name):
        artifact_dir = resolve_artifact_name(self.artifact_root, artifact_name)
        return summarize_artifact_dir(artifact_dir)

    def compare_artifacts(self, left_name, right_name):
        left_dir = resolve_artifact_name(self.artifact_root, left_name)
        right_dir = resolve_artifact_name(self.artifact_root, right_name)
        return compare_artifact_dirs(left_dir, right_dir)

    def platform_acceptance_latest(self):
        return load_platform_acceptance_latest(self.artifact_root)

    def list_suite_reports(self, limit=20):
        return list_suite_reports(self.artifact_root, limit=limit)

    def list_test_surface_reports(self, limit=20):
        return list_test_surface_reports(self.artifact_root, limit=limit)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_json_or_empty(path):
    try:
        return load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def is_complete_artifact_dir(path):
    directory = Path(path)
    return directory.is_dir() and all((directory / name).exists() for name in REQUIRED_ARTIFACT_FILES)


def list_complete_artifacts(artifact_root, limit=100, active_name=None):
    root = Path(artifact_root)
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name, reverse=True):
        if not is_complete_artifact_dir(path):
            continue
        try:
            rows.append(summarize_artifact_dir(path, include_events=False, include_telemetry=False))
        except (OSError, json.JSONDecodeError):
            continue
    rows.sort(key=lambda row: (row.get("created_at_utc") or "", row["name"]), reverse=True)
    for row in rows:
        row["active"] = row["name"] == active_name
    return rows[: max(int(limit), 0)]


def resolve_artifact_name(artifact_root, artifact_name):
    name = str(artifact_name or "")
    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("invalid artifact name: {0}".format(name))
    artifact_dir = Path(artifact_root) / name
    if not is_complete_artifact_dir(artifact_dir):
        raise ValueError("artifact is missing required files: {0}".format(name))
    return artifact_dir


def summarize_artifact_dir(path, include_events=True, include_telemetry=True):
    artifact_dir = Path(path)
    manifest = load_json(artifact_dir / "manifest.json")
    scenario = load_json_or_empty(artifact_dir / "scenario.json")
    result = load_json(artifact_dir / "result.json")
    telemetry = read_jsonl(artifact_dir / "telemetry.jsonl") if include_telemetry else []
    events = read_jsonl(artifact_dir / "events.jsonl") if include_events else []
    metrics = result.get("metrics", {})
    return {
        "name": artifact_dir.name,
        "path": str(artifact_dir),
        "created_at_utc": manifest.get("created_at_utc"),
        "scenario_name": result.get("scenario_name") or manifest.get("scenario_name") or scenario.get("name"),
        "description": scenario.get("description"),
        "backend": result.get("backend") or manifest.get("backend") or scenario.get("backend"),
        "vehicle": result.get("vehicle") or manifest.get("vehicle") or scenario.get("vehicle"),
        "status": result.get("status"),
        "metrics": metrics,
        "telemetry_count": metrics.get("telemetry_count") or len(telemetry),
        "event_count": len(events),
        "track": build_track(telemetry) if include_telemetry else [],
        "trajectory_stats": compute_trajectory_stats(telemetry) if include_telemetry else {},
    }


def build_track(telemetry):
    track = []
    for sample in telemetry:
        position = sample.get("position") or {}
        if "x_m" not in position or "y_m" not in position:
            continue
        track.append(
            {
                "t": sample.get("t"),
                "x_m": position.get("x_m"),
                "y_m": position.get("y_m"),
                "altitude_m": sample.get("altitude_m"),
                "speed_mps": sample.get("speed_mps"),
            }
        )
    return track


def compute_trajectory_stats(telemetry):
    if not telemetry:
        return {}
    distance_m = 0.0
    previous = None
    max_altitude = None
    max_speed = None
    for sample in telemetry:
        position = sample.get("position") or {}
        current = (position.get("x_m"), position.get("y_m"), position.get("z_m"))
        if previous is not None and all(value is not None for value in previous + current):
            dx = float(current[0]) - float(previous[0])
            dy = float(current[1]) - float(previous[1])
            dz = float(current[2]) - float(previous[2])
            distance_m += (dx * dx + dy * dy + dz * dz) ** 0.5
        if all(value is not None for value in current):
            previous = current
        altitude = sample.get("altitude_m")
        speed = sample.get("speed_mps")
        if altitude is not None:
            max_altitude = max(float(altitude), max_altitude if max_altitude is not None else float(altitude))
        if speed is not None:
            max_speed = max(float(speed), max_speed if max_speed is not None else float(speed))
    return {
        "sample_count": len(telemetry),
        "duration_s": telemetry[-1].get("t"),
        "distance_m": round(distance_m, 3),
        "max_altitude_m": round(max_altitude, 3) if max_altitude is not None else None,
        "max_speed_mps": round(max_speed, 3) if max_speed is not None else None,
        "start": (telemetry[0].get("position") or {}),
        "end": (telemetry[-1].get("position") or {}),
    }


def compare_artifact_dirs(left_dir, right_dir):
    left = summarize_artifact_dir(left_dir)
    right = summarize_artifact_dir(right_dir)
    return {
        "left": left,
        "right": right,
        "metric_deltas": compare_metric_dicts(left.get("metrics", {}), right.get("metrics", {})),
        "trajectory_deltas": compare_metric_dicts(
            left.get("trajectory_stats", {}),
            right.get("trajectory_stats", {}),
            keys=("sample_count", "duration_s", "distance_m", "max_altitude_m", "max_speed_mps"),
        ),
        "same_scenario": left.get("scenario_name") == right.get("scenario_name"),
        "same_backend": left.get("backend") == right.get("backend"),
    }


def compare_metric_dicts(left_metrics, right_metrics, keys=None):
    if keys is None:
        metric_names = sorted(set(left_metrics) | set(right_metrics))
    else:
        metric_names = list(keys)
    rows = []
    for name in metric_names:
        left_value = left_metrics.get(name)
        right_value = right_metrics.get(name)
        delta = None
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            delta = round(float(right_value) - float(left_value), 6)
        rows.append(
            {
                "name": name,
                "left": left_value,
                "right": right_value,
                "delta": delta,
                "changed": left_value != right_value,
            }
        )
    return rows


def load_platform_acceptance_latest(artifact_root):
    root = Path(artifact_root) / "platform_acceptance"
    report_path = root / "latest_latest.json"
    delta_path = root / "latest_latest_delta.json"
    if not report_path.exists():
        return {
            "available": False,
            "report_path": str(report_path),
            "delta_path": str(delta_path),
        }
    report = load_json_or_empty(report_path)
    delta = load_json_or_empty(delta_path)
    rows = []
    for row in report.get("rows", []):
        rows.append(
            {
                "name": row.get("name"),
                "backend": row.get("backend"),
                "status": row.get("status"),
                "artifact_dir": row.get("artifact_dir"),
                "reference_artifact_dir": row.get("reference_artifact_dir"),
                "metric_regressions": row.get("metric_regressions", {}),
                "issues": row.get("issues", []),
            }
        )
    return {
        "available": True,
        "status": report.get("status"),
        "selection_mode": report.get("selection_mode"),
        "report_path": str(report_path),
        "delta_path": str(delta_path),
        "changed_rows_count": delta.get("changed_rows_count"),
        "status_changed": delta.get("status_changed"),
        "planner_acceptance_status": (
            report.get("planner_acceptance", {}).get("status")
            if isinstance(report.get("planner_acceptance"), dict)
            else None
        ),
        "rows": rows,
        "row_deltas": delta.get("row_deltas", []),
    }


def list_suite_reports(artifact_root, limit=20):
    root = Path(artifact_root) / "suites"
    if not root.exists():
        return {
            "available": False,
            "suite_root": str(root),
            "items": [],
        }
    reports = []
    for path in sorted(root.glob("latest_*.json"), key=lambda item: item.name):
        try:
            report = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        reports.append(summarize_suite_report(report, path))
    reports.sort(key=lambda row: row.get("latest_artifact_created_at_utc") or row["latest_json"], reverse=True)
    return {
        "available": True,
        "suite_root": str(root),
        "items": reports[: max(int(limit), 0)],
    }


def list_test_surface_reports(artifact_root, limit=20):
    root = Path(artifact_root)
    surface_specs = [
        ("PX4 failure", root / "px4_failure_injection_acceptance", "latest_latest.json"),
        ("quadrotor exam", root / "quadrotor_exam_acceptance", "latest_latest.json"),
        ("flight log", root / "flight_log_analysis", "latest_artifact.json"),
        ("ULog", root / "flight_log_analysis", "latest_ulog.json"),
        ("scenario fuzz", root / "scenario_fuzz", "latest_*.json"),
        ("autotest", root / "autotest", "latest_*.json"),
    ]
    items = []
    for label, report_root, pattern in surface_specs:
        if not report_root.exists():
            continue
        paths = sorted(report_root.glob(pattern), key=lambda item: item.name, reverse=True)
        for path in paths:
            try:
                report = load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            items.append(summarize_test_surface_report(label, report, path))
    items.sort(key=lambda row: row.get("latest_json", ""), reverse=True)
    return {
        "available": bool(items),
        "artifact_root": str(root),
        "items": items[: max(int(limit), 0)],
    }


def summarize_test_surface_report(label, report, path):
    metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {}
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    rows = report.get("rows", []) if isinstance(report.get("rows"), list) else []
    steps = report.get("steps", []) if isinstance(report.get("steps"), list) else []
    return {
        "surface": label,
        "name": (
            report.get("matrix_name")
            or report.get("fuzz_name")
            or report.get("pack_name")
            or report.get("source_type")
            or label
        ),
        "status": report.get("status"),
        "latest_json": str(path),
        "report_json": (report.get("saved_report") or {}).get("report_json"),
        "source": report.get("source"),
        "profile": report.get("profile"),
        "seed": report.get("seed"),
        "row_count": len(rows),
        "passed_row_count": len([row for row in rows if row.get("status") == "passed"]),
        "step_count": len(steps),
        "passed_step_count": len([step for step in steps if step.get("status") == "passed"]),
        "key_metrics": build_test_surface_key_metrics(metrics, summary),
        "worst_cases": list(report.get("worst_cases", []))[:4],
        "issues": list(report.get("issues", []))[:4],
}


def build_test_surface_key_metrics(metrics, summary):
    keys = (
        "scene_count",
        "passed_scene_count",
        "success_rate",
        "telemetry_count",
        "duration_s",
        "max_altitude_m",
        "max_speed_mps",
        "mode_change_count",
        "armed_transition_count",
        "anomaly_event_count",
        "ulog_dropout_count",
        "ulog_warning_message_count",
    )
    values = {}
    for key in keys:
        if key in metrics:
            values[key] = metrics.get(key)
        elif key in summary:
            values[key] = summary.get(key)
    return values


def summarize_suite_report(report, report_path):
    rows = report.get("rows", []) if isinstance(report.get("rows"), list) else []
    passed_rows = [row for row in rows if row.get("status") == "passed"]
    failed_rows = [row for row in rows if row.get("status") != "passed"]
    key_metrics = []
    for row in rows:
        metrics = row.get("metrics", {}) if isinstance(row.get("metrics"), dict) else {}
        key_metrics.append(
            {
                "name": row.get("name"),
                "status": row.get("status"),
                "artifact_dir": row.get("artifact_dir"),
                "kpi_sensor_dropout_ratio": metrics.get("kpi_sensor_dropout_ratio"),
                "kpi_mission_path_error_max_m": metrics.get("kpi_mission_path_error_max_m"),
                "kpi_mission_altitude_mae_m": metrics.get("kpi_mission_altitude_mae_m"),
                "kpi_measurement_horizontal_error_max_m": metrics.get("kpi_measurement_horizontal_error_max_m"),
                "kpi_measurement_vertical_error_max_m": metrics.get("kpi_measurement_vertical_error_max_m"),
            }
        )
    return {
        "suite_name": report.get("suite_name"),
        "status": report.get("status"),
        "base_scenario": report.get("base_scenario"),
        "row_count": len(rows),
        "passed_row_count": len(passed_rows),
        "failed_row_count": len(failed_rows),
        "issues": report.get("issues", []),
        "latest_json": str(report_path),
        "report_json": (report.get("saved_report") or {}).get("report_json"),
        "top_metric_effects": list(report.get("top_metric_effects", []))[:8],
        "kpi_rankings": summarize_suite_kpi_rankings(report.get("kpi_rankings", {})),
        "key_metrics": key_metrics[:12],
        "latest_artifact_created_at_utc": newest_artifact_created_at(rows),
    }


def summarize_suite_kpi_rankings(kpi_rankings, limit=5):
    if not isinstance(kpi_rankings, dict):
        return []
    preferred_metrics = [
        "kpi_mission_path_error_max_m",
        "kpi_measurement_horizontal_error_max_m",
        "kpi_sensor_dropout_ratio",
        "kpi_speed_limit_violation_count",
        "kpi_safety_violation_count",
        "kpi_max_acceleration_mps2",
        "kpi_speed_roughness_mps",
    ]
    rows = []
    for metric in preferred_metrics:
        ranking = kpi_rankings.get(metric)
        if not isinstance(ranking, dict):
            continue
        worst = ranking.get("worst_high", [])
        if not worst:
            continue
        rows.append(
            {
                "metric": metric,
                "spread": ranking.get("spread"),
                "worst": list(worst)[:3],
            }
        )
    if len(rows) >= limit:
        return rows[:limit]
    for metric, ranking in sorted(kpi_rankings.items()):
        if metric in preferred_metrics or not isinstance(ranking, dict):
            continue
        worst = ranking.get("worst_high", [])
        if not worst:
            continue
        rows.append(
            {
                "metric": metric,
                "spread": ranking.get("spread"),
                "worst": list(worst)[:3],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def newest_artifact_created_at(rows):
    newest = None
    for row in rows:
        artifact_dir = row.get("artifact_dir")
        if not artifact_dir:
            continue
        manifest_path = Path(artifact_dir) / "manifest.json"
        manifest = load_json_or_empty(manifest_path)
        created_at = manifest.get("created_at_utc")
        if created_at and (newest is None or created_at > newest):
            newest = created_at
    return newest


class DashboardServer:
    def __init__(self, data_source, host="127.0.0.1", port=8765):
        self.data_source = data_source
        self.host = host
        self.port = port
        self.httpd = ThreadingHTTPServer((host, port), self._make_handler())
        self.thread = None

    def _make_handler(self):
        data_source = self.data_source

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/":
                    self._serve_static("index.html", "text/html; charset=utf-8")
                    return
                if parsed.path == "/app.js":
                    self._serve_static("app.js", "application/javascript; charset=utf-8")
                    return
                if parsed.path == "/styles.css":
                    self._serve_static("styles.css", "text/css; charset=utf-8")
                    return
                if parsed.path == "/api/meta":
                    self._json(data_source.meta())
                    return
                if parsed.path == "/api/state":
                    self._json(data_source.state())
                    return
                if parsed.path == "/api/telemetry":
                    query = urllib.parse.parse_qs(parsed.query)
                    after = int(query.get("after", ["0"])[0])
                    self._json(data_source.get_telemetry(after))
                    return
                if parsed.path == "/api/events":
                    query = urllib.parse.parse_qs(parsed.query)
                    after = int(query.get("after", ["0"])[0])
                    self._json(data_source.get_events(after))
                    return
                if parsed.path == "/api/artifacts":
                    query = urllib.parse.parse_qs(parsed.query)
                    limit = int(query.get("limit", ["100"])[0])
                    self._json({"items": call_optional(data_source, "list_artifacts", [], limit=limit)})
                    return
                if parsed.path == "/api/artifact":
                    query = urllib.parse.parse_qs(parsed.query)
                    name = first_query_value(query, "name")
                    self._json(call_optional(data_source, "get_artifact_summary", {}, name))
                    return
                if parsed.path == "/api/compare":
                    query = urllib.parse.parse_qs(parsed.query)
                    left = first_query_value(query, "left")
                    right = first_query_value(query, "right")
                    self._json(call_optional(data_source, "compare_artifacts", {}, left, right))
                    return
                if parsed.path == "/api/platform-acceptance/latest":
                    self._json(call_optional(data_source, "platform_acceptance_latest", {"available": False}))
                    return
                if parsed.path == "/api/suites/latest":
                    query = urllib.parse.parse_qs(parsed.query)
                    limit = int(query.get("limit", ["20"])[0])
                    self._json(call_optional(data_source, "list_suite_reports", {"available": False}, limit=limit))
                    return
                if parsed.path == "/api/test-surfaces/latest":
                    query = urllib.parse.parse_qs(parsed.query)
                    limit = int(query.get("limit", ["20"])[0])
                    self._json(call_optional(data_source, "list_test_surface_reports", {"available": False}, limit=limit))
                    return

                self.send_error(404, "Not found")

            def log_message(self, fmt, *args):
                return

            def _serve_static(self, filename, content_type):
                path = STATIC_DIR / filename
                payload = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    return

            def _json(self, payload):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler

    @property
    def url(self):
        return "http://{0}:{1}".format(self.host, self.port)

    def start(self, open_browser=False):
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        if open_browser:
            webbrowser.open(self.url)

    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)


def first_query_value(query, key):
    values = query.get(key, [""])
    return values[0]


def call_optional(data_source, method_name, default, *args, **kwargs):
    method = getattr(data_source, method_name, None)
    if method is None:
        return default
    try:
        return method(*args, **kwargs)
    except ValueError as exc:
        return {"error": str(exc)}
