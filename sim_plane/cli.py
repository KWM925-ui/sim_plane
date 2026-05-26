import argparse
import json

from sim_plane.adapters import available_adapters
from sim_plane.artifact_hygiene import (
    DEFAULT_ARTIFACT_ROOT,
    apply_artifact_hygiene,
    apply_manual_probe_hygiene,
    format_artifact_hygiene_report,
    format_manual_probe_hygiene_report,
)
from sim_plane.backends import available_backends
from sim_plane.planner_acceptance import (
    DEFAULT_ACCEPTANCE_REPORT_ROOT,
    format_acceptance_report,
    validate_acceptance_matrix,
    write_acceptance_report,
)
from sim_plane.platform_acceptance import (
    DEFAULT_PLATFORM_REPORT_ROOT,
    format_platform_acceptance_report,
    validate_platform_matrix,
    write_platform_acceptance_report,
)
from sim_plane.human_follow_stage1_acceptance import (
    DEFAULT_REPORT_ROOT as DEFAULT_HF_STAGE1_REPORT_ROOT,
    format_report as format_hf_stage1_acceptance_report,
    validate_matrix as validate_hf_stage1_acceptance_matrix,
    write_report as write_hf_stage1_acceptance_report,
)
from sim_plane.human_follow_stage1_detector_tracker_acceptance import (
    DEFAULT_REPORT_ROOT as DEFAULT_HF_STAGE1_DETECTOR_TRACKER_REPORT_ROOT,
    format_report as format_hf_stage1_detector_tracker_acceptance_report,
    validate_matrix as validate_hf_stage1_detector_tracker_acceptance_matrix,
    write_report as write_hf_stage1_detector_tracker_acceptance_report,
)
from sim_plane.human_follow_stage2_acceptance import (
    DEFAULT_REPORT_ROOT as DEFAULT_HF_STAGE2_REPORT_ROOT,
    format_report as format_hf_stage2_acceptance_report,
    validate_matrix as validate_hf_stage2_acceptance_matrix,
    write_report as write_hf_stage2_acceptance_report,
)
from sim_plane.human_follow_stage2_integrated_acceptance import (
    DEFAULT_REPORT_ROOT as DEFAULT_HF_STAGE2_INTEGRATED_REPORT_ROOT,
    format_report as format_hf_stage2_integrated_acceptance_report,
    validate_matrix as validate_hf_stage2_integrated_acceptance_matrix,
    write_report as write_hf_stage2_integrated_acceptance_report,
)
from sim_plane.live_smoke import (
    DEFAULT_LIVE_SMOKE_REPORT_ROOT,
    DEFAULT_PROFILE as DEFAULT_LIVE_SMOKE_PROFILE,
    format_live_smoke_report,
    run_live_smoke_suite,
)
from sim_plane.doctor import collect_platform_doctor_report, format_platform_doctor_report
from sim_plane.runner import ensure_artifact_root, run_scenario, serve_artifact
from sim_plane.scenario import load_scenario


def build_parser():
    parser = argparse.ArgumentParser(prog="sim-plane", description="Lightweight UAV simulation platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a scenario")
    run_parser.add_argument("scenario", help="Path to the scenario JSON file")
    run_parser.add_argument("--backend", help="Override the scenario backend")
    run_parser.add_argument("--artifact-root", default="runs", help="Where run artifacts should be written")
    run_parser.add_argument("--visualize", action="store_true", help="Launch the local web dashboard")
    run_parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
    run_parser.add_argument("--port", type=int, default=8765, help="Dashboard bind port")
    run_parser.add_argument("--open-browser", action="store_true", help="Try to open the dashboard automatically")
    run_parser.add_argument("--px4-dir", help="PX4-Autopilot checkout path for PX4-based backends such as px4_sih and px4_jsbsim")
    run_parser.add_argument("--qgc", action="store_true", help="Launch QGroundControl if the backend supports it")
    run_parser.add_argument("--no-qgc", action="store_true", help="Disable QGroundControl launch even if the scenario enables it")
    run_parser.add_argument("--jmavsim", action="store_true", help="Launch jMAVSim if the backend supports it")
    run_parser.add_argument("--no-jmavsim", action="store_true", help="Disable jMAVSim launch even if the scenario enables it")
    run_parser.add_argument("--rviz", action="store_true", help="Launch RViz if the backend supports it")
    run_parser.add_argument("--no-rviz", action="store_true", help="Disable RViz launch even if the scenario enables it")
    run_parser.add_argument("--ros-workspace", help="Override the ROS workspace path for ROS-based backends")
    run_parser.add_argument("--mavlink-endpoint", help="Override the MAVLink endpoint, for example udpin:127.0.0.1:14540")
    run_parser.add_argument("--model", help="Override the PX4 model, for example sihsim_quadx or quadrotor_x")
    run_parser.add_argument("--connect-timeout", type=float, help="Override the MAVLink heartbeat wait timeout in seconds")
    run_parser.add_argument(
        "--no-hold-open",
        action="store_true",
        help="Exit immediately after the run instead of keeping the dashboard open",
    )

    serve_parser = subparsers.add_parser("serve", help="Replay an existing artifact directory in the dashboard")
    serve_parser.add_argument("artifact_dir", help="Artifact directory to replay")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
    serve_parser.add_argument("--port", type=int, default=8765, help="Dashboard bind port")
    serve_parser.add_argument("--open-browser", action="store_true", help="Try to open the dashboard automatically")

    subparsers.add_parser("list-backends", help="List known backends")
    subparsers.add_parser("list-adapters", help="List known algorithm adapters")
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Inspect current platform readiness and print recommended next run paths",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the doctor report as JSON",
    )

    acceptance_parser = subparsers.add_parser(
        "planner-acceptance",
        help="Validate the four-row planner acceptance baseline",
    )
    acceptance_parser.add_argument(
        "--matrix",
        help="Path to the planner acceptance matrix JSON",
    )
    acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the acceptance report as JSON",
    )
    acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_ACCEPTANCE_REPORT_ROOT),
        help="Where acceptance reports should be written",
    )
    acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the acceptance report under the report root",
    )
    acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped acceptance report directories per mode; 0 disables pruning",
    )

    platform_acceptance_parser = subparsers.add_parser(
        "platform-acceptance",
        help="Validate the strict quadrotor platform acceptance baseline",
    )
    platform_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the platform acceptance matrix JSON",
    )
    platform_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    platform_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    platform_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the platform acceptance report as JSON",
    )
    platform_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_PLATFORM_REPORT_ROOT),
        help="Where platform acceptance reports should be written",
    )
    platform_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the platform acceptance report under the report root",
    )
    platform_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped platform acceptance report directories per mode; 0 disables pruning",
    )

    human_follow_stage1_acceptance_parser = subparsers.add_parser(
        "human-follow-stage1-acceptance",
        help="Validate the project-specific Stage1 human-follow behavior acceptance baseline",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the human-follow Stage1 acceptance matrix JSON",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the human-follow Stage1 acceptance report as JSON",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_HF_STAGE1_REPORT_ROOT),
        help="Where human-follow Stage1 acceptance reports should be written",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the human-follow Stage1 acceptance report under the report root",
    )
    human_follow_stage1_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped human-follow Stage1 acceptance report directories per mode; 0 disables pruning",
    )

    human_follow_stage1_detector_tracker_acceptance_parser = subparsers.add_parser(
        "human-follow-stage1-detector-tracker-acceptance",
        help="Validate the project-specific Stage1 detector/tracker-in-loop managed acceptance baseline",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the human-follow Stage1 detector/tracker acceptance matrix JSON",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the human-follow Stage1 detector/tracker acceptance report as JSON",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_HF_STAGE1_DETECTOR_TRACKER_REPORT_ROOT),
        help="Where human-follow Stage1 detector/tracker acceptance reports should be written",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the human-follow Stage1 detector/tracker acceptance report under the report root",
    )
    human_follow_stage1_detector_tracker_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped human-follow Stage1 detector/tracker acceptance report directories per mode; 0 disables pruning",
    )

    human_follow_stage2_acceptance_parser = subparsers.add_parser(
        "human-follow-stage2-acceptance",
        help="Validate the project-specific Stage2 real-EGO managed acceptance baseline",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the human-follow Stage2 acceptance matrix JSON",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the human-follow Stage2 acceptance report as JSON",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_HF_STAGE2_REPORT_ROOT),
        help="Where human-follow Stage2 acceptance reports should be written",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the human-follow Stage2 acceptance report under the report root",
    )
    human_follow_stage2_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped human-follow Stage2 acceptance report directories per mode; 0 disables pruning",
    )

    human_follow_stage2_integrated_acceptance_parser = subparsers.add_parser(
        "human-follow-stage2-integrated-acceptance",
        help="Validate the project-specific Stage2 real-EGO integrated managed acceptance baseline",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the human-follow Stage2 integrated acceptance matrix JSON",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the human-follow Stage2 integrated acceptance report as JSON",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_HF_STAGE2_INTEGRATED_REPORT_ROOT),
        help="Where human-follow Stage2 integrated acceptance reports should be written",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the human-follow Stage2 integrated acceptance report under the report root",
    )
    human_follow_stage2_integrated_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped human-follow Stage2 integrated acceptance report directories per mode; 0 disables pruning",
    )

    artifact_hygiene_parser = subparsers.add_parser(
        "artifact-hygiene",
        help="Scan and clean non-artifact directories under the artifact root",
    )
    artifact_hygiene_parser.add_argument(
        "--artifact-root",
        default=str(DEFAULT_ARTIFACT_ROOT),
        help="Artifact root to scan",
    )
    artifact_hygiene_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the artifact hygiene report as JSON",
    )
    artifact_hygiene_parser.add_argument(
        "--prune-safe",
        action="store_true",
        help="Prune unreferenced incomplete directories under the artifact root",
    )
    artifact_hygiene_parser.add_argument(
        "--migrate-retained-manual",
        action="store_true",
        help="Move repo-referenced manual probe directories under manual_probes/",
    )
    artifact_hygiene_parser.add_argument(
        "--manual-probe-root-name",
        default="manual_probes",
        help="Reserved root name for retained manual probe directories",
    )

    manual_probe_hygiene_parser = subparsers.add_parser(
        "manual-probe-hygiene",
        help="Inspect or prune manual probe directories under manual_probes/",
    )
    manual_probe_hygiene_parser.add_argument(
        "--artifact-root",
        default=str(DEFAULT_ARTIFACT_ROOT),
        help="Artifact root that contains manual_probes/",
    )
    manual_probe_hygiene_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the manual probe hygiene report as JSON",
    )
    manual_probe_hygiene_parser.add_argument(
        "--prune-safe",
        action="store_true",
        help="Prune unreferenced superseded manual probe directories",
    )
    manual_probe_hygiene_parser.add_argument(
        "--manual-probe-root-name",
        default="manual_probes",
        help="Root name for manual probe directories",
    )

    live_smoke_parser = subparsers.add_parser(
        "live-smoke",
        help="Run a fresh lightweight boot smoke suite and write a live-smoke report",
    )
    live_smoke_parser.add_argument(
        "--matrix",
        help="Path to the live smoke matrix JSON",
    )
    live_smoke_parser.add_argument(
        "--profile",
        default=DEFAULT_LIVE_SMOKE_PROFILE,
        help="Live smoke profile to run, for example default, fast, or core",
    )
    live_smoke_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh run artifacts should be written",
    )
    live_smoke_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_LIVE_SMOKE_REPORT_ROOT),
        help="Where live smoke reports should be written",
    )
    live_smoke_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the live smoke report as JSON",
    )
    live_smoke_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the live smoke report under the report root",
    )
    live_smoke_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped live smoke report directories per profile; 0 disables pruning",
    )
    live_smoke_parser.add_argument(
        "--px4-dir",
        help="PX4-Autopilot checkout path for PX4-based smoke rows",
    )
    live_smoke_parser.add_argument(
        "--ros-workspace",
        help="Override the ROS workspace path for ROS-based smoke rows",
    )
    live_smoke_parser.add_argument(
        "--connect-timeout",
        type=float,
        help="Override MAVLink heartbeat wait timeout in seconds for PX4-based smoke rows",
    )

    show_parser = subparsers.add_parser("show-scenario", help="Print a normalized scenario")
    show_parser.add_argument("scenario", help="Path to the scenario JSON file")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-backends":
        for name, backend_cls in available_backends().items():
            backend = backend_cls()
            issues = backend.validate_environment()
            status = "ready" if not issues else "scaffolded"
            print("{0}: {1}".format(name, status))
            for issue in issues:
                print("  - {0}".format(issue))
        return 0

    if args.command == "list-adapters":
        for name, adapter_cls in available_adapters().items():
            adapter = adapter_cls()
            issues = adapter.validate_environment()
            status = "ready" if not issues else "scaffolded"
            print("{0}: {1}".format(name, status))
            for issue in issues:
                print("  - {0}".format(issue))
        return 0

    if args.command == "doctor":
        report = collect_platform_doctor_report()
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_platform_doctor_report(report))
        return 0

    if args.command == "show-scenario":
        scenario = load_scenario(args.scenario)
        print(json.dumps(scenario, indent=2, ensure_ascii=False))
        return 0

    if args.command == "planner-acceptance":
        report = validate_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "platform-acceptance":
        report = validate_platform_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_platform_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_platform_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "human-follow-stage1-acceptance":
        report = validate_hf_stage1_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_hf_stage1_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_hf_stage1_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "human-follow-stage2-acceptance":
        report = validate_hf_stage2_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_hf_stage2_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_hf_stage2_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "human-follow-stage2-integrated-acceptance":
        report = validate_hf_stage2_integrated_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_hf_stage2_integrated_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_hf_stage2_integrated_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "human-follow-stage1-detector-tracker-acceptance":
        report = validate_hf_stage1_detector_tracker_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_hf_stage1_detector_tracker_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_hf_stage1_detector_tracker_acceptance_report(report))
            if saved_report is not None:
                print("report_dir: {0}".format(saved_report["report_dir"]))
                print("latest_report_json: {0}".format(saved_report["latest_report_json"]))
                print("latest_delta_json: {0}".format(saved_report["latest_delta_json"]))
                print("history_jsonl: {0}".format(saved_report["history_jsonl"]))
        return 0 if report["status"] == "passed" else 1

    if args.command == "artifact-hygiene":
        report = apply_artifact_hygiene(
            artifact_root=args.artifact_root,
            migrate_retained_manual=args.migrate_retained_manual,
            prune_safe=args.prune_safe,
            manual_probe_root_name=args.manual_probe_root_name,
        )
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_artifact_hygiene_report(report))
        return 0 if report["status"] == "clean" else 1

    if args.command == "manual-probe-hygiene":
        report = apply_manual_probe_hygiene(
            artifact_root=args.artifact_root,
            manual_probe_root_name=args.manual_probe_root_name,
            prune_safe=args.prune_safe,
        )
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_manual_probe_hygiene_report(report))
        return 0 if report["status"] == "clean" else 1

    if args.command == "live-smoke":
        try:
            report = run_live_smoke_suite(
                matrix_path=args.matrix,
                profile=args.profile,
                artifact_root=args.artifact_root,
                report_root=None if args.no_save_report else args.report_root,
                keep_last=args.keep_last_reports,
                runtime_options={
                    "px4_dir": args.px4_dir,
                    "ros_workspace_dir": args.ros_workspace,
                    "connect_timeout_s": args.connect_timeout,
                },
            )
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_live_smoke_report(report))
        return 0 if report["status"] == "passed" else 1

    if args.command == "run":
        ensure_artifact_root(args.artifact_root)
        outcome = run_scenario(
            args.scenario,
            backend_override=args.backend,
            artifact_root=args.artifact_root,
            visualize=args.visualize,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
            hold_open=not args.no_hold_open and args.visualize,
            runtime_options={
                "px4_dir": args.px4_dir,
                "launch_qgc": args.qgc,
                "disable_qgc": args.no_qgc,
                "launch_jmavsim": args.jmavsim,
                "disable_jmavsim": args.no_jmavsim,
                "launch_rviz": args.rviz,
                "disable_rviz": args.no_rviz,
                "ros_workspace_dir": args.ros_workspace,
                "mavlink_endpoint": args.mavlink_endpoint,
                "model": args.model,
                "connect_timeout_s": args.connect_timeout,
            },
        )
        print("artifact_dir: {0}".format(outcome["artifact_dir"]))
        print("status: {0}".format(outcome["result"].get("status")))
        if outcome["dashboard_url"]:
            print("dashboard_url: {0}".format(outcome["dashboard_url"]))
        return 0 if outcome["result"].get("status") == "passed" else 1

    if args.command == "serve":
        serve_artifact(
            args.artifact_dir,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
        )
        return 0

    parser.error("unknown command")
