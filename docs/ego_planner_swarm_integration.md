# EGO-Planner-Swarm Integration

## Goal

Keep the first lab-stack integration lightweight, reproducible, and separate
from the upstream checkout root.

## Chosen Workspace

- upstream checkout:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm`
- dedicated integration workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`

The workspace uses a symlink from:

- `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm/src/ego-planner-swarm`

to the managed upstream checkout. Build products stay in the dedicated
workspace, not in the cloned upstream root.

## Why Single-Drone First

- The upstream `ego-planner` README recommends `ego-planner-swarm` as the more
  robust target.
- The repo already contains a single-drone launch path:
  `ego_planner/single_run_in_sim.launch`.
- The upstream `simple_run.launch` is not actually single-drone. It includes
  `swarm.launch`, which starts a ten-drone workload and is too heavy for the
  first stable platform entrypoint.

## Build Entry

Use the project-local build script:

```bash
./scripts/build_ego_planner_swarm_ws.sh
```

Important compatibility detail:

- This host currently has `cmake 4.2.3`.
- ROS Noetic's catkin top-level still declares `cmake_minimum_required(VERSION
  3.0.2)`.
- The build therefore needs `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, which the
  script adds automatically.

## Runtime Entries

Headless single-drone simulation:

```bash
./scripts/run_ego_planner_swarm_single.sh
```

Single-drone simulation plus RViz:

```bash
./scripts/run_ego_planner_swarm_single_visual.sh
```

Headless scene-backed `MARSIM` composition:

```bash
./scripts/run_ego_planner_swarm_marsim.sh
```

Scene-backed `MARSIM` composition plus RViz and the local dashboard:

```bash
./scripts/run_ego_planner_swarm_marsim_visual.sh --no-hold-open
```

Headless planner-on-estimator composition:

```bash
./scripts/run_ego_planner_swarm_fast_lio_marsim.sh
```

Planner-on-estimator composition plus RViz and the local dashboard:

```bash
./scripts/run_ego_planner_swarm_fast_lio_marsim_visual.sh --no-hold-open
```

Both scripts write run artifacts under:

- `/home/coco/sim_plane/runs`

## Scene-Backed Composition

- `MARSIM` workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_marsim`
- `ego-planner-swarm` workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`
- repo-local wrapper:
  `/home/coco/sim_plane/sim_plane/ros/ego_planner_swarm_marsim.launch`

The shared scene-backed path keeps `ego-planner-swarm` in single-drone manual
goal mode and does not launch the upstream swarm simulator stack. The wrapper:

- remaps `~odom_world` and `~grid_map/odom` directly to
  `/quad_0/lidar_slam/odom`,
- remaps `~grid_map/cloud` directly to `/quad0_pcl_render_node/cloud`,
- leaves camera pose and depth unused,
- disables `grid_map/use_depth_filter`,
- keeps the bounded goal at `(2.5, 0.0, 1.0)`,
- and publishes the final position command on `/quad_0/planning/pos_cmd`.

The repo now also carries a planner-on-estimator wrapper at:

- `/home/coco/sim_plane/sim_plane/ros/ego_planner_swarm_fast_lio_marsim.launch`

That wrapper keeps the same swarm planner shape but swaps planner odometry onto
the aligned FAST_LIO world-odom topic:

- `/sim_plane/fast_lio_world_odom`

while preserving the same `MARSIM` world cloud:

- `/quad0_pcl_render_node/cloud`

## Initial Verified Evidence

On `2026-04-27` and `2026-04-28`, the following were validated on this host:

- `catkin_make -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -j1`
  completed successfully in
  `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`.
- `roslaunch ego_planner single_run_in_sim.launch` started the expected nodes:
  `drone_0_ego_planner_node`, `drone_0_traj_server`,
  `drone_0_poscmd_2_odom`, `drone_0_odom_visualization`,
  `drone_0_pcl_render_node`, and `random_forest`.
- `/drone_0_visual_slam/odom` published live odometry during the run.
- `roslaunch ego_planner rviz.launch` started the RViz viewer path.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_single.json` passed at
  `runs/ego_planner_swarm_single_20260427_141747` with clean probe shutdown and
  no `drone_0_pcl_render_node` teardown crash.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_single_visual.json --visualize --no-hold-open`
  passed repeatedly at `runs/ego_planner_swarm_single_visual_20260427_142328`
  and `runs/ego_planner_swarm_single_visual_20260427_142410`.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_marsim.json --no-hold-open`
  passed at `runs/ego_planner_swarm_marsim_20260427_191923` with
  `goal_reached=true`, `min_goal_distance_m=0.011`, and direct `MARSIM`
  odometry plus pointcloud remaps.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_marsim_visual.json --visualize --no-hold-open`
  passed at `runs/ego_planner_swarm_marsim_visual_20260427_192755` with
  `goal_reached=true`, `launch_rviz=true`, dashboard replay at
  `http://127.0.0.1:8765`, and an info-only event stream.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim.json --no-hold-open`
  passed at `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903` with
  `goal_reached=true`, `min_goal_distance_m=0.03`, and an info-only event
  stream.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim_visual.json --visualize --no-hold-open`
  passed at `runs/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020`
  with `goal_reached=true`, `launch_rviz=true`, dashboard replay at
  `http://127.0.0.1:8765`, and an info-only event stream.
- ROS launch logs are now isolated under each run artifact's `ros_logs/`
  directory instead of accumulating under `~/.ros/log`.

## Required Source Fixes

One upstream CMake typo blocked the first build on this host:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/uav_simulator/Utils/multi_map_server/CMakeLists.txt`
- fix:
  `multi_map_server_messages_cpp` ->
  `multi_map_server_generate_messages_cpp`

This was the earliest real source-side blocker after the CMake 4 policy
compatibility issue was bypassed.

Two additional upstream fixes were required to make the integrated runtime
stable on this host:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/uav_simulator/local_sensing/src/pointcloud_render_node.cpp`
  fixes:
  read `map/resolution`, switch to `ros::spin()`, and explicitly shut down ROS
  interfaces before process exit to avoid the teardown-time
  `boost::wrapexcept<boost::lock_error>`.
- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/uav_simulator/map_generator/src/random_forest_sensing.cpp`
  fix:
  honor the configured launch seed instead of always reseeding from
  `random_device`, which removes flaky pass/fail drift between repeated visual
  runs.

Two more source-side changes were required before the scene-backed `MARSIM`
composition could run cleanly:

- files:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/uav_simulator/Utils/quadrotor_msgs/msg/PositionCommand.msg`
  and
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner-swarm/src/planner/plan_manage/src/traj_server.cpp`
  fix:
  match the `MARSIM` superset `PositionCommand` layout and populate the added
  fields so both workspaces now report the same ROS MD5
  `d008e86de36e11deb1e4033ac2c394a9`.
- file:
  `/home/coco/sim_plane/sim_plane/ros/ego_planner_swarm_marsim.launch`
  fix:
  launch `drone_0_ego_planner_node` directly with explicit `MARSIM` odom and
  cloud remaps. The first wrapper attempt tried to chain remaps through
  `advanced_param.xml`, but the planner stayed in `FSM INIT` printing
  `no odom.` until the wrapper switched to direct topic wiring.

One more repo-local runtime adapter was required before the swarm
planner-on-estimator surface could become stable:

- file:
  `/home/coco/sim_plane/scripts/ros_align_odometry.py`
  fix:
  anchor FAST_LIO `/Odometry` to the first `MARSIM`
  `/quad_0/lidar_slam/odom` sample and republish
  `/sim_plane/fast_lio_world_odom`. The raw direct-`/Odometry` shape is
  intentionally retired because it left the swarm planner in the wrong world
  origin.

## Current Boundary

- The single-drone upstream-simulator path is now buildable, launchable, and
  exposed through the shared `sim_plane` runner.
- The scene-backed `ego_planner_swarm_marsim` path is now also exposed through
  the same runner with headless and RViz-assisted scenarios.
- The planner-on-estimator `ego_planner_swarm_fast_lio_marsim` path is now
  also exposed through the same runner with headless and RViz-assisted
  scenarios.
- The final scene-backed wrapper is intentionally cloud-only and should not
  reopen the retired dual-input `depth + cloud` branch without fresh
  contradictory evidence.
- The aligned FAST_LIO world-odom adapter is now proven on both the legacy and
  swarm planner branches.
- The remaining visual-shutdown noise is upstream `roslaunch` raw stderr from
  RViz escalation; the shared platform event stream itself is now info-only for
  the validated scene-backed runs.
