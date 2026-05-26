import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.backends.fast_lio_marsim import (
    FastLIOMARSIMBackend,
    build_runtime_config,
    prepare_ros_runtime_env,
    shutdown_ros_nodes,
    stop_roslaunch,
)
from sim_plane.runner import apply_runtime_options


class FastLIOMARSIMBackendTest(unittest.TestCase):
    def test_runtime_config_prefers_explicit_fast_lio_workspace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            marsim_workspace = Path(tmpdir) / "ros1_marsim"
            (marsim_workspace / "src").mkdir(parents=True)
            (marsim_workspace / "devel").mkdir(parents=True)
            (marsim_workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")

            fast_lio_workspace = Path(tmpdir) / "ros1_fast_lio"
            (fast_lio_workspace / "src").mkdir(parents=True)
            (fast_lio_workspace / "devel").mkdir(parents=True)
            (fast_lio_workspace / "devel" / "setup.bash").write_text("", encoding="utf-8")

            scenario = {
                "backend": "fast_lio_marsim",
                "vehicle": "quadrotor",
                "backend_options": {
                    "marsim_workspace_dir": str(marsim_workspace),
                    "fast_lio_workspace_dir": str(fast_lio_workspace),
                    "launch_rviz": True,
                },
            }
            config = build_runtime_config(scenario)
            self.assertEqual(config["marsim_workspace_dir"], marsim_workspace.resolve())
            self.assertEqual(config["fast_lio_workspace_dir"], fast_lio_workspace.resolve())
            self.assertTrue(config["launch_rviz"])

    def test_runtime_options_merge_ros_workspace_override(self):
        scenario = {
            "backend": "fast_lio_marsim",
            "vehicle": "quadrotor",
            "backend_options": {},
        }
        merged = apply_runtime_options(
            scenario,
            {
                "launch_rviz": True,
                "ros_workspace_dir": "/tmp/ros1_fast_lio",
            },
        )
        self.assertTrue(merged["backend_options"]["launch_rviz"])
        self.assertEqual(merged["backend_options"]["ros_workspace_dir"], "/tmp/ros1_fast_lio")

    def test_validate_environment_reports_missing_workspaces(self):
        backend = FastLIOMARSIMBackend()
        with mock.patch("sim_plane.backends.fast_lio_marsim.DEFAULT_MARSIM_WORKSPACE_CANDIDATES", []), mock.patch(
            "sim_plane.backends.fast_lio_marsim.DEFAULT_FAST_LIO_WORKSPACE_CANDIDATES", []
        ):
            issues = backend.validate_environment({"backend_options": {}, "vehicle": "quadrotor"})
        self.assertTrue(any("marsim workspace" in issue.lower() for issue in issues))
        self.assertTrue(any("fast_lio workspace" in issue.lower() for issue in issues))

    def test_stop_roslaunch_prefers_parent_sigint(self):
        sink = mock.Mock()
        process = mock.Mock()
        process.pid = 5678
        process.poll.return_value = None
        with mock.patch("sim_plane.backends.fast_lio_marsim.os.killpg") as killpg:
            stopped = stop_roslaunch(process, sink, "fast_lio", wait_timeout_s=4.0)
        self.assertTrue(stopped)
        killpg.assert_called_once()
        process.wait.assert_called_once_with(timeout=4.0)

    def test_shutdown_ros_nodes_targets_live_nodes_only(self):
        sink = mock.Mock()
        config = {"shutdown_nodes": ["/quad0_pcl_render_node", "/rvizvisualisation"]}
        with mock.patch(
            "sim_plane.backends.fast_lio_marsim.subprocess.check_output",
            return_value="/quad0_pcl_render_node\n",
        ), mock.patch("sim_plane.backends.fast_lio_marsim.subprocess.run") as run_mock, mock.patch(
            "sim_plane.backends.fast_lio_marsim.time.sleep"
        ):
            shutdown_ros_nodes(config, sink, env={})
        run_mock.assert_called_once()
        command = run_mock.call_args[0][0]
        self.assertEqual(command, ["rosnode", "kill", "/quad0_pcl_render_node"])

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


if __name__ == "__main__":
    unittest.main()
