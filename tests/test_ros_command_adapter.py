import signal
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from sim_plane.adapters.base import AdapterError
from sim_plane.adapters.external_command import merge_payload_success
from sim_plane.adapters.ros_command import ROSCommandAdapter, determine_success, wait_for_ros_master, wait_for_topic_bindings


class ROSCommandAdapterSuccessTest(unittest.TestCase):
    def test_payload_success_cannot_override_nonzero_exit(self):
        process_success = determine_success(
            exit_code=7,
            stop_requested=False,
            timed_out=False,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
        )
        self.assertFalse(merge_payload_success(process_success, {"success": True}))

    def test_payload_success_cannot_override_timeout(self):
        process_success = determine_success(
            exit_code=-signal.SIGKILL,
            stop_requested=False,
            timed_out=True,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
        )
        self.assertFalse(merge_payload_success(process_success, {"success": True}))

    def test_payload_false_downgrades_clean_exit(self):
        process_success = determine_success(
            exit_code=0,
            stop_requested=False,
            timed_out=False,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
        )
        self.assertFalse(merge_payload_success(process_success, {"success": False}))

    def test_stop_request_can_be_successful_when_process_exits_by_stop_signal(self):
        process_success = determine_success(
            exit_code=-signal.SIGINT,
            stop_requested=True,
            timed_out=False,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
        )
        self.assertTrue(merge_payload_success(process_success, {}))

    def test_stop_request_uses_configured_stop_signal(self):
        process_success = determine_success(
            exit_code=-signal.SIGTERM,
            stop_requested=True,
            timed_out=False,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
            stop_signal=signal.SIGTERM,
        )
        self.assertTrue(process_success)

        process_success = determine_success(
            exit_code=128 + signal.SIGTERM,
            stop_requested=True,
            timed_out=False,
            success_exit_codes=[0],
            allow_timeout_as_success=False,
            treat_stop_request_as_success=True,
            stop_signal=signal.SIGTERM,
        )
        self.assertTrue(process_success)

    def test_timeout_can_be_successful_when_explicitly_allowed(self):
        process_success = determine_success(
            exit_code=-signal.SIGKILL,
            stop_requested=False,
            timed_out=True,
            success_exit_codes=[0],
            allow_timeout_as_success=True,
            treat_stop_request_as_success=True,
        )
        self.assertTrue(process_success)

    def test_payload_success_must_be_boolean(self):
        for value in ("false", "true", 0, 1):
            with self.subTest(value=value):
                with self.assertRaises(AdapterError):
                    merge_payload_success(True, {"success": value})

    def test_readiness_failure_terminates_started_process(self):
        self._assert_readiness_failure_terminates_started_process(
            wait_for_ros_master=mock.Mock(side_effect=AdapterError("master unavailable")),
            wait_for_topic_bindings=mock.Mock(),
        )

    def test_topic_readiness_failure_terminates_started_process(self):
        self._assert_readiness_failure_terminates_started_process(
            wait_for_ros_master=mock.Mock(),
            wait_for_topic_bindings=mock.Mock(side_effect=AdapterError("topics unavailable")),
        )

    def test_master_readiness_wait_respects_stop_event(self):
        stop_event = threading.Event()
        stop_event.set()
        started = time.time()
        with self.assertRaises(AdapterError):
            wait_for_ros_master("http://127.0.0.1:11311", timeout_s=5.0, stop_event=stop_event)
        self.assertLess(time.time() - started, 0.5)

    def test_topic_readiness_wait_respects_stop_event(self):
        stop_event = threading.Event()
        stop_event.set()
        process = mock.Mock()
        process.poll.return_value = None
        started = time.time()
        with self.assertRaises(AdapterError):
            wait_for_topic_bindings(
                process=process,
                master_uri="http://127.0.0.1:11311",
                required_published_topics=["/cmd"],
                required_subscribed_topics=[],
                timeout_s=5.0,
                stop_event=stop_event,
            )
        self.assertLess(time.time() - started, 0.5)

    def _assert_readiness_failure_terminates_started_process(self, wait_for_ros_master, wait_for_topic_bindings):
        adapter = ROSCommandAdapter()
        sink = mock.Mock()
        sink.artifact_writer = mock.Mock(artifact_dir=Path("/tmp/sim_plane_test_artifact"))
        process = mock.Mock()
        process.pid = 123
        process.poll.return_value = None
        config = {
            "command": ["rosrun", "demo", "node"],
            "shell": False,
            "workdir": None,
            "env": {"ROS_MASTER_URI": "http://127.0.0.1:11311"},
            "result_json": None,
            "setup_paths": [],
            "required_published_topics": [],
            "required_subscribed_topics": [],
            "master_timeout_s": 0.1,
            "ready_timeout_s": 0.1,
            "post_launch_grace_s": 0.0,
            "stop_signal": signal.SIGTERM,
            "stop_wait_timeout_s": 0.1,
            "success_exit_codes": [0],
            "allow_timeout_as_success": False,
            "treat_stop_request_as_success": True,
            "max_runtime_s": 0.1,
        }
        with mock.patch.object(adapter, "validate_environment", return_value=[]), mock.patch(
            "sim_plane.adapters.ros_command.build_runtime_config", return_value=config
        ), mock.patch("sim_plane.adapters.ros_command.subprocess.Popen", return_value=process), mock.patch(
            "sim_plane.adapters.ros_command.start_log_threads"
        ), mock.patch(
            "sim_plane.adapters.ros_command.wait_for_ros_master", wait_for_ros_master
        ), mock.patch(
            "sim_plane.adapters.ros_command.wait_for_topic_bindings", wait_for_topic_bindings
        ), mock.patch(
            "sim_plane.adapters.ros_command.terminate_process"
        ) as terminate_mock:
            with self.assertRaises(AdapterError):
                adapter.run({"type": "ros_command"}, sink, {})

        terminate_mock.assert_called_once_with(
            process,
            sink,
            "ros_algorithm",
            stop_signal=signal.SIGTERM,
            wait_timeout_s=0.1,
        )


if __name__ == "__main__":
    unittest.main()
