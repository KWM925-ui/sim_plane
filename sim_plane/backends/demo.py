import math
import time

from sim_plane.backends.base import Backend


class DemoBackend(Backend):
    name = "demo"

    def validate_environment(self, scenario=None):
        return []

    def run(self, scenario, sink):
        update_hz = float(scenario["update_hz"])
        dt = 1.0 / update_hz
        duration_s = float(scenario["duration_s"])
        target_altitude_m = float(scenario["target_altitude_m"])
        realtime_factor = max(float(scenario.get("realtime_factor", 4.0)), 0.0)
        waypoints = scenario.get("waypoints", [])

        sink.emit_event("info", "demo backend booted", {"backend": self.name})

        telemetry_count = 0
        max_altitude_m = 0.0
        max_speed_mps = 0.0
        reached_target_altitude = False
        mode = "INIT"
        phase = "boot"

        mission_start_t = 5.0
        mission_end_t = max(mission_start_t + 1.0, duration_s - 4.0)

        current_wp = 0
        prev_phase = None

        t = 0.0
        while t <= duration_s + 1e-9:
            if t < 2.0:
                phase = "boot"
                mode = "INIT"
                armed = False
                x = 0.0
                y = 0.0
                altitude = 0.0
            elif t < 3.0:
                phase = "arm"
                mode = "STANDBY"
                armed = True
                x = 0.0
                y = 0.0
                altitude = 0.0
            elif t < mission_start_t:
                phase = "takeoff"
                mode = "TAKEOFF"
                armed = True
                climb_progress = (t - 3.0) / max(mission_start_t - 3.0, 1e-6)
                altitude = target_altitude_m * min(max(climb_progress, 0.0), 1.0)
                x = 0.0
                y = 0.0
            elif t < mission_end_t:
                phase = "mission"
                mode = "OFFBOARD"
                armed = True
                altitude = target_altitude_m
                x, y, current_wp = interpolate_path(
                    t,
                    mission_start_t,
                    mission_end_t,
                    waypoints,
                    current_wp,
                )
            else:
                phase = "land"
                mode = "LAND"
                armed = True
                landing_progress = (t - mission_end_t) / max(duration_s - mission_end_t, 1e-6)
                altitude = target_altitude_m * max(0.0, 1.0 - landing_progress)
                x = 0.0
                y = 0.0

            heading_deg = (math.degrees(math.atan2(y + 1e-6, x + 1e-6)) + 360.0) % 360.0
            speed_mps = compute_speed(phase, target_altitude_m, duration_s)
            battery_pct = max(18.0, 100.0 - (t / max(duration_s, 1e-6)) * 62.0)
            max_altitude_m = max(max_altitude_m, altitude)
            max_speed_mps = max(max_speed_mps, speed_mps)
            reached_target_altitude = reached_target_altitude or altitude >= target_altitude_m * 0.95

            if phase != prev_phase:
                sink.emit_event("info", "phase transition", {"phase": phase, "t": round(t, 2)})
                prev_phase = phase

            sample = {
                "t": round(t, 3),
                "phase": phase,
                "mode": mode,
                "armed": armed,
                "position": {
                    "x_m": round(x, 3),
                    "y_m": round(y, 3),
                    "z_m": round(-altitude, 3),
                },
                "altitude_m": round(altitude, 3),
                "speed_mps": round(speed_mps, 3),
                "battery_pct": round(battery_pct, 2),
                "heading_deg": round(heading_deg, 2),
            }
            sink.emit_telemetry(sample)
            telemetry_count += 1

            if realtime_factor > 0.0:
                time.sleep(dt / realtime_factor)
            t += dt

        sink.emit_event("info", "demo backend finished", {"backend": self.name})

        verdict = "passed" if reached_target_altitude else "failed"
        return {
            "status": verdict,
            "backend": self.name,
            "vehicle": scenario["vehicle"],
            "scenario_name": scenario["name"],
            "metrics": {
                "telemetry_count": telemetry_count,
                "max_altitude_m": round(max_altitude_m, 3),
                "max_speed_mps": round(max_speed_mps, 3),
                "target_altitude_reached": reached_target_altitude,
                "duration_s": duration_s,
            },
            "notes": [
                "This is the built-in demo backend.",
                "It validates the platform loop, artifact flow, and visualization without requiring PX4 to be installed yet.",
            ],
        }


def compute_speed(phase, target_altitude_m, duration_s):
    if phase == "takeoff":
        return max(1.5, target_altitude_m / max(duration_s, 1.0) * 4.0)
    if phase == "mission":
        return 6.0
    if phase == "land":
        return 2.0
    return 0.4


def interpolate_path(t, start_t, end_t, waypoints, current_wp):
    if len(waypoints) < 2:
        return 0.0, 0.0, 0

    normalized = (t - start_t) / max(end_t - start_t, 1e-6)
    normalized = min(max(normalized, 0.0), 0.999999)
    segment_count = len(waypoints) - 1
    scaled = normalized * segment_count
    index = min(int(scaled), segment_count - 1)
    local = scaled - index
    start = waypoints[index]
    end = waypoints[index + 1]
    x = start["x"] + (end["x"] - start["x"]) * local
    y = start["y"] + (end["y"] - start["y"]) * local
    return x, y, index
