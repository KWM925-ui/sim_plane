#!/usr/bin/env python3
import argparse
import socket
import sys


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Pick an available local ROS master port.")
    parser.add_argument("--base-port", type=int, default=11611)
    parser.add_argument("--max-offset", type=int, default=200)
    parser.add_argument("--requested-port", type=int)
    args = parser.parse_args()

    if args.requested_port is not None:
        if not port_available(args.requested_port):
            print(
                f"requested ROS master port {args.requested_port} is already in use",
                file=sys.stderr,
            )
            return 2
        print(args.requested_port)
        return 0

    for offset in range(args.max_offset + 1):
        candidate = args.base_port + offset
        if port_available(candidate):
            print(candidate)
            return 0

    print(
        f"no free ROS master port found in range [{args.base_port}, {args.base_port + args.max_offset}]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
