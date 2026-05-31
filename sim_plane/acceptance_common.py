import json


def merge_metric_regression_budgets(default_budgets, row_budgets):
    merged = {}
    for source in (default_budgets or {}, row_budgets or {}):
        for metric_name, budget in source.items():
            existing = merged.get(metric_name, {})
            merged[metric_name] = {**existing, **budget}
    return merged


def load_reference_result(reference_artifact_dir, backend, scenario_name, expected_vehicle="quadrotor"):
    issues = []
    if reference_artifact_dir is None:
        return None, ["reference artifact directory could not be resolved"]

    result_path = reference_artifact_dir / "result.json"
    if not result_path.exists():
        return None, ["missing reference result.json"]

    try:
        reference_result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, ["reference result.json is not valid JSON"]

    if reference_result.get("backend") != backend:
        issues.append(
            "reference backend mismatch: expected {0}, got {1}".format(
                backend, reference_result.get("backend")
            )
        )
    if reference_result.get("scenario_name") != scenario_name:
        issues.append(
            "reference scenario_name mismatch: expected {0}, got {1}".format(
                scenario_name, reference_result.get("scenario_name")
            )
        )
    if reference_result.get("vehicle") != expected_vehicle:
        issues.append(
            "reference vehicle mismatch: expected {0}, got {1}".format(
                expected_vehicle, reference_result.get("vehicle")
            )
        )
    if reference_result.get("status") != "passed":
        issues.append("reference result status is not passed")

    return reference_result, issues


def evaluate_metric_regression_budgets(metrics, reference_metrics, metric_regression_budgets):
    regressions = {}
    issues = []
    for metric_name, budget in (metric_regression_budgets or {}).items():
        current_value = metrics.get(metric_name)
        reference_value = reference_metrics.get(metric_name)
        if current_value is None and reference_value is None:
            continue
        if reference_value is None:
            issues.append("reference metric {0} is missing".format(metric_name))
            continue
        if current_value is None:
            issues.append("metric {0} is missing".format(metric_name))
            continue
        if not isinstance(current_value, (int, float)) or not isinstance(reference_value, (int, float)):
            issues.append("metric regression budget for {0} requires numeric metrics".format(metric_name))
            continue

        regression = round(current_value - reference_value, 3)
        regressions[metric_name] = regression
        max_drop = budget.get("max_drop")
        if max_drop is not None:
            drop = round(reference_value - current_value, 3)
            if drop > max_drop:
                issues.append(
                    "metric {0} regressed by {1} beyond allowed drop {2}".format(
                        metric_name,
                        drop,
                        max_drop,
                    )
                )
        max_increase = budget.get("max_increase")
        if max_increase is not None:
            increase = round(current_value - reference_value, 3)
            if increase > max_increase:
                issues.append(
                    "metric {0} increased by {1} beyond allowed {2}".format(
                        metric_name,
                        increase,
                        max_increase,
                    )
                )
    return regressions, issues


def build_acceptance_delta(current_report, previous_report, tracked_metrics):
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
        "changed_rows_count": 0,
        "row_deltas": [],
    }
    if previous_report is None:
        return delta

    delta["status_changed"] = current_report.get("status") != previous_report.get("status")
    delta["issues_count_delta"] = len(current_report.get("issues", [])) - len(previous_report.get("issues", []))
    previous_rows = {row["name"]: row for row in previous_report.get("rows", [])}
    current_rows = {row["name"]: row for row in current_report.get("rows", [])}
    changed_rows_count = 0

    for name in sorted(set(previous_rows) | set(current_rows)):
        current_row = current_rows.get(name)
        previous_row = previous_rows.get(name)
        metric_delta = {}
        for metric_name in tracked_metrics:
            current_value = current_row.get("metrics", {}).get(metric_name) if current_row else None
            previous_value = previous_row.get("metrics", {}).get(metric_name) if previous_row else None
            if current_value is None or previous_value is None:
                metric_delta[metric_name] = None
            elif isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                metric_delta[metric_name] = round(current_value - previous_value, 3)
            elif current_value == previous_value:
                metric_delta[metric_name] = 0
            else:
                metric_delta[metric_name] = {"previous": previous_value, "current": current_value}
        row_delta = {
            "name": name,
            "current_status": current_row.get("status") if current_row else None,
            "previous_status": previous_row.get("status") if previous_row else None,
            "status_changed": (current_row.get("status") if current_row else None)
            != (previous_row.get("status") if previous_row else None),
            "metric_delta": metric_delta,
            "issues_count_delta": (
                len(current_row.get("issues", [])) - len(previous_row.get("issues", []))
                if current_row is not None and previous_row is not None
                else None
            ),
        }
        row_changed = row_delta["status_changed"] or any(
            value not in (None, 0, 0.0) for value in metric_delta.values()
        ) or row_delta["issues_count_delta"] not in (None, 0)
        if row_changed:
            changed_rows_count += 1
        row_delta["changed"] = row_changed
        delta["row_deltas"].append(row_delta)

    delta["changed_rows_count"] = changed_rows_count
    return delta
