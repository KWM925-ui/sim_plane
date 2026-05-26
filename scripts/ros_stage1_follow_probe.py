#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import xmlrpc.client
from urllib.parse import urlparse

import rospy
from human_follow_msgs.msg import FollowCommand, FollowState
from mavros_msgs.msg import EstimatorStatus, PositionTarget, State
from mavros_msgs.srv import CommandBool, SetMode


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
            code, _, _ = proxy.getSystemState("/stage1_follow_probe")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError("Timed out waiting for ROS master at {0}".format(master_uri))


def follow_state_name_from_message(msg):
    if msg.state_name:
        return msg.state_name
    return str(msg.state)


class ProbeState:
    def __init__(self):
        self.connected = False
        self.current_mode = ""
        self.armed = False
        self.follow_state_name = ""
        self.follow_state_count = 0
        self.follow_command_count = 0
        self.follow_non_hold_count = 0
        self.follow_valid_command_seen = False
        self.setpoint_count = 0
        self.nonzero_setpoint_count = 0
        self.first_nonzero_setpoint_wall = None
        self.estimator_valid = False
        self.estimator_flags = None

    def mavros_state_callback(self, msg):
        self.connected = bool(msg.connected)
        self.current_mode = msg.mode
        self.armed = bool(msg.armed)

    def follow_state_callback(self, msg):
        self.follow_state_count += 1
        self.follow_state_name = follow_state_name_from_message(msg)

    def follow_command_callback(self, msg):
        self.follow_command_count += 1
        is_non_hold = bool(msg.valid) and str(msg.mode) != "hold"
        if is_non_hold:
            self.follow_valid_command_seen = True
            self.follow_non_hold_count += 1

    def setpoint_callback(self, msg):
        self.setpoint_count += 1
        magnitude = abs(float(msg.velocity.x)) + abs(float(msg.velocity.y)) + abs(float(msg.velocity.z))
        magnitude += abs(float(msg.yaw_rate))
        if magnitude > 1.0e-4:
            self.nonzero_setpoint_count += 1
            if self.first_nonzero_setpoint_wall is None:
                self.first_nonzero_setpoint_wall = time.time()

    def estimator_callback(self, msg):
        flags = (
            bool(msg.velocity_horiz_status_flag),
            bool(msg.velocity_vert_status_flag),
            bool(msg.pos_horiz_rel_status_flag),
            bool(msg.pos_vert_abs_status_flag),
        )
        self.estimator_flags = flags
        self.estimator_valid = all(flags)

    def as_dict(self):
        return {
            "connected": self.connected,
            "current_mode": self.current_mode,
            "armed": self.armed,
            "follow_state_name": self.follow_state_name,
            "follow_state_count": self.follow_state_count,
            "follow_command_count": self.follow_command_count,
            "follow_non_hold_count": self.follow_non_hold_count,
            "follow_valid_command_seen": self.follow_valid_command_seen,
            "setpoint_count": self.setpoint_count,
            "nonzero_setpoint_count": self.nonzero_setpoint_count,
            "first_nonzero_setpoint_age_s": (
                round(max(0.0, time.time() - self.first_nonzero_setpoint_wall), 3)
                if self.first_nonzero_setpoint_wall is not None
                else None
            ),
            "estimator_valid": self.estimator_valid,
            "estimator_flags": list(self.estimator_flags) if self.estimator_flags is not None else None,
        }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Probe Stage1 follower readiness and request OFFBOARD.")
    parser.add_argument("--master-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-connected-timeout-s", type=float, default=20.0)
    parser.add_argument("--wait-command-timeout-s", type=float, default=20.0)
    parser.add_argument("--ready-timeout-s", type=float, default=20.0)
    parser.add_argument("--mode-timeout-s", type=float, default=10.0)
    parser.add_argument("--state-topic", default="/mavros/state")
    parser.add_argument("--estimator-topic", default="/mavros/estimator_status")
    parser.add_argument("--follow-state-topic", default="/follow/state")
    parser.add_argument("--follow-command-topic", default="/follow/control/cmd_body")
    parser.add_argument("--setpoint-topic", default="/mavros/setpoint_raw/local")
    parser.add_argument("--setpoint-warmup-count", type=int, default=20)
    parser.add_argument("--setpoint-warmup-min-age-s", type=float, default=0.75)
    parser.add_argument("--require-estimator-valid", type=parse_bool, default=True)
    parser.add_argument("--request-mode", default="OFFBOARD")
    parser.add_argument("--request-arm", type=parse_bool, default=False)
    parser.add_argument("--arm-timeout-s", type=float, default=10.0)
    parser.add_argument("--cleanup-mode", default="AUTO.LOITER")
    parser.add_argument("--cleanup-mode-timeout-s", type=float, default=5.0)
    return parser.parse_args(argv)


def wait_until(predicate, timeout_s, rate_hz=20.0):
    deadline = time.time() + max(timeout_s, 0.1)
    rate = rospy.Rate(max(rate_hz, 1.0))
    while time.time() < deadline and not rospy.is_shutdown():
        if predicate():
            return True
        rate.sleep()
    return False


def main(argv=None):
    args = parse_args(argv)
    wait_for_ros_master(args.master_timeout_s)
    rospy.init_node("stage1_follow_probe", anonymous=True, disable_signals=True)

    state = ProbeState()
    rospy.Subscriber(args.state_topic, State, state.mavros_state_callback, queue_size=20)
    rospy.Subscriber(args.follow_state_topic, FollowState, state.follow_state_callback, queue_size=20)
    rospy.Subscriber(args.follow_command_topic, FollowCommand, state.follow_command_callback, queue_size=20)
    rospy.Subscriber(args.setpoint_topic, PositionTarget, state.setpoint_callback, queue_size=50)
    rospy.Subscriber(args.estimator_topic, EstimatorStatus, state.estimator_callback, queue_size=20)

    report = {
        "success": False,
        "mode_requested": str(args.request_mode),
        "arm_requested": bool(args.request_arm),
        "offboard_requested": False,
        "arm_command_sent": False,
        "failure_stage": "",
    }

    try:
        connected_ok = wait_until(lambda: state.connected, args.wait_connected_timeout_s)
        if not connected_ok:
            report["failure_stage"] = "wait_connected"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        command_ok = wait_until(lambda: state.follow_valid_command_seen, args.wait_command_timeout_s)
        if not command_ok:
            report["failure_stage"] = "wait_follow_command"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        ready_ok = wait_until(
            lambda: (
                (
                    state.nonzero_setpoint_count >= max(args.setpoint_warmup_count, 1)
                    or (
                        state.nonzero_setpoint_count >= max(min(args.setpoint_warmup_count, 10), 1)
                        and state.first_nonzero_setpoint_wall is not None
                        and (time.time() - state.first_nonzero_setpoint_wall) >= max(args.setpoint_warmup_min_age_s, 0.0)
                    )
                )
                and ((not args.require_estimator_valid) or state.estimator_valid)
            ),
            args.ready_timeout_s,
        )
        if not ready_ok:
            report["failure_stage"] = "wait_ready"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1

        rospy.wait_for_service("/mavros/set_mode", timeout=args.mode_timeout_s)
        set_mode = rospy.ServiceProxy("/mavros/set_mode", SetMode)
        pre_request_mode = str(state.current_mode or "")
        set_mode(base_mode=0, custom_mode=str(args.request_mode))
        report["offboard_requested"] = True
        report["offboard_mode_reached"] = False

        mode_ok = wait_until(lambda: state.current_mode == str(args.request_mode), args.mode_timeout_s)
        if not mode_ok:
            report["failure_stage"] = "wait_mode_switch"
            report.update(state.as_dict())
            print(json.dumps(report, ensure_ascii=False))
            return 1
        report["offboard_mode_reached"] = True

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

        cleanup_mode = str(args.cleanup_mode or "").strip()
        cleanup_target_mode = cleanup_mode
        if cleanup_mode.lower() == "previous":
            cleanup_target_mode = pre_request_mode
        report["cleanup_mode"] = cleanup_target_mode
        report["cleanup_mode_requested"] = False
        report["cleanup_mode_reached"] = False
        if cleanup_target_mode and cleanup_target_mode != str(args.request_mode):
            set_mode(base_mode=0, custom_mode=cleanup_target_mode)
            report["cleanup_mode_requested"] = True
            cleanup_ok = wait_until(
                lambda: state.current_mode == cleanup_target_mode,
                args.cleanup_mode_timeout_s,
            )
            report["cleanup_mode_reached"] = cleanup_ok
            if not cleanup_ok:
                report["failure_stage"] = "wait_cleanup_mode"
                report.update(state.as_dict())
                print(json.dumps(report, ensure_ascii=False))
                return 1

        report["success"] = True
        report["failure_stage"] = ""
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
