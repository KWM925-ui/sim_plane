import copy
import json
import random
from datetime import datetime
from pathlib import Path

from sim_plane.run_suite import run_suite, sanitize_variant_name
from sim_plane.scenario import load_scenario


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "scenario_fuzz"
DEFAULT_KEEP_LAST = 10
DEFAULT_SEED = 20260528
DEFAULT_PROFILE = "demo_fast"


def run_scenario_fuzz(
    scenario_path,
    profile=DEFAULT_PROFILE,
    seed=DEFAULT_SEED,
    variants=6,
    artifact_root="runs",
    report_root=None,
    keep_last=DEFAULT_KEEP_LAST,
    runtime_options=None,
):
    base_scenario = load_scenario(scenario_path)
    suite = build_fuzz_suite(base_scenario, profile=profile, seed=seed, variants=variants)
    suite_report = run_suite(
        scenario_path=scenario_path,
        suite_definition=suite,
        artifact_root=artifact_root,
        report_root=None,
        runtime_options=runtime_options or {},
    )
    report = {
        "fuzz_name": suite["name"],
        "profile": profile,
        "seed": int(seed),
        "base_scenario": str(scenario_path),
        "artifact_root": str(Path(artifact_root)),
        "status": suite_report["status"],
        "issues": list(suite_report.get("issues", [])),
        "generated_suite": suite,
        "rows": suite_report.get("rows", []),
        "metric_summary": suite_report.get("metric_summary", {}),
        "factor_analysis": suite_report.get("factor_analysis", {}),
        "top_metric_effects": suite_report.get("top_metric_effects", []),
        "kpi_rankings": suite_report.get("kpi_rankings", {}),
        "worst_cases": summarize_worst_cases(suite_report),
        "notes": [
            "scenario-fuzz uses deterministic seed-based variant generation.",
            "The demo_fast profile exercises demo disturbances/degradations and must not be treated as PX4-native physical failure injection.",
        ],
    }
    if report_root is not None:
        report["saved_report"] = write_fuzz_report(
            report,
            report_root=report_root,
            keep_last=keep_last,
        )
    return report


def build_fuzz_suite(base_scenario, profile=DEFAULT_PROFILE, seed=DEFAULT_SEED, variants=6):
    if profile != "demo_fast":
        raise ValueError("unsupported scenario-fuzz profile: {0}".format(profile))
    if base_scenario.get("backend") != "demo":
        raise ValueError("profile demo_fast currently supports only the built-in demo backend")
    count = max(int(variants), 1)
    random_source = random.Random(int(seed))
    base_duration = float(base_scenario.get("duration_s", 14.0))
    base_target_altitude = float(base_scenario.get("target_altitude_m", 10.0))
    suite = {
        "name": "demo_seeded_fuzz_{0}".format(int(seed)),
        "description": "Seeded fuzz/sweep suite for demo disturbances, degradations, limits, and initial conditions.",
        "base_overrides": {
            "duration_s": min(max(base_duration, 10.0), 16.0),
            "realtime_factor": 0.0,
        },
        "variants": [
            {
                "name": "baseline",
                "overrides": {},
                "required_metrics": {"target_altitude_reached": True},
            }
        ],
    }
    for index in range(count):
        target_altitude = round(random_source.uniform(max(3.0, base_target_altitude * 0.45), max(4.0, base_target_altitude * 0.95)), 2)
        wind_x = round(random_source.uniform(-0.45, 0.45), 2)
        wind_y = round(random_source.uniform(-0.45, 0.45), 2)
        offset_x = round(random_source.uniform(-1.8, 1.8), 2)
        offset_y = round(random_source.uniform(-1.8, 1.8), 2)
        noise_xy = round(random_source.uniform(0.0, 0.16), 3)
        noise_z = round(random_source.uniform(0.0, 0.08), 3)
        dropout_start = round(random_source.uniform(5.4, 7.4), 2)
        dropout_len = round(random_source.uniform(0.25, 0.95), 2)
        comm_start = round(random_source.uniform(6.0, 8.0), 2)
        comm_len = round(random_source.uniform(0.15, 0.55), 2)
        speed_limit = round(random_source.uniform(3.2, 6.0), 2)
        include_dropout = index % 2 == 0
        include_comm = index % 3 == 1
        overrides = {
            "target_altitude_m": target_altitude,
            "control_limits": {"max_speed_mps": speed_limit},
            "disturbances": {
                "seed": int(seed) + index + 1,
                "wind": {"x_mps": wind_x, "y_mps": wind_y},
                "initial_offset": {"x_m": offset_x, "y_m": offset_y, "z_m": 0.0},
            },
            "degradations": {
                "seed": int(seed) + 100 + index,
                "sensor_noise": {
                    "position_std_m": noise_xy,
                    "altitude_std_m": noise_z,
                },
                "control_saturation": {"max_speed_mps": speed_limit},
            },
        }
        if include_dropout:
            overrides["degradations"]["sensor_dropout"] = {
                "windows": [{"start_s": dropout_start, "end_s": round(dropout_start + dropout_len, 2)}]
            }
        if include_comm:
            overrides["degradations"]["communication_interruption"] = {
                "windows": [{"start_s": comm_start, "end_s": round(comm_start + comm_len, 2)}]
            }
        suite["variants"].append(
            {
                "name": "seed_{0:02d}".format(index + 1),
                "overrides": overrides,
                "factors": [
                    {"name": "target_altitude", "path": "target_altitude_m", "value": target_altitude},
                    {"name": "wind_x", "path": "disturbances.wind.x_mps", "value": wind_x},
                    {"name": "wind_y", "path": "disturbances.wind.y_mps", "value": wind_y},
                    {"name": "initial_offset_x", "path": "disturbances.initial_offset.x_m", "value": offset_x},
                    {"name": "initial_offset_y", "path": "disturbances.initial_offset.y_m", "value": offset_y},
                    {"name": "sensor_noise_xy", "path": "degradations.sensor_noise.position_std_m", "value": noise_xy},
                    {"name": "speed_limit", "path": "control_limits.max_speed_mps", "value": speed_limit},
                ],
                "required_metrics": {"target_altitude_reached": True},
            }
        )
    return suite


def summarize_worst_cases(suite_report, limit=8):
    preferred_metrics = [
        "kpi_safety_violation_count",
        "kpi_speed_limit_violation_count",
        "kpi_measurement_horizontal_error_max_m",
        "kpi_measurement_vertical_error_max_m",
        "kpi_sensor_dropout_ratio",
        "kpi_max_acceleration_mps2",
        "kpi_speed_roughness_mps",
        "kpi_altitude_max_error_m",
        "kpi_mission_path_error_max_m",
    ]
    rankings = suite_report.get("kpi_rankings", {})
    rows = []
    for metric in preferred_metrics:
        ranking = rankings.get(metric)
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
            break
    return rows


def write_fuzz_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = Path(report_root) if report_root is not None else DEFAULT_REPORT_ROOT
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fuzz_name = sanitize_variant_name(report.get("fuzz_name", "scenario_fuzz"))
    report_dir = root / "{0}_{1}".format(fuzz_name, stamp)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "report.json"
    report_txt = report_dir / "report.txt"
    suite_json = report_dir / "generated_suite.json"
    latest_json = root / "latest_{0}.json".format(fuzz_name)
    latest_txt = root / "latest_{0}.txt".format(fuzz_name)
    history_jsonl = root / "history_{0}.jsonl".format(fuzz_name)
    serializable = copy.deepcopy(report)
    serializable.pop("saved_report", None)
    report_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_txt.write_text(format_fuzz_report(serializable) + "\n", encoding="utf-8")
    suite_json.write_text(json.dumps(serializable["generated_suite"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_txt.write_text(format_fuzz_report(serializable) + "\n", encoding="utf-8")
    with history_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "created_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fuzz_name": report.get("fuzz_name"),
                    "profile": report.get("profile"),
                    "seed": report.get("seed"),
                    "status": report.get("status"),
                    "report_json": str(report_json),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    if keep_last and keep_last > 0:
        prune_fuzz_reports(root, fuzz_name, keep_last)
    return {
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "report_text": str(report_txt),
        "generated_suite_json": str(suite_json),
        "latest_json": str(latest_json),
        "latest_text": str(latest_txt),
        "history_jsonl": str(history_jsonl),
    }


def prune_fuzz_reports(report_root, fuzz_name, keep_last):
    report_dirs = sorted(
        [path for path in Path(report_root).glob("{0}_*".format(fuzz_name)) if path.is_dir()],
        key=lambda path: path.name,
    )
    for path in report_dirs[:-keep_last]:
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()


def format_fuzz_report(report):
    lines = [
        "scenario fuzz: {0}".format(report.get("status")),
        "profile: {0}".format(report.get("profile")),
        "seed: {0}".format(report.get("seed")),
        "base_scenario: {0}".format(report.get("base_scenario")),
        "rows: {0}".format(len(report.get("rows", []))),
    ]
    if report.get("worst_cases"):
        lines.append("")
        lines.append("worst cases:")
        for case in report["worst_cases"]:
            worst = (case.get("worst") or [{}])[0]
            lines.append(
                "- {0}: {1}={2} spread={3}".format(
                    case.get("metric"),
                    worst.get("name"),
                    worst.get("value"),
                    case.get("spread"),
                )
            )
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    saved = report.get("saved_report")
    if saved:
        lines.append("")
        lines.append("report_json: {0}".format(saved.get("report_json")))
        lines.append("generated_suite_json: {0}".format(saved.get("generated_suite_json")))
    return "\n".join(lines)
