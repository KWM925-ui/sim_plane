#!/usr/bin/env python3
import argparse
import copy
import math
import os
import time
import xmlrpc.client
from urllib.parse import urlparse

import numpy as np
import rospy
from nav_msgs.msg import Odometry
from tf.transformations import quaternion_from_matrix, quaternion_matrix


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Align one odometry stream onto a reference world frame")
    parser.add_argument("--source-odom-topic", required=True)
    parser.add_argument("--reference-odom-topic", required=True)
    parser.add_argument("--output-topic", required=True)
    parser.add_argument("--frame-id", default="world")
    parser.add_argument("--child-frame-id", default="body")
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
            code, _, _ = proxy.getSystemState("/sim_plane_fast_lio_world_odom")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("Timed out waiting for ROS master at {0}".format(master_uri))


def pose_to_matrix(pose):
    matrix = quaternion_matrix(
        [
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ]
    )
    matrix[0, 3] = pose.position.x
    matrix[1, 3] = pose.position.y
    matrix[2, 3] = pose.position.z
    return matrix


def vector_rotate(rotation, vector):
    return rotation.dot(np.array(vector, dtype=float))


class OdomAligner:
    def __init__(self, args):
        self.args = args
        self.publisher = rospy.Publisher(args.output_topic, Odometry, queue_size=50)
        self.source_msg = None
        self.reference_msg = None
        self.align_matrix = None
        self.align_rotation = None

    def reference_callback(self, message):
        self.reference_msg = message
        self.try_lock_transform()

    def source_callback(self, message):
        self.source_msg = message
        self.try_lock_transform()
        if self.align_matrix is None:
            return
        aligned = self.align_message(message)
        self.publisher.publish(aligned)

    def try_lock_transform(self):
        if self.align_matrix is not None or self.source_msg is None or self.reference_msg is None:
            return
        source_tf = pose_to_matrix(self.source_msg.pose.pose)
        reference_tf = pose_to_matrix(self.reference_msg.pose.pose)
        self.align_matrix = np.matmul(reference_tf, np.linalg.inv(source_tf))
        self.align_rotation = self.align_matrix[:3, :3]
        dx = float(self.align_matrix[0, 3])
        dy = float(self.align_matrix[1, 3])
        dz = float(self.align_matrix[2, 3])
        yaw_rad = math.atan2(self.align_rotation[1, 0], self.align_rotation[0, 0])
        rospy.loginfo(
            "locked initial transform dx=%.3f dy=%.3f dz=%.3f yaw_deg=%.3f",
            dx,
            dy,
            dz,
            math.degrees(yaw_rad),
        )
        rospy.loginfo("publishing aligned odometry on %s", self.args.output_topic)

    def align_message(self, source_msg):
        output = copy.deepcopy(source_msg)
        aligned_tf = np.matmul(self.align_matrix, pose_to_matrix(source_msg.pose.pose))
        quat = quaternion_from_matrix(aligned_tf)
        output.header.frame_id = self.args.frame_id
        output.child_frame_id = self.args.child_frame_id
        output.pose.pose.position.x = float(aligned_tf[0, 3])
        output.pose.pose.position.y = float(aligned_tf[1, 3])
        output.pose.pose.position.z = float(aligned_tf[2, 3])
        output.pose.pose.orientation.x = float(quat[0])
        output.pose.pose.orientation.y = float(quat[1])
        output.pose.pose.orientation.z = float(quat[2])
        output.pose.pose.orientation.w = float(quat[3])

        linear = vector_rotate(
            self.align_rotation,
            [
                source_msg.twist.twist.linear.x,
                source_msg.twist.twist.linear.y,
                source_msg.twist.twist.linear.z,
            ],
        )
        angular = vector_rotate(
            self.align_rotation,
            [
                source_msg.twist.twist.angular.x,
                source_msg.twist.twist.angular.y,
                source_msg.twist.twist.angular.z,
            ],
        )
        output.twist.twist.linear.x = float(linear[0])
        output.twist.twist.linear.y = float(linear[1])
        output.twist.twist.linear.z = float(linear[2])
        output.twist.twist.angular.x = float(angular[0])
        output.twist.twist.angular.y = float(angular[1])
        output.twist.twist.angular.z = float(angular[2])
        return output


def main(argv=None):
    args = parse_args(argv)
    wait_for_ros_master(args.master_timeout_s)
    rospy.init_node("sim_plane_fast_lio_world_odom", anonymous=False, disable_signals=True)
    aligner = OdomAligner(args)
    rospy.Subscriber(args.reference_odom_topic, Odometry, aligner.reference_callback, queue_size=20)
    rospy.Subscriber(args.source_odom_topic, Odometry, aligner.source_callback, queue_size=50)
    rospy.spin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
