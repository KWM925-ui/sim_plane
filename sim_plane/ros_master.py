import socket
from urllib.parse import urlparse


DEFAULT_ROS_MASTER_HOSTS = {"localhost", "127.0.0.1"}
DEFAULT_ROS_MASTER_PORT = 11311


def port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", int(port)))
        except OSError:
            return False
    return True


def select_ros_master_uri(base_port=11611, max_offset=200):
    for offset in range(max_offset + 1):
        candidate = int(base_port) + offset
        if port_available(candidate):
            return "http://127.0.0.1:{0}".format(candidate)
    raise RuntimeError(
        "no free ROS master port found in range [{0}, {1}]".format(
            base_port,
            int(base_port) + int(max_offset),
        )
    )


def ensure_ros_master_uri(env):
    existing = env.get("ROS_MASTER_URI")
    if existing and not _parsed_uri_is_default(parse_ros_master_uri(existing)):
        return existing
    env["ROS_MASTER_URI"] = select_ros_master_uri()
    return env["ROS_MASTER_URI"]


def is_default_ros_master_uri(uri):
    try:
        return _parsed_uri_is_default(parse_ros_master_uri(uri))
    except ValueError:
        return False


def parse_ros_master_uri(uri):
    parsed = urlparse(str(uri))
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid ROS_MASTER_URI {0!r}: {1}".format(uri, exc)) from exc
    if parsed.scheme != "http" or not parsed.hostname or port is None:
        raise ValueError("invalid ROS_MASTER_URI {0!r}: expected http://host:port".format(uri))
    return parsed


def share_ros_master_uri(*envs):
    selected_uri = None
    for env in envs:
        existing = env.get("ROS_MASTER_URI")
        if not existing:
            continue
        parsed = parse_ros_master_uri(existing)
        if _parsed_uri_is_default(parsed):
            continue
        if selected_uri is None:
            selected_uri = existing
        elif existing != selected_uri:
            raise RuntimeError(
                "conflicting explicit ROS_MASTER_URI values: {0!r} != {1!r}".format(
                    selected_uri,
                    existing,
                )
            )

    if selected_uri is None:
        selected_uri = select_ros_master_uri()

    for env in envs:
        env["ROS_MASTER_URI"] = selected_uri
    return selected_uri


def _parsed_uri_is_default(parsed):
    return parsed.hostname in DEFAULT_ROS_MASTER_HOSTS and parsed.port == DEFAULT_ROS_MASTER_PORT
