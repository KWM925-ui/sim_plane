import json
from collections import Counter
from pathlib import Path

from sim_plane.acceptance_common import (
    append_history_entry,
    build_acceptance_report_dir,
    load_previous_acceptance_report,
    load_reference_result as load_common_reference_result,
    prune_acceptance_reports,
    resolve_artifact_dir,
    resolve_artifact_root,
    resolve_reference_artifact_dir,
    validate_matrix_rows,
)
from sim_plane.artifacts import read_jsonl, utc_timestamp
from sim_plane.io_utils import atomic_write_json, atomic_write_text, report_write_lock
from sim_plane.paths import get_platform_paths, resolve_platform_path


REPO_ROOT = get_platform_paths().home
DEFAULT_MATRIX_PATH = REPO_ROOT / "configs" / "planner_acceptance_matrix.json"
DEFAULT_ACCEPTANCE_REPORT_ROOT = REPO_ROOT / "runs" / "acceptance"
DEFAULT_ACCEPTANCE_KEEP_LAST = 5


def load_acceptance_matrix(path=None):
    matrix_path = resolve_platform_path(path) if path is not None else DEFAULT_MATRIX_PATH
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    payload["_matrix_path"] = matrix_path
    return payload


def validate_acceptance_matrix(path=None, artifact_root=None, use_latest=False):
    matrix = load_acceptance_matrix(path)
    matrix_path = matrix["_matrix_path"]
    required_event_levels = set(matrix.get("required_event_levels", ["info"]))
    artifact_root_path = resolve_artifact_root(matrix_path, artifact_root)
    rows = []
    row_specs, issues = validate_matrix_rows(matrix, "planner acceptance matrix")
    max_goal_distance_regression_m = matrix.get("max_goal_distance_regression_m")

    for row_spec in row_specs:
        row_report = validate_acceptance_row(
            row_spec,
            matrix_path=matrix_path,
            artifact_root=artifact_root_path,
            required_event_levels=required_event_levels,
            goal_distance_threshold_m=matrix.get("goal_distance_threshold_m"),
            max_goal_distance_regression_m=max_goal_distance_regression_m,
            use_latest=use_latest,
        )
        rows.append(row_report)
        issues.extend(row_report["issues"])

    return {
        "matrix_name": matrix.get("matrix_name", "planner_acceptance"),
        "matrix_path": str(matrix_path),
        "artifact_root": str(artifact_root_path),
        "goal_distance_threshold_m": matrix.get("goal_distance_threshold_m"),
        "max_goal_distance_regression_m": max_goal_distance_regression_m,
        "selection_mode": "latest" if use_latest else "reference",
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "rows": rows,
    }


def validate_acceptance_row(
    row_spec,
    matrix_path,
    artifact_root,
    required_event_levels,
    goal_distance_threshold_m,
    max_goal_distance_regression_m,
    use_latest=False,
):
    row_issues = []
    modes = {}
    backend = row_spec["backend"]

    for mode_name in ("headless", "visual"):
        mode_spec = row_spec[mode_name]
        artifact_dir, resolve_issue = resolve_artifact_dir(
            mode_spec,
            matrix_path=matrix_path,
            artifact_root=artifact_root,
            use_latest=use_latest,
            expected_backend=backend,
            expected_vehicle="quadrotor",
        )
        reference_artifact_dir = resolve_reference_artifact_dir(
            mode_spec,
            matrix_path=matrix_path,
        )
        mode_report = validate_acceptance_mode(
            backend=backend,
            mode_name=mode_name,
            mode_spec=mode_spec,
            artifact_dir=artifact_dir,
            reference_artifact_dir=reference_artifact_dir,
            required_event_levels=required_event_levels,
            goal_distance_threshold_m=goal_distance_threshold_m,
            max_goal_distance_regression_m=max_goal_distance_regression_m,
            requires_cloud_only=row_spec.get("requires_cloud_only", False),
        )
        if resolve_issue is not None:
            mode_report["issues"].insert(0, resolve_issue)
        modes[mode_name] = mode_report
        row_issues.extend(mode_report["issues"])

    row_status = "passed" if not row_issues else "failed"
    summary = {
        "backend": backend,
        "surface": row_spec["surface"],
        "odom_source": row_spec["odom_source"],
        "obstacle_source": row_spec["obstacle_source"],
        "status": row_status,
        "issues": row_issues,
    }
    summary.update(modes)
    return summary


def validate_acceptance_mode(
    backend,
    mode_name,
    mode_spec,
    artifact_dir,
    reference_artifact_dir,
    required_event_levels,
    goal_distance_threshold_m,
    max_goal_distance_regression_m,
    requires_cloud_only=False,
):
    configured_baseline_min_goal_distance_m = mode_spec.get("baseline_min_goal_distance_m")
    report = {
        "mode": mode_name,
        "scenario_name": mode_spec["scenario_name"],
        "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
        "reference_artifact_dir": str(reference_artifact_dir) if reference_artifact_dir is not None else None,
        "configured_baseline_min_goal_distance_m": configured_baseline_min_goal_distance_m,
        "baseline_min_goal_distance_m": None,
        "max_goal_distance_regression_m": max_goal_distance_regression_m,
        "status": "failed",
        "issues": [],
        "metrics": {},
        "event_levels": {},
    }

    if artifact_dir is None:
        report["issues"].append("artifact directory could not be resolved")
        return report

    result_path = artifact_dir / "result.json"
    manifest_path = artifact_dir / "manifest.json"
    events_path = artifact_dir / "events.jsonl"

    for path in (result_path, manifest_path, events_path):
        if not path.exists():
            report["issues"].append("missing required file: {0}".format(path.name))
    if report["issues"]:
        return report

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    events = read_jsonl(events_path)
    event_levels = Counter(event.get("level", "unknown") for event in events)
    reference_result, reference_issues = load_reference_result(
        reference_artifact_dir=reference_artifact_dir,
        backend=backend,
        scenario_name=mode_spec["scenario_name"],
        require_baseline_metadata=bool(mode_spec.get("source_artifact")),
        expected_source_artifact=mode_spec.get("source_artifact"),
    )
    report["issues"].extend(reference_issues)
    metrics = result.get("metrics", {})
    reference_metrics = reference_result.get("metrics", {}) if reference_result else {}
    baseline_min_goal_distance_m = reference_metrics.get("min_goal_distance_m")
    report["baseline_min_goal_distance_m"] = baseline_min_goal_distance_m
    report["metrics"] = {
        "goal_reached": metrics.get("goal_reached"),
        "min_goal_distance_m": metrics.get("min_goal_distance_m"),
        "launch_rviz": metrics.get("launch_rviz"),
        "cloud_only": metrics.get("cloud_only"),
        "goal_distance_regression_m": None,
    }
    report["event_levels"] = dict(event_levels)

    if manifest.get("backend") != backend:
        report["issues"].append(
            "manifest backend mismatch: expected {0}, got {1}".format(backend, manifest.get("backend"))
        )
    if result.get("backend") != backend:
        report["issues"].append(
            "result backend mismatch: expected {0}, got {1}".format(backend, result.get("backend"))
        )
    if result.get("scenario_name") != mode_spec["scenario_name"]:
        report["issues"].append(
            "scenario_name mismatch: expected {0}, got {1}".format(
                mode_spec["scenario_name"], result.get("scenario_name")
            )
        )
    if result.get("status") != "passed":
        report["issues"].append("result status is not passed")
    if metrics.get("goal_reached") is not True:
        report["issues"].append("goal_reached is not true")
    if goal_distance_threshold_m is not None:
        goal_distance = metrics.get("min_goal_distance_m")
        if goal_distance is None:
            report["issues"].append("min_goal_distance_m is missing")
        elif goal_distance > goal_distance_threshold_m:
            report["issues"].append(
                "min_goal_distance_m {0} exceeds threshold {1}".format(
                    goal_distance, goal_distance_threshold_m
                )
            )
    else:
        goal_distance = metrics.get("min_goal_distance_m")
    if (
        configured_baseline_min_goal_distance_m is not None
        and baseline_min_goal_distance_m is not None
        and round(
            abs(configured_baseline_min_goal_distance_m - baseline_min_goal_distance_m),
            3,
        )
        > 0.0
    ):
        report["issues"].append(
            "configured baseline_min_goal_distance_m {0} does not match reference artifact value {1}".format(
                configured_baseline_min_goal_distance_m,
                baseline_min_goal_distance_m,
            )
        )
    if baseline_min_goal_distance_m is not None and goal_distance is not None:
        regression = round(goal_distance - baseline_min_goal_distance_m, 3)
        report["metrics"]["goal_distance_regression_m"] = regression
        if (
            max_goal_distance_regression_m is not None
            and regression > max_goal_distance_regression_m
        ):
            report["issues"].append(
                "min_goal_distance_m regressed by {0} m beyond allowed {1} m".format(
                    regression, max_goal_distance_regression_m
                )
            )
    if metrics.get("launch_rviz") != mode_spec["expected_launch_rviz"]:
        report["issues"].append(
            "launch_rviz mismatch: expected {0}, got {1}".format(
                mode_spec["expected_launch_rviz"], metrics.get("launch_rviz")
            )
        )
    if requires_cloud_only and metrics.get("cloud_only") is not True:
        report["issues"].append("cloud_only is not true")
    if set(event_levels) - set(required_event_levels):
        report["issues"].append(
            "event levels contain non-accepted values: {0}".format(
                ", ".join(sorted(set(event_levels) - set(required_event_levels)))
            )
        )

    report["status"] = "passed" if not report["issues"] else "failed"
    return report


def format_acceptance_report(report):
    lines = []
    lines.append(
        "planner acceptance: {0} ({1} artifacts)".format(
            report["status"], report["selection_mode"]
        )
    )
    lines.append("matrix: {0}".format(report["matrix_path"]))
    if report.get("goal_distance_threshold_m") is not None:
        lines.append("goal_distance_threshold_m: {0}".format(report["goal_distance_threshold_m"]))
    if report.get("max_goal_distance_regression_m") is not None:
        lines.append(
            "max_goal_distance_regression_m: {0}".format(report["max_goal_distance_regression_m"])
        )
    if report["selection_mode"] == "latest":
        lines.append("artifact_root: {0}".format(report["artifact_root"]))
    lines.append("")

    header = "{0:38} {1:10} {2:10} {3:10} {4}".format("backend", "headless", "visual", "row", "surface")
    lines.append(header)
    lines.append("-" * len(header))
    for row in report["rows"]:
        lines.append(
            "{0:38} {1:10} {2:10} {3:10} {4}".format(
                row["backend"],
                row["headless"]["status"],
                row["visual"]["status"],
                row["status"],
                row["surface"],
            )
        )
        for mode_name in ("headless", "visual"):
            mode = row[mode_name]
            metrics = mode["metrics"]
            lines.append(
                "  {0}: artifact={1} goal={2} min_goal_distance_m={3} regression_m={4} launch_rviz={5} event_levels={6}".format(
                    mode_name,
                    Path(mode["artifact_dir"]).name if mode["artifact_dir"] else "missing",
                    metrics.get("goal_reached"),
                    metrics.get("min_goal_distance_m"),
                    metrics.get("goal_distance_regression_m"),
                    metrics.get("launch_rviz"),
                    mode["event_levels"],
                )
            )
            if mode.get("baseline_min_goal_distance_m") is not None:
                lines.append(
                    "    baseline_min_goal_distance_m={0}".format(mode["baseline_min_goal_distance_m"])
                )
            if mode.get("configured_baseline_min_goal_distance_m") is not None:
                lines.append(
                    "    configured_baseline_min_goal_distance_m={0}".format(
                        mode["configured_baseline_min_goal_distance_m"]
                    )
                )
            if mode.get("max_goal_distance_regression_m") is not None:
                lines.append(
                    "    max_goal_distance_regression_m={0}".format(mode["max_goal_distance_regression_m"])
                )
            for issue in mode["issues"]:
                lines.append("    issue: {0}".format(issue))
    if report["issues"]:
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    delta = report.get("delta_from_previous")
    if delta is not None:
        lines.append("")
        lines.extend(format_acceptance_delta_lines(delta))
    return "\n".join(lines)


def write_acceptance_report(report, report_root=None, keep_last=DEFAULT_ACCEPTANCE_KEEP_LAST):
    report_root_path = resolve_platform_path(report_root) if report_root is not None else DEFAULT_ACCEPTANCE_REPORT_ROOT
    report_root_path.mkdir(parents=True, exist_ok=True)
    with report_write_lock(report_root_path):
        return _write_acceptance_report_locked(report, report_root_path, keep_last)


def _write_acceptance_report_locked(report, report_root_path, keep_last):
    report_root_path = Path(report_root_path)
    matrix_name = report.get("matrix_name", "planner_acceptance")
    selection_mode = report.get("selection_mode", "reference")
    report_dir = build_acceptance_report_dir(
        report_root_path,
        matrix_name=matrix_name,
        selection_mode=selection_mode,
    )
    report_dir.mkdir(parents=True, exist_ok=False)

    payload = dict(report)
    payload["report_dir"] = str(report_dir)
    payload["written_at_utc"] = utc_timestamp()
    text_report = format_acceptance_report(payload) + "\n"

    json_path = report_dir / "report.json"
    text_path = report_dir / "report.txt"
    delta_json_path = report_dir / "delta.json"
    delta_text_path = report_dir / "delta.txt"
    manifest_path = report_dir / "manifest.json"
    latest_json_path = report_root_path / "latest_{0}.json".format(selection_mode)
    latest_text_path = report_root_path / "latest_{0}.txt".format(selection_mode)
    latest_delta_json_path = report_root_path / "latest_{0}_delta.json".format(selection_mode)
    latest_delta_text_path = report_root_path / "latest_{0}_delta.txt".format(selection_mode)
    history_jsonl_path = report_root_path / "history_{0}.jsonl".format(selection_mode)
    previous_report = load_previous_acceptance_report(latest_json_path)
    delta = build_acceptance_delta(payload, previous_report)
    payload["delta_from_previous"] = delta
    text_report = format_acceptance_report(payload) + "\n"
    delta_text = format_acceptance_delta(delta) + "\n"

    atomic_write_json(json_path, payload)
    atomic_write_text(text_path, text_report)
    atomic_write_json(delta_json_path, delta)
    atomic_write_text(delta_text_path, delta_text)
    append_history_entry(
        history_jsonl_path,
        {
            "written_at_utc": payload["written_at_utc"],
            "matrix_name": matrix_name,
            "selection_mode": selection_mode,
            "status": payload.get("status"),
            "report_dir": str(report_dir),
            "issues_count": len(payload.get("issues", [])),
            "previous_report_dir": delta.get("previous_report_dir"),
            "status_changed": delta.get("status_changed"),
            "changed_modes_count": delta.get("changed_modes_count"),
            "row_status": {
                row["backend"]: row["status"]
                for row in payload.get("rows", [])
            },
        },
    )
    pruned_report_dirs = prune_acceptance_reports(
        report_root_path=report_root_path,
        matrix_name=matrix_name,
        selection_mode=selection_mode,
        keep_last=keep_last,
    )
    atomic_write_json(
        manifest_path,
        {
            "created_at_utc": payload["written_at_utc"],
            "matrix_name": matrix_name,
            "selection_mode": selection_mode,
            "status": payload.get("status"),
            "report_dir": str(report_dir),
            "files": {
                "report_json": "report.json",
                "report_text": "report.txt",
                "delta_json": "delta.json",
                "delta_text": "delta.txt",
            },
            "latest_files": {
                "report_json": str(latest_json_path),
                "report_text": str(latest_text_path),
                "delta_json": str(latest_delta_json_path),
                "delta_text": str(latest_delta_text_path),
            },
            "history_file": str(history_jsonl_path),
            "keep_last": keep_last,
            "pruned_report_dirs": pruned_report_dirs,
        },
    )
    atomic_write_json(latest_json_path, payload)
    atomic_write_text(latest_text_path, text_report)
    atomic_write_json(latest_delta_json_path, delta)
    atomic_write_text(latest_delta_text_path, delta_text)

    return {
        "report_root": str(report_root_path),
        "report_dir": str(report_dir),
        "report_json": str(json_path),
        "report_text": str(text_path),
        "delta_json": str(delta_json_path),
        "delta_text": str(delta_text_path),
        "latest_report_json": str(latest_json_path),
        "latest_report_text": str(latest_text_path),
        "latest_delta_json": str(latest_delta_json_path),
        "latest_delta_text": str(latest_delta_text_path),
        "history_jsonl": str(history_jsonl_path),
        "keep_last": keep_last,
        "pruned_report_dirs": pruned_report_dirs,
        "delta": delta,
    }


def load_reference_result(
    reference_artifact_dir,
    backend,
    scenario_name,
    require_baseline_metadata=False,
    expected_source_artifact=None,
):
    reference_result, issues = load_common_reference_result(
        reference_artifact_dir,
        backend,
        scenario_name,
        require_baseline_metadata=require_baseline_metadata,
        expected_source_artifact=expected_source_artifact,
    )
    if reference_result is None:
        return None, issues

    reference_metrics = reference_result.get("metrics", {})
    if reference_metrics.get("goal_reached") is not True:
        issues.append("reference goal_reached is not true")
    if reference_metrics.get("min_goal_distance_m") is None:
        issues.append("reference min_goal_distance_m is missing")

    return reference_result, issues


def build_acceptance_delta(current_report, previous_report):
    delta = {
        "has_previous_report": previous_report is not None,
        "selection_mode": current_report.get("selection_mode"),
        "current_report_dir": current_report.get("report_dir"),
        "current_written_at_utc": current_report.get("written_at_utc"),
        "current_status": current_report.get("status"),
        "current_issues_count": len(current_report.get("issues", [])),
        "previous_report_dir": previous_report.get("report_dir") if previous_report else None,
        "previous_written_at_utc": previous_report.get("written_at_utc") if previous_report else None,
        "previous_status": previous_report.get("status") if previous_report else None,
        "previous_issues_count": len(previous_report.get("issues", [])) if previous_report else None,
        "status_changed": False,
        "issues_count_delta": None,
        "changed_modes_count": 0,
        "changed_backends_count": 0,
        "row_deltas": [],
    }
    if previous_report is None:
        return delta

    delta["status_changed"] = current_report.get("status") != previous_report.get("status")
    delta["issues_count_delta"] = len(current_report.get("issues", [])) - len(previous_report.get("issues", []))
    previous_rows = {row["backend"]: row for row in previous_report.get("rows", [])}
    current_rows = {row["backend"]: row for row in current_report.get("rows", [])}
    changed_backends_count = 0
    changed_modes_count = 0

    for backend in sorted(set(previous_rows) | set(current_rows)):
        current_row = current_rows.get(backend)
        previous_row = previous_rows.get(backend)
        row_delta = {
            "backend": backend,
            "current_status": current_row.get("status") if current_row else None,
            "previous_status": previous_row.get("status") if previous_row else None,
            "status_changed": (current_row.get("status") if current_row else None)
            != (previous_row.get("status") if previous_row else None),
            "mode_deltas": [],
        }
        row_changed = row_delta["status_changed"]
        for mode_name in ("headless", "visual"):
            current_mode = current_row.get(mode_name) if current_row else None
            previous_mode = previous_row.get(mode_name) if previous_row else None
            current_metrics = current_mode.get("metrics", {}) if current_mode else {}
            previous_metrics = previous_mode.get("metrics", {}) if previous_mode else {}
            metric_delta = diff_metric(
                current_metrics.get("min_goal_distance_m"),
                previous_metrics.get("min_goal_distance_m"),
            )
            regression_delta = diff_metric(
                current_metrics.get("goal_distance_regression_m"),
                previous_metrics.get("goal_distance_regression_m"),
            )
            mode_delta = {
                "mode": mode_name,
                "current_status": current_mode.get("status") if current_mode else None,
                "previous_status": previous_mode.get("status") if previous_mode else None,
                "status_changed": (current_mode.get("status") if current_mode else None)
                != (previous_mode.get("status") if previous_mode else None),
                "current_min_goal_distance_m": current_metrics.get("min_goal_distance_m"),
                "previous_min_goal_distance_m": previous_metrics.get("min_goal_distance_m"),
                "min_goal_distance_delta_m": metric_delta,
                "current_goal_distance_regression_m": current_metrics.get("goal_distance_regression_m"),
                "previous_goal_distance_regression_m": previous_metrics.get("goal_distance_regression_m"),
                "goal_distance_regression_delta_m": regression_delta,
                "issues_count_delta": (
                    len(current_mode.get("issues", [])) - len(previous_mode.get("issues", []))
                    if current_mode is not None and previous_mode is not None
                    else None
                ),
                "changed": False,
            }
            mode_changed = (
                mode_delta["status_changed"]
                or metric_delta not in (None, 0.0)
                or regression_delta not in (None, 0.0)
                or mode_delta["issues_count_delta"] not in (None, 0)
            )
            mode_delta["changed"] = mode_changed
            if mode_changed:
                changed_modes_count += 1
                row_changed = True
            row_delta["mode_deltas"].append(mode_delta)
        if row_changed:
            changed_backends_count += 1
        delta["row_deltas"].append(row_delta)

    delta["changed_modes_count"] = changed_modes_count
    delta["changed_backends_count"] = changed_backends_count
    return delta


def diff_metric(current_value, previous_value):
    if current_value is None or previous_value is None:
        return None
    return round(current_value - previous_value, 3)


def format_acceptance_delta(delta):
    return "\n".join(format_acceptance_delta_lines(delta))


def format_acceptance_delta_lines(delta):
    lines = ["delta from previous acceptance:"]
    if not delta.get("has_previous_report"):
        lines.append("- no previous acceptance snapshot for this mode")
        return lines

    lines.append(
        "- previous_status={0} current_status={1} status_changed={2}".format(
            delta.get("previous_status"),
            delta.get("current_status"),
            delta.get("status_changed"),
        )
    )
    lines.append(
        "- previous_report_dir={0}".format(delta.get("previous_report_dir"))
    )
    lines.append(
        "- issues_count_delta={0} changed_backends_count={1} changed_modes_count={2}".format(
            delta.get("issues_count_delta"),
            delta.get("changed_backends_count"),
            delta.get("changed_modes_count"),
        )
    )
    changed_rows = [row for row in delta.get("row_deltas", []) if row.get("status_changed") or any(mode.get("changed") for mode in row.get("mode_deltas", []))]
    if not changed_rows:
        lines.append("- no status or tracked metric changes versus previous snapshot")
        return lines

    for row in changed_rows:
        lines.append(
            "- {0}: previous_status={1} current_status={2} status_changed={3}".format(
                row.get("backend"),
                row.get("previous_status"),
                row.get("current_status"),
                row.get("status_changed"),
            )
        )
        for mode in row.get("mode_deltas", []):
            if not mode.get("changed"):
                continue
            lines.append(
                "  {0}: previous_status={1} current_status={2} min_goal_distance_delta_m={3} goal_distance_regression_delta_m={4} issues_count_delta={5}".format(
                    mode.get("mode"),
                    mode.get("previous_status"),
                    mode.get("current_status"),
                    mode.get("min_goal_distance_delta_m"),
                    mode.get("goal_distance_regression_delta_m"),
                    mode.get("issues_count_delta"),
                )
            )
    return lines
