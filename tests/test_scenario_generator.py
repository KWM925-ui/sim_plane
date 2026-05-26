import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from sim_plane.cli import main
from sim_plane.scenario_generator import (
    build_custom_algorithm_scenario,
    write_scenario_file,
)


class ScenarioGeneratorTest(unittest.TestCase):
    def test_external_command_generator_defaults_to_px4_sih(self):
        scenario, output_path = build_custom_algorithm_scenario(
            adapter="external_command",
            command="python3 my_controller.py",
            name="my_control_case",
        )

        self.assertEqual(output_path, Path("/home/coco/sim_plane/scenarios/my_control_case.json"))
        self.assertEqual(scenario["backend"], "px4_sih")
        self.assertEqual(scenario["algorithm_adapter"]["type"], "external_command")
        self.assertEqual(scenario["algorithm_adapter"]["command"], ["python3", "my_controller.py"])
        self.assertEqual(scenario["backend_options"]["success_criteria"], "adapter_takeoff")

    def test_ros_command_generator_custom_topics(self):
        scenario, _ = build_custom_algorithm_scenario(
            adapter="ros_command",
            command="roslaunch my_pkg planner.launch",
            backend="fast_lio_marsim",
            required_subscribed_topics="/odom,/cloud",
            required_published_topics="/cmd",
            launch_rviz=True,
        )

        adapter = scenario["algorithm_adapter"]
        self.assertEqual(scenario["backend"], "fast_lio_marsim")
        self.assertEqual(adapter["command"], ["roslaunch", "my_pkg", "planner.launch"])
        self.assertEqual(adapter["required_subscribed_topics"], ["/odom", "/cloud"])
        self.assertEqual(adapter["required_published_topics"], ["/cmd"])
        self.assertTrue(scenario["backend_options"]["launch_rviz"])
        self.assertTrue(scenario["backend_options"]["fast_lio_launch_rviz"])

    def test_write_scenario_file_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "scenario.json"
            scenario = {"name": "case"}
            write_scenario_file(scenario, output)

            with self.assertRaises(FileExistsError):
                write_scenario_file(scenario, output)

            write_scenario_file({"name": "case2"}, output, force=True)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["name"], "case2")

    def test_cli_generate_scenario_dry_run(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "generate-scenario",
                    "--adapter",
                    "external_command",
                    "--command",
                    "python3 my_controller.py",
                    "--name",
                    "dry_run_case",
                    "--dry-run",
                ]
            )

        self.assertEqual(code, 0)
        scenario = json.loads(stdout.getvalue())
        self.assertEqual(scenario["name"], "dry_run_case")
        self.assertEqual(scenario["algorithm_adapter"]["command"], ["python3", "my_controller.py"])

    def test_cli_generate_scenario_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "my_ros_case.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "generate-scenario",
                        "--adapter",
                        "ros_command",
                        "--backend",
                        "marsim",
                        "--command",
                        "python3 my_ros_node.py",
                        "--name",
                        "my_ros_case",
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            scenario = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(scenario["name"], "my_ros_case")
            self.assertIn("python3 -m sim_plane run", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
