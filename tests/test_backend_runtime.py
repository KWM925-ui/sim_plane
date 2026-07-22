import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest import mock

from sim_plane.backends.planner_composition_runtime import (
    stream_estimator_telemetry,
    stream_scene_telemetry,
)
from sim_plane.backends.fast_lio_runtime import parse_aligned_odom_log_event
from sim_plane.backends.ros_runtime import (
    prepare_ros_runtime_env,
    resolve_workspace_dir,
    shutdown_ros_nodes,
)


class ProcessStub:
    def poll(self):
        return None


class SinkStub:
    def __init__(self):
        self.events = []
        self.telemetry = []

    def emit_event(self, level, message, details=None):
        self.events.append((level, message, details or {}))

    def emit_telemetry(self, sample):
        self.telemetry.append(sample)


def planner_config():
    return {
        "duration_s": 2.0,
        "startup_timeout_s": 1.0,
        "goal_reach_tolerance_m": 0.1,
        "goal_settle_speed_mps": 0.25,
        "goal_settle_hold_s": 0.0,
        "target_altitude_m": 1.0,
        "goal": {"x": 1.0, "y": 0.0, "z": 1.0},
        "odom_topic": "/odom",
        "command_topic": "/cmd",
        "pointcloud_topic": "/cloud",
        "launch_rviz": False,
        "marsim_launch_rviz": False,
        "fast_lio_launch_rviz": False,
    }


def goal_sample():
    return {
        "t": 0.2,
        "position": {"x_m": 1.0, "y_m": 0.0, "z_m": -1.0},
        "altitude_m": 1.0,
        "speed_mps": 0.0,
        "position_cmd_count": 2,
        "pointcloud_count": 1,
        "pointcloud_width": 100,
    }


class SharedBackendRuntimeTest(unittest.TestCase):
    def test_aligned_odometry_log_classification_is_shared(self):
        info = parse_aligned_odom_log_event(
            "aligned_odom",
            "stdout",
            "locked initial transform",
        )
        warning = parse_aligned_odom_log_event(
            "aligned_odom",
            "stderr",
            "Traceback: failed",
        )

        self.assertEqual(info["level"], "info")
        self.assertEqual(warning["level"], "warning")

    def test_workspace_resolution_honors_explicit_then_environment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            explicit = root / "explicit"
            fallback = root / "fallback"
            (explicit / "src").mkdir(parents=True)
            (fallback / "src").mkdir(parents=True)

            with mock.patch.dict("os.environ", {"TEST_ROS_WS": str(fallback)}):
                selected = resolve_workspace_dir(
                    explicit,
                    env_var="TEST_ROS_WS",
                    candidates=[],
                )

            self.assertEqual(selected, explicit.resolve())

    def test_ros_runtime_env_uses_artifact_local_logs_and_explicit_master(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact"
            env = prepare_ros_runtime_env(
                {
                    "PATH": "/usr/bin",
                    "ROS_MASTER_URI": "http://127.0.0.1:12555",
                },
                artifact,
            )

            self.assertEqual(env["ROS_MASTER_URI"], "http://127.0.0.1:12555")
            self.assertEqual(Path(env["ROS_HOME"]), artifact.resolve() / "ros_home")
            self.assertEqual(Path(env["ROS_LOG_DIR"]), artifact.resolve() / "ros_logs")

    @mock.patch("sim_plane.backends.ros_runtime.cleanup_live_ros_nodes")
    def test_shutdown_ros_nodes_applies_skip_list(self, cleanup):
        shutdown_ros_nodes(
            {"shutdown_nodes": ["/keep", "/stop"]},
            SinkStub(),
            {},
            skip_nodes=["/keep"],
        )

        cleanup.assert_called_once()
        self.assertEqual(cleanup.call_args.args[0], ["/stop"])

    def test_scene_stream_preserves_goal_and_cloud_metrics(self):
        queue = Queue()
        queue.put(goal_sample())
        sink = SinkStub()

        summary = stream_scene_telemetry(
            planner_config(),
            sink,
            queue,
            ProcessStub(),
            ProcessStub(),
        )

        self.assertTrue(summary["goal_reached"])
        self.assertTrue(summary["pointcloud_seen"])
        self.assertTrue(summary["position_cmd_seen"])
        self.assertTrue(summary["cloud_only"])
        self.assertEqual(summary["max_pointcloud_width"], 100)
        self.assertIn("planner-on-scene odometry received", [item[1] for item in sink.events])

    def test_estimator_stream_preserves_viewer_metrics(self):
        queue = Queue()
        queue.put(goal_sample())
        sink = SinkStub()

        summary = stream_estimator_telemetry(
            planner_config(),
            sink,
            queue,
            ProcessStub(),
            ProcessStub(),
            ProcessStub(),
        )

        self.assertTrue(summary["goal_reached"])
        self.assertFalse(summary["marsim_launch_rviz"])
        self.assertFalse(summary["fast_lio_launch_rviz"])
        self.assertIn("planner-on-estimator odometry received", [item[1] for item in sink.events])


if __name__ == "__main__":
    unittest.main()
