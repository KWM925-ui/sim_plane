import json
from pathlib import Path

from sim_plane.artifacts import read_jsonl, utc_timestamp
from sim_plane.planner_acceptance import (
    _resolve_artifact_root,
    append_history_entry,
    build_acceptance_report_dir,
    load_previous_acceptance_report,
    prune_acceptance_reports,
    resolve_artifact_dir,
)
from sim_plane.acceptance_common import (
    build_acceptance_delta,
    evaluate_metric_regression_budgets,
    format_delta_lines,
    load_reference_result,
    merge_metric_regression_budgets,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_PATH = REPO_ROOT / "configs" / "px4_failure_injection_acceptance_matrix.json"
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "px4_failure_injection_acceptance"
DEFAULT_KEEP_LAST = 5


def load_matrix(path=None):
    matrix_path = Path(path) if path is not None else DEFAULT_MATRIX_PATH
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    payload["_matrix_path"] = matrix_path
    return payload


def validate_matrix(path=None, artifact_root=None, use_latest=False):
    matrix = load_matrix(path)
    matrix_path = matrix["_matrix_path"]
    artifact_root_path = _resolve_artifact_root(matrix_path, artifact_root)
    required_event_levels = set(matrix.get("required_event_levels", ["info"]))
    default_metric_regression_budgets = matrix.get("metric_regression_budgets", {})
    rows = []
    issues = []
    for row_spec in matrix.get("rows", []):
        row_report = validate_row(
            row_spec=row_spec,
            matrix_path=matrix_path,
            artifact_root=artifact_root_path,
            required_event_levels=required_event_levels,
            default_metric_regression_budgets=default_metric_regression_budgets,
            use_latest=use_latest,
        )
        rows.append(row_report)
        issues.extend(row_report["issues"])
    return {
        "matrix_name": matrix.get("matrix_name", "px4_failure_injection_acceptance"),
        "matrix_path": str(matrix_path),
        "artifact_root": str(artifact_root_path),
        "selection_mode": "latest" if use_latest else "reference",
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "rows": rows,
    }


def validate_row(
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
    )
    reference_artifact_dir, _ = resolve_artifact_dir(
        {
            "scenario_name": row_spec["scenario_name"],
            "reference_artifact": row_spec["reference_artifact"],
        },
        matrix_path=matrix_path,
        artifact_root=artifact_root,
        use_latest=False,
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
        "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
        "reference_artifact_dir": str(reference_artifact_dir) if reference_artifact_dir is not None else None,
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
    for file_path in (result_path, manifest_path, events_path):
        if not file_path.exists():
            report["issues"].append("missing required file: {0}".format(file_path.name))
    if report["issues"]:
        return report

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    events = read_jsonl(events_path)
    reference_result, reference_issues = load_reference_result(
        reference_artifact_dir=reference_artifact_dir,
        backend=row_spec["backend"],
        scenario_name=row_spec["scenario_name"],
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
            "manifest backend mismatch: expected {0}, got {1}".format(row_spec["backend"], manifest.get("backend"))
        )
    if result.get("backend") != row_spec["backend"]:
        report["issues"].append(
            "result backend mismatch: expected {0}, got {1}".format(row_spec["backend"], result.get("backend"))
        )
    if result.get("scenario_name") != row_spec["scenario_name"]:
        report["issues"].append(
            "scenario_name mismatch: expected {0}, got {1}".format(row_spec["scenario_name"], result.get("scenario_name"))
        )
    if result.get("vehicle") != "quadrotor":
        report["issues"].append("vehicle mismatch: expected quadrotor, got {0}".format(result.get("vehicle")))
    if result.get("status") != "passed":
        report["issues"].append("result status is not passed")

    for metric_name, expected_value in row_spec.get("required_metrics", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value != expected_value:
            report["issues"].append(
                "metric {0} mismatch: expected {1}, got {2}".format(metric_name, expected_value, actual_value)
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


def format_report(report):
    lines = [
        "px4 failure injection acceptance: {0} ({1} artifacts)".format(
            report["status"], report["selection_mode"]
        ),
        "matrix: {0}".format(report["matrix_path"]),
    ]
    if report["selection_mode"] == "latest":
        lines.append("artifact_root: {0}".format(report["artifact_root"]))
    lines.append("")
    header = "{0:34} {1:12} {2:10} {3}".format("name", "backend", "status", "surface")
    lines.append(header)
    lines.append("-" * len(header))
    for row in report["rows"]:
        lines.append(
            "{0:34} {1:12} {2:10} {3}".format(
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
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    delta = report.get("delta_from_previous")
    if delta is not None:
        lines.append("")
        lines.extend(format_delta_lines(delta))
    return "\n".join(lines)


def write_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    report_root_path = Path(report_root) if report_root is not None else DEFAULT_REPORT_ROOT
    report_root_path.mkdir(parents=True, exist_ok=True)
    matrix_name = report.get("matrix_name", "px4_failure_injection_acceptance")
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
    delta = build_acceptance_delta(
        payload,
        previous_report,
        tracked_metrics=[
            "telemetry_count",
            "mode_changes",
            "failure_injection_accepted",
            "failure_injection_reset_accepted",
            "failure_injection_health_changed_count",
        ],
    )
    payload["delta_from_previous"] = delta

    json_path = report_dir / "report.json"
    text_path = report_dir / "report.txt"
    delta_json_path = report_dir / "delta.json"
    delta_text_path = report_dir / "delta.txt"
    manifest_path = report_dir / "manifest.json"
    text_report = format_report(payload) + "\n"
    delta_text = "\n".join(format_delta_lines(delta)) + "\n"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(text_report, encoding="utf-8")
    delta_json_path.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    delta_text_path.write_text(delta_text, encoding="utf-8")

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
            "row_status": {row["name"]: row["status"] for row in payload.get("rows", [])},
        },
    )

    latest_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_text_path.write_text(text_report, encoding="utf-8")
    latest_delta_json_path.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_delta_text_path.write_text(delta_text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "matrix_name": matrix_name,
                "selection_mode": selection_mode,
                "report_files": {
                    "json": json_path.name,
                    "text": text_path.name,
                    "delta_json": delta_json_path.name,
                    "delta_text": delta_text_path.name,
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    pruned_report_dirs = prune_acceptance_reports(
        report_root_path,
        matrix_name=matrix_name,
        selection_mode=selection_mode,
        keep_last=keep_last,
    )

    return {
        "report_dir": str(report_dir),
        "report_json": str(json_path),
        "report_text": str(text_path),
        "latest_report_json": str(latest_json_path),
        "latest_report_text": str(latest_text_path),
        "latest_delta_json": str(latest_delta_json_path),
        "latest_delta_text": str(latest_delta_text_path),
        "history_jsonl": str(history_jsonl_path),
        "keep_last": keep_last,
        "pruned_report_dirs": pruned_report_dirs,
        "delta": delta,
    }
