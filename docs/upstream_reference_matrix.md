# Upstream Reference Matrix

## Goal

This file locks the first upstream reference set for `sim_plane` so future work does not drift into random forks or ad hoc clones.

All external workspaces should stay under:

- `/home/coco/sim_plane_ws`

The canonical clone map lives in:

- [configs/upstreams.json](/home/coco/sim_plane/configs/upstreams.json)

The sync entrypoint lives in:

- [scripts/sync_upstreams.py](/home/coco/sim_plane/scripts/sync_upstreams.py)

## Selection Policy

- Prefer official lab or project repositories.
- Keep the first set small but high value.
- Cover flight stack, planning, simulation, and state estimation references.
- Do not import every interesting repo before the integration queue is clear.

## First Reference Set

### Core

- `PX4/PX4-Autopilot`
  - role: core flight stack and the `px4_sih` backend target
  - why: this is the default live flight-stack contract for the current platform

### ZJU FAST Lab

- `ZJU-FAST-Lab/ego-planner`
  - role: local planning baseline
  - why: direct future target for algorithm integration

- `ZJU-FAST-Lab/ego-planner-swarm`
  - role: swarm planning baseline
  - why: gives a natural future widening path after single-agent baseline work

- `ZJU-FAST-Lab/visPlanner`
  - role: target-tracking planner reference
  - why: high-value frontier planner that now has a managed Ubuntu 20.04 ROS1
    build and an isolated tracking probe path

### HKU MARS Lab

- `hku-mars/MARSIM`
  - role: simulator reference
  - why: directly relevant to the platform's simulation layer and valuable for architecture comparison

- `hku-mars/FAST_LIO`
  - role: state-estimation reference
  - why: important future target for perception and onboard autonomy chains

- `hku-mars/SUPER`
  - role: navigation-stack reference
  - why: strong current frontier algorithm with a managed ROS1 workspace and a
    clean isolated benchmark probe path

### Managed Dependencies

- `Livox-SDK/livox_ros_driver`
  - role: official ROS driver dependency for `FAST_LIO`
  - why: `FAST_LIO` depends on `livox_ros_driver/CustomMsg`, including the upstream `mapping_marsim.launch` path

### Other Strong References

- `HKUST-Aerial-Robotics/Fast-Planner`
  - role: planning reference
  - why: important upstream planner lineage

- `HKUST-Aerial-Robotics/TopoTraj`
  - role: planning reference
  - why: useful topology-aware planning comparison target

- `uzh-rpg/flightmare`
  - role: simulator reference
  - why: high-quality 3D simulation reference, useful when the platform grows beyond lightweight SIH-first scope

- `utiasDSL/gym-pybullet-drones`
  - role: lightweight simulator reference
  - why: useful contrast against heavier stacks

- `ethz-asl/rotors_simulator`
  - role: classic ROS/Gazebo simulator reference
  - why: still useful as a long-standing reference line

- `PegasusSimulator/PegasusSimulator`
  - role: modern simulator reference
  - why: useful as a comparison point for future richer backend design

## Current Integration Order

1. `PX4-Autopilot`
2. `ego-planner-swarm`
3. `MARSIM`
4. `FAST_LIO`
5. `ego-planner`
6. `Fast-Planner`

Why `ego-planner-swarm` first:

- the upstream `ego-planner` README explicitly says `ego-planner-swarm` is more robust and recommended,
- it still supports the single-drone case by setting `drone_id=0`,
- it gives a better first lab-integration target than starting from the older branch.

Why legacy `ego-planner` now comes before `Fast-Planner`:

- `Fast-Planner`'s upstream quick start requires a manual `NLopt v2.7.1`
  install step outside the managed workspace shape,
- legacy `ego-planner` still targets Ubuntu 20.04 directly and its upstream
  README only calls out `libarmadillo-dev` plus a normal `catkin_make`,
- that makes legacy `ego-planner` the lighter next planner branch on the
  current host until `Fast-Planner` has a bounded dependency plan.

Everything else is secondary until the first live `px4_sih` run and first planner integration are proven. The live `px4_sih` run is now proven, so the current priority is the first planner integration.
