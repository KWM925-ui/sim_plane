#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path

from mavsdk import System


def result_path():
    raw = os.environ.get("SIM_PLANE_ADAPTER_RESULT_JSON", "").strip()
    if not raw:
        return None
    return Path(raw)


def write_result(success, metrics=None, notes=None, error=None):
    path = result_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "success": bool(success),
        "metrics": metrics or {},
        "notes": notes or [],
    }
    if error:
        payload["error"] = str(error)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


async def wait_connected(drone):
    async for state in drone.core.connection_state():
        if state.is_connected:
            return


async def wait_armable(drone):
    async for health in drone.telemetry.health():
        if health.is_armable and health.is_local_position_ok:
            return


async def wait_altitude(drone, target_altitude_m):
    threshold = float(target_altitude_m) * 0.95
    async for sample in drone.telemetry.position_velocity_ned():
        altitude = max(0.0, -float(sample.position.down_m))
        if altitude >= threshold:
            return altitude


async def wait_disarmed(drone):
    async for is_armed in drone.telemetry.armed():
        if not is_armed:
            return


async def main():
    system_address = os.environ.get("SIM_PLANE_SYSTEM_ADDRESS", "udp://127.0.0.1:14580")
    target_altitude_m = float(os.environ.get("SIM_PLANE_TARGET_ALTITUDE_M", "4.0"))
    scenario_name = os.environ.get("SIM_PLANE_SCENARIO_NAME", "unknown")

    drone = System()
    await drone.connect(system_address=system_address)
    await wait_connected(drone)
    await wait_armable(drone)

    await drone.action.set_takeoff_altitude(target_altitude_m)
    await drone.action.arm()
    await drone.action.takeoff()
    reached_altitude = await wait_altitude(drone, target_altitude_m)
    await asyncio.sleep(2.0)
    await drone.action.land()
    await wait_disarmed(drone)

    write_result(
        True,
        metrics={
            "template_connected": True,
            "template_target_altitude_m": target_altitude_m,
            "template_reached_altitude_m": round(float(reached_altitude), 3),
        },
        notes=[
            "This example script is a user-side algorithm template, not part of the built-in simulator backend.",
            "Replace the takeoff/land logic here with your own MAVSDK control loop once you are ready.",
            "Scenario: {0}".format(scenario_name),
        ],
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        write_result(False, error=exc)
        raise
