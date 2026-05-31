import json
from datetime import datetime
from pathlib import Path

from sim_plane.artifact_hygiene import apply_artifact_hygiene
from sim_plane.doctor import collect_platform_doctor_report
from sim_plane.flight_log_analysis import analyze_flight_log
from sim_plane.live_smoke import run_live_smoke_suite
from sim_plane.platform_acceptance import validate_platform_matrix, write_platform_acceptance_report
from sim_plane.px4_failure_acceptance import validate_matrix as validate_px4_failure_matrix
from sim_plane.px4_failure_acceptance import write_report as write_px4_failure_report
from sim_plane.run_suite import run_suite
from sim_plane.scenario_fuzz import run_scenario_fuzz
from sim_plane.web import is_complete_artifact_dir


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_ROOT = REPO_ROOT / "runs" / "autotest"
DEFAULT_KEEP_LAST = 10
DEFAULT_PROFILE = "fast"


def run_autotest_pack(
    profile=DEFAULT_PROFILE,
    artifact_root="runs",
    report_root=None,
    keep_last=DEFAULT_KEEP_LAST,
    runtime_options=None,
):
    if profile != "fast":
        raise ValueError("unsupported autotest profile: {0}".format(profile))
    runtime_options = runtime_options or {}
    artifact_root_path = Path(artifact_root)
    steps = []

    steps.append(run_step("doctor", "python3 -m sim_plane doctor --json", run_doctor_step))
    steps.append(
        run_step(
            "artifact_hygiene",
            "python3 -m sim_plane artifact-hygiene --artifact-root {0} --json".format(artifact_root),
            lambda: run_artifact_hygiene_step(artifact_root_path),
        )
    )
    steps.append(
        run_step(
            "live_smoke_fast",
            "python3 -m sim_plane live-smoke --profile fast --artifact-root {0} --report-root runs/live_smoke --json".format(
                artifact_root
            ),
            lambda: run_live_smoke_suite(
                profile="fast",
                artifact_root=artifact_root,
                report_root=artifact_root_path / "live_smoke",
                runtime_options=runtime_options,
            ),
        )
    )
    steps.append(
        run_step(
            "demo_degradation_suite",
            "python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_degradation_suite.json --artifact-root {0} --report-root runs/suites --json".format(
                artifact_root
            ),
            lambda: run_suite(
                "scenarios/basic_takeoff.json",
                suite_path="configs/demo_degradation_suite.json",
                artifact_root=artifact_root,
                report_root=artifact_root_path / "suites",
                runtime_options=runtime_options,
            ),
        )
    )
    steps.append(
        run_step(
            "scenario_fuzz_demo_fast",
            "python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast --seed 20260528 --variants 4 --artifact-root {0} --report-root runs/scenario_fuzz --json".format(
                artifact_root
            ),
            lambda: run_scenario_fuzz(
                "scenarios/basic_takeoff.json",
                profile="demo_fast",
                seed=20260528,
                variants=4,
                artifact_root=artifact_root,
                report_root=artifact_root_path / "scenario_fuzz",
                runtime_options=runtime_options,
            ),
        )
    )
    latest_px4_artifact = find_latest_artifact(artifact_root_path, backend_prefix="px4", preferred_scenario_prefix="px4_sih")
    if latest_px4_artifact is not None:
        steps.append(
            run_step(
                "flight_log_artifact_replay",
                "python3 -m sim_plane flight-log-analyze {0} --report-root runs/flight_log_analysis --json".format(
                    latest_px4_artifact
                ),
                lambda: analyze_flight_log(
                    latest_px4_artifact,
                    report_root=artifact_root_path / "flight_log_analysis",
                ),
            )
        )
    else:
        steps.append(
            {
                "name": "flight_log_artifact_replay",
                "command": "python3 -m sim_plane flight-log-analyze <latest-px4-artifact>",
                "status": "failed",
                "issues": ["no complete PX4 artifact found under {0}".format(artifact_root)],
            }
        )
    steps.append(
        run_step(
            "px4_failure_acceptance_latest",
            "python3 -m sim_plane px4-failure-acceptance --latest --artifact-root {0} --json".format(artifact_root),
            lambda: write_and_return(
                validate_px4_failure_matrix(artifact_root=artifact_root, use_latest=True),
                writer=write_px4_failure_report,
                report_root=artifact_root_path / "px4_failure_injection_acceptance",
            ),
        )
    )
    steps.append(
        run_step(
            "platform_acceptance_latest",
            "python3 -m sim_plane platform-acceptance --latest --artifact-root {0} --json".format(artifact_root),
            lambda: write_and_return(
                validate_platform_matrix(artifact_root=artifact_root, use_latest=True),
                writer=write_platform_acceptance_report,
                report_root=artifact_root_path / "platform_acceptance",
            ),
        )
    )

    issues = []
    for step in steps:
        if step.get("status") != "passed":
            step_issues = step.get("issues", [])
            if step_issues:
                issues.extend("{0}: {1}".format(step["name"], issue) for issue in step_issues)
            else:
                issues.append("{0}: step status is {1}".format(step["name"], step.get("status")))
    report = {
        "pack_name": "sim_plane_autotest_{0}".format(profile),
        "profile": profile,
        "artifact_root": str(artifact_root_path),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "steps": steps,
    }
    if report_root is not None:
        report["saved_report"] = write_autotest_report(
            report,
            report_root=report_root,
            keep_last=keep_last,
        )
    return report


def run_step(name, command, fn):
    try:
        payload = fn()
    except Exception as exc:
        return {
            "name": name,
            "command": command,
            "status": "failed",
            "issues": ["step raised exception: {0}".format(exc)],
        }
    status = payload.get("status", "passed") if isinstance(payload, dict) else "passed"
    issues = list(payload.get("issues", [])) if isinstance(payload, dict) else []
    return {
        "name": name,
        "command": command,
        "status": "passed" if is_success_status(status) and not issues else "failed",
        "issues": issues,
        "summary": summarize_step_payload(payload),
        "report_paths": extract_report_paths(payload),
    }


def is_success_status(status):
    return status in {"passed", "clean"}


def run_doctor_step():
    report = collect_platform_doctor_report()
    issues = []
    if report["summary"].get("ready_backend_count", 0) < 1:
        issues.append("no ready backend reported by doctor")
    return {
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "summary": report["summary"],
    }


def run_artifact_hygiene_step(artifact_root):
    return apply_artifact_hygiene(artifact_root=artifact_root)


def write_and_return(report, writer, report_root):
    saved = writer(report, report_root=report_root)
    report = dict(report)
    report["saved_report"] = saved
    report["delta_from_previous"] = saved.get("delta")
    return report


def summarize_step_payload(payload):
    if not isinstance(payload, dict):
        return {}
    summary = {}
    for key in (
        "status",
        "profile",
        "matrix_name",
        "suite_name",
        "fuzz_name",
        "source_type",
        "selection_mode",
        "artifact_root",
    ):
        if key in payload:
            summary[key] = payload[key]
    if "rows" in payload and isinstance(payload["rows"], list):
        summary["row_count"] = len(payload["rows"])
        summary["passed_row_count"] = len([row for row in payload["rows"] if row.get("status") == "passed"])
    if "metrics" in payload and isinstance(payload["metrics"], dict):
        summary["metrics"] = {
            key: payload["metrics"].get(key)
            for key in (
                "telemetry_count",
                "duration_s",
                "max_altitude_m",
                "max_speed_mps",
                "mode_change_count",
                "anomaly_event_count",
            )
            if key in payload["metrics"]
        }
    if "summary" in payload and isinstance(payload["summary"], dict):
        summary["summary"] = payload["summary"]
    return summary


def extract_report_paths(payload):
    if not isinstance(payload, dict):
        return {}
    saved = payload.get("saved_report")
    if isinstance(saved, dict):
        return {
            key: value
            for key, value in saved.items()
            if isinstance(value, str) and ("json" in key or "report" in key or "history" in key)
        }
    return {}


def find_latest_artifact(artifact_root, backend_prefix=None, preferred_scenario_prefix=None):
    root = Path(artifact_root)
    candidates = []
    if not root.exists():
        return None
    for path in root.iterdir():
        if not is_complete_artifact_dir(path):
            continue
        try:
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        backend = str(result.get("backend") or manifest.get("backend") or "")
        scenario_name = str(result.get("scenario_name") or manifest.get("scenario_name") or path.name)
        if backend_prefix and not backend.startswith(backend_prefix):
            continue
        preferred = preferred_scenario_prefix and scenario_name.startswith(preferred_scenario_prefix)
        created_at = manifest.get("created_at_utc") or ""
        candidates.append((bool(preferred), created_at, path.name, path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][3]


def write_autotest_report(report, report_root=None, keep_last=DEFAULT_KEEP_LAST):
    root = Path(report_root) if report_root is not None else DEFAULT_REPORT_ROOT
    pack_name = report.get("pack_name", "sim_plane_autotest")
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    report_dir = root / "{0}_{1}".format(pack_name, stamp)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / "report.json"
    report_txt = report_dir / "report.txt"
    latest_json = root / "latest_{0}.json".format(pack_name)
    latest_txt = root / "latest_{0}.txt".format(pack_name)
    history_jsonl = root / "history_{0}.jsonl".format(pack_name)
    serializable = dict(report)
    serializable.pop("saved_report", None)
    report_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_txt.write_text(format_autotest_report(serializable) + "\n", encoding="utf-8")
    latest_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest_txt.write_text(format_autotest_report(serializable) + "\n", encoding="utf-8")
    with history_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "created_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "pack_name": pack_name,
                    "profile": report.get("profile"),
                    "status": report.get("status"),
                    "report_json": str(report_json),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    if keep_last and keep_last > 0:
        prune_autotest_reports(root, pack_name, keep_last)
    return {
        "report_dir": str(report_dir),
        "report_json": str(report_json),
        "report_text": str(report_txt),
        "latest_json": str(latest_json),
        "latest_text": str(latest_txt),
        "history_jsonl": str(history_jsonl),
    }


def prune_autotest_reports(report_root, pack_name, keep_last):
    report_dirs = sorted(
        [path for path in Path(report_root).glob("{0}_*".format(pack_name)) if path.is_dir()],
        key=lambda path: path.name,
    )
    for path in report_dirs[:-keep_last]:
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()


def format_autotest_report(report):
    lines = [
        "autotest pack: {0}".format(report.get("status")),
        "profile: {0}".format(report.get("profile")),
        "artifact_root: {0}".format(report.get("artifact_root")),
        "",
        "{0:<34} {1:<8} {2}".format("step", "status", "command"),
        "-" * 100,
    ]
    for step in report.get("steps", []):
        lines.append("{0:<34} {1:<8} {2}".format(step["name"], step["status"], step["command"]))
        for issue in step.get("issues", []):
            lines.append("  issue={0}".format(issue))
    if report.get("issues"):
        lines.append("")
        lines.append("issues:")
        for issue in report["issues"]:
            lines.append("- {0}".format(issue))
    saved = report.get("saved_report")
    if saved:
        lines.append("")
        lines.append("report_json: {0}".format(saved.get("report_json")))
        lines.append("latest_json: {0}".format(saved.get("latest_json")))
    return "\n".join(lines)
