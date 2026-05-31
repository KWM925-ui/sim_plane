from pathlib import Path

from sim_plane.runner import run_scenario
from sim_plane.scenario import load_scenario
from sim_plane.scenario_generator import build_custom_algorithm_scenario, write_scenario_file


DEFAULT_INGRESS_REPORT_ROOT = Path("runs") / "algorithm_ingress"


def run_algorithm_ingress_check(
    scenario_path=None,
    adapter=None,
    command=None,
    backend=None,
    workdir=None,
    shell=False,
    duration_s=None,
    target_altitude_m=None,
    artifact_root="runs",
    report_root=DEFAULT_INGRESS_REPORT_ROOT,
    runtime_options=None,
):
    scenario, source = resolve_ingress_scenario(
        scenario_path=scenario_path,
        adapter=adapter,
        command=command,
        backend=backend,
        workdir=workdir,
        shell=shell,
        duration_s=duration_s,
        target_altitude_m=target_altitude_m,
        report_root=report_root,
    )
    temp_scenario_path = write_temp_scenario(scenario, report_root)
    outcome = run_scenario(
        str(temp_scenario_path),
        artifact_root=artifact_root,
        visualize=False,
        hold_open=False,
        runtime_options=runtime_options or {},
    )
    report = build_ingress_report(source, temp_scenario_path, outcome)
    return report


def resolve_ingress_scenario(
    scenario_path,
    adapter,
    command,
    backend,
    workdir,
    shell,
    duration_s,
    target_altitude_m,
    report_root,
):
    if scenario_path:
        return load_scenario(scenario_path), {"type": "existing_scenario", "path": str(scenario_path)}
    if not adapter or not command:
        raise ValueError("check-algorithm-ingress requires --scenario or both --adapter and --command")
    scenario, _ = build_custom_algorithm_scenario(
        adapter=adapter,
        command=command,
        backend=backend,
        workdir=workdir,
        shell=shell,
        duration_s=duration_s,
        target_altitude_m=target_altitude_m,
        output=Path(report_root) / "generated_ingress_check_scenario.json",
    )
    return scenario, {"type": "generated_scenario", "adapter": adapter, "backend": scenario["backend"]}


def write_temp_scenario(scenario, report_root):
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "latest_ingress_check_scenario.json"
    return write_scenario_file(scenario, path, force=True)


def build_ingress_report(source, scenario_path, outcome):
    result = outcome.get("result", {})
    metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}
    adapter_name = metrics.get("algorithm_adapter_name") or (result.get("algorithm_adapter") or {}).get("type")
    checks = [
        build_check("run_completed", result.get("status") == "passed", "scenario status is {0}".format(result.get("status"))),
        build_check("adapter_present", bool(adapter_name), "algorithm adapter is {0}".format(adapter_name or "missing")),
        build_check(
            "adapter_success",
            metrics.get("algorithm_adapter_completed_successfully") is True,
            "algorithm_adapter_completed_successfully={0}".format(
                metrics.get("algorithm_adapter_completed_successfully")
            ),
        ),
        build_check("telemetry_present", numeric_metric(metrics, "telemetry_count") > 0, "telemetry_count={0}".format(metrics.get("telemetry_count"))),
        build_check(
            "control_or_command_observed",
            control_or_command_observed(metrics),
            summarize_control_command(metrics),
        ),
        build_check("kpi_present", any(key.startswith("kpi_") for key in metrics), "kpi metrics generated"),
    ]
    issues = [check["message"] for check in checks if check["status"] != "passed"]
    status = "passed" if not issues else "failed"
    return {
        "status": status,
        "source": source,
        "scenario_path": str(scenario_path),
        "artifact_dir": outcome.get("artifact_dir"),
        "checks": checks,
        "issues": issues,
        "key_metrics": summarize_key_metrics(metrics),
    }


def build_check(name, passed, message):
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "message": message,
    }


def numeric_metric(metrics, name):
    value = metrics.get(name)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def control_or_command_observed(metrics):
    if metrics.get("algorithm_adapter_completed_successfully") is True and metrics.get("target_altitude_reached") is True:
        return True
    if metrics.get("algorithm_adapter_target_altitude_reached") is True:
        return True
    if metrics.get("algorithm_adapter_takeoff_commanded") is True:
        return True
    if metrics.get("algorithm_adapter_land_commanded") is True:
        return True
    if metrics.get("algorithm_adapter_arm_commanded") is True:
        return True
    if metrics.get("position_cmd_seen") is True:
        return True
    if numeric_metric(metrics, "algorithm_adapter_nonzero_setpoint_count") > 0:
        return True
    if numeric_metric(metrics, "algorithm_adapter_stage2_ego_cmd_count") > 0:
        return True
    if numeric_metric(metrics, "template_reached_altitude_m") > 0:
        return True
    return False


def summarize_control_command(metrics):
    fields = [
        "algorithm_adapter_target_altitude_reached",
        "algorithm_adapter_takeoff_commanded",
        "algorithm_adapter_land_commanded",
        "algorithm_adapter_arm_commanded",
        "template_reached_altitude_m",
        "target_altitude_reached",
        "ever_armed",
        "position_cmd_seen",
        "algorithm_adapter_nonzero_setpoint_count",
        "algorithm_adapter_stage2_ego_cmd_count",
    ]
    return ", ".join("{0}={1}".format(field, metrics.get(field)) for field in fields if field in metrics) or "no known control metric"


def summarize_key_metrics(metrics):
    keys = [
        "algorithm_adapter_name",
        "algorithm_adapter_completed_successfully",
        "algorithm_adapter_ready",
        "telemetry_count",
        "target_altitude_reached",
        "position_cmd_seen",
        "algorithm_adapter_target_altitude_reached",
        "algorithm_adapter_takeoff_commanded",
        "algorithm_adapter_land_commanded",
        "algorithm_adapter_arm_commanded",
        "template_reached_altitude_m",
        "ever_armed",
        "kpi_sample_count",
        "kpi_mission_path_error_max_m",
        "kpi_sensor_dropout_ratio",
    ]
    return {key: metrics.get(key) for key in keys if key in metrics}


def format_algorithm_ingress_report(report):
    lines = [
        "algorithm ingress check: {0}".format(report["status"]),
        "scenario_path: {0}".format(report["scenario_path"]),
        "artifact_dir: {0}".format(report.get("artifact_dir") or "-"),
        "",
        "{0:<32} {1:<8} {2}".format("check", "status", "message"),
        "-" * 88,
    ]
    for check in report["checks"]:
        lines.append("{0:<32} {1:<8} {2}".format(check["name"], check["status"], check["message"]))
    if report.get("key_metrics"):
        lines.append("")
        lines.append("key_metrics={0}".format(report["key_metrics"]))
    if report.get("issues"):
        lines.append("")
        for issue in report["issues"]:
            lines.append("issue={0}".format(issue))
    return "\n".join(lines)
