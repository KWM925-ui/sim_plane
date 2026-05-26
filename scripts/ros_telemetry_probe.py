#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys
import time
import xmlrpc.client
from urllib.parse import urlparse

import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2


def yaw_from_quaternion(x, y, z, w):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return (math.degrees(math.atan2(siny_cosp, cosy_cosp)) + 360.0) % 360.0


class ProbeState:
    def __init__(self, odom_topic, command_topic, pointcloud_topic, sample_hz, target_altitude_m):
        self.odom_topic = odom_topic
        self.command_topic = command_topic
        self.pointcloud_topic = pointcloud_topic
        self.sample_hz = sample_hz
        self.target_altitude_m = target_altitude_m
        self.start_wall = time.time()
        self.latest_odom = None
        self.latest_odom_wall = None
        self.position_cmd_count = 0
        self.latest_command_wall = None
        self.pointcloud_count = 0
        self.latest_pointcloud_wall = None
        self.latest_pointcloud_width = 0

    def odom_callback(self, message):
        self.latest_odom = message
        self.latest_odom_wall = time.time()

    def command_callback(self, _message):
        self.position_cmd_count += 1
        self.latest_command_wall = time.time()

    def pointcloud_callback(self, message):
        self.pointcloud_count += 1
        self.latest_pointcloud_wall = time.time()
        self.latest_pointcloud_width = int(message.width)

    def build_sample(self):
        if self.latest_odom is None:
            return None

        pose = self.latest_odom.pose.pose
        twist = self.latest_odom.twist.twist
        altitude_m = float(pose.position.z)
        speed_mps = math.sqrt(
            float(twist.linear.x) * float(twist.linear.x)
            + float(twist.linear.y) * float(twist.linear.y)
            + float(twist.linear.z) * float(twist.linear.z)
        )
        heading_deg = yaw_from_quaternion(
            float(pose.orientation.x),
            float(pose.orientation.y),
            float(pose.orientation.z),
            float(pose.orientation.w),
        )

        phase = infer_phase(
            altitude_m=altitude_m,
            speed_mps=speed_mps,
            position_cmd_count=self.position_cmd_count,
            target_altitude_m=self.target_altitude_m,
        )
        return {
            "t": round(time.time() - self.start_wall, 3),
            "phase": phase,
            "mode": "ROS_SIM",
            "armed": bool(self.position_cmd_count > 0 or altitude_m > 0.15 or speed_mps > 0.15),
            "position": {
                "x_m": round(float(pose.position.x), 3),
                "y_m": round(float(pose.position.y), 3),
                "z_m": round(-altitude_m, 3),
            },
            "altitude_m": round(altitude_m, 3),
            "speed_mps": round(speed_mps, 3),
            "battery_pct": None,
            "heading_deg": round(heading_deg, 2),
            "position_cmd_count": self.position_cmd_count,
            "pointcloud_count": self.pointcloud_count,
            "pointcloud_width": self.latest_pointcloud_width,
            "odom_age_s": round(time.time() - self.latest_odom_wall, 3) if self.latest_odom_wall is not None else None,
            "command_age_s": round(time.time() - self.latest_command_wall, 3)
            if self.latest_command_wall is not None
            else None,
            "pointcloud_age_s": round(time.time() - self.latest_pointcloud_wall, 3)
            if self.latest_pointcloud_wall is not None
            else None,
        }


def infer_phase(altitude_m, speed_mps, position_cmd_count, target_altitude_m):
    if position_cmd_count == 0 and altitude_m < 0.15:
        return "standby"
    if altitude_m < max(0.6, target_altitude_m * 0.75):
        return "takeoff"
    if speed_mps > 0.15 or position_cmd_count > 0:
        return "mission"
    return "hover"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Emit ROS odometry telemetry as JSON lines")
    parser.add_argument("--odom-topic", required=True)
    parser.add_argument("--command-topic", default="")
    parser.add_argument("--pointcloud-topic", default="")
    parser.add_argument("--sample-hz", type=float, default=5.0)
    parser.add_argument("--target-altitude-m", type=float, default=1.0)
    parser.add_argument("--master-timeout-s", type=float, default=20.0)
    return parser.parse_args(argv)


def wait_for_ros_master(timeout_s):
    master_uri = os.environ.get("ROS_MASTER_URI", "http://localhost:11311")
    parsed = urlparse(master_uri)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("Invalid ROS_MASTER_URI: {0}".format(master_uri))

    deadline = time.time() + max(timeout_s, 0.1)
    while time.time() < deadline:
        try:
            proxy = xmlrpc.client.ServerProxy(master_uri)
            code, _, _ = proxy.getSystemState("/sim_plane_ros_probe")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)

    raise RuntimeError("Timed out waiting for ROS master at {0}".format(master_uri))


def main(argv=None):
    args = parse_args(argv)
    wait_for_ros_master(args.master_timeout_s)
    rospy.init_node("sim_plane_ros_probe", anonymous=True, disable_signals=True)
    state = ProbeState(
        odom_topic=args.odom_topic,
        command_topic=args.command_topic,
        pointcloud_topic=args.pointcloud_topic,
        sample_hz=args.sample_hz,
        target_altitude_m=args.target_altitude_m,
    )
    rospy.Subscriber(args.odom_topic, Odometry, state.odom_callback, queue_size=20)
    if args.command_topic:
        rospy.Subscriber(args.command_topic, rospy.AnyMsg, state.command_callback, queue_size=100)
    if args.pointcloud_topic:
        rospy.Subscriber(args.pointcloud_topic, PointCloud2, state.pointcloud_callback, queue_size=20)

    rate = rospy.Rate(max(args.sample_hz, 1.0))
    try:
        while not rospy.is_shutdown():
            sample = state.build_sample()
            if sample is not None:
                sys.stdout.write(json.dumps(sample, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            rate.sleep()
    except (KeyboardInterrupt, rospy.ROSInterruptException):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
