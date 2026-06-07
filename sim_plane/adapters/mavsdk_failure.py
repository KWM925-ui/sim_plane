import asyncio
from urllib.parse import urlparse

from sim_plane.adapters.base import AdapterError, AlgorithmAdapter
from sim_plane.adapters.mavsdk_compat import install_aiogrpc_wrapped_iterator_del_guard

try:
    from mavsdk import System
    from mavsdk.failure import FailureError, FailureType, FailureUnit
except Exception as exc:  # pragma: no cover - exercised through validate_environment
    System = None
    FailureError = Exception
    FailureType = None
    FailureUnit = None
    MAVSDK_FAILURE_IMPORT_ERROR = exc
else:
    MAVSDK_FAILURE_IMPORT_ERROR = None
    install_aiogrpc_wrapped_iterator_del_guard()


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


FAILURE_UNIT_ALIASES = {
    "gyro": "SENSOR_GYRO",
    "accel": "SENSOR_ACCEL",
    "mag": "SENSOR_MAG",
    "baro": "SENSOR_BARO",
    "gps": "SENSOR_GPS",
    "optical_flow": "SENSOR_OPTICAL_FLOW",
    "vio": "SENSOR_VIO",
    "distance_sensor": "SENSOR_DISTANCE_SENSOR",
    "airspeed": "SENSOR_AIRSPEED",
    "battery": "SYSTEM_BATTERY",
    "motor": "SYSTEM_MOTOR",
    "servo": "SYSTEM_SERVO",
    "avoidance": "SYSTEM_AVOIDANCE",
    "rc_signal": "SYSTEM_RC_SIGNAL",
    "mavlink_signal": "SYSTEM_MAVLINK_SIGNAL",
}

FAILURE_TYPE_ALIASES = {
    "ok": "OK",
    "off": "OFF",
    "stuck": "STUCK",
    "garbage": "GARBAGE",
    "wrong": "WRONG",
    "slow": "SLOW",
    "delayed": "DELAYED",
    "intermittent": "INTERMITTENT",
}


def parse_failure_unit(value):
    if FailureUnit is None:
        raise AdapterError("MAVSDK failure module is not importable: {0}".format(MAVSDK_FAILURE_IMPORT_ERROR))
    normalized = str(value or "").strip()
    if not normalized:
        raise AdapterError("failure_unit is required")
    normalized = normalized.upper()
    normalized = FAILURE_UNIT_ALIASES.get(normalized.lower(), normalized)
    try:
        return FailureUnit[normalized]
    except KeyError:
        raise AdapterError("Unknown failure_unit: {0}".format(value))


def parse_failure_type(value):
    if FailureType is None:
        raise AdapterError("MAVSDK failure module is not importable: {0}".format(MAVSDK_FAILURE_IMPORT_ERROR))
    normalized = str(value or "").strip()
    if not normalized:
        raise AdapterError("failure_type is required")
    normalized = normalized.upper()
    normalized = FAILURE_TYPE_ALIASES.get(normalized.lower(), normalized)
    try:
        return FailureType[normalized]
    except KeyError:
        raise AdapterError("Unknown failure_type: {0}".format(value))


def health_to_dict(health):
    if health is None:
        return {}
    return {
        "is_gyrometer_calibration_ok": bool(health.is_gyrometer_calibration_ok),
        "is_accelerometer_calibration_ok": bool(health.is_accelerometer_calibration_ok),
        "is_magnetometer_calibration_ok": bool(health.is_magnetometer_calibration_ok),
        "is_local_position_ok": bool(health.is_local_position_ok),
        "is_global_position_ok": bool(health.is_global_position_ok),
        "is_home_position_ok": bool(health.is_home_position_ok),
        "is_armable": bool(health.is_armable),
    }


def enum_name(value):
    return getattr(value, "name", str(value))


class MAVSDKFailureInjectionAdapter(AlgorithmAdapter):
    name = "mavsdk_failure_injection"
    requires_dedicated_udp_port = True

    def validate_environment(self, spec=None, context=None):
        issues = []
        if System is None:
            issues.append(
                "MAVSDK failure plugin is not importable on this host: {0}".format(
                    MAVSDK_FAILURE_IMPORT_ERROR
                )
            )
        if spec is None:
            return issues
        system_address = resolve_mavsdk_system_address(spec, context)
        if extract_udp_port(system_address) is None:
            issues.append(
                "The MAVSDK failure adapter requires a UDP system_address such as udp://127.0.0.1:14580."
            )
        for key, parser in (("failure_unit", parse_failure_unit), ("failure_type", parse_failure_type)):
            try:
                parser((spec or {}).get(key))
            except AdapterError as exc:
                issues.append(str(exc))
        reset_type = (spec or {}).get("reset_failure_type", "OK")
        if reset_type:
            try:
                parse_failure_type(reset_type)
            except AdapterError as exc:
                issues.append(str(exc))
        return issues

    def run(self, spec, sink, context):
        return asyncio.run(self._run_async(spec or {}, sink, context or {}))

    async def _run_async(self, spec, sink, context):
        if System is None:
            raise AdapterError("MAVSDK failure plugin is not importable: {0}".format(MAVSDK_FAILURE_IMPORT_ERROR))

        system_address = resolve_mavsdk_system_address(spec, context)
        connect_timeout_s = float(spec.get("connect_timeout_s", 15.0))
        ready_timeout_s = float(spec.get("ready_timeout_s", 20.0))
        pre_injection_wait_s = float(spec.get("pre_injection_wait_s", 1.0))
        post_injection_observe_s = float(spec.get("post_injection_observe_s", 2.0))
        reset_after_s = float(spec.get("reset_after_s", 1.0))
        instance = int(spec.get("instance", 0))
        failure_unit = parse_failure_unit(spec.get("failure_unit"))
        failure_type = parse_failure_type(spec.get("failure_type"))
        reset_failure_type = parse_failure_type(spec.get("reset_failure_type", "OK"))
        reset_after_injection = bool(spec.get("reset_after_injection", True))

        sink.emit_event(
            "info",
            "algorithm adapter launch plan",
            {
                "adapter": self.name,
                "system_address": system_address,
                "failure_unit": enum_name(failure_unit),
                "failure_type": enum_name(failure_type),
                "reset_failure_type": enum_name(reset_failure_type),
                "instance": instance,
            },
        )

        drone = System()
        try:
            await drone.connect(system_address=system_address)
            await asyncio.wait_for(self._wait_for_connection(drone, sink), timeout=connect_timeout_s)
            health_before = await asyncio.wait_for(self._wait_for_health_sample(drone), timeout=ready_timeout_s)
            mode_before = await self._sample_flight_mode(drone, timeout_s=ready_timeout_s)
            await asyncio.sleep(pre_injection_wait_s)

            accepted = await self._inject_failure(
                drone,
                sink,
                failure_unit=failure_unit,
                failure_type=failure_type,
                instance=instance,
            )
            await asyncio.sleep(post_injection_observe_s)
            health_after = await self._sample_health(drone, timeout_s=ready_timeout_s)
            mode_after = await self._sample_flight_mode(drone, timeout_s=ready_timeout_s)

            reset_accepted = False
            if reset_after_injection:
                await asyncio.sleep(reset_after_s)
                reset_accepted = await self._inject_failure(
                    drone,
                    sink,
                    failure_unit=failure_unit,
                    failure_type=reset_failure_type,
                    instance=instance,
                    reset=True,
                )

            health_before_dict = health_to_dict(health_before)
            health_after_dict = health_to_dict(health_after)
            health_changed_keys = sorted(
                key for key in set(health_before_dict) | set(health_after_dict)
                if health_before_dict.get(key) != health_after_dict.get(key)
            )

            return {
                "metrics": {
                    "algorithm_adapter_name": self.name,
                    "algorithm_adapter_connected": True,
                    "algorithm_adapter_completed_successfully": bool(accepted and (reset_accepted or not reset_after_injection)),
                    "algorithm_adapter_system_address": system_address,
                    "failure_injection_backend": "px4_mavsdk_failure_plugin",
                    "failure_injection_command": "MAV_CMD_INJECT_FAILURE",
                    "failure_injection_unit": enum_name(failure_unit),
                    "failure_injection_type": enum_name(failure_type),
                    "failure_injection_instance": instance,
                    "failure_injection_accepted": bool(accepted),
                    "failure_injection_reset_type": enum_name(reset_failure_type),
                    "failure_injection_reset_accepted": bool(reset_accepted),
                    "failure_injection_health_changed_count": len(health_changed_keys),
                    "failure_injection_health_changed_keys": health_changed_keys,
                    "failure_injection_mode_before": mode_before,
                    "failure_injection_mode_after": mode_after,
                    "failure_injection_mode_changed": mode_before != mode_after,
                },
                "notes": [
                    "This run uses PX4-native MAV_CMD_INJECT_FAILURE through the MAVSDK failure plugin.",
                    "The first accepted sim-plane surface is intentionally limited to a PX4-supported failure unit/type pair proven on this host.",
                    "Demo backend disturbances are not treated as PX4-native failures.",
                ],
            }
        finally:
            self._shutdown_drone(drone)

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

    async def _wait_for_health_sample(self, drone):
        stream = drone.telemetry.health().__aiter__()
        try:
            return await stream.__anext__()
        except StopAsyncIteration:
            return None
        finally:
            await self._close_stream(stream)

    async def _sample_health(self, drone, timeout_s):
        try:
            return await asyncio.wait_for(self._wait_for_health_sample(drone), timeout=timeout_s)
        except asyncio.TimeoutError:
            return None

    async def _sample_flight_mode(self, drone, timeout_s):
        stream = drone.telemetry.flight_mode().__aiter__()
        try:
            mode = await asyncio.wait_for(stream.__anext__(), timeout=timeout_s)
            return enum_name(mode)
        except (asyncio.TimeoutError, StopAsyncIteration):
            return None
        finally:
            await self._close_stream(stream)

    async def _inject_failure(self, drone, sink, failure_unit, failure_type, instance, reset=False):
        try:
            await drone.failure.inject(failure_unit, failure_type, instance)
        except FailureError as exc:
            raise AdapterError("PX4 failure injection was rejected: {0}".format(exc))
        except Exception as exc:
            raise AdapterError("PX4 failure injection failed: {0}".format(exc))
        sink.emit_event(
            "info",
            "algorithm adapter failure injection accepted",
            {
                "adapter": self.name,
                "reset": bool(reset),
                "failure_unit": enum_name(failure_unit),
                "failure_type": enum_name(failure_type),
                "instance": int(instance),
            },
        )
        return True

    async def _close_stream(self, stream):
        close = getattr(stream, "aclose", None)
        if callable(close):
            await close()

    def _shutdown_drone(self, drone):
        stop = getattr(drone, "_stop_mavsdk_server", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass
