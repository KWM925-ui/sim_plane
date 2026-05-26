#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

import rospy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2

from quadrotor_msgs.msg import PositionCommand


class TemplatePlanner:
    def __init__(self):
        self.odom_topic = os.environ.get("SIM_PLANE_ODOM_TOPIC", "/quad_0/lidar_slam/odom")
        self.pointcloud_topic = os.environ.get("SIM_PLANE_POINTCLOUD_TOPIC", "/quad0_pcl_render_node/cloud")
        self.command_topic = os.environ.get("SIM_PLANE_COMMAND_TOPIC", "/quad_0/planning/pos_cmd")
        self.map_topic = os.environ.get("SIM_PLANE_MAP_TOPIC", "/map_generator/global_cloud")
        self.result_json = os.environ.get("SIM_PLANE_ADAPTER_RESULT_JSON", "")
        self.target_altitude_m = float(os.environ.get("SIM_PLANE_TARGET_ALTITUDE_M", "1.0"))

        self.latest_odom = None
        self.first_odom_wall = None
        self.first_local_cloud_wall = None
        self.first_map_wall = None
        self.published_count = 0
        self.start_wall = time.time()
        self.anchor = None

        self.publisher = rospy.Publisher(self.command_topic, PositionCommand, queue_size=20)
        rospy.Subscriber(self.odom_topic, Odometry, self.odom_callback, queue_size=20)
        rospy.Subscriber(self.pointcloud_topic, PointCloud2, self.local_cloud_callback, queue_size=20)
        if self.map_topic:
            rospy.Subscriber(self.map_topic, PointCloud2, self.map_callback, queue_size=2)

    def odom_callback(self, message):
        self.latest_odom = message
        if self.first_odom_wall is None:
            self.first_odom_wall = time.time()
            pose = message.pose.pose.position
            self.anchor = {
                "x": float(pose.x),
                "y": float(pose.y),
                "z": max(float(pose.z), self.target_altitude_m),
            }

    def local_cloud_callback(self, _message):
        if self.first_local_cloud_wall is None:
            self.first_local_cloud_wall = time.time()

    def map_callback(self, _message):
        if self.first_map_wall is None:
            self.first_map_wall = time.time()

    def ready(self):
        return self.latest_odom is not None and self.first_local_cloud_wall is not None and self.anchor is not None

    def build_target(self, elapsed_s):
        target = dict(self.anchor)
        if elapsed_s < 2.0:
            return target
        if elapsed_s < 6.0:
            target["x"] += 1.5
            return target
        if elapsed_s < 10.0:
            target["x"] += 1.5
            target["y"] += 1.5
            return target
        if elapsed_s < 14.0:
            target["y"] += 1.5
            return target
        return target

    def publish_once(self):
        elapsed_s = time.time() - self.start_wall
        target = self.build_target(elapsed_s)

        command = PositionCommand()
        command.header.stamp = rospy.Time.now()
        command.header.frame_id = "world"
        command.trajectory_id = 0
        command.trajectory_flag = getattr(PositionCommand, "TRAJECTORY_STATUS_READY", 1)

        command.position.x = target["x"]
        command.position.y = target["y"]
        command.position.z = target["z"]
        command.velocity.x = 0.0
        command.velocity.y = 0.0
        command.velocity.z = 0.0
        command.acceleration.x = 0.0
        command.acceleration.y = 0.0
        command.acceleration.z = 0.0
        command.jerk.x = 0.0
        command.jerk.y = 0.0
        command.jerk.z = 0.0
        command.yaw = 0.0
        command.yaw_dot = 0.0
        command.kx[0] = 7.0
        command.kx[1] = 7.0
        command.kx[2] = 6.2
        command.kv[0] = 4.0
        command.kv[1] = 4.0
        command.kv[2] = 4.0

        self.publisher.publish(command)
        self.published_count += 1

    def write_result(self, success):
        if not self.result_json:
            return
        payload = {
            "success": bool(success),
            "metrics": {
                "template_algorithm_ready": self.ready(),
                "template_algorithm_commands_sent": self.published_count,
                "template_algorithm_map_seen": self.first_map_wall is not None,
            },
            "notes": [
                "The repo-local ROS template subscribed odom/cloud/map and published PositionCommand into the MARSIM control chain.",
            ],
        }
        path = Path(self.result_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    rospy.init_node("sim_plane_ros_position_command_template", anonymous=False)
    planner = TemplatePlanner()
    rate = rospy.Rate(30.0)
    success = False
    try:
        wait_deadline = time.time() + 12.0
        while not rospy.is_shutdown() and not planner.ready():
            if time.time() > wait_deadline:
                raise RuntimeError("Timed out waiting for odom/cloud inputs.")
            rate.sleep()

        success = True
        while not rospy.is_shutdown():
            planner.publish_once()
            rate.sleep()
    except (KeyboardInterrupt, rospy.ROSInterruptException):
        success = success and planner.published_count > 0
    finally:
        planner.write_result(success and planner.published_count > 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
