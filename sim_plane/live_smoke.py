import json
from datetime import datetime
from pathlib import Path

from sim_plane.io_utils import atomic_write_json, append_jsonl, prune_directories, report_write_lock
from sim_plane.paths import get_platform_paths, resolve_platform_path

from sim_plane.runner import ensure_artifact_root, run_scenario


REPO_ROOT = get_platform_paths().home
DEFAULT_LIVE_SMOKE_MATRIX = REPO_ROOT / "configs" / "live_smoke_matrix.json"
DEFAULT_LIVE_SMOKE_REPORT_ROOT = REPO_ROOT / "runs" / "live_smoke"
DEFAULT_PROFILE = "default"
DEFAULT_KEEP_LAST = 10


def load_live_smoke_matrix(path=None):
    matrix_path = resolve_platform_path(path) if path is not None else DEFAULT_LIVE_SMOKE_MATRIX
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["_matrix_path"] = matrix_path
    return matrix


def run_live_smoke_suite(
    matrix_path=None,
    profile=DEFAULT_PROFILE,
    artifact_root="runs",
    report_root=None,
    keep_last=DEFAULT_KEEP_LAST,
    runtime_options=None,
):
    artifact_root_path = resolve_platform_path(artifact_root)
    matrix = load_live_smoke_matrix(matrix_path)
    rows = select_rows(matrix, profile)
    ensure_artifact_root(artifact_root_path)
    reports = []
    issues = []
    for row in rows:
        report = run_live_smoke_row(
            row,
            matrix_path=matrix["_matrix_path"],
            artifact_root=artifact_root_path,
            runtime_options=runtime_options or {},
        )
        reports.append(report)
        issues.extend(report["issues"])
    suite = {
        "matrix_name": matrix.get("matrix_name", "live_smoke"),
        "matrix_path": str(matrix["_matrix_path"]),
        "profile": profile,
        "artifact_root": str(artifact_root_path),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "rows": reports,
    }
    if report_root is not None:
        suite["saved_report"] = write_live_smoke_report(
            suite,
            report_root=report_root,
            keep_last=keep_last,
        )
    return suite


def select_rows(matrix, profile):
    profiles = matrix.get("profiles", {})
    if profile not in profiles:
        raise ValueError(
            "Unknown live smoke profile: {0}. Known profiles: {1}".format(
                profile,
                ", ".join(sorted(profiles)),
            )
        )
    selected_names = profiles[profile]
    rows_by_name = {row["name"]: row for row in matrix.get("rows", [])}
    rows = []
    for name in selected_names:
        if name not in rows_by_name:
            raise ValueError("Live smoke profile {0} references unknown row: {1}".format(profile, name))
        rows.append(rows_by_name[name])
    return rows


def run_live_smoke_row(row, matrix_path, artifact_root, runtime_options):
    scenario_path = resolve_matrix_relative_path(matrix_path, row["scenario"])
    report = {
        "name": row["name"],
        "surface": row.get("surface", ""),
        "scenario": str(scenario_path),
        "status": "failed",
        "artifact_dir": None,
        "metrics": {},
        "issues": [],
    }
    try:
        outcome = run_scenario(
            str(scenario_path),
            artifact_root=artifact_root,
            visualize=False,
            hold_open=False,
            runtime_options=runtime_options,
        )
    except Exception as exc:
        report["issues"].append("run raised exception: {0}".format(exc))
        return report

    result = outcome.get("result", {})
    metrics = result.get("metrics", {})
    report["artifact_dir"] = outcome.get("artifact_dir")
    report["metrics"] = metrics
    expected_status = row.get("required_status", "passed")
    if result.get("status") != expected_status:
        report["issues"].append(
            "status mismatch: expected {0}, got {1}".format(expected_status, result.get("status"))
        )
    for metric_name, expected_value in row.get("required_metrics", {}).items():
        actual_value = metrics.get(metric_name)
        if actual_value != expected_value:
            report["issues"].append(
                "metric {0} mismatch: expected {1}, got {2}".format(
                    metric_name,
                    expected_value,
                    actual_value,
                )
            )
    report["status"] = "passed" if not report["issues"] else "failed"
    return report


def resolve_matrix_relative_path(matrix_path, value):
    path = Path(value)
    if path.is_absolute():
        return path
    matrix_dir_candidate = (Path(matrix_path).parent / path).resolve()
    if matrix_dir_candidate.exists():
        return matrix_dir_candidate
    return (REPO_ROOT / path).resolve()


def write_live_smoke_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = resolve_platform_path(report_root) if report_root is not None else DEFAULT_LIVE_SMOKE_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with report_write_lock(root):
        return _write_live_smoke_report_locked(report, root, keep_last)


def _write_live_smoke_report_locked(report, root, keep_last):
    root = root if hasattr(root, "joinpath") else resolve_platform_path(root)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    report_dir = root / "live_smoke_{0}_{1}".format(report.get("profile", "default"), stamp)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "report.json"
    latest_json = root / "latest_{0}.json".format(report.get("profile", "default"))
    history_jsonl = root / "history_{0}.jsonl".format(report.get("profile", "default"))
    serializable = dict(report)
    serializable.pop("saved_report", None)
    atomic_write_json(report_json, serializable)
    atomic_write_json(latest_json, serializable)
    append_jsonl(
        history_jsonl,
        {
            "created_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "profile": report.get("profile"),
            "status": report.get("status"),
            "report_json": str(report_json),
        },
    )
    if keep_last and keep_last > 0:
        prune_live_smoke_reports(root, report.get("profile", "default"), keep_last)
    return {
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "latest_json": str(latest_json),
        "history_jsonl": str(history_jsonl),
    }


def prune_live_smoke_reports(report_root, profile, keep_last):
    return prune_directories(
        report_root,
        "live_smoke_{0}_*".format(profile),
        keep_last,
    )


def format_live_smoke_report(report):
    lines = [
        "live smoke: {0} (profile={1})".format(report["status"], report["profile"]),
        "matrix: {0}".format(report["matrix_path"]),
        "artifact_root: {0}".format(report["artifact_root"]),
        "",
        "{0:<24} {1:<8} {2}".format("name", "status", "artifact_dir"),
        "-" * 78,
    ]
    for row in report["rows"]:
        lines.append(
            "{0:<24} {1:<8} {2}".format(
                row["name"],
                row["status"],
                row.get("artifact_dir") or "-",
            )
        )
        if row.get("surface"):
            lines.append("  surface={0}".format(row["surface"]))
        if row.get("metrics"):
            lines.append("  metrics={0}".format(json.dumps(row["metrics"], ensure_ascii=False, sort_keys=True)))
        for issue in row.get("issues", []):
            lines.append("  issue={0}".format(issue))
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    saved = report.get("saved_report")
    if saved:
        lines.append("")
        lines.append("report_dir: {0}".format(saved["report_dir"]))
        lines.append("latest_json: {0}".format(saved["latest_json"]))
        lines.append("history_jsonl: {0}".format(saved["history_jsonl"]))
    return "\n".join(lines)
