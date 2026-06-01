import json
from pathlib import Path

from sim_plane.run_suite import DEFAULT_SUITE_REPORT_ROOT, format_suite_report, run_suite, write_suite_report


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXAM_SUITE = REPO_ROOT / "configs" / "paper_quadrotor_exam_suite.json"


def run_quadrotor_exam(
    scenario_path=None,
    suite_path=None,
    artifact_root="runs",
    report_root=DEFAULT_SUITE_REPORT_ROOT,
    keep_last=10,
    runtime_options=None,
):
    scenario = Path(scenario_path) if scenario_path else REPO_ROOT / "scenarios" / "basic_takeoff.json"
    suite = Path(suite_path) if suite_path else DEFAULT_EXAM_SUITE
    report = run_suite(
        scenario_path=scenario,
        suite_path=suite,
        artifact_root=artifact_root,
        report_root=None,
        keep_last=keep_last,
        runtime_options=runtime_options or {},
    )
    report["exam"] = build_exam_summary(report)
    if report_root is not None:
        report["saved_report"] = write_suite_report(
            report,
            report_root=report_root,
            keep_last=keep_last,
        )
    return report


def build_exam_summary(report):
    rows = report.get("rows", [])
    total = len(rows)
    passed = sum(1 for row in rows if row.get("status") == "passed")
    metric_names = [
        "kpi_target_reach_time_s",
        "kpi_distance_m",
        "kpi_max_speed_mps",
        "kpi_max_acceleration_mps2",
        "kpi_speed_roughness_mps",
        "kpi_safety_violation_count",
        "kpi_final_goal_distance_m",
        "kpi_sensor_recovery_time_s",
        "kpi_measurement_horizontal_error_max_m",
    ]
    metrics = {}
    for metric_name in metric_names:
        values = [
            row.get("metrics", {}).get(metric_name)
            for row in rows
            if isinstance(row.get("metrics", {}).get(metric_name), (int, float))
            and not isinstance(row.get("metrics", {}).get(metric_name), bool)
        ]
        if not values:
            continue
        metrics[metric_name] = {
            "mean": round(sum(values) / len(values), 6),
            "max": max(values),
            "min": min(values),
        }
    return {
        "scene_count": total,
        "passed_scene_count": passed,
        "success_rate": round(passed / total, 6) if total else 0.0,
        "metrics": metrics,
        "notes": [
            "This is a standard algorithm-validation exam surface, not a high-fidelity visual simulator.",
            "Use it for paper/project repeatability: fixed scenes, fixed KPI names, and retained artifacts.",
        ],
    }


def format_quadrotor_exam_report(report):
    lines = [format_suite_report(report)]
    exam = report.get("exam") or {}
    if exam:
        lines.extend(
            [
                "",
                "paper_exam_summary={0}".format(json.dumps(exam, ensure_ascii=False, sort_keys=True)),
            ]
        )
    return "\n".join(lines)
