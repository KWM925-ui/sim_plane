import os
import tempfile
import time
import unittest
from pathlib import Path

from sim_plane.console_commands import (
    CONSOLE_COMMANDS,
    CONSOLE_RUN_LOG_OUTPUTS,
    EVIDENCE_META,
    HIDDEN_CLI_COMMANDS,
    WORKFLOW_META,
    ConsoleCommandRunner,
    build_cli_coverage,
    detect_console_outputs,
    list_console_commands,
    sim_plane_subcommand,
    snapshot_console_outputs,
)
from sim_plane.cli import build_parser


def cli_command_names():
    parser = build_parser()
    for action in parser._actions:
        if getattr(action, "choices", None):
            return sorted(action.choices)
    return []


class ConsoleCommandsTest(unittest.TestCase):
    def test_console_commands_have_workflow_evidence_and_exact_cli_mapping(self):
        parser = build_parser()
        ids = set()
        for command in CONSOLE_COMMANDS:
            with self.subTest(command=command["id"]):
                self.assertNotIn(command["id"], ids)
                ids.add(command["id"])
                self.assertIn(command.get("workflow_id"), WORKFLOW_META)
                self.assertIn(command.get("evidence_id"), EVIDENCE_META)
                self.assertTrue(command.get("outputs"), "outputs must tell the user where evidence/logs go")
                self.assertTrue(command.get("description"))
                self.assertTrue(command.get("value"))
                self.assertTrue(command.get("when_to_use"))
                self.assertEqual(command["command"][:3], ["python3", "-m", "sim_plane"])
                self.assertTrue(sim_plane_subcommand(command["command"]))
                parser.parse_args(command["command"][3:])

        rows = list_console_commands()
        for row in rows:
            with self.subTest(row=row["id"]):
                self.assertIn("workflow", row)
                self.assertIn("workflow_goal", row)
                self.assertIn("workflow_order", row)
                self.assertIn("evidence_type", row)
                self.assertIn("freshness", row)
                self.assertIn("concurrency_policy", row)
                self.assertIn(row["cli_command"], cli_command_names())
                self.assertIn(row["cli_command"], row["command_display"])

    def test_console_coverage_marks_parameterized_commands_as_hidden_only_when_not_surfaced(self):
        report = build_cli_coverage(cli_command_names())
        rows = {row["cli_command"]: row for row in report["rows"]}

        self.assertIn("subcommand-level", report["summary"]["scope"])
        self.assertGreater(report["summary"]["fixed_preset_count"], 0)
        self.assertEqual(rows["run-baseline"]["frontend_status"], "fixed_preset")
        self.assertIn("固定前端入口", rows["run-baseline"]["reason"])
        self.assertIn("不是完整参数面", rows["run-baseline"]["reason"])
        self.assertEqual(rows["check-algorithm-ingress"]["frontend_status"], "fixed_preset")
        self.assertEqual(rows["generate-scenario"]["frontend_status"], "hidden")
        self.assertEqual(rows["flight-log-analyze"]["frontend_status"], "hidden")
        for cli_command, reason in HIDDEN_CLI_COMMANDS.items():
            if rows[cli_command]["frontend_status"] == "hidden":
                self.assertEqual(rows[cli_command]["reason"], reason)

    def test_console_command_outputs_are_precise_for_user_facing_catalog(self):
        commands = {command["id"]: command for command in CONSOLE_COMMANDS}

        for command in CONSOLE_COMMANDS:
            with self.subTest(command=command["id"]):
                self.assertNotIn("控制台日志", command["outputs"])

        self.assertEqual(commands["doctor"]["outputs"], CONSOLE_RUN_LOG_OUTPUTS)
        self.assertIn("runs/basic_takeoff_*", commands["autotest_fast"]["outputs"])

    def test_console_presets_match_documented_mainline_choices(self):
        commands = {command["id"]: command for command in CONSOLE_COMMANDS}

        run_suite_command = commands["run_suite_basic"]["command"]
        self.assertIn("--suite", run_suite_command)
        self.assertEqual(
            run_suite_command[run_suite_command.index("--suite") + 1],
            "configs/demo_degradation_suite.json",
        )

        fuzz_command = commands["scenario_fuzz_basic"]["command"]
        self.assertEqual(fuzz_command[fuzz_command.index("--seed") + 1], "20260528")

    def test_console_read_only_buttons_disclose_console_log_writes(self):
        for command in CONSOLE_COMMANDS:
            if command.get("evidence_id") != "read_only":
                continue
            with self.subTest(command=command["id"]):
                self.assertIn("console 日志", command["risk"])
        self.assertIn("console 日志", EVIDENCE_META["read_only"]["freshness"])

    def test_latest_checks_that_write_reports_disclose_report_roots(self):
        for command in CONSOLE_COMMANDS:
            if command.get("evidence_id") != "latest_artifact_check":
                continue
            with self.subTest(command=command["id"]):
                self.assertTrue(any(str(output).startswith("runs/") for output in command["outputs"]))
                self.assertIn("写", command["risk"])

    def test_runner_rewrites_preset_artifact_root_to_current_browser_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            artifact_root = repo_root / "alt_runs"
            runner = ConsoleCommandRunner(run_root=artifact_root / "console_commands", repo_root=repo_root)

            command = runner.get_command("demo_takeoff")

        self.assertEqual(command["command"][command["command"].index("--artifact-root") + 1], "alt_runs")
        self.assertIn("alt_runs/basic_takeoff_*", command["outputs"])
        self.assertIn("--artifact-root alt_runs", command["command_display"])

    def test_runner_rewrites_report_root_to_current_browser_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            artifact_root = repo_root / "alt_runs"
            runner = ConsoleCommandRunner(run_root=artifact_root / "console_commands", repo_root=repo_root)

            command = runner.get_command("platform_health")

        self.assertEqual(command["command"][command["command"].index("--artifact-root") + 1], "alt_runs")
        self.assertEqual(command["command"][command["command"].index("--report-root") + 1], "alt_runs/platform_health")
        self.assertIn("alt_runs/platform_health/", command["outputs"])
        self.assertIn("--report-root alt_runs/platform_health", command["command_display"])

    def test_runner_rewrites_autotest_report_root_to_current_browser_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            artifact_root = repo_root / "alt_runs"
            runner = ConsoleCommandRunner(run_root=artifact_root / "console_commands", repo_root=repo_root)

            command = runner.get_command("autotest_fast")

        self.assertEqual(command["command"][command["command"].index("--artifact-root") + 1], "alt_runs")
        self.assertEqual(command["command"][command["command"].index("--report-root") + 1], "alt_runs/autotest")
        self.assertIn("alt_runs/autotest/", command["outputs"])

    def test_runner_records_evidence_metadata_for_started_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            run_root = Path(tmpdir) / "runs"
            runner = ConsoleCommandRunner(
                run_root=run_root,
                repo_root=Path(tmpdir),
                commands=[
                    {
                        "id": "echo_probe",
                        "workflow_id": "fresh_run",
                        "evidence_id": "fresh_artifact",
                        "category": "test",
                        "title": "Echo Probe",
                        "risk": "test",
                        "duration_hint": "fast",
                        "command": ["python3", "-c", "print('ok')"],
                        "description": "test",
                        "value": "test",
                        "when_to_use": "test",
                        "outputs": ["控制台日志"],
                    }
                ],
            )

            started = runner.start("echo_probe")
            deadline = time.time() + 5
            record = started
            while time.time() < deadline:
                record = runner.get_run(started["run_id"])
                if record["status"] != "running":
                    break
                time.sleep(0.05)

            self.assertEqual(record["status"], "passed")
            self.assertEqual(record["workflow"], "2 Fresh 运行")
            self.assertEqual(record["evidence_type"], "Fresh 运行证据")
            self.assertIn("会重新跑场景", record["freshness"])
            self.assertIn("不要同时点 hygiene", record["concurrency_policy"])

    def test_runner_only_reports_outputs_created_or_updated_by_this_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            run_root = repo_root / "console_runs"
            output_path = repo_root / "runs" / "probe.txt"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("old\n", encoding="utf-8")
            runner = ConsoleCommandRunner(
                run_root=run_root,
                repo_root=repo_root,
                commands=[
                    {
                        "id": "no_output",
                        "workflow_id": "fresh_run",
                        "evidence_id": "fresh_artifact",
                        "category": "test",
                        "title": "No Output",
                        "risk": "test",
                        "duration_hint": "fast",
                        "command": ["python3", "-c", "print('ok')"],
                        "description": "test",
                        "value": "test",
                        "when_to_use": "test",
                        "outputs": ["runs/probe.txt"],
                    },
                    {
                        "id": "write_output",
                        "workflow_id": "fresh_run",
                        "evidence_id": "fresh_artifact",
                        "category": "test",
                        "title": "Write Output",
                        "risk": "test",
                        "duration_hint": "fast",
                        "command": ["python3", "-c", "from pathlib import Path; Path('runs/probe.txt').write_text('new\\n')"],
                        "description": "test",
                        "value": "test",
                        "when_to_use": "test",
                        "outputs": ["runs/probe.txt"],
                    },
                ],
            )

            first = runner.start("no_output")
            first_record = self._wait_console_run(runner, first["run_id"])
            self.assertEqual(first_record["status"], "passed")
            self.assertEqual(first_record["detected_outputs"], [])

            second = runner.start("write_output")
            second_record = self._wait_console_run(runner, second["run_id"])
            self.assertEqual(second_record["status"], "passed")
            self.assertEqual(second_record["detected_outputs"], [str(output_path)])

    def test_detect_console_outputs_uses_signature_not_only_mtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            output_path = repo_root / "runs" / "probe.txt"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("old\n", encoding="utf-8")
            snapshot = snapshot_console_outputs(["runs/probe.txt"], repo_root)
            old_mtime_ns = output_path.stat().st_mtime_ns

            output_path.write_text("new content with same timestamp\n", encoding="utf-8")
            os.utime(output_path, ns=(old_mtime_ns, old_mtime_ns))

            detected = detect_console_outputs(["runs/probe.txt"], repo_root, snapshot)

        self.assertEqual(detected, [str(output_path)])

    def _wait_console_run(self, runner, run_id):
        deadline = time.time() + 5
        record = runner.get_run(run_id)
        while time.time() < deadline:
            record = runner.get_run(run_id)
            if record["status"] != "running":
                return record
            time.sleep(0.05)
        return record


if __name__ == "__main__":
    unittest.main()
