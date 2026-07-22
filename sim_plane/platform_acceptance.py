import json
from pathlib import Path

from sim_plane.acceptance_common import (
    append_history_entry,
    build_acceptance_report_dir,
    evaluate_metric_regression_budgets,
    load_previous_acceptance_report,
    load_reference_result,
    merge_metric_regression_budgets,
    prune_acceptance_reports,
    resolve_artifact_dir,
    resolve_artifact_root,
    validate_matrix_rows,
)
from sim_plane.artifacts import read_jsonl, utc_timestamp
from sim_plane.io_utils import atomic_write_json, atomic_write_text, report_write_lock
from sim_plane.paths import get_platform_paths, resolve_platform_path
from sim_plane.planner_acceptance import (
    validate_acceptance_matrix,
)


REPO_ROOT = get_platform_paths().home
DEFAULT_MATRIX_PATH = REPO_ROOT / "configs" / "platform_acceptance_matrix.json"
DEFAULT_PLATFORM_REPORT_ROOT = REPO_ROOT / "runs" / "platform_acceptance"
DEFAULT_PLATFORM_KEEP_LAST = 5


def load_platform_matrix(path=None):
    matrix_path = resolve_platform_path(path) if path is not None else DEFAULT_MATRIX_PATH
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    payload["_matrix_path"] = matrix_path
    return payload


def validate_platform_matrix(path=None, artifact_root=None, use_latest=False):
    matrix = load_platform_matrix(path)
    matrix_path = matrix["_matrix_path"]
    artifact_root_path = resolve_artifact_root(matrix_path, artifact_root)
    required_event_levels = set(matrix.get("required_event_levels", ["info"]))
    default_metric_regression_budgets = matrix.get("metric_regression_budgets", {})
    rows = []
    row_specs, issues = validate_matrix_rows(matrix, "platform acceptance matrix")

    for row_spec in row_specs:
        row_report = validate_platform_row(
            row_spec,
            matrix_path=matrix_path,
            artifact_root=artifact_root_path,
            required_event_levels=required_event_levels,
            default_metric_regression_budgets=default_metric_regression_budgets,
            use_latest=use_latest,
        )
        rows.append(row_report)
        issues.extend(row_report["issues"])

    planner_report = None
    planner_matrix = matrix.get("planner_acceptance_matrix")
    if matrix.get("require_planner_acceptance") and not planner_matrix:
        issues.append("platform acceptance matrix requires planner_acceptance_matrix")
    if planner_matrix:
        planner_matrix_path = resolve_matrix_relative_path(matrix_path, planner_matrix)
        planner_report = validate_acceptance_matrix(
            path=planner_matrix_path,
            artifact_root=artifact_root_path,
            use_latest=use_latest,
        )
        if planner_report["status"] != "passed":
            issues.append(
                "nested planner acceptance failed with status {0}".format(planner_report["status"])
            )

    return {
        "matrix_name": matrix.get("matrix_name", "platform_acceptance"),
        "matrix_path": str(matrix_path),
        "artifact_root": str(artifact_root_path),
        "selection_mode": "latest" if use_latest else "reference",
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "rows": rows,
        "planner_acceptance": planner_report,
    }


def validate_platform_row(
    row_spec,
    matrix_path,
    artifact_root,
    required_event_levels,
    default_metric_regression_budgets,
    use_latest=False,
):
    artifact_dir, resolve_issue = resolve_artifact_dir(
        {
            "scenario_name": row_spec["scenario_name"],
            "reference_artifact": row_spec["reference_artifact"],
        },
        matrix_path=matrix_path,
        artifact_root=artifact_root,
        use_latest=use_latest,
        expected_backend=row_spec["backend"],
        expected_vehicle=row_spec.get("expected_vehicle", "quadrotor"),
    )
    reference_artifact_dir, _ = resolve_artifact_dir(
        {
            "scenario_name": row_spec["scenario_name"],
            "reference_artifact": row_spec["reference_artifact"],
        },
        matrix_path=matrix_path,
        artifact_root=artifact_root,
        use_latest=False,
        expected_backend=row_spec["backend"],
        expected_vehicle=row_spec.get("expected_vehicle", "quadrotor"),
    )
    metric_regression_budgets = merge_metric_regression_budgets(
        default_metric_regression_budgets,
        row_spec.get("metric_regression_budgets", {}),
    )
    report = {
        "name": row_spec["name"],
        "backend": row_spec["backend"],
        "surface": row_spec["surface"],
        "scenario_name": row_spec["scenario_name"],
        "expected_vehicle": row_spec.get("expected_vehicle", "quadrotor"),
        "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
        "reference_artifact_dir": (
            str(reference_artifact_dir) if reference_artifact_dir is not None else None
        ),
        "status": "failed",
        "issues": [],
        "metrics": {},
        "reference_metrics": {},
        "metric_regressions": {},
        "metric_regression_budgets": metric_regression_budgets,
        "event_levels": {},
        "notes": [],
    }
    if resolve_issue is not None:
        report["issues"].append(resolve_issue)
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
    reference_result, reference_issues = load_reference_result(
        reference_artifact_dir=reference_artifact_dir,
        backend=row_spec["backend"],
        scenario_name=row_spec["scenario_name"],
        expected_vehicle=row_spec.get("expected_vehicle", "quadrotor"),
        require_baseline_metadata=bool(row_spec.get("source_artifact")),
        expected_source_artifact=row_spec.get("source_artifact"),
    )
    report["issues"].extend(reference_issues)
    metrics = result.get("metrics", {})
    notes = result.get("notes", [])
    reference_metrics = reference_result.get("metrics", {}) if reference_result is not None else {}
    event_levels = {}
    for event in events:
        level = event.get("level", "unknown")
        event_levels[level] = event_levels.get(level, 0) + 1

    report["metrics"] = metrics
    report["reference_metrics"] = {
        metric_name: reference_metrics.get(metric_name)
        for metric_name in metric_regression_budgets
    }
    report["event_levels"] = event_levels
    report["notes"] = notes

    if manifest.get("backend") != row_spec["backend"]:
        report["issues"].append(
            "manifest backend mismatch: expected {0}, got {1}".format(
                row_spec["backend"], manifest.get("backend")
            )
        )
    if result.get("backend") != row_spec["backend"]:
        report["issues"].append(
            "result backend mismatch: expected {0}, got {1}".format(
                row_spec["backend"], result.get("backend")
            )
        )
    if result.get("scenario_name") != row_spec["scenario_name"]:
        report["issues"].append(
            "scenario_name mismatch: expected {0}, got {1}".format(
                row_spec["scenario_name"], result.get("scenario_name")
            )
        )
    if result.get("vehicle") != row_spec.get("expected_vehicle", "quadrotor"):
        report["issues"].append(
            "vehicle mismatch: expected {0}, got {1}".format(
                row_spec.get("expected_vehicle", "quadrotor"), result.get("vehicle")
            )
        )
    if result.get("status") != "passed":
        report["issues"].append("result status is not passed")

    for metric_name, expected_value in row_spec.get("required_metrics", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value != expected_value:
            report["issues"].append(
                "metric {0} mismatch: expected {1}, got {2}".format(
                    metric_name, expected_value, actual_value
                )
            )

    for metric_name, threshold in row_spec.get("metric_thresholds", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value is None:
            report["issues"].append("metric {0} is missing".format(metric_name))
            continue
        min_value = threshold.get("min")
        max_value = threshold.get("max")
        if min_value is not None and actual_value < min_value:
            report["issues"].append(
                "metric {0} value {1} is below min {2}".format(metric_name, actual_value, min_value)
            )
        if max_value is not None and actual_value > max_value:
            report["issues"].append(
                "metric {0} value {1} exceeds max {2}".format(metric_name, actual_value, max_value)
            )

    joined_notes = "\n".join(notes)
    for required_note in row_spec.get("notes_must_contain", []):
        if required_note not in joined_notes:
            report["issues"].append("missing required note substring: {0}".format(required_note))

    if set(event_levels) - set(required_event_levels):
        report["issues"].append(
            "event levels contain non-accepted values: {0}".format(
                ", ".join(sorted(set(event_levels) - set(required_event_levels)))
            )
        )

    regressions, regression_issues = evaluate_metric_regression_budgets(
        metrics=metrics,
        reference_metrics=reference_metrics,
        metric_regression_budgets=metric_regression_budgets,
    )
    report["metric_regressions"] = regressions
    report["issues"].extend(regression_issues)

    report["status"] = "passed" if not report["issues"] else "failed"
    return report


def resolve_matrix_relative_path(matrix_path, child_path):
    path = Path(child_path)
    if path.is_absolute():
        return path
    return (matrix_path.parent.parent / path).resolve()


def format_platform_acceptance_report(report):
    lines = []
    lines.append(
        "platform acceptance: {0} ({1} artifacts)".format(
            report["status"], report["selection_mode"]
        )
    )
    lines.append("matrix: {0}".format(report["matrix_path"]))
    if report["selection_mode"] == "latest":
        lines.append("artifact_root: {0}".format(report["artifact_root"]))
    lines.append("")

    header = "{0:28} {1:18} {2:10} {3}".format("name", "backend", "status", "surface")
    lines.append(header)
    lines.append("-" * len(header))
    for row in report["rows"]:
        lines.append(
            "{0:28} {1:18} {2:10} {3}".format(
                row["name"],
                row["backend"],
                row["status"],
                row["surface"],
            )
        )
        lines.append(
            "  artifact={0} scenario={1} event_levels={2}".format(
                Path(row["artifact_dir"]).name if row["artifact_dir"] else "missing",
                row["scenario_name"],
                row["event_levels"],
            )
        )
        lines.append("  metrics={0}".format(json.dumps(row["metrics"], sort_keys=True, ensure_ascii=False)))
        if row.get("metric_regressions"):
            lines.append(
                "  regressions={0}".format(
                    json.dumps(row["metric_regressions"], sort_keys=True, ensure_ascii=False)
                )
            )
        for issue in row["issues"]:
            lines.append("  issue: {0}".format(issue))

    planner_report = report.get("planner_acceptance")
    if planner_report is not None:
        lines.append("")
        lines.append(
            "nested planner acceptance: {0} ({1})".format(
                planner_report["status"], planner_report["selection_mode"]
            )
        )
        lines.append("planner matrix: {0}".format(planner_report["matrix_path"]))
        lines.append("planner issues: {0}".format(len(planner_report.get("issues", []))))
        for issue in planner_report.get("issues", []):
            lines.append("  issue: {0}".format(issue))

    if report["issues"]:
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))

    delta = report.get("delta_from_previous")
    if delta is not None:
        lines.append("")
        lines.extend(format_platform_acceptance_delta_lines(delta))
    return "\n".join(lines)


def write_platform_acceptance_report(
    report,
    report_root=None,
    keep_last=DEFAULT_PLATFORM_KEEP_LAST,
):
    report_root_path = resolve_platform_path(report_root) if report_root is not None else DEFAULT_PLATFORM_REPORT_ROOT
    report_root_path.mkdir(parents=True, exist_ok=True)
    with report_write_lock(report_root_path):
        return _write_platform_acceptance_report_locked(
            report,
            report_root_path,
            keep_last,
        )


def _write_platform_acceptance_report_locked(report, report_root_path, keep_last):
    report_root_path = Path(report_root_path)
    matrix_name = report.get("matrix_name", "platform_acceptance")
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
    latest_json_path = report_root_path / "latest_{0}.json".format(selection_mode)
    latest_text_path = report_root_path / "latest_{0}.txt".format(selection_mode)
    latest_delta_json_path = report_root_path / "latest_{0}_delta.json".format(selection_mode)
    latest_delta_text_path = report_root_path / "latest_{0}_delta.txt".format(selection_mode)
    history_jsonl_path = report_root_path / "history_{0}.jsonl".format(selection_mode)
    previous_report = load_previous_acceptance_report(latest_json_path)
    delta = build_platform_acceptance_delta(payload, previous_report)
    payload["delta_from_previous"] = delta

    json_path = report_dir / "report.json"
    text_path = report_dir / "report.txt"
    delta_json_path = report_dir / "delta.json"
    delta_text_path = report_dir / "delta.txt"
    manifest_path = report_dir / "manifest.json"
    text_report = format_platform_acceptance_report(payload) + "\n"
    delta_text = format_platform_acceptance_delta(delta) + "\n"

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
            "changed_rows_count": delta.get("changed_rows_count"),
            "row_status": {
                row["name"]: row["status"]
                for row in payload.get("rows", [])
            },
            "planner_acceptance_status": (
                payload.get("planner_acceptance", {}).get("status")
                if payload.get("planner_acceptance") is not None
                else None
            ),
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


def build_platform_acceptance_delta(current_report, previous_report):
    delta = {
        "has_previous_report": previous_report is not None,
        "selection_mode": current_report.get("selection_mode"),
        "current_report_dir": current_report.get("report_dir"),
        "current_written_at_utc": current_report.get("written_at_utc"),
        "current_status": current_report.get("status"),
        "current_issues_count": len(current_report.get("issues", [])),
        "current_planner_acceptance_status": (
            current_report.get("planner_acceptance", {}).get("status")
            if current_report.get("planner_acceptance") is not None
            else None
        ),
        "previous_report_dir": previous_report.get("report_dir") if previous_report else None,
        "previous_written_at_utc": previous_report.get("written_at_utc") if previous_report else None,
        "previous_status": previous_report.get("status") if previous_report else None,
        "previous_issues_count": len(previous_report.get("issues", [])) if previous_report else None,
        "previous_planner_acceptance_status": (
            previous_report.get("planner_acceptance", {}).get("status")
            if previous_report and previous_report.get("planner_acceptance") is not None
            else None
        ),
        "status_changed": False,
        "planner_acceptance_status_changed": False,
        "issues_count_delta": None,
        "changed_rows_count": 0,
        "row_deltas": [],
    }
    if previous_report is None:
        return delta

    delta["status_changed"] = current_report.get("status") != previous_report.get("status")
    delta["planner_acceptance_status_changed"] = (
        delta["current_planner_acceptance_status"] != delta["previous_planner_acceptance_status"]
    )
    delta["issues_count_delta"] = len(current_report.get("issues", [])) - len(previous_report.get("issues", []))

    previous_rows = {row["name"]: row for row in previous_report.get("rows", [])}
    current_rows = {row["name"]: row for row in current_report.get("rows", [])}
    changed_rows_count = 0
    for name in sorted(set(previous_rows) | set(current_rows)):
        current_row = current_rows.get(name)
        previous_row = previous_rows.get(name)
        current_metrics = current_row.get("metrics", {}) if current_row else {}
        previous_metrics = previous_row.get("metrics", {}) if previous_row else {}
        changed_metric_names = sorted(
            metric_name
            for metric_name in set(current_metrics) | set(previous_metrics)
            if current_metrics.get(metric_name) != previous_metrics.get(metric_name)
        )
        row_delta = {
            "name": name,
            "backend": current_row.get("backend") if current_row else previous_row.get("backend"),
            "current_status": current_row.get("status") if current_row else None,
            "previous_status": previous_row.get("status") if previous_row else None,
            "status_changed": (current_row.get("status") if current_row else None)
            != (previous_row.get("status") if previous_row else None),
            "issues_count_delta": (
                len(current_row.get("issues", [])) - len(previous_row.get("issues", []))
                if current_row is not None and previous_row is not None
                else None
            ),
            "changed_metric_names": changed_metric_names,
            "changed": False,
        }
        row_delta["changed"] = (
            row_delta["status_changed"]
            or row_delta["issues_count_delta"] not in (None, 0)
            or bool(changed_metric_names)
        )
        if row_delta["changed"]:
            changed_rows_count += 1
        delta["row_deltas"].append(row_delta)
    delta["changed_rows_count"] = changed_rows_count
    return delta


def format_platform_acceptance_delta(delta):
    return "\n".join(format_platform_acceptance_delta_lines(delta))


def format_platform_acceptance_delta_lines(delta):
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
    lines.append("- previous_report_dir={0}".format(delta.get("previous_report_dir")))
    lines.append(
        "- planner_acceptance_status_changed={0} previous_planner_status={1} current_planner_status={2}".format(
            delta.get("planner_acceptance_status_changed"),
            delta.get("previous_planner_acceptance_status"),
            delta.get("current_planner_acceptance_status"),
        )
    )
    lines.append(
        "- issues_count_delta={0} changed_rows_count={1}".format(
            delta.get("issues_count_delta"),
            delta.get("changed_rows_count"),
        )
    )
    changed_rows = [row for row in delta.get("row_deltas", []) if row.get("changed")]
    if not changed_rows:
        lines.append("- no status or tracked metric changes versus previous snapshot")
        return lines

    for row in changed_rows:
        lines.append(
            "- {0}: previous_status={1} current_status={2} changed_metrics={3} issues_count_delta={4}".format(
                row.get("name"),
                row.get("previous_status"),
                row.get("current_status"),
                ",".join(row.get("changed_metric_names", [])) or "none",
                row.get("issues_count_delta"),
            )
        )
    return lines
