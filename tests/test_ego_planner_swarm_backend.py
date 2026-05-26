import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.ego_planner_swarm import (
    EgoPlannerSwarmBackend,
    build_runtime_config,
    parse_ros_log_event,
    prepare_ros_runtime_env,
    shutdown_ros_nodes,
    stop_roslaunch,
)
from sim_plane.runner import apply_runtime_options


class EgoPlannerSwarmBackendTest(unittest.TestCase):
    def test_runtime_config_prefers_explicit_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "ros1_ego_swarm"
            (workspace / "src").mkdir(parents=True)
            (workspace / "devel").mkdir(parents=True)
            (workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")
            scenario = {
                "backend": "ego_planner_swarm",
                "vehicle": "quadrotor",
                "backend_options": {
                    "ros_workspace_dir": str(workspace),
                    "launch_rviz": True,
                },
            }
            config = build_runtime_config(scenario)
            self.assertEqual(config["workspace_dir"], workspace.resolve())
            self.assertTrue(config["launch_rviz"])

    def test_runtime_options_merge_ros_overrides(self):
        scenario = {
            "backend": "ego_planner_swarm",
            "vehicle": "quadrotor",
            "backend_options": {},
        }
        merged = apply_runtime_options(
            scenario,
            {
                "launch_rviz": True,
                "ros_workspace_dir": "/tmp/ros1_ego_swarm",
            },
        )
        self.assertTrue(merged["backend_options"]["launch_rviz"])
        self.assertEqual(merged["backend_options"]["ros_workspace_dir"], "/tmp/ros1_ego_swarm")

    def test_validate_environment_reports_missing_workspace(self):
        backend = EgoPlannerSwarmBackend()
        with mock.patch("sim_plane.backends.ego_planner_swarm.DEFAULT_WORKSPACE_CANDIDATES", []):
            issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("workspace" in issue.lower() for issue in issues))

    def test_stop_roslaunch_prefers_parent_sigint(self):
        sink = mock.Mock()
        process = mock.Mock()
        process.pid = 4321
        process.poll.return_value = None
        with mock.patch("sim_plane.backends.ego_planner_swarm.os.killpg") as killpg:
            stopped = stop_roslaunch(process, sink, "ego_swarm", wait_timeout_s=3.0)
        self.assertTrue(stopped)
        killpg.assert_called_once()
        process.wait.assert_called_once_with(timeout=3.0)

    def test_shutdown_ros_nodes_skips_excluded_nodes(self):
        sink = mock.Mock()
        config = {"shutdown_nodes": ["/random_forest", "/drone_0_pcl_render_node"]}
        with mock.patch(
            "sim_plane.backends.ego_planner_swarm.subprocess.check_output",
            return_value="/random_forest\n/drone_0_pcl_render_node\n",
        ), mock.patch("sim_plane.backends.ego_planner_swarm.subprocess.run") as run_mock, mock.patch(
            "sim_plane.backends.ego_planner_swarm.time.sleep"
        ):
            shutdown_ros_nodes(config, sink, env={}, skip_nodes={"/drone_0_pcl_render_node"})
        run_mock.assert_called_once()
        command = run_mock.call_args[0][0]
        self.assertEqual(command, ["rosnode", "kill", "/random_forest"])

    def test_prepare_ros_runtime_env_isolates_ros_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir) / "artifact"
            env = prepare_ros_runtime_env({"PATH": "/usr/bin"}, artifact_dir)
            self.assertEqual(env["PATH"], "/usr/bin")
            self.assertEqual(env["ROS_HOME"], str(artifact_dir / "ros_home"))
            self.assertEqual(env["ROS_LOG_DIR"], str(artifact_dir / "ros_logs"))
            self.assertEqual(env["ROS_HOSTNAME"], "127.0.0.1")
            self.assertEqual(env["ROS_IP"], "127.0.0.1")
            self.assertTrue((artifact_dir / "ros_home").is_dir())
            self.assertTrue((artifact_dir / "ros_logs").is_dir())

    def test_parse_retryable_planner_chatter_is_info(self):
        event = parse_ros_log_event(
            "ego_swarm_stderr",
            "stderr",
            "[ERROR] [123.0]: Ran out of pool, index=-1 62 59",
        )
        self.assertEqual(event["level"], "info")

    def test_parse_emergency_stop_safety_transition_stays_warning(self):
        event = parse_ros_log_event(
            "ego_swarm_stdout",
            "stdout",
            "[SAFETY]: from EXEC_TRAJ to EMERGENCY_STOP",
        )
        self.assertEqual(event["level"], "warning")


if __name__ == "__main__":
    unittest.main()
