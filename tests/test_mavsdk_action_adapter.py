import asyncio
import unittest

from sim_plane.adapters.base import AdapterError
from sim_plane.adapters import validate_algorithm_adapter
from sim_plane.adapters.mavsdk_action import MAVSDKActionAdapter, extract_udp_port, resolve_mavsdk_system_address


class AsyncStream:
    def __init__(self, samples, repeat_last=False):
        self.samples = list(samples)
        self.repeat_last = repeat_last
        self.last_sample = self.samples[-1] if self.samples else None
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.sleep(0)
        if not self.samples:
            if self.repeat_last and self.last_sample is not None:
                await asyncio.sleep(0.01)
                return self.last_sample
            raise StopAsyncIteration
        self.last_sample = self.samples.pop(0)
        return self.last_sample

    async def aclose(self):
        self.closed = True


class LocalPositionSample:
    def __init__(self, down_m):
        self.position = type("Position", (), {"down_m": down_m})()


class RelativePositionSample:
    def __init__(self, relative_altitude_m):
        self.relative_altitude_m = relative_altitude_m


class FlightModeSample:
    def __init__(self, mode):
        self.mode = mode

    def __str__(self):
        return self.mode


class FakeTelemetry:
    def __init__(self, local_samples, relative_samples, flight_mode_samples=None, repeat_last=False):
        self.local_stream = AsyncStream(local_samples, repeat_last=repeat_last)
        self.relative_stream = AsyncStream(relative_samples, repeat_last=repeat_last)
        self.flight_mode_stream = AsyncStream(flight_mode_samples or [], repeat_last=repeat_last)

    def position_velocity_ned(self):
        return self.local_stream

    def position(self):
        return self.relative_stream

    def flight_mode(self):
        return self.flight_mode_stream


class FakeDrone:
    def __init__(self, local_samples, relative_samples, flight_mode_samples=None, repeat_last=False):
        self.telemetry = FakeTelemetry(
            local_samples,
            relative_samples,
            flight_mode_samples=flight_mode_samples,
            repeat_last=repeat_last,
        )


class RecordingSink:
    def __init__(self):
        self.events = []

    def emit_event(self, level, message, details=None):
        self.events.append((level, message, details or {}))


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

    def test_wait_with_timeout_reports_action_label(self):
        adapter = MAVSDKActionAdapter()

        async def slow_wait():
            await asyncio.sleep(0.05)
            return True

        with self.assertRaises(AdapterError) as context:
            asyncio.run(adapter._wait_with_timeout(slow_wait(), 0.001, "probe wait"))
        self.assertIn("probe wait timed out after", str(context.exception))

    def test_shutdown_drone_is_best_effort(self):
        adapter = MAVSDKActionAdapter()

        class BrokenDrone:
            def __init__(self):
                self.called = False

            def _stop_mavsdk_server(self):
                self.called = True
                raise RuntimeError("cleanup failed")

        drone = BrokenDrone()
        adapter._shutdown_drone(drone)
        self.assertTrue(drone.called)

    def test_takeoff_altitude_accepts_relative_altitude_when_local_ned_lags(self):
        adapter = MAVSDKActionAdapter()
        sink = RecordingSink()
        drone = FakeDrone(
            local_samples=[
                LocalPositionSample(-2.5),
                LocalPositionSample(-3.4),
                LocalPositionSample(-3.58),
            ],
            relative_samples=[
                RelativePositionSample(2.0),
                RelativePositionSample(3.9),
            ],
            flight_mode_samples=[
                FlightModeSample("TAKEOFF"),
            ],
        )

        reached = asyncio.run(adapter._wait_for_takeoff_altitude(drone, 4.0, sink))

        self.assertTrue(reached)
        altitude_events = [event for event in sink.events if event[1] == "algorithm adapter altitude reached"]
        self.assertEqual(altitude_events[-1][2]["altitude_source"], "relative")
        self.assertGreaterEqual(altitude_events[-1][2]["max_relative_altitude_m"], 3.8)

    def test_takeoff_altitude_does_not_accept_local_ned_while_px4_still_taking_off(self):
        adapter = MAVSDKActionAdapter()
        sink = RecordingSink()
        drone = FakeDrone(
            local_samples=[
                LocalPositionSample(-3.9),
            ],
            relative_samples=[
                RelativePositionSample(2.0),
            ],
            flight_mode_samples=[
                FlightModeSample("TAKEOFF"),
            ],
        )

        reached = asyncio.run(adapter._wait_for_takeoff_altitude(drone, 4.0, sink))

        self.assertFalse(reached)
        self.assertFalse([event for event in sink.events if event[1] == "algorithm adapter altitude reached"])

    def test_takeoff_altitude_accepts_local_ned_after_px4_leaves_takeoff_mode(self):
        adapter = MAVSDKActionAdapter()
        sink = RecordingSink()
        drone = FakeDrone(
            local_samples=[
                LocalPositionSample(-3.9),
            ],
            relative_samples=[
                RelativePositionSample(2.0),
            ],
            flight_mode_samples=[
                FlightModeSample("HOLD"),
            ],
        )

        reached = asyncio.run(adapter._wait_for_takeoff_altitude(drone, 4.0, sink))

        self.assertTrue(reached)
        altitude_events = [event for event in sink.events if event[1] == "algorithm adapter altitude reached"]
        self.assertEqual(altitude_events[-1][2]["altitude_source"], "local_ned")
        self.assertEqual(altitude_events[-1][2]["flight_mode"], "HOLD")

    def test_takeoff_altitude_timeout_reports_both_altitude_sources(self):
        adapter = MAVSDKActionAdapter()

        async def wait_for_low_altitudes():
            sink = RecordingSink()
            drone = FakeDrone(
                local_samples=[LocalPositionSample(-1.5), LocalPositionSample(-2.0)],
                relative_samples=[RelativePositionSample(1.2), RelativePositionSample(2.1)],
                repeat_last=True,
            )
            await adapter._wait_for_takeoff_altitude(drone, 4.0, sink)

        with self.assertRaises(AdapterError) as context:
            asyncio.run(
                adapter._wait_with_timeout(
                    wait_for_low_altitudes(),
                    0.05,
                    "MAVSDK takeoff altitude reach",
                )
            )

        message = str(context.exception)
        self.assertIn("max_local_altitude_m=2.0", message)
        self.assertIn("max_relative_altitude_m=2.1", message)

    def test_takeoff_altitude_returns_false_when_all_streams_close_below_threshold(self):
        adapter = MAVSDKActionAdapter()
        sink = RecordingSink()
        drone = FakeDrone(
            local_samples=[LocalPositionSample(-1.5), LocalPositionSample(-2.0)],
            relative_samples=[RelativePositionSample(1.2), RelativePositionSample(2.1)],
        )

        reached = asyncio.run(adapter._wait_for_takeoff_altitude(drone, 4.0, sink))

        self.assertFalse(reached)


if __name__ == "__main__":
    unittest.main()
