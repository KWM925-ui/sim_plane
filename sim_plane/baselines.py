BASELINE_CATALOG = [
    {
        "name": "pid_position_demo",
        "family": "control",
        "status": "ready",
        "backend": "demo",
        "scenario": "scenarios/basic_takeoff.json",
        "command": "python3 -m sim_plane run scenarios/basic_takeoff.json --artifact-root runs --no-hold-open",
        "notes": [
            "Built-in demo backend position loop used as the lightest deterministic control baseline.",
            "Use it to verify KPI, suite, dashboard, and report plumbing before running PX4 or ROS.",
        ],
    },
    {
        "name": "mavsdk_takeoff_mission",
        "family": "control",
        "status": "ready",
        "backend": "px4_sih",
        "scenario": "scenarios/px4_sih_quadx_external_command_template.json",
        "command": "python3 -m sim_plane run scenarios/px4_sih_quadx_external_command_template.json --artifact-root runs --no-hold-open",
        "notes": [
            "Repo-local MAVSDK template baseline for arm, takeoff, target altitude, and landing through external_command.",
        ],
    },
    {
        "name": "ros_position_command_template",
        "family": "planner",
        "status": "ready",
        "backend": "marsim",
        "scenario": "scenarios/marsim_ros_command_template.json",
        "command": "python3 -m sim_plane run scenarios/marsim_ros_command_template.json --artifact-root runs --no-hold-open",
        "notes": [
            "Repo-local ROS planner/perception ingress baseline that subscribes odom/cloud/map and publishes PositionCommand.",
        ],
    },
    {
        "name": "ego_planner_marsim",
        "family": "planner",
        "status": "ready",
        "backend": "ego_planner_marsim",
        "scenario": "scenarios/ego_planner_marsim.json",
        "command": "python3 -m sim_plane run scenarios/ego_planner_marsim.json --artifact-root runs --no-hold-open",
        "notes": [
            "Legacy EGO-Planner on the stable MARSIM scene-backed path.",
        ],
    },
    {
        "name": "ego_planner_swarm_marsim",
        "family": "planner",
        "status": "ready",
        "backend": "ego_planner_swarm_marsim",
        "scenario": "scenarios/ego_planner_swarm_marsim.json",
        "command": "python3 -m sim_plane run scenarios/ego_planner_swarm_marsim.json --artifact-root runs --no-hold-open",
        "notes": [
            "EGO-Planner-Swarm single-drone planner on the stable MARSIM scene-backed path.",
        ],
    },
    {
        "name": "a_star_minimum_snap",
        "family": "planner",
        "status": "planned",
        "backend": "demo",
        "scenario": "",
        "command": "",
        "notes": [
            "Catalog placeholder only. It is not advertised as runnable until a repo-local implementation and tests are landed.",
        ],
    },
    {
        "name": "rrt_star_polynomial_smoothing",
        "family": "planner",
        "status": "planned",
        "backend": "demo",
        "scenario": "",
        "command": "",
        "notes": [
            "Catalog placeholder only. It is not advertised as runnable until a repo-local implementation and tests are landed.",
        ],
    },
]


def list_baselines(include_planned=False, family=None):
    rows = []
    for baseline in BASELINE_CATALOG:
        if not include_planned and baseline["status"] != "ready":
            continue
        if family and baseline["family"] != family:
            continue
        rows.append(dict(baseline))
    return rows


def get_baseline(name):
    for baseline in BASELINE_CATALOG:
        if baseline["name"] == name:
            return dict(baseline)
    raise KeyError(name)


def format_baselines(rows):
    lines = ["baseline algorithms:"]
    lines.append("{0:<34} {1:<10} {2:<8} {3}".format("name", "family", "status", "scenario"))
    lines.append("-" * 90)
    for row in rows:
        lines.append(
            "{0:<34} {1:<10} {2:<8} {3}".format(
                row["name"],
                row["family"],
                row["status"],
                row.get("scenario") or "-",
            )
        )
        if row.get("command"):
            lines.append("  command: {0}".format(row["command"]))
    return "\n".join(lines)
