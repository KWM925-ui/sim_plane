import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


class PlatformPathError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlatformPaths:
    home: Path
    package: Path
    configs: Path
    scenarios: Path
    scripts: Path
    baselines: Path
    runs: Path
    ros: Path
    static: Path


def is_platform_home(path):
    root = Path(path)
    return (
        (root / "pyproject.toml").is_file()
        and (root / "sim_plane").is_dir()
        and (root / "configs").is_dir()
        and (root / "scenarios").is_dir()
    )


def discover_platform_home(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if is_platform_home(candidate):
            return candidate
        raise PlatformPathError(
            "explicit sim_plane workspace root is invalid: {0}".format(candidate)
        )
    env_home = os.environ.get("SIM_PLANE_HOME")
    if env_home:
        candidate = Path(env_home).expanduser().resolve()
        if is_platform_home(candidate):
            return candidate
        raise PlatformPathError(
            "SIM_PLANE_HOME does not point to a complete workspace: {0}".format(candidate)
        )

    candidates = []
    package_dir = Path(__file__).resolve().parent
    candidates.extend(package_dir.parents)
    candidates.extend(Path.cwd().resolve().parents)
    candidates.append(Path.cwd().resolve())

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if is_platform_home(resolved):
            return resolved

    raise PlatformPathError(
        "sim_plane workspace root was not found. Run from a complete checkout "
        "or set SIM_PLANE_HOME to the directory containing pyproject.toml, configs/, and scenarios/."
    )


@lru_cache(maxsize=4)
def get_platform_paths(explicit_home=None):
    home = discover_platform_home(explicit_home)
    package = home / "sim_plane"
    return PlatformPaths(
        home=home,
        package=package,
        configs=home / "configs",
        scenarios=home / "scenarios",
        scripts=home / "scripts",
        baselines=home / "baselines",
        runs=home / "runs",
        ros=package / "ros",
        static=package / "static",
    )


def resolve_platform_path(value, home=None):
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return get_platform_paths(home).home / path
