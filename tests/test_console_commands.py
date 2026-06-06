import tempfile
import time
import unittest
from pathlib import Path

from sim_plane.console_commands import (
    CONSOLE_COMMANDS,
    EVIDENCE_META,
    HIDDEN_CLI_COMMANDS,
    WORKFLOW_META,
    ConsoleCommandRunner,
    build_cli_coverage,
    list_console_commands,
    sim_plane_subcommand,
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

        self.assertEqual(rows["run-baseline"]["frontend_status"], "covered")
        self.assertEqual(rows["check-algorithm-ingress"]["frontend_status"], "covered")
        self.assertEqual(rows["generate-scenario"]["frontend_status"], "hidden")
        self.assertEqual(rows["flight-log-analyze"]["frontend_status"], "hidden")
        for cli_command, reason in HIDDEN_CLI_COMMANDS.items():
            if rows[cli_command]["frontend_status"] == "hidden":
                self.assertEqual(rows[cli_command]["reason"], reason)

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


if __name__ == "__main__":
    unittest.main()
