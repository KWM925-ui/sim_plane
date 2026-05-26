import unittest

from sim_plane.adapters import validate_algorithm_adapter
from sim_plane.adapters.mavsdk_action import extract_udp_port, resolve_mavsdk_system_address


class MAVSDKActionAdapterTest(unittest.TestCase):
    def test_default_system_address_uses_offboard_port(self):
        self.assertEqual(
            resolve_mavsdk_system_address({}, {}),
            "udp://127.0.0.1:14580",
        )

    def test_extract_udp_port_supports_mavsdk_and_pymavlink_formats(self):
        self.assertEqual(extract_udp_port("udpin://0.0.0.0:14540"), 14540)
        self.assertEqual(extract_udp_port("udpin:127.0.0.1:14550"), 14550)

    def test_validate_algorithm_adapter_flags_udp_port_collision(self):
        issues = validate_algorithm_adapter(
            {"type": "mavsdk_action_takeoff", "system_address": "udpin://0.0.0.0:14540"},
            context={"telemetry_endpoint": "udpin:127.0.0.1:14540"},
        )
        self.assertTrue(any("both use UDP port 14540" in issue for issue in issues))
        self.assertTrue(any("keep MAVSDK on PX4's onboard listener 14580" in issue for issue in issues))

    def test_validate_algorithm_adapter_allows_separate_telemetry_port(self):
        issues = validate_algorithm_adapter(
            {"type": "mavsdk_action_takeoff", "system_address": "udp://127.0.0.1:14580"},
            context={"telemetry_endpoint": "udpin:127.0.0.1:14550"},
        )
        self.assertEqual(issues, [])

    def test_validate_algorithm_adapter_prefers_gcs_port_14550(self):
        issues = validate_algorithm_adapter(
            {"type": "mavsdk_action_takeoff", "system_address": "udp://127.0.0.1:14580"},
            context={"backend": "px4_gazebo_classic", "telemetry_endpoint": "udpin:127.0.0.1:14540", "preferred_telemetry_port": 14550},
        )
        self.assertTrue(any("should use UDP port 14550" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
