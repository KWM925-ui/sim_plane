# Legacy EGO-Planner Integration

## Goal

Bring the older `ego-planner` branch into the shared `sim_plane` control
surface without widening back to heavier planner or simulator branches.

## Chosen Workspace

- upstream checkout:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner`
- dedicated integration workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner`

The workspace uses a symlink from:

- `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner/src/ego-planner`

to the managed upstream checkout. Build products stay in the dedicated
workspace, not in the cloned upstream root.

## Why This Path Exists

- `ego-planner-swarm` is still the recommended upstream branch and remains the
  stronger first planner path.
- The older `ego-planner` branch is still valuable as a lighter historical
  baseline and a compatibility reference for other FAST Lab reproductions.
- `Fast-Planner` remains demoted on this host because its upstream quick start
  still requires an unmanaged `NLopt v2.7.1` install.

## Build Entry

Use the project-local build script:

```bash
./scripts/build_ego_planner_ws.sh
```

Important compatibility detail:

- this host currently has `cmake 4.2.3`
- ROS Noetic's catkin top-level still declares `cmake_minimum_required(VERSION
  3.0.2)`
- the build therefore needs `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, which the
  script adds automatically
- the script also adds `-Wno-dev` so host-side CMake 4 policy chatter does not
  pollute the build verdict

## Runtime Entries

Headless single-drone simulation:

```bash
./scripts/run_ego_planner_single.sh
```

Single-drone simulation plus RViz:

```bash
./scripts/run_ego_planner_single_visual.sh
```

Both scripts write run artifacts under:

- `/home/coco/sim_plane/runs`

## Scene-Backed Composition On MARSIM

The repository now also carries a repo-local planner-on-scene wrapper at:

- `/home/coco/sim_plane/sim_plane/ros/ego_planner_marsim.launch`

Why this wrapper exists:

- the upstream `run_in_sim.launch` path always starts the legacy local
  simulator stack
- the shared scene-backed path must instead subscribe to the already-landed
  `MARSIM` single-drone contract
- the wrapper therefore launches only `ego_planner_node`, `traj_server`, and
  `waypoint_generator`, while `MARSIM` stays responsible for odometry, scene
  cloud, and the downstream `pos_cmd` consumer

Important boundary:

- the wrapper is intentionally cloud-only
- it remaps to `/quad_0/lidar_slam/odom`, `/quad0_pcl_render_node/cloud`, and
  `/quad_0/planning/pos_cmd`
- it leaves the depth path unused and forces `grid_map/use_depth_filter=false`
  because feeding both `MARSIM` depth and cloud into the legacy `GridMap`
  produced repeated false-obstacle and `EMERGENCY_STOP` churn on this host

## Auto-Goal Boundary

The upstream `run_in_sim.launch` path is manual-goal mode. The shared backend
therefore auto-publishes one bounded `/move_base_simple/goal` so the legacy
stack can run unattended through `sim_plane` without depending on an RViz click
for every test.

The current bounded goal is:

- `(2.5, 0.0, 1.0)` in the `world` frame

Why this goal is not farther right now:

- a farther `(5.0, 0.0, 1.0)` goal produced avoidable late-stage replanning
  noise and occasional `EMERGENCY_STOP` churn on this host
- the bounded `2.5 m` goal still exercises the planner, local sensing, and
  command path, but exits earlier and more cleanly

## Initial Verified Evidence

On `2026-04-28`, the following were validated on this host:

- `./scripts/build_ego_planner_ws.sh` completed successfully in
  `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner`
- the shared-runner headless scenario
  `runs/ego_planner_single_20260427_182825` passed with
  `goal_reached=true`, `min_goal_distance_m=0.118`, and clean return to
  `WAIT_TARGET`
- the shared-runner visual scenario
  `runs/ego_planner_single_visual_20260427_182852` passed with
  `goal_reached=true`, `min_goal_distance_m=0.123`, RViz launch, and only
  cosmetic viewer warnings
- the first shared-runner headless scene-backed composition
  `runs/ego_planner_marsim_20260427_185547` passed with
  `goal_reached=true`, `min_goal_distance_m=0.064`, `pointcloud_seen=true`,
  and info-only event output
- the first shared-runner visual scene-backed composition
  `runs/ego_planner_marsim_visual_20260427_185758` passed with
  `goal_reached=true`, `min_goal_distance_m=0.066`, `launch_rviz=true`, and
  info-only event output

## Required Source Fixes

One upstream CMake typo blocked the first build on this host:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/uav_simulator/Utils/multi_map_server/CMakeLists.txt`
- fix:
  `multi_map_server_messages_cpp` ->
  `multi_map_server_generate_messages_cpp`

Two additional low-risk package-noise fixes were also required:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/uav_simulator/Utils/rviz_plugins/CMakeLists.txt`
  fix:
  remove bogus `system_lib` from `catkin_package(...)`
- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/uav_simulator/so3_quadrotor_simulator/CMakeLists.txt`
  fix:
  remove bogus `Eigen3` and `system_lib` `catkin_package(...)` dependencies

One upstream shutdown hardening fix was required to retire the shared-runner
teardown crash:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/uav_simulator/local_sensing/src/pointcloud_render_node.cpp`
  fixes:
  read `map/resolution`, switch back to `ros::spin()`, and explicitly shut down
  ROS interfaces before process exit so normal teardown no longer aborts with
  `boost::wrapexcept<boost::lock_error>`

One cross-workspace message-contract fix was required before `MARSIM` could
consume the legacy planner output:

- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/uav_simulator/Utils/quadrotor_msgs/msg/PositionCommand.msg`
  fix:
  extend the legacy message definition to the `MARSIM` superset so both
  workspaces publish the same ROS MD5 for `quadrotor_msgs/PositionCommand`
- file:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/ego-planner/src/planner/plan_manage/src/traj_server.cpp`
  fix:
  explicitly populate the newly aligned message fields so the scene-backed
  bridge does not rely on implicit defaults

## Current Boundary

- legacy `ego-planner` is now buildable on this host through a dedicated
  workspace
- the shared `sim_plane` control surface now exposes both headless and RViz
  legacy `ego_planner` scenarios with artifact-backed passed evidence
- the shared `sim_plane` control surface now also exposes headless and RViz
  `ego_planner_marsim` scenarios through the cloud-only planner-on-scene
  wrapper
- the previous `pcl_render_node` teardown crash is retired for this path
- remaining RViz mesh-format and missing-material warnings are cosmetic viewer
  noise, not a pass/fail blocker
