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
from sim_plane.px4_failure_acceptance import (
    DEFAULT_REPORT_ROOT as DEFAULT_PX4_FAILURE_REPORT_ROOT,
    format_report as format_px4_failure_acceptance_report,
    validate_matrix as validate_px4_failure_acceptance_matrix,
    write_report as write_px4_failure_acceptance_report,
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
from sim_plane.scenario_generator import (
    build_custom_algorithm_scenario,
    format_generated_scenario_help,
    write_scenario_file,
)
from sim_plane.run_suite import (
    DEFAULT_SUITE_REPORT_ROOT,
    format_suite_report,
    run_suite,
)
from sim_plane.algorithm_ingress_check import (
    DEFAULT_INGRESS_REPORT_ROOT,
    format_algorithm_ingress_report,
    run_algorithm_ingress_check,
)
from sim_plane.autotest_pack import (
    DEFAULT_PROFILE as DEFAULT_AUTOTEST_PROFILE,
    DEFAULT_REPORT_ROOT as DEFAULT_AUTOTEST_REPORT_ROOT,
    format_autotest_report,
    run_autotest_pack,
)
from sim_plane.flight_log_analysis import (
    DEFAULT_REPORT_ROOT as DEFAULT_FLIGHT_LOG_REPORT_ROOT,
    analyze_flight_log,
    format_flight_log_report,
)
from sim_plane.scenario_fuzz import (
    DEFAULT_PROFILE as DEFAULT_FUZZ_PROFILE,
    DEFAULT_REPORT_ROOT as DEFAULT_FUZZ_REPORT_ROOT,
    DEFAULT_SEED as DEFAULT_FUZZ_SEED,
    format_fuzz_report,
    run_scenario_fuzz,
)
from sim_plane.baselines import format_baselines, get_baseline, list_baselines
from sim_plane.quadrotor_exam import (
    DEFAULT_EXAM_SUITE,
    format_quadrotor_exam_report,
    run_quadrotor_exam,
)


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

    serve_parser = subparsers.add_parser("serve", help="Replay an artifact or browse an artifact root in the dashboard")
    serve_parser.add_argument("artifact_dir", help="Artifact directory to replay, or an artifact root such as runs/")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
    serve_parser.add_argument("--port", type=int, default=8765, help="Dashboard bind port")
    serve_parser.add_argument("--open-browser", action="store_true", help="Try to open the dashboard automatically")

    subparsers.add_parser("list-backends", help="List known backends")
    subparsers.add_parser("list-adapters", help="List known algorithm adapters")
    baseline_parser = subparsers.add_parser(
        "list-baselines",
        help="List built-in baseline algorithm entrypoints",
    )
    baseline_parser.add_argument(
        "--include-planned",
        action="store_true",
        help="Also show planned catalog entries that are not runnable yet",
    )
    baseline_parser.add_argument(
        "--family",
        help="Filter by baseline family, for example control, planner, or tracking",
    )
    baseline_parser.add_argument(
        "--json",
        action="store_true",
        help="Print baseline catalog as JSON",
    )
    run_baseline_parser = subparsers.add_parser(
        "run-baseline",
        help="Run a ready baseline algorithm entrypoint",
    )
    run_baseline_parser.add_argument("name", help="Baseline name from list-baselines")
    run_baseline_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh baseline artifacts should be written",
    )
    run_baseline_parser.add_argument("--visualize", action="store_true", help="Launch the local web dashboard")
    run_baseline_parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
    run_baseline_parser.add_argument("--port", type=int, default=8765, help="Dashboard bind port")
    run_baseline_parser.add_argument("--open-browser", action="store_true", help="Try to open the dashboard automatically")
    run_baseline_parser.add_argument("--no-hold-open", action="store_true", help="Do not keep the dashboard open")
    run_baseline_parser.add_argument("--px4-dir", help="PX4-Autopilot checkout path for PX4-based baselines")
    run_baseline_parser.add_argument("--ros-workspace", help="Override ROS workspace path for ROS-based baselines")
    run_baseline_parser.add_argument("--connect-timeout", type=float, help="Override MAVLink heartbeat wait timeout in seconds")
    run_baseline_parser.add_argument("--json", action="store_true", help="Print baseline run outcome as JSON")
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

    px4_failure_acceptance_parser = subparsers.add_parser(
        "px4-failure-acceptance",
        help="Validate the PX4-native failure-injection acceptance surface",
    )
    px4_failure_acceptance_parser.add_argument(
        "--matrix",
        help="Path to the PX4 failure-injection acceptance matrix JSON",
    )
    px4_failure_acceptance_parser.add_argument(
        "--artifact-root",
        help="Artifact root to search when --latest is used",
    )
    px4_failure_acceptance_parser.add_argument(
        "--latest",
        action="store_true",
        help="Validate the latest matching artifacts instead of the frozen reference artifacts",
    )
    px4_failure_acceptance_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the PX4 failure-injection acceptance report as JSON",
    )
    px4_failure_acceptance_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_PX4_FAILURE_REPORT_ROOT),
        help="Where PX4 failure-injection acceptance reports should be written",
    )
    px4_failure_acceptance_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the PX4 failure-injection acceptance report under the report root",
    )
    px4_failure_acceptance_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=5,
        help="Keep only the newest N timestamped PX4 failure-injection acceptance report directories per mode; 0 disables pruning",
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

    suite_parser = subparsers.add_parser(
        "run-suite",
        help="Run one scenario through a suite of deterministic simulation variants",
    )
    suite_parser.add_argument("scenario", help="Base scenario JSON file")
    suite_parser.add_argument(
        "--suite",
        help="Suite JSON file. If omitted, a built-in demo disturbance suite is used.",
    )
    suite_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh variant artifacts should be written",
    )
    suite_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_SUITE_REPORT_ROOT),
        help="Where suite reports should be written",
    )
    suite_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the suite report as JSON",
    )
    suite_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the suite report under the report root",
    )
    suite_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped suite report directories; 0 disables pruning",
    )
    suite_parser.add_argument(
        "--px4-dir",
        help="PX4-Autopilot checkout path for PX4-based suite variants",
    )
    suite_parser.add_argument(
        "--ros-workspace",
        help="Override the ROS workspace path for ROS-based suite variants",
    )
    suite_parser.add_argument(
        "--connect-timeout",
        type=float,
        help="Override MAVLink heartbeat wait timeout in seconds for PX4-based suite variants",
    )

    exam_parser = subparsers.add_parser(
        "quadrotor-exam",
        help="Run the standard paper/project-style quadrotor validation exam",
    )
    exam_parser.add_argument(
        "--scenario",
        default="scenarios/basic_takeoff.json",
        help="Base scenario JSON file. Defaults to scenarios/basic_takeoff.json",
    )
    exam_parser.add_argument(
        "--suite",
        default=str(DEFAULT_EXAM_SUITE),
        help="Exam suite JSON. Defaults to configs/paper_quadrotor_exam_suite.json",
    )
    exam_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh exam artifacts should be written",
    )
    exam_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_SUITE_REPORT_ROOT),
        help="Where exam reports should be written",
    )
    exam_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the exam report under the report root",
    )
    exam_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped exam report directories; 0 disables pruning",
    )
    exam_parser.add_argument("--px4-dir", help="PX4-Autopilot checkout path for PX4-based exam rows")
    exam_parser.add_argument("--ros-workspace", help="Override ROS workspace path for ROS-based exam rows")
    exam_parser.add_argument("--connect-timeout", type=float, help="Override MAVLink heartbeat wait timeout in seconds")
    exam_parser.add_argument("--json", action="store_true", help="Print the exam report as JSON")

    flight_log_parser = subparsers.add_parser(
        "flight-log-analyze",
        help="Analyze a sim_plane run artifact or PX4 .ulg file into replay KPIs",
    )
    flight_log_parser.add_argument("source", help="Run artifact directory or PX4 .ulg file")
    flight_log_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_FLIGHT_LOG_REPORT_ROOT),
        help="Where flight-log analysis reports should be written",
    )
    flight_log_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the flight-log analysis report",
    )
    flight_log_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped reports for the same source; 0 disables pruning",
    )
    flight_log_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the flight-log analysis report as JSON",
    )

    fuzz_parser = subparsers.add_parser(
        "scenario-fuzz",
        help="Generate and run a deterministic fuzz/sweep suite, then report worst cases",
    )
    fuzz_parser.add_argument("scenario", help="Base scenario JSON file")
    fuzz_parser.add_argument(
        "--profile",
        default=DEFAULT_FUZZ_PROFILE,
        help="Fuzz profile to use. Currently: demo_fast",
    )
    fuzz_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_FUZZ_SEED,
        help="Deterministic fuzz seed",
    )
    fuzz_parser.add_argument(
        "--variants",
        type=int,
        default=6,
        help="Number of generated fuzz variants, excluding the baseline row",
    )
    fuzz_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh fuzz variant artifacts should be written",
    )
    fuzz_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_FUZZ_REPORT_ROOT),
        help="Where scenario-fuzz reports should be written",
    )
    fuzz_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the scenario-fuzz report",
    )
    fuzz_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped reports for the same fuzz name; 0 disables pruning",
    )
    fuzz_parser.add_argument(
        "--px4-dir",
        help="PX4-Autopilot checkout path for PX4-based fuzz profiles",
    )
    fuzz_parser.add_argument(
        "--ros-workspace",
        help="Override ROS workspace path for ROS-based fuzz profiles",
    )
    fuzz_parser.add_argument(
        "--connect-timeout",
        type=float,
        help="Override MAVLink heartbeat wait timeout in seconds for PX4-based fuzz profiles",
    )
    fuzz_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the scenario-fuzz report as JSON",
    )

    autotest_parser = subparsers.add_parser(
        "autotest-pack",
        help="Run a CI/autotest-like local validation pack",
    )
    autotest_parser.add_argument(
        "--profile",
        default=DEFAULT_AUTOTEST_PROFILE,
        help="Autotest profile to run. Currently: fast",
    )
    autotest_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Artifact root to use for fresh runs and latest acceptance checks",
    )
    autotest_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_AUTOTEST_REPORT_ROOT),
        help="Where autotest pack reports should be written",
    )
    autotest_parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Do not persist the autotest pack report",
    )
    autotest_parser.add_argument(
        "--keep-last-reports",
        type=int,
        default=10,
        help="Keep only the newest N timestamped autotest report directories; 0 disables pruning",
    )
    autotest_parser.add_argument(
        "--px4-dir",
        help="PX4-Autopilot checkout path for PX4-based steps",
    )
    autotest_parser.add_argument(
        "--ros-workspace",
        help="Override ROS workspace path for ROS-based steps",
    )
    autotest_parser.add_argument(
        "--connect-timeout",
        type=float,
        help="Override MAVLink heartbeat wait timeout in seconds for PX4-based steps",
    )
    autotest_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the autotest pack report as JSON",
    )

    show_parser = subparsers.add_parser("show-scenario", help="Print a normalized scenario")
    show_parser.add_argument("scenario", help="Path to the scenario JSON file")

    generate_parser = subparsers.add_parser(
        "generate-scenario",
        help="Generate a custom algorithm scenario for external_command or ros_command",
    )
    generate_parser.add_argument(
        "--adapter",
        choices=["external_command", "ros_command"],
        required=True,
        help="Algorithm adapter family to generate",
    )
    generate_parser.add_argument(
        "--command",
        dest="user_command",
        required=True,
        help="Command that starts the user algorithm. Quote it as one shell string.",
    )
    generate_parser.add_argument(
        "--name",
        help="Scenario name. Defaults to a backend-specific custom name.",
    )
    generate_parser.add_argument(
        "--output",
        help="Output scenario JSON path. Defaults to scenarios/<name>.json",
    )
    generate_parser.add_argument(
        "--backend",
        help="Backend to use. external_command: px4_sih/px4_jsbsim/px4_gazebo_classic; ros_command: marsim/fast_lio_marsim",
    )
    generate_parser.add_argument(
        "--workdir",
        help="Working directory for the user algorithm command",
    )
    generate_parser.add_argument(
        "--shell",
        action="store_true",
        help="Keep --command as a shell string instead of splitting it into argv",
    )
    generate_parser.add_argument(
        "--duration-s",
        type=float,
        help="Scenario duration in seconds",
    )
    generate_parser.add_argument(
        "--target-altitude-m",
        type=float,
        help="Target altitude used by the scenario/backend",
    )
    generate_parser.add_argument(
        "--rviz",
        action="store_true",
        help="Enable RViz for ROS-command generated scenarios",
    )
    generate_parser.add_argument(
        "--gpu",
        action="store_true",
        help="Enable GPU sensing where supported by the ROS backend",
    )
    generate_parser.add_argument(
        "--required-subscribed-topics",
        help="Comma-separated ROS topics your algorithm must subscribe before the adapter marks it ready",
    )
    generate_parser.add_argument(
        "--required-published-topics",
        help="Comma-separated ROS topics your algorithm must publish before the adapter marks it ready",
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated scenario JSON without writing it",
    )
    generate_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output scenario if it already exists",
    )

    ingress_parser = subparsers.add_parser(
        "check-algorithm-ingress",
        help="Run one custom algorithm scenario and report adapter/interface health",
    )
    ingress_parser.add_argument(
        "--scenario",
        help="Existing scenario JSON to run for ingress health checking",
    )
    ingress_parser.add_argument(
        "--adapter",
        choices=["external_command", "ros_command"],
        help="Adapter to generate when --scenario is not provided",
    )
    ingress_parser.add_argument(
        "--command",
        dest="user_command",
        help="User algorithm command to generate when --scenario is not provided",
    )
    ingress_parser.add_argument(
        "--backend",
        help="Backend to use for generated ingress scenario",
    )
    ingress_parser.add_argument(
        "--workdir",
        help="Working directory for generated user command",
    )
    ingress_parser.add_argument(
        "--shell",
        action="store_true",
        help="Keep generated --command as a shell string instead of splitting it into argv",
    )
    ingress_parser.add_argument(
        "--duration-s",
        type=float,
        help="Generated scenario duration in seconds",
    )
    ingress_parser.add_argument(
        "--target-altitude-m",
        type=float,
        help="Generated scenario target altitude",
    )
    ingress_parser.add_argument(
        "--artifact-root",
        default="runs",
        help="Where fresh ingress artifacts should be written",
    )
    ingress_parser.add_argument(
        "--report-root",
        default=str(DEFAULT_INGRESS_REPORT_ROOT),
        help="Where generated ingress scenario templates should be written",
    )
    ingress_parser.add_argument(
        "--px4-dir",
        help="PX4-Autopilot checkout path for PX4-based ingress checks",
    )
    ingress_parser.add_argument(
        "--ros-workspace",
        help="Override ROS workspace path for ROS-based ingress checks",
    )
    ingress_parser.add_argument(
        "--connect-timeout",
        type=float,
        help="Override MAVLink heartbeat wait timeout in seconds",
    )
    ingress_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the ingress health report as JSON",
    )

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

    if args.command == "list-baselines":
        rows = list_baselines(include_planned=args.include_planned, family=args.family)
        if args.json:
            print(json.dumps({"baselines": rows}, indent=2, ensure_ascii=False))
        else:
            print(format_baselines(rows))
        return 0

    if args.command == "run-baseline":
        try:
            baseline = get_baseline(args.name)
        except KeyError:
            parser.error("unknown baseline: {0}".format(args.name))
        if baseline.get("status") != "ready":
            parser.error("baseline {0} is not runnable yet: status={1}".format(args.name, baseline.get("status")))
        scenario = baseline.get("scenario")
        if not scenario:
            parser.error("baseline {0} has no scenario".format(args.name))
        ensure_artifact_root(args.artifact_root)
        outcome = run_scenario(
            scenario,
            artifact_root=args.artifact_root,
            visualize=args.visualize,
            host=args.host,
            port=args.port,
            open_browser=args.open_browser,
            hold_open=not args.no_hold_open and args.visualize,
            runtime_options={
                "px4_dir": args.px4_dir,
                "ros_workspace_dir": args.ros_workspace,
                "connect_timeout_s": args.connect_timeout,
            },
        )
        payload = {"baseline": baseline, "outcome": outcome}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("baseline: {0}".format(args.name))
            print("status: {0}".format(outcome["result"].get("status")))
            print("artifact_dir: {0}".format(outcome["artifact_dir"]))
            if outcome.get("dashboard_url"):
                print("dashboard_url: {0}".format(outcome["dashboard_url"]))
        return 0 if outcome["result"].get("status") == "passed" else 1

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

    if args.command == "generate-scenario":
        try:
            scenario, output_path = build_custom_algorithm_scenario(
                adapter=args.adapter,
                command=args.user_command,
                name=args.name,
                output=args.output,
                backend=args.backend,
                workdir=args.workdir,
                shell=args.shell,
                duration_s=args.duration_s,
                target_altitude_m=args.target_altitude_m,
                launch_rviz=args.rviz if args.rviz else None,
                use_gpu=args.gpu if args.gpu else None,
                required_subscribed_topics=args.required_subscribed_topics,
                required_published_topics=args.required_published_topics,
            )
            if args.dry_run:
                print(json.dumps(scenario, indent=2, ensure_ascii=False))
                return 0
            written_path = write_scenario_file(scenario, output_path, force=args.force)
        except (ValueError, FileExistsError) as exc:
            parser.error(str(exc))
        print(format_generated_scenario_help(scenario, written_path))
        return 0

    if args.command == "check-algorithm-ingress":
        try:
            report = run_algorithm_ingress_check(
                scenario_path=args.scenario,
                adapter=args.adapter,
                command=args.user_command,
                backend=args.backend,
                workdir=args.workdir,
                shell=args.shell,
                duration_s=args.duration_s,
                target_altitude_m=args.target_altitude_m,
                artifact_root=args.artifact_root,
                report_root=args.report_root,
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
            print(format_algorithm_ingress_report(report))
        return 0 if report["status"] == "passed" else 1

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

    if args.command == "px4-failure-acceptance":
        report = validate_px4_failure_acceptance_matrix(
            path=args.matrix,
            artifact_root=args.artifact_root,
            use_latest=args.latest,
        )
        saved_report = None
        if not args.no_save_report:
            saved_report = write_px4_failure_acceptance_report(
                report,
                report_root=args.report_root,
                keep_last=args.keep_last_reports,
            )
            report["saved_report"] = saved_report
            report["delta_from_previous"] = saved_report["delta"]
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_px4_failure_acceptance_report(report))
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

    if args.command == "run-suite":
        try:
            report = run_suite(
                scenario_path=args.scenario,
                suite_path=args.suite,
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
            print(format_suite_report(report))
        return 0 if report["status"] == "passed" else 1

    if args.command == "quadrotor-exam":
        try:
            report = run_quadrotor_exam(
                scenario_path=args.scenario,
                suite_path=args.suite,
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
            print(format_quadrotor_exam_report(report))
        return 0 if report["status"] == "passed" else 1

    if args.command == "flight-log-analyze":
        try:
            report = analyze_flight_log(
                args.source,
                report_root=None if args.no_save_report else args.report_root,
                keep_last=args.keep_last_reports,
                save_report=not args.no_save_report,
            )
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_flight_log_report(report))
        return 0 if report["status"] == "passed" else 1

    if args.command == "scenario-fuzz":
        try:
            report = run_scenario_fuzz(
                scenario_path=args.scenario,
                profile=args.profile,
                seed=args.seed,
                variants=args.variants,
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
            print(format_fuzz_report(report))
        return 0 if report["status"] == "passed" else 1

    if args.command == "autotest-pack":
        try:
            report = run_autotest_pack(
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
            print(format_autotest_report(report))
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
