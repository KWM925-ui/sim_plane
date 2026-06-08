# Platform Validation Matrix

## Goal

Freeze the strict quadrotor platform surfaces into one executable acceptance
gate so later sessions do not need to infer platform readiness from README
bullets and scattered run directories.

The canonical machine-readable source now lives at:

- [configs/platform_acceptance_matrix.json](/home/coco/sim_plane/configs/platform_acceptance_matrix.json)

Validate the frozen strict baseline with:

```bash
python3 -m sim_plane platform-acceptance
```

Validate the latest matching artifacts under `runs/` against the same gate
with:

```bash
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

Each invocation now writes a durable report pack under:

```text
runs/platform_acceptance/
```

including stable snapshots at:

```text
runs/platform_acceptance/latest_reference.json
runs/platform_acceptance/latest_latest.json
runs/platform_acceptance/latest_reference_delta.json
runs/platform_acceptance/latest_latest_delta.json
runs/platform_acceptance/history_reference.jsonl
runs/platform_acceptance/history_latest.jsonl
```

The default retention rule keeps only the newest 5 timestamped report
directories per mode while preserving the stable snapshots and append-only
history files. Pass `--keep-last-reports 0` if pruning must be disabled for a
specific audit round.

## Acceptance Shape

The strict platform gate currently requires all of the following:

- all listed quadrotor platform rows pass with `status=passed`
- each row's shared event surface stays `info`-only
- each row matches its required metrics and note substrings
- each row also stays within the configured reference-artifact regression budgets
  for tracked metrics such as `telemetry_count` and `mode_changes`
- the nested four-row planner baseline also passes through
  `python3 -m sim_plane planner-acceptance`

## Current Matrix

| Name | Backend | Surface | Reference artifact | Status |
| --- | --- | --- | --- | --- |
| `ego_planner_single` | `ego_planner` | legacy upstream single-run planner | `runs/ego_planner_single_20260428_142011` | passed |
| `ego_planner_single_visual` | `ego_planner` | legacy upstream single-run planner with RViz | `runs/ego_planner_single_visual_20260428_142039` | passed |
| `ego_planner_swarm_single` | `ego_planner_swarm` | swarm upstream single-run planner | `runs/ego_planner_swarm_single_20260428_141841` | passed |
| `ego_planner_swarm_single_visual` | `ego_planner_swarm` | swarm upstream single-run planner with RViz | `runs/ego_planner_swarm_single_visual_20260428_141921` | passed |
| `px4_sih_headless` | `px4_sih` | light closed-loop PX4 takeoff | `runs/px4_sih_quadx_headless_20260428_130601` | passed |
| `px4_sih_3d` | `px4_sih` | SIH plus QGroundControl plus jMAVSim viewer | `runs/px4_sih_quadx_3d_20260428_130651` | passed |
| `px4_sih_mavsdk_action` | `px4_sih` | SIH quadrotor driven by the repo-local MAVSDK action adapter | `runs/px4_sih_quadx_mavsdk_action_20260428_160345` | passed |
| `px4_jsbsim_headless` | `px4_jsbsim` | JSBSim quadrotor dynamics | `runs/px4_jsbsim_quadx_headless_20260428_130736` | passed |
| `px4_jsbsim_mavsdk_action` | `px4_jsbsim` | JSBSim quadrotor dynamics driven by the repo-local MAVSDK action adapter | `runs/px4_jsbsim_quadx_mavsdk_action_20260428_161256` | passed |
| `px4_jsbsim_mavsdk_action_visual` | `px4_jsbsim` | JSBSim quadrotor dynamics with FlightGear viewer driven by the repo-local MAVSDK action adapter | `runs/px4_jsbsim_quadx_mavsdk_action_visual_20260428_170517` | passed |
| `px4_jsbsim_visual` | `px4_jsbsim` | JSBSim quadrotor dynamics with FlightGear viewer | `runs/px4_jsbsim_quadx_visual_20260428_145759` | passed |
| `px4_gazebo_classic_headless` | `px4_gazebo_classic` | Gazebo Classic scene-backed PX4 takeoff headless | `runs/px4_gazebo_classic_iris_headless_20260428_152015` | passed |
| `px4_gazebo_classic_visual` | `px4_gazebo_classic` | Gazebo Classic scene-backed PX4 takeoff with native GUI | `runs/px4_gazebo_classic_iris_visual_20260428_152300` | passed |
| `px4_gazebo_classic_mavsdk_action` | `px4_gazebo_classic` | Gazebo Classic scene-backed PX4 takeoff driven by the repo-local MAVSDK action adapter | `runs/px4_gazebo_classic_iris_mavsdk_action_20260428_172653` | passed |
| `px4_gazebo_classic_mavsdk_action_visual` | `px4_gazebo_classic` | Gazebo Classic scene-backed PX4 takeoff with native GUI driven by the repo-local MAVSDK action adapter | `runs/px4_gazebo_classic_iris_mavsdk_action_visual_20260428_172755` | passed |
| `marsim_headless` | `marsim` | scene-backed sensor stack headless | `runs/marsim_single_20260428_130820` | passed |
| `marsim_visual` | `marsim` | scene-backed sensor stack with RViz | `runs/marsim_single_visual_20260428_130846` | passed |
| `marsim_gpu_headless` | `marsim` | scene-backed GPU sensor stack headless | `runs/marsim_single_gpu_20260428_143322` | passed |
| `marsim_gpu_visual` | `marsim` | scene-backed GPU sensor stack with RViz | `runs/marsim_single_gpu_visual_20260428_143543` | passed |
| `fast_lio_marsim_headless` | `fast_lio_marsim` | estimation stack headless | `runs/fast_lio_marsim_20260428_130913` | passed |
| `fast_lio_marsim_visual` | `fast_lio_marsim` | estimation stack with FAST_LIO RViz | `runs/fast_lio_marsim_visual_20260428_131215` | passed |

## Shared Constraints

- The strict platform matrix is quadrotor-only by design.
- Historical fixed-wing `px4_jsbsim_rascal_smoke` artifacts have been removed
  from `runs/`; fixed-wing remains outside the active product direction.
- The first local MAVSDK control surface landed on `PX4 SIH` first, because
  the platform blueprint treats `MAVSDK` as the primary narrow command/control
  adapter and keeps ROS optional for the core path.
- The same repo-local MAVSDK adapter is now also proven on both headless and
  FlightGear-visual `PX4 + JSBSim`, but those surfaces only stayed clean
  after moving the shared telemetry collector to JSBSim's `Normal`-mode
  `14550` port instead of reusing the onboard `14540/14580` pair.
- The same repo-local MAVSDK adapter is now also proven on both headless and
  native-GUI `PX4 + Gazebo Classic`, and those surfaces are accepted only
  with two source-side contracts locked: each run gets a dedicated local
  `GAZEBO_MASTER_URI` so other Gazebo Classic workspaces cannot pollute it,
  and the shared telemetry collector stays on a GCS-facing UDP port such as
  `14550` instead of reusing PX4's onboard `14580`.
- The platform gate now also treats silent quantitative drift as a failure,
  not only absolute threshold misses: globally tracked `telemetry_count`
  cannot drop by more than `10`, PX4-family `mode_changes` cannot regress
  below their frozen reference count.
- `px4_gazebo_classic` is accepted only as a transitional Ubuntu 20.04 scene
  backend, not as the forever default simulator, because Gazebo Classic is
  already upstream end-of-life.
- The platform gate nests the frozen four-row planner acceptance matrix rather
  than duplicating those planner rows here.
- The nested planner gate still enforces the `0.01 m` regression budget
  anchored to the frozen planner reference artifacts.

## Newly Retired Exclusion

The earlier exclusion of the upstream single-run `ego_planner_single` and
`ego_planner_swarm_single` demo surfaces is now retired.

Why it was safe to promote them:

- retained `2026-04-28` runs now keep both headless and visual single-run
  artifacts on an `info`-only shared event surface
- the prior `ego_planner_swarm_single` warning flood was bounded to internal
  retry chatter such as `a star error` and `Ran out of pool`, not to
  `EMERGENCY_STOP` or a failed run verdict
- that chatter is now normalized into informational log events while true
  emergency-stop transitions remain warnings

## Current Boundary

- The strict quadrotor platform baseline is now executable through
  `python3 -m sim_plane platform-acceptance`, not only implied by static docs.
- The platform gate now sits above the planner gate and treats it as a nested
  contract instead of a separate manual check.
- The platform gate no longer only enforces absolute pass/fail thresholds; it
  also rejects tracked metric regressions versus the frozen reference artifacts.
- The retained `2026-04-28` core and upstream-demo reference artifacts all expose
  an `info`-only shared event surface, including the newly landed GPU local
  sensing `MARSIM` rows, the newly landed `PX4 + JSBSim + FlightGear`
  visual row, the newly landed `PX4 + JSBSim + FlightGear + MAVSDK` visual
  row, the newly landed `PX4 + Gazebo Classic` headless plus native-GUI
  rows, the newly landed `PX4 + Gazebo Classic + MAVSDK` headless plus
  native-GUI rows, the newly landed `PX4 SIH + MAVSDK` action row,
  and the newly landed headless `PX4 + JSBSim + MAVSDK` action row.
