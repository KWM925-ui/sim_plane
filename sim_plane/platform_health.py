import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

from sim_plane.io_utils import atomic_write_json, atomic_write_text, append_jsonl, prune_directories, report_write_lock
from sim_plane.paths import get_platform_paths, resolve_platform_path

from sim_plane.artifact_hygiene import apply_artifact_hygiene, apply_manual_probe_hygiene
from sim_plane.artifacts import safe_artifact_name, utc_timestamp
from sim_plane.doctor import collect_platform_doctor_report
from sim_plane.planner_acceptance import validate_acceptance_matrix
from sim_plane.platform_acceptance import validate_platform_matrix
from sim_plane.px4_failure_acceptance import validate_matrix as validate_px4_failure_matrix
from sim_plane.quadrotor_exam_acceptance import validate_matrix as validate_quadrotor_exam_matrix
from sim_plane.web import list_complete_artifacts, list_suite_reports, list_test_surface_reports


REPO_ROOT = get_platform_paths().home
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "platform_health"
DEFAULT_KEEP_LAST = 10
DEFAULT_HEALTH_NAME = "sim_plane_platform_health"
SUCCESS_STATUSES = {"passed", "clean"}
NON_BLOCKING_STATUSES = SUCCESS_STATUSES | {"warning"}


def collect_platform_health(artifact_root="runs", repo_root=None):
    artifact_root_path = resolve_platform_path(artifact_root)
    repo_root_path = Path(repo_root) if repo_root is not None else REPO_ROOT
    components = []

    components.append(
        build_component(
            name="git",
            command="git status --short",
            payload=collect_git_report(repo_root_path),
        )
    )
    components.append(
        collect_component(
            name="doctor",
            command="python3 -m sim_plane doctor --json",
            fn=collect_platform_doctor_report,
            status_fn=status_from_doctor_report,
        )
    )
    components.append(
        collect_component(
            name="artifact_hygiene",
            command="python3 -m sim_plane artifact-hygiene --artifact-root {0} --json".format(
                artifact_root
            ),
            fn=lambda: apply_artifact_hygiene(artifact_root=artifact_root_path),
        )
    )
    components.append(
        collect_component(
            name="manual_probe_hygiene",
            command="python3 -m sim_plane manual-probe-hygiene --artifact-root {0} --json".format(
                artifact_root
            ),
            fn=lambda: apply_manual_probe_hygiene(artifact_root=artifact_root_path),
        )
    )
    components.extend(
        [
            collect_component(
                name="platform_acceptance_latest",
                command="python3 -m sim_plane platform-acceptance --latest --artifact-root {0} --json".format(
                    artifact_root
                ),
                fn=lambda: validate_platform_matrix(artifact_root=artifact_root_path, use_latest=True),
            ),
            collect_component(
                name="planner_acceptance_latest",
                command="python3 -m sim_plane planner-acceptance --latest --artifact-root {0} --json".format(
                    artifact_root
                ),
                fn=lambda: validate_acceptance_matrix(artifact_root=artifact_root_path, use_latest=True),
            ),
            collect_component(
                name="px4_failure_acceptance_latest",
                command="python3 -m sim_plane px4-failure-acceptance --latest --artifact-root {0} --json".format(
                    artifact_root
                ),
                fn=lambda: validate_px4_failure_matrix(artifact_root=artifact_root_path, use_latest=True),
            ),
            collect_component(
                name="quadrotor_exam_acceptance_latest",
                command="python3 -m sim_plane quadrotor-exam-acceptance --latest --artifact-root {0} --json".format(
                    artifact_root
                ),
                fn=lambda: validate_quadrotor_exam_matrix(artifact_root=artifact_root_path, use_latest=True),
            ),
        ]
    )

    latest_evidence = collect_latest_evidence(artifact_root_path)
    boundaries = build_objective_boundaries()
    summary = build_health_summary(components, latest_evidence)
    blockers = build_component_messages(components, accepted_statuses=NON_BLOCKING_STATUSES)
    warnings = build_component_messages(components, accepted_statuses=SUCCESS_STATUSES | {"failed"})
    status = "failed" if blockers else ("warning" if warnings else "passed")
    return {
        "health_name": DEFAULT_HEALTH_NAME,
        "generated_at_utc": utc_timestamp(),
        "repo_root": str(repo_root_path),
        "artifact_root": str(artifact_root_path),
        "status": status,
        "summary": summary,
        "issues": blockers,
        "warnings": warnings,
        "components": components,
        "latest_evidence": latest_evidence,
        "objective_boundaries": boundaries,
    }


def collect_component(name, command, fn, status_fn=None):
    try:
        payload = fn()
    except Exception as exc:
        return {
            "name": name,
            "command": command,
            "status": "failed",
            "issues": ["component raised exception: {0}".format(exc)],
            "summary": {},
        }
    return build_component(
        name=name,
        command=command,
        payload=payload,
        status_fn=status_fn,
    )


def build_component(name, command, payload, status_fn=None):
    status = status_fn(payload) if status_fn else normalize_status(payload.get("status"))
    issues = list(payload.get("issues", [])) if isinstance(payload, dict) else []
    if status == "failed" and not issues:
        issues.append("component status is failed")
    return {
        "name": name,
        "command": command,
        "status": status,
        "issues": issues,
        "summary": summarize_component_payload(payload),
    }


def normalize_status(status):
    if status in SUCCESS_STATUSES:
        return "passed"
    if status == "warning":
        return "warning"
    return "failed"


def status_from_doctor_report(report):
    summary = report.get("summary", {})
    return "passed" if summary.get("ready_backend_count", 0) >= 1 else "failed"


def collect_git_report(repo_root):
    root = Path(repo_root)
    inside = run_git(root, "rev-parse", "--is-inside-work-tree")
    if inside["returncode"] != 0 or inside["stdout"].strip() != "true":
        return {
            "status": "failed",
            "issues": ["workspace is not a git repository"],
            "summary": {
                "repo_root": str(root),
                "inside_work_tree": False,
            },
        }
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = run_git(root, "rev-parse", "--short", "HEAD")
    status = run_git(root, "status", "--short")
    entries = [line for line in status["stdout"].splitlines() if line.strip()]
    return {
        "status": "warning" if entries else "passed",
        "issues": [] if status["returncode"] == 0 else ["git status failed"],
        "summary": {
            "repo_root": str(root),
            "inside_work_tree": True,
            "branch": branch["stdout"].strip() if branch["returncode"] == 0 else None,
            "commit": commit["stdout"].strip() if commit["returncode"] == 0 else None,
            "dirty": bool(entries),
            "dirty_count": len(entries),
            "dirty_entries": entries[:40],
        },
    }


def run_git(repo_root, *args):
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"returncode": 1, "stdout": "", "stderr": str(exc)}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def summarize_component_payload(payload):
    if not isinstance(payload, dict):
        return {}
    if "health_name" in payload:
        return {
            "status": payload.get("status"),
            "component_count": len(payload.get("components", [])),
        }
    if payload.get("manual_probe_root_name"):
        return summarize_hygiene_payload(payload)
    if "summary" in payload and "backends" in payload and "adapters" in payload:
        return summarize_doctor_payload(payload)
    if "matrix_name" in payload:
        return summarize_acceptance_payload(payload)
    if "summary" in payload and "repo_root" in payload["summary"]:
        return payload["summary"]
    return {
        key: payload[key]
        for key in ("status", "profile", "selection_mode", "artifact_root")
        if key in payload
    }


def summarize_doctor_payload(report):
    summary = dict(report.get("summary", {}))
    summary["scaffolded_backends"] = [
        row["name"]
        for row in report.get("backends", [])
        if row.get("status") != "ready"
    ][:8]
    summary["scaffolded_adapters"] = [
        row["name"]
        for row in report.get("adapters", [])
        if row.get("status") != "ready"
    ][:8]
    return summary


def summarize_hygiene_payload(report):
    before = report.get("before", {}).get("summary", {})
    after = report.get("after", {}).get("summary", {})
    summary = {
        "artifact_root": report.get("artifact_root"),
        "before_attention_count": before.get("attention_count"),
        "after_attention_count": after.get("attention_count"),
        "complete_artifact_count": after.get("complete_artifact_count"),
        "reserved_root_count": after.get("reserved_root_count"),
        "retained_manual_probe_count": after.get("retained_manual_probe_count"),
        "stale_manual_probe_count": after.get("stale_manual_probe_count"),
        "pruned_count": len(report.get("actions", {}).get("pruned", [])),
        "migrated_count": len(report.get("actions", {}).get("migrated", [])),
    }
    remaining_attention = [
        {
            "name": entry.get("name"),
            "category": entry.get("category"),
            "reason": entry.get("reason"),
        }
        for entry in report.get("after", {}).get("entries", [])
        if not entry.get("clean")
    ]
    if remaining_attention:
        summary["remaining_attention"] = remaining_attention[:8]
    return summary


def summarize_acceptance_payload(report):
    rows = report.get("rows", []) if isinstance(report.get("rows"), list) else []
    passed_rows = [row for row in rows if row.get("status") == "passed"]
    failed_rows = [row for row in rows if row.get("status") != "passed"]
    summary = {
        "matrix_name": report.get("matrix_name"),
        "selection_mode": report.get("selection_mode"),
        "matrix_path": report.get("matrix_path"),
        "artifact_root": report.get("artifact_root"),
        "report_path": report.get("report_path"),
        "row_count": len(rows),
        "passed_row_count": len(passed_rows),
        "failed_row_count": len(failed_rows),
        "failed_rows": [row.get("name") or row.get("backend") for row in failed_rows[:8]],
    }
    if report.get("summary"):
        summary["report_summary"] = report.get("summary")
    planner = report.get("planner_acceptance")
    if isinstance(planner, dict):
        summary["nested_planner_acceptance_status"] = planner.get("status")
    return summary


def collect_latest_evidence(artifact_root):
    return {
        "latest_complete_artifacts": compact_artifact_rows(
            list_complete_artifacts(artifact_root, limit=10)
        ),
        "latest_suite_reports": compact_suite_reports(
            list_suite_reports(artifact_root, limit=10)
        ),
        "latest_test_surface_reports": compact_test_surface_reports(
            list_test_surface_reports(artifact_root, limit=12)
        ),
    }


def compact_artifact_rows(rows):
    compact_rows = []
    metric_keys = (
        "telemetry_count",
        "duration_s",
        "max_altitude_m",
        "max_speed_mps",
        "target_altitude_reached",
        "goal_reached",
        "min_goal_distance_m",
        "kpi_safety_violation_count",
        "kpi_final_goal_distance_m",
    )
    for row in rows:
        metrics = row.get("metrics", {}) if isinstance(row.get("metrics"), dict) else {}
        compact_rows.append(
            {
                "name": row.get("name"),
                "path": row.get("path"),
                "created_at_utc": row.get("created_at_utc"),
                "scenario_name": row.get("scenario_name"),
                "backend": row.get("backend"),
                "vehicle": row.get("vehicle"),
                "status": row.get("status"),
                "telemetry_count": row.get("telemetry_count"),
                "event_count": row.get("event_count"),
                "key_metrics": {
                    key: metrics.get(key)
                    for key in metric_keys
                    if key in metrics
                },
            }
        )
    return compact_rows


def compact_suite_reports(report):
    compact = dict(report)
    compact["items"] = [
        {
            "suite_name": item.get("suite_name"),
            "status": item.get("status"),
            "row_count": item.get("row_count"),
            "passed_row_count": item.get("passed_row_count"),
            "failed_row_count": item.get("failed_row_count"),
            "latest_json": item.get("latest_json"),
            "report_json": item.get("report_json"),
            "latest_artifact_created_at_utc": item.get("latest_artifact_created_at_utc"),
            "top_metric_effects": list(item.get("top_metric_effects", []))[:4],
            "kpi_rankings": list(item.get("kpi_rankings", []))[:4],
            "issues": list(item.get("issues", []))[:4],
        }
        for item in report.get("items", [])
    ]
    return compact


def compact_test_surface_reports(report):
    compact = dict(report)
    compact["items"] = [
        {
            "surface": item.get("surface"),
            "name": item.get("name"),
            "status": item.get("status"),
            "latest_json": item.get("latest_json"),
            "report_json": item.get("report_json"),
            "profile": item.get("profile"),
            "seed": item.get("seed"),
            "row_count": item.get("row_count"),
            "passed_row_count": item.get("passed_row_count"),
            "step_count": item.get("step_count"),
            "passed_step_count": item.get("passed_step_count"),
            "key_metrics": item.get("key_metrics", {}),
            "worst_cases": list(item.get("worst_cases", []))[:3],
            "issues": list(item.get("issues", []))[:4],
        }
        for item in report.get("items", [])
    ]
    return compact


def build_health_summary(components, latest_evidence):
    counts = Counter(component["status"] for component in components)
    suite_items = latest_evidence.get("latest_suite_reports", {}).get("items", [])
    test_surface_items = latest_evidence.get("latest_test_surface_reports", {}).get("items", [])
    artifacts = latest_evidence.get("latest_complete_artifacts", [])
    return {
        "component_count": len(components),
        "passed_component_count": counts.get("passed", 0),
        "warning_component_count": counts.get("warning", 0),
        "failed_component_count": counts.get("failed", 0),
        "latest_complete_artifact_count_sampled": len(artifacts),
        "latest_suite_report_count_sampled": len(suite_items),
        "latest_test_surface_report_count_sampled": len(test_surface_items),
        "surface_status": {
            item.get("surface") or item.get("suite_name") or item.get("name"): item.get("status")
            for item in test_surface_items
        },
    }


def build_component_messages(components, accepted_statuses):
    messages = []
    for component in components:
        if component["status"] in accepted_statuses:
            continue
        issues = component.get("issues") or []
        if issues:
            messages.extend("{0}: {1}".format(component["name"], issue) for issue in issues)
        else:
            messages.append("{0}: status={1}".format(component["name"], component["status"]))
    return messages


def build_objective_boundaries():
    return [
        {
            "name": "positioning",
            "status": "locked",
            "detail": "sim_plane is an algorithm-validation and experiment-management platform, not a high-fidelity visual-realism simulator.",
        },
        {
            "name": "px4_native_failure_scope",
            "status": "open_boundary",
            "detail": "PX4-native failure acceptance currently proves the SYSTEM_MOTOR/OFF/OK path only.",
        },
        {
            "name": "sensor_fault_scope",
            "status": "locked",
            "detail": "demo sensor_stream_faults and scenario fuzz are data-stream degradation tests, not PX4-native physical failure injection.",
        },
        {
            "name": "flight_log_collection",
            "status": "implemented_with_runtime_dependency",
            "detail": "PX4-family backends attempt artifact-local .ulg collection by default; px4_ulog/index.json records collected, missing, disabled, or failed status without changing the simulation verdict.",
        },
        {
            "name": "legacy_runtime_stack",
            "status": "known_debt",
            "detail": "ROS1 Noetic and Gazebo Classic remain supported for current Ubuntu 20.04 workflows, but they are not the long-term migration endpoint.",
        },
    ]


def format_platform_health_report(report):
    lines = [
        "platform health: {0}".format(report.get("status")),
        "generated_at_utc: {0}".format(report.get("generated_at_utc")),
        "repo_root: {0}".format(report.get("repo_root")),
        "artifact_root: {0}".format(report.get("artifact_root")),
        "components: passed={0} warning={1} failed={2}".format(
            report.get("summary", {}).get("passed_component_count"),
            report.get("summary", {}).get("warning_component_count"),
            report.get("summary", {}).get("failed_component_count"),
        ),
        "",
        "{0:<38} {1:<8} {2}".format("component", "status", "command"),
        "-" * 110,
    ]
    for component in report.get("components", []):
        lines.append(
            "{0:<38} {1:<8} {2}".format(
                component["name"],
                component["status"],
                component["command"],
            )
        )
        for issue in component.get("issues", []):
            lines.append("  issue: {0}".format(issue))
    if report.get("warnings"):
        lines.append("")
        lines.append("warnings:")
        for warning in report["warnings"]:
            lines.append("- {0}".format(warning))
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    lines.append("")
    lines.append("objective boundaries:")
    for item in report.get("objective_boundaries", []):
        lines.append("- {0}: {1} | {2}".format(item["name"], item["status"], item["detail"]))
    saved = report.get("saved_report")
    if saved:
        lines.append("")
        lines.append("report_json: {0}".format(saved.get("report_json")))
        lines.append("latest_json: {0}".format(saved.get("latest_json")))
    return "\n".join(lines)


def write_platform_health_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = resolve_platform_path(report_root) if report_root is not None else DEFAULT_REPORT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with report_write_lock(root):
        return _write_platform_health_report_locked(report, root, keep_last)


def _write_platform_health_report_locked(report, root, keep_last):
    root = root if hasattr(root, "joinpath") else resolve_platform_path(root)
    root.mkdir(parents=True, exist_ok=True)
    health_name = safe_artifact_name(report.get("health_name", DEFAULT_HEALTH_NAME))
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    report_dir = root / "{0}_{1}".format(health_name, stamp)
    report_dir.mkdir(parents=True, exist_ok=False)
    payload = dict(report)
    payload["report_dir"] = str(report_dir)
    payload["written_at_utc"] = utc_timestamp()
    report_json = report_dir / "report.json"
    report_txt = report_dir / "report.txt"
    manifest = report_dir / "manifest.json"
    latest_json = root / "latest.json"
    latest_txt = root / "latest.txt"
    history_jsonl = root / "history.jsonl"
    text = format_platform_health_report(payload) + "\n"
    atomic_write_json(report_json, payload)
    atomic_write_text(report_txt, text)
    atomic_write_json(latest_json, payload)
    atomic_write_text(latest_txt, text)
    atomic_write_json(
        manifest,
        {
            "created_at_utc": payload["written_at_utc"],
            "health_name": payload.get("health_name", DEFAULT_HEALTH_NAME),
            "status": payload.get("status"),
            "report_dir": str(report_dir),
            "files": {
                "report_json": "report.json",
                "report_text": "report.txt",
            },
            "latest_files": {
                "report_json": str(latest_json),
                "report_text": str(latest_txt),
            },
            "history_file": str(history_jsonl),
            "keep_last": keep_last,
        },
    )
    append_jsonl(
        history_jsonl,
        {
            "written_at_utc": payload["written_at_utc"],
            "health_name": payload.get("health_name", DEFAULT_HEALTH_NAME),
            "status": payload.get("status"),
            "failed_component_count": payload.get("summary", {}).get("failed_component_count"),
            "warning_component_count": payload.get("summary", {}).get("warning_component_count"),
            "report_json": str(report_json),
        },
    )
    pruned_report_dirs = prune_platform_health_reports(root, health_name, keep_last)
    return {
        "report_root": str(root),
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "report_text": str(report_txt),
        "latest_json": str(latest_json),
        "latest_text": str(latest_txt),
        "history_jsonl": str(history_jsonl),
        "pruned_report_dirs": pruned_report_dirs,
    }


def prune_platform_health_reports(report_root, health_name, keep_last):
    return prune_directories(
        report_root,
        "{0}_*".format(health_name),
        keep_last,
    )
