#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import xmlrpc.client
from urllib.parse import urlparse

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import EstimatorStatus, PositionTarget, State
from nav_msgs.msg import Path
from mavros_msgs.srv import CommandBool, SetMode
from quadrotor_msgs.msg import PositionCommand
from std_msgs.msg import String


def parse_bool(value):
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise argparse.ArgumentTypeError("invalid boolean value: {0}".format(value))


def wait_for_ros_master(timeout_s):
    master_uri = os.environ.get("ROS_MASTER_URI", "http://localhost:11311")
    parsed = urlparse(master_uri)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("Invalid ROS_MASTER_URI: {0}".format(master_uri))

    deadline = time.time() + max(timeout_s, 0.1)
    while time.time() < deadline:
        try:
            proxy = xmlrpc.client.ServerProxy(master_uri)
            code, _, _ = proxy.getSystemState("/stage2_integrated_probe")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError("Timed out waiting for ROS master at {0}".format(master_uri))


def wait_until(predicate, timeout_s, rate_hz=20.0):
    deadline = time.time() + max(timeout_s, 0.1)
    rate = rospy.Rate(max(rate_hz, 1.0))
    while time.time() < deadline and not rospy.is_shutdown():
        if predicate():
            return True
        rate.sleep()
    return False


def setpoint_norm(msg):
    norm_value = 0.0
    if not (msg.type_mask & PositionTarget.IGNORE_PX):
        norm_value += abs(float(msg.position.x))
    if not (msg.type_mask & PositionTarget.IGNORE_PY):
        norm_value += abs(float(msg.position.y))
    if not (msg.type_mask & PositionTarget.IGNORE_PZ):
        norm_value += abs(float(msg.position.z))
    if not (msg.type_mask & PositionTarget.IGNORE_VX):
        norm_value += abs(float(msg.velocity.x))
    if not (msg.type_mask & PositionTarget.IGNORE_VY):
        norm_value += abs(float(msg.velocity.y))
    if not (msg.type_mask & PositionTarget.IGNORE_VZ):
        norm_value += abs(float(msg.velocity.z))
    if not (msg.type_mask & PositionTarget.IGNORE_AFX):
        norm_value += abs(float(msg.acceleration_or_force.x))
    if not (msg.type_mask & PositionTarget.IGNORE_AFY):
        norm_value += abs(float(msg.acceleration_or_force.y))
    if not (msg.type_mask & PositionTarget.IGNORE_AFZ):
        norm_value += abs(float(msg.acceleration_or_force.z))
    if not (msg.type_mask & PositionTarget.IGNORE_YAW):
        norm_value += abs(float(msg.yaw))
    if not (msg.type_mask & PositionTarget.IGNORE_YAW_RATE):
        norm_value += abs(float(msg.yaw_rate))
    return norm_value


class ProbeState:
    def __init__(self):
        self.connected = False
        self.current_mode = ""
        self.armed = False
        self.estimator_valid = False
        self.estimator_flags = None
        self.stage2_goal_count = 0
        self.ego_goal_count = 0
        self.ego_cmd_count = 0
        self.bridge_setpoint_count = 0
        self.mavros_setpoint_count = 0
        self.nonzero_bridge_setpoint_count = 0
        self.nonzero_mavros_setpoint_count = 0
        self.phase_label = ""
        self.pre_search_goal = None
        self.search_first_goal = None
        self.search_last_goal = None
        self.search_goal_count = 0
        self.search_goal_observed = False
        self.follow_goal_count = 0
        self.follow_goal_observed = False
        self.hold_goal_count = 0
        self.lost_hold_observed = False
        self.waypoint_count = 0
        self.real_ego_path_observed = False
        self.distinct_goal_count = 0
        self.distinct_ego_cmd_count = 0
        self._last_counted_goal = None
        self._last_counted_cmd = None
        self.mode_changes = 0
        self._last_mode = ""

    def mavros_state_callback(self, msg):
        self.connected = bool(msg.connected)
        self.current_mode = msg.mode
        self.armed = bool(msg.armed)
        if msg.mode != self._last_mode:
            if self._last_mode:
                self.mode_changes += 1
            self._last_mode = msg.mode

    def estimator_callback(self, msg):
        flags = (
            bool(msg.velocity_horiz_status_flag),
            bool(msg.velocity_vert_status_flag),
            bool(msg.pos_horiz_rel_status_flag),
            bool(msg.pos_vert_abs_status_flag),
        )
        self.estimator_flags = flags
        self.estimator_valid = all(flags)

    def stage2_goal_callback(self, _msg):
        point_xyz = (
            float(_msg.pose.position.x),
            float(_msg.pose.position.y),
            float(_msg.pose.position.z),
        )
        self.stage2_goal_count += 1
        if self._count_distinct(point_xyz, "goal"):
            self.distinct_goal_count += 1
        if self.phase_label in ("approach_center", "stop_go_pause", "reacquire_right", "retreat_center", "reacquire_left"):
            self.follow_goal_count += 1
            self.follow_goal_observed = True
        if self.phase_label == "long_loss":
            self.hold_goal_count += 1
            self.lost_hold_observed = True
        if self.phase_label.startswith("search_loss_") or self.phase_label == "long_loss":
            if self.search_first_goal is None:
                self.search_first_goal = point_xyz
            self.search_last_goal = point_xyz
            self.search_goal_count += 1
            if (
                self.search_goal_count >= 2
                and self.search_first_goal is not None
                and self.search_last_goal is not None
                and self._distance(self.search_first_goal, self.search_last_goal) >= 0.35
            ):
                self.search_goal_observed = True
        else:
            self.pre_search_goal = point_xyz
            self.search_first_goal = None
            self.search_last_goal = None
            self.search_goal_count = 0

    def ego_goal_callback(self, _msg):
        self.ego_goal_count += 1

    def ego_cmd_callback(self, _msg):
        point_xyz = (
            float(_msg.position.x),
            float(_msg.position.y),
            float(_msg.position.z),
        )
        self.ego_cmd_count += 1
        if self._count_distinct(point_xyz, "cmd"):
            self.distinct_ego_cmd_count += 1

    def bridge_setpoint_callback(self, msg):
        self.bridge_setpoint_count += 1
        if setpoint_norm(msg) > 1.0e-4:
            self.nonzero_bridge_setpoint_count += 1

    def mavros_setpoint_callback(self, msg):
        self.mavros_setpoint_count += 1
        if setpoint_norm(msg) > 1.0e-4:
            self.nonzero_mavros_setpoint_count += 1

    def phase_callback(self, msg):
        raw_text = msg.data.strip()
        self.phase_label = raw_text
        if raw_text.startswith("label="):
            for part in raw_text.split(";"):
                if part.startswith("label="):
                    self.phase_label = part.split("=", 1)[1].strip()
                    break

    def waypoint_callback(self, msg):
        self.waypoint_count += 1
        if getattr(msg, "poses", None):
            self.real_ego_path_observed = True

    def _distance(self, a_xyz, b_xyz):
        dx = a_xyz[0] - b_xyz[0]
        dy = a_xyz[1] - b_xyz[1]
        dz = a_xyz[2] - b_xyz[2]
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def _count_distinct(self, point_xyz, kind):
        if kind == "goal":
            last_value = self._last_counted_goal
        else:
            last_value = self._last_counted_cmd
        if last_value is None:
            if kind == "goal":
                self._last_counted_goal = point_xyz
            else:
                self._last_counted_cmd = point_xyz
            return True
        if self._distance(point_xyz, last_value) >= 0.25:
            if kind == "goal":
                self._last_counted_goal = point_xyz
            else:
                self._last_counted_cmd = point_xyz
            return True
        return False

    def as_dict(self):
        return {
            "connected": self.connected,
            "current_mode": self.current_mode,
            "armed": self.armed,
            "estimator_valid": self.estimator_valid,
            "estimator_flags": list(self.estimator_flags) if self.estimator_flags is not None else None,
            "stage2_goal_count": self.stage2_goal_count,
            "ego_goal_count": self.ego_goal_count,
            "ego_cmd_count": self.ego_cmd_count,
            "bridge_setpoint_count": self.bridge_setpoint_count,
            "mavros_setpoint_count": self.mavros_setpoint_count,
            "nonzero_bridge_setpoint_count": self.nonzero_bridge_setpoint_count,
            "nonzero_mavros_setpoint_count": self.nonzero_mavros_setpoint_count,
            "phase_label": self.phase_label,
            "search_goal_count": self.search_goal_count,
            "search_goal_observed": self.search_goal_observed,
            "follow_goal_count": self.follow_goal_count,
            "follow_goal_observed": self.follow_goal_observed,
            "hold_goal_count": self.hold_goal_count,
            "lost_hold_observed": self.lost_hold_observed,
            "waypoint_count": self.waypoint_count,
            "real_ego_path_observed": self.real_ego_path_observed,
            "distinct_goal_count": self.distinct_goal_count,
            "distinct_ego_cmd_count": self.distinct_ego_cmd_count,
            "mode_changes": self.mode_changes,
        }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Probe managed Stage2 integrated readiness and observe gate-owned OFFBOARD.")
    parser.add_argument("--master-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-connected-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-estimator-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-goal-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-command-timeout-s", type=float, default=20.0)
    parser.add_argument("--mode-timeout-s", type=float, default=15.0)
    parser.add_argument("--arm-timeout-s", type=float, default=10.0)
    parser.add_argument("--cleanup-mode-timeout-s", type=float, default=5.0)
    parser.add_argument("--state-topic", default="/mavros/state")
    parser.add_argument("--estimator-topic", default="/mavros/estimator_status")
    parser.add_argument("--stage2-goal-topic", default="/follow/stage2/goal")
    parser.add_argument("--ego-goal-topic", default="/move_base_simple/goal")
    parser.add_argument("--ego-cmd-topic", default="/follow/stage2/ego_position_cmd")
    parser.add_argument("--bridge-setpoint-topic", default="/follow/stage2/offboard/setpoint")
    parser.add_argument("--mavros-setpoint-topic", default="/mavros/setpoint_raw/local")
    parser.add_argument("--phase-topic", default="/follow/sim/truth_phase")
    parser.add_argument("--ego-waypoint-topic", default="/waypoint_generator/waypoints")
    parser.add_argument("--min-goal-count", type=int, default=2)
    parser.add_argument("--min-command-count", type=int, default=2)
    parser.add_argument("--min-nonzero-setpoint-count", type=int, default=10)
    parser.add_argument("--require-follow-goal-observed", type=parse_bool, default=False)
    parser.add_argument("--require-search-goal-observed", type=parse_bool, default=False)
    parser.add_argument("--require-lost-hold-observed", type=parse_bool, default=False)
    parser.add_argument("--semantic-timeout-s", type=float, default=20.0)
    parser.add_argument("--require-estimator-valid", type=parse_bool, default=True)
    parser.add_argument("--request-arm", type=parse_bool, default=True)
    parser.add_argument("--request-mode", default="OFFBOARD")
    parser.add_argument("--cleanup-mode", default="AUTO.LOITER")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    wait_for_ros_master(args.master_timeout_s)
    rospy.init_node("stage2_integrated_probe", anonymous=True, disable_signals=True)

    state = ProbeState()
    rospy.Subscriber(args.state_topic, State, state.mavros_state_callback, queue_size=20)
    rospy.Subscriber(args.estimator_topic, EstimatorStatus, state.estimator_callback, queue_size=20)
    rospy.Subscriber(args.stage2_goal_topic, PoseStamped, state.stage2_goal_callback, queue_size=20)
    rospy.Subscriber(args.ego_goal_topic, PoseStamped, state.ego_goal_callback, queue_size=20)
    rospy.Subscriber(args.ego_cmd_topic, PositionCommand, state.ego_cmd_callback, queue_size=20)
    rospy.Subscriber(args.bridge_setpoint_topic, PositionTarget, state.bridge_setpoint_callback, queue_size=50)
    rospy.Subscriber(args.mavros_setpoint_topic, PositionTarget, state.mavros_setpoint_callback, queue_size=50)
    rospy.Subscriber(args.phase_topic, String, state.phase_callback, queue_size=50)
    rospy.Subscriber(args.ego_waypoint_topic, Path, state.waypoint_callback, queue_size=20)

    report = {
        "success": False,
        "mode_requested": str(args.request_mode),
        "arm_requested": bool(args.request_arm),
        "offboard_requested": False,
        "arm_command_sent": False,
        "cleanup_mode": str(args.cleanup_mode or ""),
        "cleanup_mode_requested": False,
        "cleanup_mode_reached": False,
        "failure_stage": "",
    }

    try:
        connected_ok = wait_until(lambda: state.connected, args.wait_connected_timeout_s)
        if not connected_ok:
            report["failure_stage"] = "wait_connected"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        estimator_ok = wait_until(
            lambda: (not args.require_estimator_valid) or state.estimator_valid,
            args.wait_estimator_timeout_s,
        )
        if not estimator_ok:
            report["failure_stage"] = "wait_estimator"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        goals_ok = wait_until(
            lambda: state.stage2_goal_count >= args.min_goal_count and state.ego_goal_count >= args.min_goal_count,
            args.wait_goal_timeout_s,
        )
        if not goals_ok:
            report["failure_stage"] = "wait_stage2_goals"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        commands_ok = wait_until(
            lambda: state.ego_cmd_count >= args.min_command_count
            and state.nonzero_bridge_setpoint_count >= args.min_nonzero_setpoint_count
            and state.nonzero_mavros_setpoint_count >= args.min_nonzero_setpoint_count,
            args.wait_command_timeout_s,
        )
        if not commands_ok:
            report["failure_stage"] = "wait_stage2_command_flow"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        semantic_ok = wait_until(
            lambda: (
                (not args.require_follow_goal_observed or state.follow_goal_observed)
                and (not args.require_search_goal_observed or state.search_goal_observed)
                and (not args.require_lost_hold_observed or state.lost_hold_observed)
                and state.real_ego_path_observed
            ),
            args.semantic_timeout_s,
        )
        if not semantic_ok:
            report["failure_stage"] = "wait_stage2_semantics"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        if args.request_arm:
            rospy.wait_for_service("/mavros/cmd/arming", timeout=args.arm_timeout_s)
            arm = rospy.ServiceProxy("/mavros/cmd/arming", CommandBool)
            arm(True)
            report["arm_command_sent"] = True
            armed_ok = wait_until(lambda: state.armed, args.arm_timeout_s)
            if not armed_ok:
                report["failure_stage"] = "wait_arm"
                report.update(state.as_dict())
                print(json.dumps(report, ensure_ascii=False))
                return 1

        offboard_ok = wait_until(lambda: state.current_mode == str(args.request_mode), args.mode_timeout_s)
        report["offboard_mode_reached"] = offboard_ok
        if not offboard_ok:
            report["failure_stage"] = "wait_mode_switch"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        cleanup_mode = str(args.cleanup_mode or "").strip()
        if cleanup_mode and cleanup_mode != str(args.request_mode):
            rospy.wait_for_service("/mavros/set_mode", timeout=args.cleanup_mode_timeout_s)
            set_mode = rospy.ServiceProxy("/mavros/set_mode", SetMode)
            set_mode(base_mode=0, custom_mode=cleanup_mode)
            report["cleanup_mode_requested"] = True
            cleanup_ok = wait_until(lambda: state.current_mode == cleanup_mode, args.cleanup_mode_timeout_s)
            report["cleanup_mode_reached"] = cleanup_ok
            if not cleanup_ok:
                report["failure_stage"] = "wait_cleanup_mode"
                report.update(state.as_dict())
                print(json.dumps(report, ensure_ascii=False))
                return 1

        report["success"] = True
        report["failure_stage"] = ""
        report["gate_owned_offboard_inferred"] = True
        report["search_goal_observed"] = bool(state.search_goal_observed)
        report["follow_goal_observed"] = bool(state.follow_goal_observed)
        report["lost_hold_observed"] = bool(state.lost_hold_observed)
        report["real_ego_path_observed"] = bool(state.real_ego_path_observed)
        report.update(state.as_dict())
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:
        report["failure_stage"] = "exception"
        report["error"] = str(exc)
        report.update(state.as_dict())
        print(json.dumps(report, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
