import unittest
from unittest import mock

from sim_plane.ros_nodes import cleanup_live_ros_nodes


class RosNodesTest(unittest.TestCase):
    def test_cleanup_live_ros_nodes_emits_info_only_when_cleanup_succeeds(self):
        sink = mock.Mock()
        run_result = mock.Mock(returncode=0, stderr="")
        with mock.patch(
            "sim_plane.ros_nodes.subprocess.check_output",
            side_effect=[
                "/stale_a\n/stale_b\n",
                "",
            ],
        ), mock.patch(
            "sim_plane.ros_nodes.subprocess.run",
            return_value=run_result,
        ) as run_mock, mock.patch("sim_plane.ros_nodes.time.sleep"):
            report = cleanup_live_ros_nodes(
                ["/stale_a", "/stale_b"],
                sink,
                env={},
                request_message="requesting cleanup",
                success_message="cleanup complete",
                failure_message="cleanup failed",
            )

        run_mock.assert_called_once_with(
            ["rosnode", "kill", "/stale_a", "/stale_b"],
            env={},
            stdout=mock.ANY,
            stderr=mock.ANY,
            text=True,
        )
        self.assertEqual(report["remaining"], [])
        self.assertEqual(
            sink.emit_event.call_args_list,
            [
                mock.call("info", "requesting cleanup", {"nodes": ["/stale_a", "/stale_b"]}),
                mock.call("info", "cleanup complete", {"nodes": ["/stale_a", "/stale_b"]}),
            ],
        )

    def test_cleanup_live_ros_nodes_warns_when_nodes_remain(self):
        sink = mock.Mock()
        run_result = mock.Mock(returncode=0, stderr="")
        with mock.patch(
            "sim_plane.ros_nodes.subprocess.check_output",
            side_effect=[
                "/stale_a\n/stale_b\n",
                "/stale_b\n",
            ],
        ), mock.patch(
            "sim_plane.ros_nodes.subprocess.run",
            return_value=run_result,
        ), mock.patch("sim_plane.ros_nodes.time.sleep"):
            report = cleanup_live_ros_nodes(
                ["/stale_a", "/stale_b"],
                sink,
                env={},
                request_message="requesting cleanup",
                failure_message="cleanup failed",
            )

        self.assertEqual(report["remaining"], ["/stale_b"])
        self.assertEqual(
            sink.emit_event.call_args_list[-1],
            mock.call(
                "warning",
                "cleanup failed",
                {"nodes": ["/stale_a", "/stale_b"], "remaining_nodes": ["/stale_b"]},
            ),
        )


if __name__ == "__main__":
    unittest.main()
