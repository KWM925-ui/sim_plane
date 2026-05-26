#!/usr/bin/env python3
import argparse
import json
import os
import time
import xmlrpc.client
from threading import Event
from urllib.parse import urlparse

import rospy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Publish a bounded ROS nav goal after simulator readiness")
    parser.add_argument("--goal-topic", default="/move_base_simple/goal")
    parser.add_argument("--odom-topic", required=True)
    parser.add_argument("--pointcloud-topic", default="")
    parser.add_argument("--command-topic", required=True)
    parser.add_argument("--frame-id", default="world")
    parser.add_argument("--goal-x", type=float, default=5.0)
    parser.add_argument("--goal-y", type=float, default=0.0)
    parser.add_argument("--goal-z", type=float, default=1.0)
    parser.add_argument("--master-timeout-s", type=float, default=20.0)
    parser.add_argument("--odom-timeout-s", type=float, default=25.0)
    parser.add_argument("--pointcloud-timeout-s", type=float, default=15.0)
    parser.add_argument("--command-timeout-s", type=float, default=12.0)
    parser.add_argument("--publish-count", type=int, default=10)
    parser.add_argument("--publish-interval-s", type=float, default=0.5)
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
            code, _, _ = proxy.getSystemState("/sim_plane_goal_publisher")
            if code == 1:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("Timed out waiting for ROS master at {0}".format(master_uri))


def main(argv=None):
    args = parse_args(argv)
    result = {
        "odom_seen": False,
        "pointcloud_seen": False,
        "pos_cmd_seen": False,
        "goal_topic": args.goal_topic,
        "command_topic": args.command_topic,
        "goal": {"x": args.goal_x, "y": args.goal_y, "z": args.goal_z},
    }
    try:
        wait_for_ros_master(args.master_timeout_s)
        rospy.init_node("sim_plane_goal_publisher", anonymous=True, disable_signals=True)
        odom = rospy.wait_for_message(args.odom_topic, Odometry, timeout=args.odom_timeout_s)
        result["odom_seen"] = True
        result["odom_altitude_m"] = round(float(odom.pose.pose.position.z), 3)

        if args.pointcloud_topic:
            cloud = rospy.wait_for_message(args.pointcloud_topic, PointCloud2, timeout=args.pointcloud_timeout_s)
            result["pointcloud_seen"] = True
            result["pointcloud_width"] = int(cloud.width)

        seen_cmd = Event()

        def _cmd_cb(_message):
            seen_cmd.set()

        subscriber = rospy.Subscriber(args.command_topic, rospy.AnyMsg, _cmd_cb, queue_size=20)
        publisher = rospy.Publisher(args.goal_topic, PoseStamped, queue_size=10)
        connect_deadline = time.time() + 5.0
        while publisher.get_num_connections() == 0 and time.time() < connect_deadline:
            time.sleep(0.1)

        message = PoseStamped()
        message.header.frame_id = args.frame_id
        message.pose.orientation.w = 1.0
        message.pose.position.x = args.goal_x
        message.pose.position.y = args.goal_y
        message.pose.position.z = args.goal_z

        for _ in range(max(args.publish_count, 1)):
            message.header.stamp = rospy.Time.now()
            publisher.publish(message)
            if seen_cmd.wait(max(args.publish_interval_s, 0.05)):
                break

        result["pos_cmd_seen"] = seen_cmd.wait(max(args.command_timeout_s, 0.1))
        subscriber.unregister()
    except Exception as exc:
        result["error"] = "{0}: {1}".format(type(exc).__name__, exc)
        print(json.dumps(result, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pos_cmd_seen"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
