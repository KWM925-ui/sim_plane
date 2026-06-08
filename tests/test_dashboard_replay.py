import json
import re
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from sim_plane.web import (
    ArtifactRootBrowser,
    DashboardServer,
    compare_artifact_dirs,
    list_complete_artifacts,
    list_suite_reports,
    list_test_surface_reports,
    load_platform_acceptance_latest,
    summarize_artifact_dir,
)


PROXYLESS_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def urlopen_local(url_or_request, timeout=2):
    return PROXYLESS_OPENER.open(url_or_request, timeout=timeout)


def strip_js_literals_and_comments(source):
    result = []
    index = 0
    state = "code"
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                result.extend("  ")
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                result.extend("  ")
                index += 2
                state = "block_comment"
                continue
            if char == "'":
                result.append(" ")
                index += 1
                state = "single"
                continue
            if char == '"':
                result.append(" ")
                index += 1
                state = "double"
                continue
            if char == "`":
                result.append(" ")
                index += 1
                state = "template"
                continue
            result.append(char)
            index += 1
            continue
        if state == "line_comment":
            result.append("\n" if char == "\n" else " ")
            state = "code" if char == "\n" else state
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                result.extend("  ")
                index += 2
                state = "code"
            else:
                result.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if state in {"single", "double", "template"}:
            terminator = {"single": "'", "double": '"', "template": "`"}[state]
            if char == "\\":
                result.extend("  ")
                index += 2
                continue
            result.append("\n" if char == "\n" else " ")
            if char == terminator:
                state = "code"
            index += 1
            continue
    if state != "code":
        raise AssertionError(f"unterminated JavaScript {state}")
    return "".join(result)


def assert_balanced_js_delimiters(test_case, source):
    stripped = strip_js_literals_and_comments(source)
    pairs = {"(": ")", "[": "]", "{": "}"}
    reverse = {value: key for key, value in pairs.items()}
    stack = []
    for index, char in enumerate(stripped):
        if char in pairs:
            stack.append((char, index))
        elif char in reverse:
            test_case.assertTrue(stack, f"unmatched closing delimiter {char!r} at {index}")
            opener, opener_index = stack.pop()
            test_case.assertEqual(
                opener,
                reverse[char],
                f"delimiter {opener!r} at {opener_index} closed by {char!r} at {index}",
            )
    test_case.assertFalse(stack, f"unclosed delimiters: {stack[-5:]}")


def assert_no_duplicate_block_js_bindings(test_case, source):
    stripped = strip_js_literals_and_comments(source)
    token_pattern = re.compile(r"[{}]|\b(?:const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)")
    scopes = [set()]
    for match in token_pattern.finditer(stripped):
        token = match.group(0)
        if token == "{":
            scopes.append(set())
            continue
        if token == "}":
            if len(scopes) > 1:
                scopes.pop()
            continue
        name = match.group(1)
        test_case.assertNotIn(name, scopes[-1], f"duplicate block-scoped JS binding: {name}")
        scopes[-1].add(name)


def write_artifact(root, name, scenario_name, backend, max_altitude, max_speed, points):
    artifact_dir = root / name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "manifest.json").write_text(
        json.dumps(
            {
                "created_at_utc": "2026-05-26T17:00:00Z",
                "backend": backend,
                "scenario_name": scenario_name,
                "vehicle": "quadrotor",
                "artifact_dir": str(artifact_dir),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "scenario.json").write_text(
        json.dumps(
            {
                "name": scenario_name,
                "description": "test scenario",
                "backend": backend,
                "vehicle": "quadrotor",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "result.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "backend": backend,
                "vehicle": "quadrotor",
                "scenario_name": scenario_name,
                "metrics": {
                    "telemetry_count": len(points),
                    "max_altitude_m": max_altitude,
                    "max_speed_mps": max_speed,
                    "target_altitude_reached": True,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "events.jsonl").write_text(
        json.dumps({"level": "info", "message": "ok"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with (artifact_dir / "telemetry.jsonl").open("w", encoding="utf-8") as handle:
        for index, point in enumerate(points):
            handle.write(
                json.dumps(
                    {
                        "t": float(index),
                        "phase": "mission",
                        "mode": "AUTO",
                        "armed": True,
                        "position": {"x_m": point[0], "y_m": point[1], "z_m": -point[2]},
                        "altitude_m": point[2],
                        "speed_mps": max_speed,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return artifact_dir


class DashboardReplayTest(unittest.TestCase):
    def test_dashboard_javascript_static_guard(self):
        app_js = Path(__file__).resolve().parents[1] / "sim_plane" / "static" / "app.js"
        source = app_js.read_text(encoding="utf-8")

        assert_balanced_js_delimiters(self, source)
        assert_no_duplicate_block_js_bindings(self, source)
        self.assertNotIn(
            'const item = document.createElement("div");\n    const item = document.createElement("div");',
            source,
        )
        self.assertIn('.hero-nav a[href="#console"], .hero-nav a[href="#evidence"]', source)

    def test_list_complete_artifacts_and_root_browser(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first = write_artifact(root, "demo_20260526_170000", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            second = write_artifact(root, "demo_20260526_170100", "demo", "demo", 3.0, 1.5, [(0, 0, 0), (2, 0, 2)])
            (root / "incomplete").mkdir()

            rows = list_complete_artifacts(root)
            browser = ArtifactRootBrowser(root)

            self.assertEqual([row["name"] for row in rows], [second.name, first.name])
            self.assertEqual(len(browser.list_artifacts()), 2)
            self.assertEqual(browser.state()["status"], "passed")
            self.assertEqual(browser.meta()["mode"], "browser")
            commands = browser.list_console_commands()
            self.assertTrue(any(command["id"] == "platform_health" for command in commands))
            platform_health = next(command for command in commands if command["id"] == "platform_health")
            self.assertEqual(platform_health["command"][:3], ["python3", "-m", "sim_plane"])
            self.assertIn("platform-health", platform_health["command_display"])

    def test_artifact_summary_includes_optional_px4_ulog_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact = write_artifact(
                root,
                "px4_sih_20260606_120000",
                "px4_sih",
                "px4_sih",
                2.0,
                1.0,
                [(0, 0, 0), (1, 0, 1)],
            )
            ulog_dir = artifact / "px4_ulog"
            ulog_dir.mkdir()
            (ulog_dir / "run.ulg").write_bytes(b"ulog")
            (ulog_dir / "index.json").write_text(
                json.dumps(
                    {
                        "status": "collected",
                        "count": 1,
                        "files": [{"artifact_path": "px4_ulog/run.ulg", "size_bytes": 4}],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            summary = summarize_artifact_dir(artifact, include_events=False, include_telemetry=False)

            self.assertTrue(summary["px4_ulog"]["available"])
            self.assertEqual(summary["px4_ulog"]["status"], "collected")
            self.assertEqual(summary["px4_ulog"]["count"], 1)

    def test_artifact_summary_keeps_older_artifacts_without_px4_ulog_compatible(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact = write_artifact(
                root,
                "demo_20260606_120000",
                "demo",
                "demo",
                2.0,
                1.0,
                [(0, 0, 0), (1, 0, 1)],
            )

            summary = summarize_artifact_dir(artifact, include_events=False, include_telemetry=False)

            self.assertFalse(summary["px4_ulog"]["available"])
            self.assertEqual(summary["px4_ulog"]["status"], "missing")

    def test_console_runner_executes_only_catalog_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_artifact(root, "demo_20260526_170000", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            browser = ArtifactRootBrowser(root)
            browser.console_runner.commands = [
                {
                    "id": "echo_probe",
                    "category": "test",
                    "title": "Echo Probe",
                    "risk": "test",
                    "duration_hint": "fast",
                    "command": ["python3", "-c", "print('console-probe-ok')"],
                    "description": "test",
                    "value": "test",
                    "when_to_use": "test",
                    "outputs": ["log"],
                }
            ]

            started = browser.start_console_command("echo_probe")
            deadline = time.time() + 5
            record = started
            while time.time() < deadline:
                record = browser.get_console_run(started["run_id"])
                if record["status"] != "running":
                    break
                time.sleep(0.05)

            self.assertEqual(record["status"], "passed")
            self.assertIn("console-probe-ok", browser.get_console_log(started["run_id"]))
            with self.assertRaises(KeyError):
                browser.start_console_command("not_in_catalog")

    def test_dashboard_console_api_rejects_unknown_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            write_artifact(root, "demo_20260526_170000", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            browser = ArtifactRootBrowser(root)
            browser.console_runner.commands = [
                {
                    "id": "echo_probe",
                    "category": "test",
                    "title": "Echo Probe",
                    "risk": "test",
                    "duration_hint": "fast",
                    "command": ["python3", "-c", "print('ok')"],
                    "description": "test",
                    "value": "test",
                    "when_to_use": "test",
                    "outputs": ["log"],
                }
            ]
            server = DashboardServer(browser, host="127.0.0.1", port=0)
            server.start()
            try:
                commands = json.loads(
                    urlopen_local(server.url + "/api/console/commands", timeout=2).read().decode("utf-8")
                )
                self.assertEqual(commands["items"][0]["id"], "echo_probe")
                request = urllib.request.Request(
                    server.url + "/api/console/start",
                    data=json.dumps({"id": "missing"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urlopen_local(request, timeout=2)
                self.assertEqual(context.exception.code, 400)
                missing = json.loads(
                    urlopen_local(server.url + "/api/console/run?id=missing", timeout=2).read().decode("utf-8")
                )
                self.assertIn("error", missing)
            finally:
                server.shutdown()

    def test_compare_artifacts_reports_metric_and_trajectory_deltas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            left = write_artifact(root, "left", "demo", "demo", 2.0, 1.0, [(0, 0, 0), (1, 0, 1)])
            right = write_artifact(root, "right", "demo", "demo", 3.0, 1.5, [(0, 0, 0), (2, 0, 2)])

            report = compare_artifact_dirs(left, right)

            self.assertTrue(report["same_scenario"])
            metric_deltas = {row["name"]: row for row in report["metric_deltas"]}
            trajectory_deltas = {row["name"]: row for row in report["trajectory_deltas"]}
            self.assertEqual(metric_deltas["max_altitude_m"]["delta"], 1.0)
            self.assertGreater(trajectory_deltas["distance_m"]["delta"], 0.0)
            self.assertEqual(len(report["left"]["track"]), 2)
            self.assertEqual(len(report["right"]["track"]), 2)

    def test_load_platform_acceptance_latest_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report_root = root / "platform_acceptance"
            report_root.mkdir(parents=True)
            (report_root / "latest_latest.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "selection_mode": "latest",
                        "issues": ["top level note"],
                        "planner_acceptance": {"status": "passed", "issues": ["planner note"]},
                        "rows": [
                            {
                                "name": "px4_sih_headless",
                                "backend": "px4_sih",
                                "status": "passed",
                                "artifact_dir": "runs/new",
                                "reference_artifact_dir": "runs/ref",
                                "metric_regressions": {"telemetry_count": 0},
                                "issues": [],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (report_root / "latest_latest_delta.json").write_text(
                json.dumps(
                    {
                        "changed_rows_count": 1,
                        "status_changed": False,
                        "row_deltas": [
                            {
                                "name": "px4_sih_headless",
                                "changed": True,
                                "changed_metric_names": ["max_altitude_m"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = load_platform_acceptance_latest(root)

            self.assertTrue(report["available"])
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["changed_rows_count"], 1)
            self.assertEqual(report["issues"], ["top level note"])
            self.assertEqual(report["planner_acceptance_issues"], ["planner note"])
            self.assertEqual(report["rows"][0]["name"], "px4_sih_headless")

    def test_list_suite_reports_summarizes_latest_kpi_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifact_dir = write_artifact(
                root,
                "basic_takeoff_dropout_20260528_010101",
                "basic_takeoff_dropout",
                "demo",
                3.0,
                1.0,
                [(0, 0, 0), (1, 0, 1)],
            )
            suite_root = root / "suites"
            suite_root.mkdir(parents=True)
            report_json = suite_root / "latest_demo_degradation_suite.json"
            report_json.write_text(
                json.dumps(
                    {
                        "suite_name": "demo_degradation_suite",
                        "base_scenario": "scenarios/basic_takeoff.json",
                        "status": "passed",
                        "issues": [],
                        "rows": [
                            {
                                "name": "dropout",
                                "status": "passed",
                                "artifact_dir": str(artifact_dir),
                                "metrics": {
                                    "kpi_sensor_dropout_ratio": 0.1,
                                    "kpi_mission_path_error_max_m": 0.2,
                                    "kpi_mission_altitude_mae_m": 0.0,
                                    "kpi_measurement_horizontal_error_max_m": 0.4,
                                },
                            }
                        ],
                        "top_metric_effects": [
                            {
                                "factor": "dropout",
                                "metric": "kpi_sensor_dropout_ratio",
                                "mean_spread": 0.1,
                            }
                        ],
                        "kpi_rankings": {
                            "kpi_sensor_dropout_ratio": {
                                "spread": 0.1,
                                "worst_high": [
                                    {
                                        "name": "dropout",
                                        "status": "passed",
                                        "artifact_dir": str(artifact_dir),
                                        "value": 0.1,
                                    }
                                ],
                                "best_low": [
                                    {
                                        "name": "dropout",
                                        "status": "passed",
                                        "artifact_dir": str(artifact_dir),
                                        "value": 0.1,
                                    }
                                ],
                            }
                        },
                        "saved_report": {
                            "report_json": str(suite_root / "demo_degradation_suite_report" / "report.json")
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            report = list_suite_reports(root)

            self.assertTrue(report["available"])
            self.assertEqual(len(report["items"]), 1)
            suite = report["items"][0]
            self.assertEqual(suite["suite_name"], "demo_degradation_suite")
            self.assertEqual(suite["passed_row_count"], 1)
            self.assertEqual(suite["key_metrics"][0]["kpi_sensor_dropout_ratio"], 0.1)
            self.assertEqual(suite["top_metric_effects"][0]["factor"], "dropout")
            self.assertEqual(suite["kpi_rankings"][0]["metric"], "kpi_sensor_dropout_ratio")

    def test_list_test_surface_reports_summarizes_professional_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            flight_root = root / "flight_log_analysis"
            flight_root.mkdir(parents=True)
            (flight_root / "latest_artifact.json").write_text(
                json.dumps(
                    {
                        "source_type": "artifact",
                        "source": "runs/px4",
                        "status": "passed",
                        "metrics": {
                            "telemetry_count": 10,
                            "max_altitude_m": 3.0,
                            "mode_change_count": 2,
                        },
                        "issues": [],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            fuzz_root = root / "scenario_fuzz"
            fuzz_root.mkdir(parents=True)
            (fuzz_root / "latest_demo_seeded_fuzz_1.json").write_text(
                json.dumps(
                    {
                        "fuzz_name": "demo_seeded_fuzz_1",
                        "profile": "demo_fast",
                        "seed": 1,
                        "status": "passed",
                        "rows": [{"status": "passed"}],
                        "worst_cases": [
                            {
                                "metric": "kpi_sensor_dropout_ratio",
                                "spread": 0.2,
                                "worst": [{"name": "seed_01", "value": 0.2}],
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            exam_root = root / "quadrotor_exam_acceptance"
            exam_root.mkdir(parents=True)
            (exam_root / "latest_latest.json").write_text(
                json.dumps(
                    {
                        "matrix_name": "quadrotor_exam_acceptance",
                        "status": "passed",
                        "summary": {
                            "scene_count": 8,
                            "passed_scene_count": 8,
                            "success_rate": 1.0,
                        },
                        "rows": [{"status": "passed"} for _ in range(8)],
                        "issues": [],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            report = list_test_surface_reports(root)

            self.assertTrue(report["available"])
            surfaces = {item["surface"]: item for item in report["items"]}
            self.assertEqual(surfaces["quadrotor exam"]["key_metrics"]["success_rate"], 1.0)
            self.assertEqual(surfaces["flight log"]["key_metrics"]["telemetry_count"], 10)
            self.assertEqual(surfaces["scenario fuzz"]["profile"], "demo_fast")
            self.assertEqual(surfaces["scenario fuzz"]["worst_cases"][0]["metric"], "kpi_sensor_dropout_ratio")


if __name__ == "__main__":
    unittest.main()
