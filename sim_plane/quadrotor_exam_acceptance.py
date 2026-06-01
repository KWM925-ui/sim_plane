import json
from pathlib import Path

from sim_plane.acceptance_common import evaluate_metric_regression_budgets
from sim_plane.artifacts import utc_timestamp
from sim_plane.planner_acceptance import (
    append_history_entry,
    build_acceptance_report_dir,
    load_previous_acceptance_report,
    prune_acceptance_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_PATH = REPO_ROOT / "configs" / "quadrotor_exam_acceptance_matrix.json"
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "quadrotor_exam_acceptance"
DEFAULT_KEEP_LAST = 10


def load_matrix(path=None):
    matrix_path = Path(path) if path is not None else DEFAULT_MATRIX_PATH
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    payload["_matrix_path"] = matrix_path
    return payload


def validate_matrix(path=None, artifact_root=None, use_latest=False):
    matrix = load_matrix(path)
    matrix_path = matrix["_matrix_path"]
    suite_name = matrix.get("suite_name", "paper_quadrotor_exam_suite")
    current_report_path = resolve_suite_report_path(
        matrix=matrix,
        matrix_path=matrix_path,
        artifact_root=artifact_root,
        use_latest=use_latest,
    )
    reference_report_path = resolve_path(matrix.get("reference_report"), matrix_path)
    current_report, current_load_issues = load_suite_report(current_report_path)
    reference_report, reference_load_issues = load_suite_report(reference_report_path)
    rows = []
    issues = []
    issues.extend(current_load_issues)
    issues.extend("reference {0}".format(issue) for issue in reference_load_issues)

    if current_report is not None:
        issues.extend(validate_suite_identity(current_report, suite_name))
        issues.extend(validate_exam_summary(current_report, matrix))
    if reference_report is not None:
        issues.extend("reference {0}".format(issue) for issue in validate_suite_identity(reference_report, suite_name))
        issues.extend("reference {0}".format(issue) for issue in validate_exam_summary(reference_report, matrix))

    if current_report is not None and reference_report is not None:
        rows, row_issues = validate_rows(
            current_report=current_report,
            reference_report=reference_report,
            matrix=matrix,
        )
        issues.extend(row_issues)
        issues.extend(validate_exam_summary_regression(current_report, reference_report, matrix))

    return {
        "matrix_name": matrix.get("matrix_name", "quadrotor_exam_acceptance"),
        "matrix_path": str(matrix_path),
        "suite_name": suite_name,
        "selection_mode": "latest" if use_latest else "reference",
        "report_path": str(current_report_path) if current_report_path is not None else None,
        "reference_report_path": str(reference_report_path) if reference_report_path is not None else None,
        "artifact_root": str(Path(artifact_root)) if artifact_root is not None else str(REPO_ROOT / "runs"),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "summary": build_summary(current_report),
        "reference_summary": build_summary(reference_report),
        "rows": rows,
    }


def resolve_suite_report_path(matrix, matrix_path, artifact_root=None, use_latest=False):
    if use_latest:
        if artifact_root is not None:
            return Path(artifact_root) / "suites" / "latest_{0}.json".format(
                matrix.get("suite_name", "paper_quadrotor_exam_suite")
            )
        latest_report = matrix.get("latest_report")
        if latest_report:
            return resolve_path(latest_report, matrix_path)
    return resolve_path(matrix.get("reference_report"), matrix_path)


def resolve_path(path_value, matrix_path):
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (matrix_path.parent.parent / path).resolve()


def load_suite_report(path):
    if path is None:
        return None, ["suite report path is not configured"]
    report_path = Path(path)
    if not report_path.exists():
        return None, ["missing suite report: {0}".format(report_path)]
    try:
        return json.loads(report_path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError:
        return None, ["suite report is not valid JSON: {0}".format(report_path)]


def validate_suite_identity(report, suite_name):
    issues = []
    if report.get("suite_name") != suite_name:
        issues.append("suite_name mismatch: expected {0}, got {1}".format(suite_name, report.get("suite_name")))
    if report.get("status") != "passed":
        issues.append("suite status is not passed")
    return issues


def validate_exam_summary(report, matrix):
    issues = []
    exam = ensure_exam_summary(report)
    required_scene_count = matrix.get("required_scene_count")
    required_success_rate = matrix.get("required_success_rate")
    if required_scene_count is not None and exam.get("scene_count") != required_scene_count:
        issues.append(
            "exam scene_count mismatch: expected {0}, got {1}".format(
                required_scene_count,
                exam.get("scene_count"),
            )
        )
    if required_success_rate is not None and exam.get("success_rate") != required_success_rate:
        issues.append(
            "exam success_rate mismatch: expected {0}, got {1}".format(
                required_success_rate,
                exam.get("success_rate"),
            )
        )
    return issues


def validate_exam_summary_regression(current_report, reference_report, matrix):
    current_summary = build_summary(current_report)
    reference_summary = build_summary(reference_report)
    _, issues = evaluate_metric_regression_budgets(
        metrics=current_summary,
        reference_metrics=reference_summary,
        metric_regression_budgets=matrix.get("exam_regression_budgets", {}),
    )
    return ["exam {0}".format(issue) for issue in issues]


def validate_rows(current_report, reference_report, matrix):
    current_rows = {row.get("name"): row for row in current_report.get("rows", [])}
    reference_rows = {row.get("name"): row for row in reference_report.get("rows", [])}
    required_scene_names = matrix.get("required_scene_names") or sorted(reference_rows)
    required_row_status = matrix.get("required_row_status", "passed")
    row_metric_budgets = matrix.get("row_metric_regression_budgets", {})
    rows = []
    issues = []

    for name in required_scene_names:
        current_row = current_rows.get(name)
        reference_row = reference_rows.get(name)
        row_report = validate_row(
            name=name,
            current_row=current_row,
            reference_row=reference_row,
            required_row_status=required_row_status,
            row_metric_budgets=row_metric_budgets,
        )
        rows.append(row_report)
        issues.extend(row_report["issues"])

    extra_scenes = sorted(set(current_rows) - set(required_scene_names))
    if extra_scenes and not matrix.get("allow_extra_scenes", False):
        issues.append("unexpected exam scenes: {0}".format(", ".join(extra_scenes)))
    missing_reference_scenes = sorted(set(required_scene_names) - set(reference_rows))
    if missing_reference_scenes:
        issues.append("reference missing exam scenes: {0}".format(", ".join(missing_reference_scenes)))
    return rows, issues


def validate_row(name, current_row, reference_row, required_row_status, row_metric_budgets):
    row_issues = []
    current_metrics = dict((current_row or {}).get("metrics") or {})
    reference_metrics = dict((reference_row or {}).get("metrics") or {})
    if current_row is None:
        row_issues.append("row {0} missing in current report".format(name))
    if reference_row is None:
        row_issues.append("row {0} missing in reference report".format(name))
    if current_row is not None and current_row.get("status") != required_row_status:
        row_issues.append(
            "row {0} status mismatch: expected {1}, got {2}".format(
                name,
                required_row_status,
                current_row.get("status"),
            )
        )
    regressions, regression_issues = evaluate_metric_regression_budgets(
        metrics=current_metrics,
        reference_metrics=reference_metrics,
        metric_regression_budgets=row_metric_budgets,
    )
    row_issues.extend("row {0} {1}".format(name, issue) for issue in regression_issues)
    return {
        "name": name,
        "status": "passed" if not row_issues else "failed",
        "current_status": current_row.get("status") if current_row else None,
        "reference_status": reference_row.get("status") if reference_row else None,
        "artifact_dir": current_row.get("artifact_dir") if current_row else None,
        "reference_artifact_dir": reference_row.get("artifact_dir") if reference_row else None,
        "metrics": select_metrics(current_metrics, row_metric_budgets),
        "reference_metrics": select_metrics(reference_metrics, row_metric_budgets),
        "metric_regressions": regressions,
        "issues": row_issues,
    }


def select_metrics(metrics, budgets):
    return {metric_name: metrics.get(metric_name) for metric_name in budgets}


def build_summary(report):
    if not report:
        return {}
    exam = ensure_exam_summary(report)
    return {
        "scene_count": exam.get("scene_count"),
        "passed_scene_count": exam.get("passed_scene_count"),
        "success_rate": exam.get("success_rate"),
    }


def ensure_exam_summary(report):
    exam = report.get("exam")
    if isinstance(exam, dict) and exam:
        return exam
    rows = report.get("rows") or []
    scene_count = len(rows)
    passed_scene_count = sum(1 for row in rows if row.get("status") == "passed")
    return {
        "scene_count": scene_count,
        "passed_scene_count": passed_scene_count,
        "success_rate": round(passed_scene_count / scene_count, 6) if scene_count else 0.0,
    }


def format_report(report):
    lines = [
        "quadrotor exam acceptance: {0} ({1})".format(report["status"], report["selection_mode"]),
        "matrix: {0}".format(report["matrix_path"]),
        "suite_report: {0}".format(report.get("report_path")),
        "reference_report: {0}".format(report.get("reference_report_path")),
        "summary: {0}".format(json.dumps(report.get("summary", {}), ensure_ascii=False, sort_keys=True)),
        "",
    ]
    header = "{0:<28} {1:<10} {2:<10} {3}".format("scene", "row", "current", "artifact")
    lines.append(header)
    lines.append("-" * len(header))
    for row in report.get("rows", []):
        lines.append(
            "{0:<28} {1:<10} {2:<10} {3}".format(
                row["name"],
                row["status"],
                row.get("current_status"),
                Path(row["artifact_dir"]).name if row.get("artifact_dir") else "-",
            )
        )
        if row.get("metric_regressions"):
            lines.append(
                "  regressions={0}".format(
                    json.dumps(row["metric_regressions"], ensure_ascii=False, sort_keys=True)
                )
            )
        for issue in row.get("issues", []):
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
    matrix_name = report.get("matrix_name", "quadrotor_exam_acceptance")
    selection_mode = report.get("selection_mode", "reference")
    report_dir = build_acceptance_report_dir(report_root_path, matrix_name, selection_mode)
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
    delta = build_delta(payload, previous_report)
    payload["delta_from_previous"] = delta

    json_path = report_dir / "report.json"
    text_path = report_dir / "report.txt"
    delta_json_path = report_dir / "delta.json"
    delta_text_path = report_dir / "delta.txt"
    manifest_path = report_dir / "manifest.json"
    text_report = format_report(payload) + "\n"
    delta_text = format_delta(delta) + "\n"

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
            "summary": payload.get("summary"),
        },
    )
    pruned_report_dirs = prune_acceptance_reports(
        report_root_path=report_root_path,
        matrix_name=matrix_name,
        selection_mode=selection_mode,
        keep_last=keep_last,
    )
    manifest_path.write_text(
        json.dumps(
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
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    latest_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_text_path.write_text(text_report, encoding="utf-8")
    latest_delta_json_path.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_delta_text_path.write_text(delta_text, encoding="utf-8")
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


def build_delta(current_report, previous_report):
    delta = {
        "has_previous_report": previous_report is not None,
        "selection_mode": current_report.get("selection_mode"),
        "current_report_dir": current_report.get("report_dir"),
        "current_status": current_report.get("status"),
        "current_issues_count": len(current_report.get("issues", [])),
        "previous_report_dir": previous_report.get("report_dir") if previous_report else None,
        "previous_status": previous_report.get("status") if previous_report else None,
        "previous_issues_count": len(previous_report.get("issues", [])) if previous_report else None,
        "status_changed": False,
        "issues_count_delta": None,
        "changed_rows_count": 0,
        "summary_delta": {},
        "row_deltas": [],
    }
    if previous_report is None:
        return delta
    delta["status_changed"] = current_report.get("status") != previous_report.get("status")
    delta["issues_count_delta"] = len(current_report.get("issues", [])) - len(previous_report.get("issues", []))
    delta["summary_delta"] = diff_mapping(current_report.get("summary", {}), previous_report.get("summary", {}))
    current_rows = {row["name"]: row for row in current_report.get("rows", [])}
    previous_rows = {row["name"]: row for row in previous_report.get("rows", [])}
    changed_rows_count = 0
    for name in sorted(set(current_rows) | set(previous_rows)):
        current_row = current_rows.get(name)
        previous_row = previous_rows.get(name)
        metric_delta = diff_mapping(
            (current_row or {}).get("metrics", {}),
            (previous_row or {}).get("metrics", {}),
        )
        row_delta = {
            "name": name,
            "current_status": current_row.get("status") if current_row else None,
            "previous_status": previous_row.get("status") if previous_row else None,
            "status_changed": (current_row.get("status") if current_row else None)
            != (previous_row.get("status") if previous_row else None),
            "issues_count_delta": (
                len(current_row.get("issues", [])) - len(previous_row.get("issues", []))
                if current_row is not None and previous_row is not None
                else None
            ),
            "metric_delta": metric_delta,
            "changed": False,
        }
        row_delta["changed"] = (
            row_delta["status_changed"]
            or row_delta["issues_count_delta"] not in (None, 0)
            or any(value not in (None, 0, 0.0) for value in metric_delta.values())
        )
        if row_delta["changed"]:
            changed_rows_count += 1
        delta["row_deltas"].append(row_delta)
    delta["changed_rows_count"] = changed_rows_count
    return delta


def diff_mapping(current, previous):
    diff = {}
    for key in sorted(set(current) | set(previous)):
        current_value = current.get(key)
        previous_value = previous.get(key)
        if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
            diff[key] = round(current_value - previous_value, 6)
        elif current_value == previous_value:
            diff[key] = 0
        else:
            diff[key] = {"previous": previous_value, "current": current_value}
    return diff


def format_delta(delta):
    return "\n".join(format_delta_lines(delta))


def format_delta_lines(delta):
    lines = ["delta from previous quadrotor exam acceptance:"]
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
    lines.append("- changed_rows_count={0}".format(delta.get("changed_rows_count")))
    if delta.get("summary_delta"):
        lines.append("- summary_delta={0}".format(json.dumps(delta["summary_delta"], ensure_ascii=False, sort_keys=True)))
    return lines
