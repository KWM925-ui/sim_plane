import json
from datetime import datetime, timezone
from pathlib import Path

from sim_plane.artifacts import is_complete_artifact_dir, safe_artifact_name
from sim_plane.baseline_store import BASELINE_META_FILE, verify_artifact_baseline
from sim_plane.io_utils import append_jsonl, prune_directories
from sim_plane.paths import resolve_platform_path


def resolve_artifact_root(matrix_path, artifact_root):
    if artifact_root is not None:
        return resolve_platform_path(artifact_root)
    return Path(matrix_path).parent.parent / "runs"


def resolve_artifact_dir(
    mode_spec,
    matrix_path,
    artifact_root,
    use_latest=False,
    expected_backend=None,
    expected_vehicle=None,
):
    if use_latest:
        scenario_name = mode_spec["scenario_name"]
        candidates = []
        for path in Path(artifact_root).iterdir():
            if not is_complete_artifact_dir(path):
                continue
            result_path = path / "result.json"
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if result.get("scenario_name") != scenario_name:
                continue
            if expected_backend is not None and result.get("backend") != expected_backend:
                continue
            if expected_vehicle is not None and result.get("vehicle") != expected_vehicle:
                continue
            candidates.append(path)
        if not candidates:
            identity = ["scenario={0}".format(scenario_name)]
            if expected_backend is not None:
                identity.append("backend={0}".format(expected_backend))
            if expected_vehicle is not None:
                identity.append("vehicle={0}".format(expected_vehicle))
            return None, "no artifact found for latest {0}".format(", ".join(identity))
        return max(candidates, key=artifact_sort_key), None

    artifact_dir = Path(mode_spec["reference_artifact"])
    if not artifact_dir.is_absolute():
        artifact_dir = (Path(matrix_path).parent.parent / artifact_dir).resolve()
    return artifact_dir, None


def artifact_sort_key(artifact_dir):
    return (artifact_created_timestamp(artifact_dir), artifact_dir.name)


def artifact_created_timestamp(artifact_dir):
    artifact_dir = Path(artifact_dir)
    manifest_path = artifact_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
        timestamp = parse_artifact_timestamp(manifest.get("created_at_utc"))
        if timestamp is not None:
            return timestamp

    mtimes = []
    for child_name in ("result.json", "manifest.json", "events.jsonl"):
        child = artifact_dir / child_name
        if child.exists():
            mtimes.append(child.stat().st_mtime)
    try:
        mtimes.append(artifact_dir.stat().st_mtime)
    except OSError:
        pass
    return max(mtimes) if mtimes else 0.0


def parse_artifact_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def resolve_reference_artifact_dir(mode_spec, matrix_path):
    artifact_dir = Path(mode_spec["reference_artifact"])
    if not artifact_dir.is_absolute():
        artifact_dir = (Path(matrix_path).parent.parent / artifact_dir).resolve()
    return artifact_dir


def build_acceptance_report_dir(report_root, matrix_name, selection_mode):
    safe_matrix_name = safe_artifact_name(matrix_name)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return Path(report_root) / "{0}_{1}_{2}".format(
        safe_matrix_name,
        selection_mode,
        stamp,
    )


def append_history_entry(path, entry):
    append_jsonl(path, entry)


def prune_acceptance_reports(report_root_path, matrix_name, selection_mode, keep_last):
    safe_matrix_name = safe_artifact_name(matrix_name)
    return prune_directories(
        report_root_path,
        "{0}_{1}_*".format(safe_matrix_name, selection_mode),
        keep_last,
    )


def load_previous_acceptance_report(path):
    report_path = Path(path)
    if not report_path.exists():
        return None
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def merge_metric_regression_budgets(default_budgets, row_budgets):
    merged = {}
    for source in (default_budgets or {}, row_budgets or {}):
        for metric_name, budget in source.items():
            existing = merged.get(metric_name, {})
            merged[metric_name] = {**existing, **budget}
    return merged


def load_reference_result(
    reference_artifact_dir,
    backend,
    scenario_name,
    expected_vehicle="quadrotor",
    require_baseline_metadata=False,
    expected_source_artifact=None,
):
    issues = []
    if reference_artifact_dir is None:
        return None, ["reference artifact directory could not be resolved"]

    metadata_path = Path(reference_artifact_dir) / BASELINE_META_FILE
    if require_baseline_metadata or metadata_path.exists():
        issues.extend(
            verify_artifact_baseline(
                reference_artifact_dir,
                expected_source_artifact=expected_source_artifact,
            )
        )

    result_path = reference_artifact_dir / "result.json"
    if not result_path.exists():
        issues.append("missing reference result.json")
        return None, issues

    try:
        reference_result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        issues.append("reference result.json is not valid JSON")
        return None, issues

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


def validate_matrix_rows(matrix, label):
    rows = matrix.get("rows")
    issues = []
    if not isinstance(rows, list):
        return [], ["{0}.rows must be a non-empty list".format(label)]
    if not rows:
        issues.append("{0}.rows must not be empty".format(label))
    required_count = matrix.get("required_row_count")
    if required_count is not None:
        if isinstance(required_count, bool) or not isinstance(required_count, int) or required_count <= 0:
            issues.append("{0}.required_row_count must be a positive integer".format(label))
        elif len(rows) != required_count:
            issues.append(
                "{0} row count mismatch: expected {1}, got {2}".format(
                    label,
                    required_count,
                    len(rows),
                )
            )
    return rows, issues


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


def format_delta_lines(delta):
    lines = [
        "delta_from_previous:",
        "  previous_report_dir: {0}".format(delta.get("previous_report_dir") or "-"),
        "  status_changed: {0}".format(delta.get("status_changed")),
        "  issues_count_delta: {0}".format(delta.get("issues_count_delta")),
        "  changed_rows_count: {0}".format(delta.get("changed_rows_count")),
    ]
    for row_delta in delta.get("row_deltas", []):
        if not row_delta.get("changed"):
            continue
        lines.append(
            "  row {0}: {1}->{2}, issues_delta={3}, metric_delta={4}".format(
                row_delta.get("name"),
                row_delta.get("previous_status"),
                row_delta.get("current_status"),
                row_delta.get("issues_count_delta"),
                json.dumps(row_delta.get("metric_delta", {}), sort_keys=True, ensure_ascii=False),
            )
        )
    return lines
