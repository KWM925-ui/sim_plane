import json
from collections import OrderedDict

from sim_plane.adapters import available_adapters


DEFAULT_CONTROL_SCENARIO = "scenarios/px4_sih_quadx_external_command_template.json"
DEFAULT_ROS_SCENARIO = "scenarios/marsim_ros_command_template.json"
DEFAULT_ESTIMATION_ROS_SCENARIO = "scenarios/fast_lio_marsim_ros_command_template.json"
DEFAULT_VISUAL_SCENARIO = "scenarios/px4_sih_quadx_3d.json"
DEFAULT_PLATFORM_ACCEPTANCE_COMMAND = "python3 -m sim_plane platform-acceptance --latest --artifact-root runs"
DEFAULT_ARTIFACT_HYGIENE_COMMAND = (
    "python3 -m sim_plane artifact-hygiene --artifact-root runs "
    "--migrate-retained-manual --prune-safe"
)


def collect_platform_doctor_report():
    backend_rows = collect_backend_rows()
    adapter_rows = collect_adapter_rows()
    recommendations = build_recommendations(backend_rows, adapter_rows)
    summary = build_summary(backend_rows, adapter_rows, recommendations)
    return {
        "summary": summary,
        "backends": backend_rows,
        "adapters": adapter_rows,
        "recommendations": recommendations,
    }


def collect_backend_rows():
    # Keep adapter-only inventory usable even when an optional backend import is unavailable.
    from sim_plane.backends import available_backends

    rows = []
    for name, backend_cls in sorted(available_backends().items()):
        backend = backend_cls()
        issues = list(backend.validate_environment())
        rows.append(
            {
                "name": name,
                "status": "ready" if not issues else "scaffolded",
                "issues": issues,
            }
        )
    return rows


def collect_adapter_rows():
    rows = []
    for name, adapter_cls in sorted(available_adapters().items()):
        adapter = adapter_cls()
        issues = list(adapter.validate_environment())
        issue_report = classify_adapter_issues(name, issues)
        doctor_ready = not issue_report["blocking_issues"]
        rows.append(
            {
                "name": name,
                "status": "ready" if doctor_ready else "scaffolded",
                "issues": issues,
                "blocking_issues": issue_report["blocking_issues"],
                "notes": issue_report["notes"],
                "doctor_ready": doctor_ready,
            }
        )
    return rows


def build_summary(backend_rows, adapter_rows, recommendations):
    ready_backends = [row["name"] for row in backend_rows if row["status"] == "ready"]
    ready_adapters = [row["name"] for row in adapter_rows if row["status"] == "ready"]
    return {
        "ready_backend_count": len(ready_backends),
        "ready_adapter_count": len(ready_adapters),
        "recommended_default_backend": recommendations["default_backend"]["backend"] if recommendations["default_backend"] else None,
        "recommended_control_path": recommendations["control_algorithm_path"]["label"] if recommendations["control_algorithm_path"] else None,
        "recommended_ros_path": recommendations["ros_algorithm_path"]["label"] if recommendations["ros_algorithm_path"] else None,
    }


def build_recommendations(backend_rows, adapter_rows):
    backend_map = {row["name"]: row for row in backend_rows}
    adapter_map = {row["name"]: row for row in adapter_rows}

    default_backend = None
    for backend_name in ("px4_sih", "marsim", "demo"):
        row = backend_map.get(backend_name)
        if row and row["status"] == "ready":
            default_backend = {
                "backend": backend_name,
                "why": default_backend_reason(backend_name),
            }
            break

    control_path = None
    if is_ready(backend_map, "px4_sih") and is_ready(adapter_map, "external_command"):
        control_path = {
            "label": "px4_sih + external_command",
            "why": "The light PX4 path and the generic host-process adapter are both ready on this machine.",
            "command": "python3 -m sim_plane run {0} --visualize --no-hold-open".format(DEFAULT_CONTROL_SCENARIO),
        }
    elif is_ready(backend_map, "px4_sih"):
        control_path = {
            "label": "px4_sih only",
            "why": "The light PX4 backend is ready, but the generic external adapter still has blocking issues.",
            "command": "python3 -m sim_plane run scenarios/px4_sih_quadx_headless.json --no-hold-open",
        }
    elif is_ready(backend_map, "demo"):
        control_path = {
            "label": "demo fallback",
            "why": "PX4 is not ready yet on this machine, so the built-in demo remains the fastest closed-loop smoke path.",
            "command": "python3 -m sim_plane run scenarios/basic_takeoff.json --visualize --no-hold-open",
        }

    ros_path = None
    if is_ready(backend_map, "marsim") and is_ready(adapter_map, "ros_command"):
        ros_path = {
            "label": "marsim + ros_command",
            "why": "The scene-backed ROS path and the generic ROS adapter are both ready.",
            "command": "python3 -m sim_plane run {0} --rviz --visualize --no-hold-open".format(DEFAULT_ROS_SCENARIO),
        }
    elif is_ready(backend_map, "fast_lio_marsim") and is_ready(adapter_map, "ros_command"):
        ros_path = {
            "label": "fast_lio_marsim + ros_command",
            "why": "The estimator-coupled ROS path is ready and can drive user planner/perception nodes directly.",
            "command": "python3 -m sim_plane run {0} --rviz --visualize --no-hold-open".format(DEFAULT_ESTIMATION_ROS_SCENARIO),
        }
    elif is_ready(adapter_map, "ros_command"):
        ros_path = {
            "label": "ros_command not yet paired",
            "why": "The generic ROS adapter is present, but the recommended scene backend is not fully ready.",
            "command": None,
        }

    visual_path = None
    if is_ready(backend_map, "px4_sih"):
        visual_path = {
            "label": "px4_sih 3d viewer",
            "why": "This is the lightest retained viewer-backed PX4 path on the current machine.",
            "command": "python3 -m sim_plane run {0} --visualize --qgc --jmavsim --no-hold-open".format(DEFAULT_VISUAL_SCENARIO),
        }

    return OrderedDict(
        [
            ("default_backend", default_backend),
            ("control_algorithm_path", control_path),
            ("ros_algorithm_path", ros_path),
            ("visual_demo_path", visual_path),
            (
                "platform_validation_path",
                {
                    "label": "latest platform acceptance",
                    "why": "This checks the current latest artifacts against the frozen platform baseline without changing acceptance semantics.",
                    "command": DEFAULT_PLATFORM_ACCEPTANCE_COMMAND,
                },
            ),
            (
                "artifact_hygiene_path",
                {
                    "label": "artifact hygiene",
                    "why": "This keeps retained evidence and stale probe directories separated before trusting the artifact root.",
                    "command": DEFAULT_ARTIFACT_HYGIENE_COMMAND,
                },
            ),
        ]
    )


def default_backend_reason(name):
    if name == "px4_sih":
        return "PX4 SIH is the light default closed-loop flight path for this platform."
    if name == "marsim":
        return "MARSIM is the first richer 3D ROS path when sensor-side work is needed."
    return "The built-in demo backend is always the lowest-friction smoke path."


def is_ready(rows, name):
    row = rows.get(name)
    return bool(row) and row["status"] == "ready"


def classify_adapter_issues(name, issues):
    template_only_issues = {
        "external_command": {
            "The external_command adapter requires a non-empty command field.",
        },
        "ros_command": {
            "The ros_command adapter requires a non-empty command field.",
        },
    }
    allowed = template_only_issues.get(name)
    notes = []
    blocking_issues = []
    for issue in issues:
        if allowed and issue in allowed:
            notes.append(template_adapter_note(name))
        else:
            blocking_issues.append(issue)
    return {
        "blocking_issues": blocking_issues,
        "notes": sorted(set(notes)),
    }


def template_adapter_note(name):
    if name == "external_command":
        return "template adapter ready; provide the user command in a scenario to use it"
    if name == "ros_command":
        return "template adapter ready; provide the ROS command in a scenario to use it"
    return "template adapter ready; scenario-specific fields are still required"


def format_platform_doctor_report(report):
    lines = []
    summary = report["summary"]
    lines.append("sim_plane doctor")
    lines.append(
        "ready backends: {0} | ready adapters: {1}".format(
            summary["ready_backend_count"],
            summary["ready_adapter_count"],
        )
    )
    if summary["recommended_default_backend"]:
        lines.append("default backend: {0}".format(summary["recommended_default_backend"]))
    lines.append("")
    lines.append("recommendations:")
    for key, item in report["recommendations"].items():
        if not item:
            continue
        label = item.get("label") or item.get("backend") or key
        lines.append("- {0}: {1}".format(key, label))
        lines.append("  why: {0}".format(item["why"]))
        if item.get("command"):
            lines.append("  next: {0}".format(item["command"]))
    lines.append("")
    lines.append("backends:")
    for row in report["backends"]:
        lines.append(render_row(row))
    lines.append("")
    lines.append("adapters:")
    for row in report["adapters"]:
        lines.append(render_row(row))
    return "\n".join(lines)


def render_row(row):
    blocking_issues = row.get("blocking_issues", row.get("issues", []))
    if blocking_issues:
        return "- {0}: {1} | first blocking issue: {2}".format(row["name"], row["status"], blocking_issues[0])
    notes = row.get("notes") or []
    if notes:
        return "- {0}: {1} | note: {2}".format(row["name"], row["status"], notes[0])
    return "- {0}: {1}".format(row["name"], row["status"])


def report_as_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False)
