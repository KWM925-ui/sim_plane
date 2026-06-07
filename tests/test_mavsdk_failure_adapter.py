import unittest

from sim_plane.adapters import validate_algorithm_adapter
from sim_plane.adapters.mavsdk_failure import (
    MAVSDKFailureInjectionAdapter,
    extract_udp_port,
    parse_failure_type,
    parse_failure_unit,
    resolve_mavsdk_system_address,
)


class MAVSDKFailureAdapterTest(unittest.TestCase):
    def test_default_system_address_uses_px4_onboard_port(self):
        self.assertEqual(resolve_mavsdk_system_address({}, {}), "udp://127.0.0.1:14580")

    def test_extract_udp_port_supports_mavsdk_and_pymavlink_formats(self):
        self.assertEqual(extract_udp_port("udp://127.0.0.1:14580"), 14580)
        self.assertEqual(extract_udp_port("udpin:127.0.0.1:14550"), 14550)

    def test_parse_failure_aliases(self):
        self.assertEqual(parse_failure_unit("motor").name, "SYSTEM_MOTOR")
        self.assertEqual(parse_failure_unit("SYSTEM_MOTOR").name, "SYSTEM_MOTOR")
        self.assertEqual(parse_failure_type("off").name, "OFF")
        self.assertEqual(parse_failure_type("OK").name, "OK")

    def test_validate_algorithm_adapter_flags_udp_port_collision(self):
        issues = validate_algorithm_adapter(
            {
                "type": "mavsdk_failure_injection",
                "system_address": "udp://127.0.0.1:14550",
                "failure_unit": "motor",
                "failure_type": "off",
            },
            context={
                "backend": "px4_sih",
                "telemetry_endpoint": "udpin:127.0.0.1:14550",
                "preferred_telemetry_port": 14550,
            },
        )
        self.assertTrue(any("both use UDP port 14550" in issue for issue in issues))

    def test_validate_algorithm_adapter_rejects_unknown_failure_unit(self):
        issues = validate_algorithm_adapter(
            {
                "type": "mavsdk_failure_injection",
                "system_address": "udp://127.0.0.1:14580",
                "failure_unit": "not_a_unit",
                "failure_type": "off",
            },
            context={"telemetry_endpoint": "udpin:127.0.0.1:14550"},
        )
        self.assertTrue(any("Unknown failure_unit" in issue for issue in issues))

    def test_validate_algorithm_adapter_allows_known_failure_contract(self):
        issues = validate_algorithm_adapter(
            {
                "type": "mavsdk_failure_injection",
                "system_address": "udp://127.0.0.1:14580",
                "failure_unit": "motor",
                "failure_type": "off",
                "reset_failure_type": "ok",
            },
            context={
                "backend": "px4_sih",
                "telemetry_endpoint": "udpin:127.0.0.1:14550",
                "preferred_telemetry_port": 14550,
            },
        )
        self.assertEqual(issues, [])

    def test_shutdown_drone_is_best_effort(self):
        adapter = MAVSDKFailureInjectionAdapter()

        class BrokenDrone:
            def __init__(self):
                self.called = False

            def _stop_mavsdk_server(self):
                self.called = True
                raise RuntimeError("cleanup failed")

        drone = BrokenDrone()
        adapter._shutdown_drone(drone)
        self.assertTrue(drone.called)


if __name__ == "__main__":
    unittest.main()
