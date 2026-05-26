import asyncio
from urllib.parse import urlparse

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter

try:
    from mavsdk import System
    from mavsdk.action import ActionError
except Exception as exc:  # pragma: no cover - exercised through validate_environment
    System = None
    ActionError = Exception
    MAVSDK_IMPORT_ERROR = exc
else:
    MAVSDK_IMPORT_ERROR = None


def resolve_mavsdk_system_address(spec, context=None):
    configured = (spec or {}).get("system_address")
    if configured:
        return configured
    default_port = int((spec or {}).get("udp_port", 14580))
    default_host = (spec or {}).get("udp_host", "127.0.0.1")
    return "udp://{0}:{1}".format(default_host, default_port)


def extract_udp_port(address):
    if not address:
        return None
    if "://" in address:
        parsed = urlparse(address)
        return parsed.port
    parts = address.split(":")
    if len(parts) >= 3:
        try:
            return int(parts[-1])
        except ValueError:
            return None
    return None


class MAVSDKActionAdapter(AlgorithmAdapter):
    name = "mavsdk_action_takeoff"
    requires_dedicated_udp_port = True

    def validate_environment(self, spec=None, context=None):
        issues = []
        if System is None:
            issues.append(
                "MAVSDK Python is not importable on this host: {0}".format(MAVSDK_IMPORT_ERROR)
            )
        system_address = resolve_mavsdk_system_address(spec, context)
        if extract_udp_port(system_address) is None:
            issues.append(
                "The MAVSDK action adapter requires a UDP system_address such as udp://127.0.0.1:14580."
            )
        return issues

    def run(self, spec, sink, context):
        return asyncio.run(self._run_async(spec or {}, sink, context or {}))

    async def _run_async(self, spec, sink, context):
        if System is None:
            raise AdapterError("MAVSDK Python is not importable: {0}".format(MAVSDK_IMPORT_ERROR))

        system_address = resolve_mavsdk_system_address(spec, context)
        connect_timeout_s = float(spec.get("connect_timeout_s", 15.0))
        armable_timeout_s = float(spec.get("armable_timeout_s", 20.0))
        takeoff_reach_timeout_s = float(spec.get("takeoff_reach_timeout_s", 15.0))
        hold_after_takeoff_s = float(spec.get("hold_after_takeoff_s", 5.0))
        land_timeout_s = float(spec.get("land_timeout_s", 12.0))
        target_altitude_m = float(
            spec.get("target_altitude_m", context.get("target_altitude_m", 5.0))
        )
        land_at_end = bool(spec.get("land_at_end", True))

        sink.emit_event(
            "info",
            "algorithm adapter launch plan",
            {
                "adapter": self.name,
                "system_address": system_address,
                "target_altitude_m": target_altitude_m,
                "hold_after_takeoff_s": hold_after_takeoff_s,
                "land_at_end": land_at_end,
            },
        )

        drone = System()
        await drone.connect(system_address=system_address)

        await asyncio.wait_for(self._wait_for_connection(drone, sink), timeout=connect_timeout_s)
        armable = await asyncio.wait_for(self._wait_for_armable(drone, sink), timeout=armable_timeout_s)

        await drone.action.set_takeoff_altitude(target_altitude_m)
        sink.emit_event(
            "info",
            "algorithm adapter command",
            {"adapter": self.name, "command": "set_takeoff_altitude", "target_altitude_m": target_altitude_m},
        )
        await drone.action.arm()
        sink.emit_event("info", "algorithm adapter command", {"adapter": self.name, "command": "arm"})
        await drone.action.takeoff()
        sink.emit_event("info", "algorithm adapter command", {"adapter": self.name, "command": "takeoff"})
        reached_target_altitude = await asyncio.wait_for(
            self._wait_for_local_altitude(drone, target_altitude_m, sink),
            timeout=takeoff_reach_timeout_s,
        )
        await asyncio.sleep(hold_after_takeoff_s)

        landed = False
        if land_at_end:
            try:
                await drone.action.land()
                sink.emit_event("info", "algorithm adapter command", {"adapter": self.name, "command": "land"})
                landed = await asyncio.wait_for(
                    self._wait_for_disarmed(drone),
                    timeout=land_timeout_s,
                )
            except ActionError as exc:
                raise AdapterError("MAVSDK action land failed: {0}".format(exc))

        return {
            "metrics": {
                "algorithm_adapter_name": self.name,
                "algorithm_adapter_connected": True,
                "algorithm_adapter_armable": bool(armable),
                "algorithm_adapter_arm_commanded": True,
                "algorithm_adapter_takeoff_commanded": True,
                "algorithm_adapter_target_altitude_reached": bool(reached_target_altitude),
                "algorithm_adapter_land_commanded": land_at_end,
                "algorithm_adapter_landed": landed if land_at_end else False,
                "algorithm_adapter_completed_successfully": True,
                "algorithm_adapter_system_address": system_address,
            },
            "notes": [
                "A repo-local MAVSDK action adapter commanded arm, takeoff, and land through PX4's onboard MAVLink UDP listener.",
                "The local MAVSDK path on this host connects to PX4's onboard UDP listener on 14580 while the telemetry collector stays on a separate GCS-facing UDP port such as 14550.",
            ],
        }

    async def _wait_for_connection(self, drone, sink):
        stream = drone.core.connection_state().__aiter__()
        try:
            while True:
                state = await stream.__anext__()
                if state.is_connected:
                    sink.emit_event(
                        "info",
                        "algorithm adapter connected",
                        {"adapter": self.name, "is_connected": state.is_connected},
                    )
                    return True
        except StopAsyncIteration:
            return False
        finally:
            await self._close_stream(stream)

    async def _wait_for_armable(self, drone, sink):
        stream = drone.telemetry.health().__aiter__()
        try:
            while True:
                health = await stream.__anext__()
                if health.is_armable and health.is_local_position_ok:
                    sink.emit_event(
                        "info",
                        "algorithm adapter health ready",
                        {
                            "adapter": self.name,
                            "is_armable": health.is_armable,
                            "is_local_position_ok": health.is_local_position_ok,
                        },
                    )
                    return True
        except StopAsyncIteration:
            return False
        finally:
            await self._close_stream(stream)

    async def _wait_for_in_air_state(self, drone, expected):
        stream = drone.telemetry.in_air().__aiter__()
        try:
            while True:
                is_in_air = await stream.__anext__()
                if bool(is_in_air) == bool(expected):
                    return True
        except StopAsyncIteration:
            return False
        finally:
            await self._close_stream(stream)

    async def _wait_for_disarmed(self, drone):
        stream = drone.telemetry.armed().__aiter__()
        try:
            while True:
                is_armed = await stream.__anext__()
                if not bool(is_armed):
                    return True
        except StopAsyncIteration:
            return False
        finally:
            await self._close_stream(stream)

    async def _wait_for_local_altitude(self, drone, target_altitude_m, sink):
        threshold_m = float(target_altitude_m) * 0.95
        stream = drone.telemetry.position_velocity_ned().__aiter__()
        try:
            while True:
                sample = await stream.__anext__()
                altitude_m = max(0.0, -float(sample.position.down_m))
                if altitude_m >= threshold_m:
                    sink.emit_event(
                        "info",
                        "algorithm adapter altitude reached",
                        {
                            "adapter": self.name,
                            "altitude_m": round(altitude_m, 3),
                            "target_altitude_m": float(target_altitude_m),
                        },
                    )
                    return True
        except StopAsyncIteration:
            return False
        finally:
            await self._close_stream(stream)

    async def _close_stream(self, stream):
        close = getattr(stream, "aclose", None)
        if callable(close):
            await close()
