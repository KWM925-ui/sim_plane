# Frontier Algorithm Probes

## Scope

This note records retained `2026-04-29` managed bring-up evidence for additional
open-source frontier algorithms that are not yet part of the strict
twenty-one-row platform acceptance gate.

These probes follow the repo-wide rules:

- all upstream clones stay under `/home/coco/sim_plane_ws`
- incomplete or manual evidence lives under `runs/manual_probes/`
- the strict platform and planner acceptance gates stay green before and after
  widening work

## HKU MARS Lab `SUPER`

- upstream root:
  `/home/coco/sim_plane_ws/src/labs/HKU_MARS_Lab/SUPER`
- managed catkin workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_super`
- standard build script:
  `./scripts/build_super_ws.sh`
- standard probe script:
  `./scripts/run_super_benchmark.sh`
- optional stress probe:
  `./scripts/run_super_benchmark.sh --profile high_speed`
- retained canonical artifact:
  latest successful `runs/manual_probes/super_benchmark_dense_*`

Build contract:

```bash
source /opt/ros/noetic/setup.bash
export ROS_VERSION=1 ROS_DISTRO=noetic
export CMAKE_PREFIX_PATH="/home/coco/sim_plane_ws/toolchains/glfw/install:$CMAKE_PREFIX_PATH"
catkin_make \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -Dglfw3_DIR=/home/coco/sim_plane_ws/toolchains/glfw/install/lib/cmake/glfw3 \
  -DGLFW3_INCLUDE_DIR=/home/coco/sim_plane_ws/toolchains/glfw/install/include \
  -DGLFW3_LIBRARY=/home/coco/sim_plane_ws/toolchains/glfw/install/lib/libglfw3.a \
  -j1
```

Resolved blockers:

- `mission_planner` no longer hard-requires `mavros_msgs/RCIn.h` for builds
  that do not use the `MAVROS_RC` start trigger.
- stale `-ldw` links were removed from the ROS1 build path.
- optional ncurses tuning tools are now skipped cleanly when curses headers are
  absent.
- the benchmark goal publisher is now latched so late subscribers still receive
  the first mission goal.
- probes now auto-select a free isolated ROS master port by default, and an
  explicitly requested `SIM_PLANE_ROS_MASTER_PORT` now fails fast if the port is
  already occupied instead of silently attaching to an old master.
- the `marsim_render` PCD loader now fills a synthetic `intensity=0` field when
  the source PCD omits intensity, so the old startup warning no longer appears.
- the repeated optimizer rejection and transient replan-miss messages were
  downgraded from raw warning spam to informational probe-layer detail as long
  as the committed trajectory remains valid.

Retained runtime result:

- default stable profile now uses `dense`
- `runs/manual_probes/super_benchmark_dense_20260429_153853/summary.json`
  reports:
  - `click_goal_seen=true`
  - `pos_cmd_seen=true`
  - `follow_traj_seen=true`
  - `replan_success_seen=true`
  - `replan_success_count=166`
  - `planner_warn_count=3`
  - `hard_warn_count=0`
  - `transient_replan_miss_count=19`
  - `soft_optimizer_reject_count=22`
  - `intensity_warn_count=0`
  - `intensity_fallback_applied=true`
- `fsm.log` still contains transient replanning misses and optimizer candidate
  rejections, but those are now tracked explicitly in `summary.json` instead of
  dominating the shared warning surface.

## ZJU FAST Lab `visPlanner`

- upstream root:
  `/home/coco/sim_plane_ws/src/labs/ZJU_FAST_Lab/visPlanner`
- managed catkin workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_visplanner`
- standard build script:
  `./scripts/build_visplanner_ws.sh`
- standard probe script:
  `./scripts/run_visplanner_tracking.sh`
- retained canonical artifact:
  latest successful `runs/manual_probes/visplanner_tracking_*`

Build contract:

```bash
source /opt/ros/noetic/setup.bash
catkin_make -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -j1
```

Resolved blockers:

- `local_sensing` now falls back to CPU rendering if CUDA is unavailable.
- `multi_map_server` now depends on the generated message target that actually
  exists.
- the dead OOQP-only `bezier_predict` build branch is no longer required for the
  active `tracking.launch` path on this Ubuntu 20.04 host.
- the tracker now has a bounded fallback subscription to
  `/drone_1_planning/bspline`, so the tracking demo does not depend on an
  unavailable predictor-only side branch just to leave `WAIT_TARGET`.
- the tracker now accepts the first external target trajectory instead of
  dropping the only useful bootstrap message.
- the target-side `planning/bspline` writer now sets `bspline.drone_id`
  correctly, which was the earliest semantic writer bug blocking the tracker.
- format and signedness warnings in the active target/tracker path were cleaned
  from the ROS1 build output.
- the probe now auto-selects a free isolated ROS master port by default, and an
  explicitly requested `SIM_PLANE_ROS_MASTER_PORT` now fails fast if the port is
  already occupied.

Retained runtime result:

- `runs/manual_probes/visplanner_tracking_20260429_153921/summary.json`
  reports:
  - `target_pos_cmd_seen=true`
  - `tracker_pos_cmd_seen=true`
  - `target_bspline_seen=true`
  - `target_bspline_drone_id_line="drone_id: 1"`
  - `tracker_left_wait_target=true`
  - `tracker_exec_traj=true`
  - `predict_callback_seen=true`
  - `local_target_seen=true`
  - `warn_count=5`
- `launch.log` shows the key transition:
  `WAIT_TARGET -> GEN_NEW_TRAJ -> EXEC_TRAJ`

## Baseline Relationship

These `SUPER` and `visPlanner` probes are currently managed as clean
`manual_probes` evidence, not as rows in the strict platform acceptance matrix.

That keeps the top-level accepted baseline stable while new upstream algorithms
are still being normalized.

The latest successful canonical result for each probe is now retained by
`probe_meta.json` plus `python3 -m sim_plane manual-probe-hygiene`, while older
superseded probe directories can be pruned safely.
