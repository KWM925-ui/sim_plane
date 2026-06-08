import socket
import unittest

from sim_plane.ros_master import (
    ensure_ros_master_uri,
    is_default_ros_master_uri,
    port_available,
    select_ros_master_uri,
    share_ros_master_uri,
)


class RosMasterSelectionTest(unittest.TestCase):
    def test_select_ros_master_uri_skips_busy_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            busy_port = sock.getsockname()[1]
            uri = select_ros_master_uri(base_port=busy_port, max_offset=20)

        self.assertNotEqual(uri, "http://127.0.0.1:{0}".format(busy_port))
        self.assertTrue(uri.startswith("http://127.0.0.1:"))

    def test_ensure_ros_master_uri_preserves_explicit_value(self):
        env = {"ROS_MASTER_URI": "http://127.0.0.1:12345"}

        uri = ensure_ros_master_uri(env)

        self.assertEqual(uri, "http://127.0.0.1:12345")
        self.assertEqual(env["ROS_MASTER_URI"], "http://127.0.0.1:12345")

    def test_ensure_ros_master_uri_sets_available_local_value(self):
        env = {}

        uri = ensure_ros_master_uri(env)
        port = int(uri.rsplit(":", 1)[1])

        self.assertEqual(env["ROS_MASTER_URI"], uri)
        self.assertTrue(port_available(port))

    def test_ensure_ros_master_uri_replaces_ros_default_port(self):
        env = {"ROS_MASTER_URI": "http://localhost:11311"}

        uri = ensure_ros_master_uri(env)

        self.assertNotEqual(uri, "http://localhost:11311")
        self.assertFalse(is_default_ros_master_uri(uri))

    def test_ensure_ros_master_uri_rejects_malformed_value(self):
        with self.assertRaises(ValueError):
            ensure_ros_master_uri({"ROS_MASTER_URI": "http://localhost:notaport"})

    def test_share_ros_master_uri_sets_one_uri_for_all_default_envs(self):
        first = {"ROS_MASTER_URI": "http://localhost:11311"}
        second = {}
        third = {"ROS_MASTER_URI": "http://127.0.0.1:11311"}

        uri = share_ros_master_uri(first, second, third)

        self.assertEqual(first["ROS_MASTER_URI"], uri)
        self.assertEqual(second["ROS_MASTER_URI"], uri)
        self.assertEqual(third["ROS_MASTER_URI"], uri)
        self.assertFalse(is_default_ros_master_uri(uri))

    def test_share_ros_master_uri_preserves_one_explicit_value(self):
        first = {"ROS_MASTER_URI": "http://127.0.0.1:12345"}
        second = {"ROS_MASTER_URI": "http://localhost:11311"}

        uri = share_ros_master_uri(first, second)

        self.assertEqual(uri, "http://127.0.0.1:12345")
        self.assertEqual(second["ROS_MASTER_URI"], "http://127.0.0.1:12345")

    def test_share_ros_master_uri_rejects_conflicting_explicit_values(self):
        with self.assertRaises(RuntimeError):
            share_ros_master_uri(
                {"ROS_MASTER_URI": "http://127.0.0.1:12345"},
                {"ROS_MASTER_URI": "http://127.0.0.1:12346"},
            )


if __name__ == "__main__":
    unittest.main()
