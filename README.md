# sim_plane

A lightweight but capable UAV algorithm simulation and evaluation platform, designed to run on the current machine first and grow into richer validation later.

This repository is positioned as an algorithm-validation and experiment-management layer. It is not a high-fidelity visual-realism simulator in the same category as AirSim, Isaac Sim, Flightmare, FlightGoggles, or Unity/Unreal-based camera simulation stacks.

## Current Status

The repository now has a runnable MVP skeleton with:

- a Python CLI,
- a shared backend interface,
- a built-in demo backend,
- artifact output for each run,
- and a lightweight local web dashboard for visualization,
- a top-level `platform-health` entrypoint that aggregates git state,
  readiness, artifact hygiene, latest acceptance, latest professional test
  reports, objective boundaries, and next-stage priorities,
- a validated legacy `EGO-Planner` ROS1 backend path,
- a validated scene-backed `EGO-Planner + MARSIM` ROS1 planner path,
- a validated scene-backed `EGO-Planner-Swarm + MARSIM` ROS1 planner path,
- a validated planner-on-estimator `EGO-Planner + FAST_LIO + MARSIM` ROS1 path,
- a validated planner-on-estimator `EGO-Planner-Swarm + FAST_LIO + MARSIM` ROS1 path,
- a validated real `PX4 SIH` backend path,
- validated repo-local `MAVSDK` action adapter paths on top of `PX4 SIH`, headless plus FlightGear-visual `PX4 + JSBSim`, and headless plus native-GUI `PX4 + Gazebo Classic`,
- validated generic repo-local `ros_command` adapter paths on top of `MARSIM` and `FAST_LIO + MARSIM` for user ROS planner/perception processes,
- a validated real `PX4 + JSBSim` backend path in both headless and FlightGear visual modes,
- a validated real `PX4 + Gazebo Classic` backend path in both headless and native GUI modes,
- a validated real `MARSIM` ROS1 3D sensor backend path on both CPU and GPU local sensing routes,
- a validated real `FAST_LIO + MARSIM` ROS1 estimation backend path,
- managed `SUPER` and `visPlanner` upstream probes that now build cleanly and
  have fresh isolated `manual_probes` evidence outside the strict platform
  baseline,
- those frontier probe scripts now auto-select a free isolated ROS master port
  by default so stale masters do not silently contaminate new reproductions,
- and auxiliary `QGroundControl` plus `jMAVSim` viewer launch.

Fresh validated local evidence on `2026-04-27`, `2026-04-28`, and `2026-04-29`:

- headless SIH takeoff passed at `runs/px4_sih_quadx_headless_20260427_114632`,
- the default-path `QGroundControl` script passed at `runs/px4_sih_quadx_20260427_120430`,
- the default-path SIH plus `QGroundControl` plus `jMAVSim` script passed at `runs/px4_sih_quadx_3d_20260427_120519`,
- the first `ego-planner-swarm` ROS1 workspace build completed successfully at `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`,
- `ego_planner/single_run_in_sim.launch` produced live `/drone_0_visual_slam/odom`,
- the main-surface headless `ego_planner_swarm` run passed at `runs/ego_planner_swarm_single_20260427_141747`,
- repeated main-surface visual `ego_planner_swarm` runs passed at `runs/ego_planner_swarm_single_visual_20260427_142328` and `runs/ego_planner_swarm_single_visual_20260427_142410`,
- the main-surface headless `px4_jsbsim` quadrotor run passed at `runs/px4_jsbsim_quadx_headless_20260427_153027`,
- the first shared-runner `px4_sih + mavsdk_action_takeoff` pass completed at `runs/px4_sih_quadx_mavsdk_action_20260428_160345` with `target_altitude_reached=true`, `algorithm_adapter_completed_successfully=true`, `algorithm_adapter_landed=true`, and an info-only event stream,
- the first shared-runner `px4_jsbsim + mavsdk_action_takeoff` pass completed at `runs/px4_jsbsim_quadx_mavsdk_action_20260428_161256` with `target_altitude_reached=true`, `algorithm_adapter_completed_successfully=true`, `algorithm_adapter_landed=true`, and an info-only event stream,
- the first shared-runner `px4_jsbsim + FlightGear + mavsdk_action_takeoff` pass completed at `runs/px4_jsbsim_quadx_mavsdk_action_visual_20260428_170517` with `flightgear_viewer=true`, `target_altitude_reached=true`, `algorithm_adapter_completed_successfully=true`, and an info-only event stream,
- the main-surface visual `px4_jsbsim` quadrotor run passed at `runs/px4_jsbsim_quadx_visual_20260428_145759` with `flightgear_viewer=true`, `headless=false`, and info-only shared events,
- historical fixed-wing `px4_jsbsim` smoke artifacts have been removed from `runs/`; fixed-wing remains out of the current platform-mainline entry set,
- the main-surface headless `px4_gazebo_classic` quadrotor run passed at `runs/px4_gazebo_classic_iris_headless_20260428_152015` with `gazebo_gui=false`, `world=empty`, and info-only shared events,
- the main-surface visual `px4_gazebo_classic` quadrotor run passed at `runs/px4_gazebo_classic_iris_visual_20260428_152300` with `gazebo_gui=true`, `world=warehouse`, and info-only shared events,
- the first shared-runner `px4_gazebo_classic + mavsdk_action_takeoff` pass completed at `runs/px4_gazebo_classic_iris_mavsdk_action_20260428_172653` with `target_altitude_reached=true`, `algorithm_adapter_completed_successfully=true`, dedicated local `GAZEBO_MASTER_URI` isolation, and an info-only event stream,
- the first shared-runner `px4_gazebo_classic + native GUI + mavsdk_action_takeoff` pass completed at `runs/px4_gazebo_classic_iris_mavsdk_action_visual_20260428_172755` with `gazebo_gui=true`, `algorithm_adapter_completed_successfully=true`, dedicated local `GAZEBO_MASTER_URI` isolation, and an info-only event stream,
- the dedicated `MARSIM` workspace build completed successfully at `/home/coco/sim_plane_ws/workspaces/ros1_marsim`,
- the main-surface visual `marsim` run passed at `runs/marsim_single_visual_20260427_163908`,
- the main-surface headless `marsim` run passed at `runs/marsim_single_20260427_164011`,
- the GPU-path headless `marsim` run passed at `runs/marsim_single_gpu_20260428_143322` with `use_gpu=true` and info-only event output,
- the GPU-path visual `marsim` run passed at `runs/marsim_single_gpu_visual_20260428_143543` with `use_gpu=true`, `launch_rviz=true`, and info-only event output,
- the dedicated `FAST_LIO` workspace build completed successfully at `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`,
- the main-surface headless `fast_lio_marsim` run passed at `runs/fast_lio_marsim_20260427_173428`,
- the main-surface visual `fast_lio_marsim` run passed at `runs/fast_lio_marsim_visual_20260427_173600`,
- the first generic ROS-side `marsim + ros_command` pass completed at `runs/marsim_ros_command_template_20260429_083036` with `pointcloud_seen=true`, `position_cmd_seen=true`, `algorithm_adapter_completed_successfully=true`, and a repo-local sample node that subscribed `odom/cloud/map` then published `PositionCommand` into the native MARSIM control chain,
- the first generic ROS-side `fast_lio_marsim + ros_command` pass completed at `runs/fast_lio_marsim_ros_command_template_20260429_083251` with `odometry_seen=true`, `pointcloud_seen=true`, `position_cmd_seen=true`, `algorithm_adapter_completed_successfully=true`, and the default workspace overlay order narrowed so `quadrotor_msgs` stays available to user algorithms,
- the dedicated legacy `ego-planner` workspace build completed successfully at `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner`,
- the shared-runner headless legacy `ego_planner` run passed at `runs/ego_planner_single_20260427_182825`,
- the shared-runner visual legacy `ego_planner` run passed at `runs/ego_planner_single_visual_20260427_182852`,
- both legacy `ego_planner` runs auto-published the bounded goal `(2.5, 0.0, 1.0)`, returned to `WAIT_TARGET`, and exited without the prior `pcl_render_node` teardown crash,
- the first shared-runner headless `ego_planner_marsim` pass completed at `runs/ego_planner_marsim_20260427_185547` with `goal_reached=true`, `min_goal_distance_m=0.064`, and info-only event output,
- the first shared-runner visual `ego_planner_marsim` pass completed at `runs/ego_planner_marsim_visual_20260427_185758` with `goal_reached=true`, `launch_rviz=true`, and info-only event output,
- the shared-runner headless `ego_planner_swarm_marsim` pass completed at `runs/ego_planner_swarm_marsim_20260427_191923` with `goal_reached=true`, `min_goal_distance_m=0.011`, and direct MARSIM odom plus cloud remaps,
- the shared-runner visual `ego_planner_swarm_marsim` pass completed at `runs/ego_planner_swarm_marsim_visual_20260427_192755` with `goal_reached=true`, `launch_rviz=true`, dashboard replay at `http://127.0.0.1:8765`, and an info-only event stream,
- the first shared-runner headless `ego_planner_fast_lio_marsim` pass completed at `runs/ego_planner_fast_lio_marsim_20260427_194838` with `goal_reached=true`, `min_goal_distance_m=0.042`, and a world-aligned FAST_LIO odom adapter,
- the first shared-runner visual `ego_planner_fast_lio_marsim` pass completed at `runs/ego_planner_fast_lio_marsim_visual_20260427_194947` with `goal_reached=true`, `launch_rviz=true`, dashboard replay at `http://127.0.0.1:8765`, and an info-only event stream,
- the first shared-runner headless `ego_planner_swarm_fast_lio_marsim` pass completed at `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903` with `goal_reached=true`, `min_goal_distance_m=0.03`, and the reused world-aligned FAST_LIO odom adapter,
- the first shared-runner visual `ego_planner_swarm_fast_lio_marsim` pass completed at `runs/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020` with `goal_reached=true`, `launch_rviz=true`, dashboard replay at `http://127.0.0.1:8765`, and an info-only event stream,
- the scene-backed planner wrapper now runs cloud-only because the earlier dual-input `depth + cloud` shape caused repeated false-obstacle and `EMERGENCY_STOP` churn,
- `python3 -m sim_plane planner-acceptance` passed against the frozen four-row planner baseline,
- `python3 -m sim_plane planner-acceptance --latest --artifact-root runs` also passed against the latest matching planner artifacts,
- the planner acceptance gate now also rejects `min_goal_distance_m` regressions larger than `0.01 m` relative to each frozen row baseline,
- the planner acceptance gate now anchors that baseline to the frozen reference artifacts themselves and fails loudly if the copied matrix value drifts away from the reference artifact metric,
- each acceptance run now writes durable reports under `runs/acceptance/`, including timestamped report directories, stable `latest_reference.json` / `latest_latest.json` snapshots, append-only `history_reference.jsonl` / `history_latest.jsonl`, and a default retention rule that keeps only the newest 5 timestamped directories per mode,
- each acceptance run now also writes compact compare snapshots at `latest_reference_delta.json` / `latest_latest_delta.json`, and the CLI prints the previous-vs-current delta summary directly,
- a strict quadrotor platform acceptance matrix now exists at `configs/platform_acceptance_matrix.json`, and fresh `2026-04-28` reference artifacts were frozen for `ego_planner` single-run headless plus visual, `ego_planner_swarm` single-run headless plus visual, `px4_sih` headless plus 3D plus MAVSDK-action control, `px4_jsbsim` quadrotor headless plus headless-MAVSDK plus FlightGear visual plus FlightGear-visual-MAVSDK, `px4_gazebo_classic` quadrotor headless plus native GUI visual plus headless-MAVSDK plus native-GUI-MAVSDK, `marsim` CPU headless plus visual, `marsim` GPU headless plus visual, and `fast_lio_marsim` headless plus visual,
- the strict top-level platform baseline now includes those upstream single-run legacy and swarm planner surfaces plus the clean GPU `MARSIM` sensor-stack rows because their shared event surfaces were normalized to `info`-only without relaxing true `EMERGENCY_STOP` handling,
- the strict top-level platform baseline now also includes the clean headless and native-GUI `PX4 + Gazebo Classic + MAVSDK` rows, and those surfaces stay accepted only because the repo now isolates each Gazebo Classic run behind a dedicated local `GAZEBO_MASTER_URI` while keeping the shared telemetry collector on a GCS-facing UDP port such as `14550`,
- the strict top-level platform gate now also rejects silent quantitative drift relative to the frozen reference artifacts: globally tracked `telemetry_count` cannot drop by more than `10`, and PX4-family `mode_changes` cannot regress,
- ROS-family backends now also treat stale-node cleanup as hygiene instead of failure noise: a successful preflight or shutdown cleanup stays on the shared `info` surface, and only failed or incomplete cleanup escalates to `warning`,
- `python3 -m sim_plane artifact-hygiene` now classifies `runs/` into complete artifacts, reserved report roots, retained manual probes, and safe-to-prune stale probe directories so artifact hygiene stops depending on manual inspection,
- `python3 -m sim_plane platform-acceptance` and `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` now validate that strict top-level platform baseline while nesting the four-row planner acceptance gate underneath it,
- each platform acceptance run now writes durable reports under `runs/platform_acceptance/`, including timestamped report directories, stable `latest_reference.json` / `latest_latest.json` snapshots, append-only `history_reference.jsonl` / `history_latest.jsonl`, and compact `latest_reference_delta.json` / `latest_latest_delta.json` compare snapshots,
- the default stable `SUPER` probe now runs through `./scripts/run_super_benchmark.sh` with the cleaner `dense` profile, auto-selects a free ROS master port, and has retained canonical evidence at `runs/manual_probes/super_benchmark_dense_20260429_153853` with `click_goal_seen=true`, `pos_cmd_seen=true`, `planner_warn_count=3`, and `intensity_warn_count=0`,
- the rerun `visPlanner` tracking probe now also auto-selects a free ROS master port and has retained canonical evidence at `runs/manual_probes/visplanner_tracking_20260429_153921` with both tracker and target command streams present, `tracker_exec_traj=true`, and `warn_count=5`,
- `python3 -m sim_plane list-adapters` reports the generic adapter surface, including `external_command`, `mavsdk_action_takeoff`, `mavsdk_failure_injection`, and `ros_command`,
- and `python3 -m sim_plane list-backends` reports `demo: ready`, `ego_planner: ready`, `ego_planner_fast_lio_marsim: ready`, `ego_planner_marsim: ready`, `ego_planner_swarm: ready`, `ego_planner_swarm_fast_lio_marsim: ready`, `ego_planner_swarm_marsim: ready`, `fast_lio_marsim: ready`, `marsim: ready`, `px4_gazebo_classic: ready`, `px4_jsbsim: ready`, and `px4_sih: ready`.

## Current Recommendation

Use a layered approach instead of forcing one heavy simulator to do everything:

- Default backend: `PX4 SIH` for the lightest closed-loop iteration path.
- First algorithm adapter: `MAVSDK`, now validated through a repo-local `mavsdk_action_takeoff` control path on top of `PX4 SIH`, headless `PX4 + JSBSim`, and FlightGear-visual `PX4 + JSBSim`.
- Alternative dynamics backend: `PX4 + JSBSim`, with both the lighter headless quadrotor path and the FlightGear viewer path validated for the current quadrotor mainline.
- Transitional scene-backed PX4 backend: `PX4 + Gazebo Classic`, with both lighter headless and native GUI paths validated on the current Ubuntu 20.04 host, while still treated as a bridge because Gazebo Classic is already end-of-life.
- Transitional scene-backed MAVSDK control surface: `PX4 + Gazebo Classic + MAVSDK`, with both headless and native-GUI paths validated after isolating each run behind a dedicated local `GAZEBO_MASTER_URI` and keeping shared telemetry on `14550`.
- Rich 3D and sensor backend: `MARSIM` on the current Ubuntu 20.04 host, with `RViz` as the main 3D viewer and a lighter headless CPU path still available.
- First planner-on-scene backend: `legacy EGO-Planner + MARSIM` through the shared runner's cloud-only wrapper.
- Second planner-on-scene backend: `EGO-Planner-Swarm + MARSIM` through the shared runner's direct-topic, manual-goal, cloud-only wrapper.
- First planner-on-estimator backend: `legacy EGO-Planner + FAST_LIO + MARSIM` through the shared runner's aligned-odom adapter plus the stable MARSIM world cloud.
- Second planner-on-estimator backend: `EGO-Planner-Swarm + FAST_LIO + MARSIM` through the same aligned-odom adapter plus the stable MARSIM world cloud.
- Algorithm adapters: `external_command` for generic PX4-side host processes, `mavsdk_action_takeoff` / `mavsdk_failure_injection` for MAVSDK-based control and PX4-native failure surfaces, and `ros_command` for generic ROS-side planner/perception processes on `MARSIM` and `FAST_LIO + MARSIM`.
- Ground-control UI: optional `QGroundControl`, not a hard dependency for the MVP.

## Why This Shape

- The host baseline is Ubuntu 20.04 with 14 GiB RAM, so newer Ubuntu-only simulator stacks should not be the default starting point.
- The platform needs to stay easy to operate and integrate, so the core runtime should avoid mandatory ROS and other heavy layers until they are justified.
- The project should support both fast closed-loop testing and a future path toward richer scenes or sensor simulation.
- Current QGroundControl docs have moved toward Ubuntu 22.04 and 24.04, so QGC should remain optional on this host even though older QGC documentation still covered Ubuntu 20.04.

## Repo Docs

- [Platform blueprint](docs/platform_blueprint.md)
- [Upstream reference matrix](docs/upstream_reference_matrix.md)
- [Legacy EGO-Planner integration](docs/ego_planner_integration.md)
- [EGO-Planner-Swarm integration](docs/ego_planner_swarm_integration.md)
- [FAST_LIO + MARSIM integration](docs/fast_lio_marsim_integration.md)
- [Frontier algorithm probes](docs/frontier_algorithm_probes.md)
- [平台总入口（中文）](<docs/平台总入口_zh.md>)
- [项目结构与维护说明（中文）](<docs/项目结构与维护说明_zh.md>)
- [前沿算法探针说明（中文）](<docs/前沿算法探针说明_zh.md>)
- [算法复现手册（中文）](<docs/算法复现手册_zh.md>)
- [自定义算法接入指南（中文）](<docs/自定义算法接入指南_zh.md>)
- [Platform validation matrix](docs/platform_validation_matrix.md)
- [Platform acceptance matrix config](configs/platform_acceptance_matrix.json)
- [Planner validation matrix](docs/planner_validation_matrix.md)
- [Planner acceptance matrix config](configs/planner_acceptance_matrix.json)
- [Execution plan](.agent/PLANS.md)
- [Repository guide](AGENTS.md)

## External Workspace Root

All cloned upstream repositories should stay under:

```text
/home/coco/sim_plane_ws
```

Sync or update the managed upstream set with:

```bash
python3 scripts/sync_upstreams.py
```

The default managed PX4 checkout path is:

```text
/home/coco/sim_plane_ws/src/core/PX4-Autopilot
```

## Quick Start

Run the lightweight visual demo:

```bash
python3 -m sim_plane run scenarios/basic_takeoff.json --visualize
```

Replay a finished run later:

```bash
python3 -m sim_plane serve runs/<artifact_dir>
```

Browse retained artifacts and compare two runs in the dashboard:

```bash
python3 -m sim_plane serve runs
```

The dashboard also shows the latest suite reports under `runs/suites/`,
including KPI rows, KPI rankings, and the strongest `top_metric_effects` from
parameter sweeps. It also lists the latest professional test-surface reports:
PX4 failure injection, flight-log replay, seeded fuzz, and local autotest pack
results.

List backends:

```bash
python3 -m sim_plane list-backends
```

List algorithm adapters:

```bash
python3 -m sim_plane list-adapters
```

Inspect what is ready on this machine and get the recommended next run path:

```bash
python3 -m sim_plane doctor
```

Run a fresh one-command live smoke suite:

```bash
python3 -m sim_plane live-smoke
```

Run the first functional disturbance suite over the lightweight demo backend:

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_disturbance_suite.json
```

Run the PX4-native failure-injection proof:

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_mavsdk_failure_motor.json \
  --artifact-root runs --no-hold-open

python3 -m sim_plane px4-failure-acceptance --latest --artifact-root runs
```

This is deliberately not a demo disturbance. It uses PX4 `MAV_CMD_INJECT_FAILURE`
through the MAVSDK failure plugin and currently locks the first proven SIH path:
`SYSTEM_MOTOR/OFF` followed by `SYSTEM_MOTOR/OK`. Other failure units must be
added only after fresh PX4-backed evidence proves they are accepted on the
selected backend.

Run an automatic parameter sweep without hand-writing every variant:

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_parameter_sweep_suite.json
```

Run deterministic sensor degradation and KPI gates on the lightweight demo
backend:

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_degradation_suite.json
```

Run the standard paper/project-style quadrotor exam:

```bash
python3 -m sim_plane quadrotor-exam --artifact-root runs
```

The exam writes a normal suite report under `runs/suites/` and adds a compact
`exam` summary with success rate and fixed KPI names for repeatable
paper/project tables.

Validate the latest quadrotor exam against the frozen reference report:

```bash
python3 -m sim_plane quadrotor-exam-acceptance --latest --artifact-root runs
```

This turns the exam into a regression surface: fixed scenes, fixed KPI budgets,
latest-vs-reference comparison, persisted reports, history, and deltas.

Run data-stream-level sensor fault checks on the lightweight demo backend:

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_sensor_stream_fault_suite.json
```

This surface simulates GPS dropout, VIO scale drift, and IMU noise bursts in
the telemetry data flow. It is deliberately separate from PX4-native failure
injection.

List and run built-in baseline algorithm entrypoints:

```bash
python3 -m sim_plane list-baselines
python3 -m sim_plane run-baseline pid_position_demo --artifact-root runs
```

The catalog includes ready baselines and planned entries. Planned entries are
not runnable until an implementation and tests are landed.

Replay a run artifact or PX4 `.ulg` flight log into normalized KPI evidence:

```bash
python3 -m sim_plane flight-log-analyze runs/<artifact_dir>

python3 -m sim_plane flight-log-analyze /path/to/log.ulg
```

Reports are written under `runs/flight_log_analysis/`. Artifact replay reads
`telemetry.jsonl`, `result.json`, and `events.jsonl`; `.ulg` replay uses
`pyulog` and extracts duration, altitude/speed summaries, nav/arming state
changes, PX4 log warnings, dropout counts, and replay `kpi_*` metrics. These
are two different analysis inputs: artifact replay itself does not parse PX4
raw logs unless the source is a `.ulg` file.

PX4-family backends now also attempt to collect new or changed PX4 `.ulg` files
into each run artifact under `px4_ulog/`. Check `px4_ulog/index.json` inside an
artifact for the exact status: `collected`, `missing`, `disabled`, or `failed`.

Run a deterministic seeded fuzz/sweep and rank worst cases:

```bash
python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json \
  --profile demo_fast --seed 20260528 --variants 6
```

Reports are written under `runs/scenario_fuzz/` and include the generated suite
JSON, fresh variant artifacts, KPI rankings, `top_metric_effects`, and
`worst_cases`. The current `demo_fast` profile deliberately exercises the
lightweight demo backend's disturbance/degradation knobs; do not label it as
PX4-native physical failure injection.

Run the fast CI/autotest-like pack:

```bash
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

The fast pack runs doctor, artifact hygiene, `live-smoke --profile fast`, the
demo degradation suite, seeded fuzz, flight-log artifact replay, PX4 failure
acceptance latest, and platform acceptance latest. Reports are written under
`runs/autotest/`.

Run the standard lightweight task-family exam:

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_task_family_suite.json
```

Run the same suite surface on the real PX4 SIH flight-stack path:

```bash
python3 -m sim_plane run-suite scenarios/px4_sih_quadx_headless.json \
  --suite configs/px4_sih_takeoff_suite.json
```

`run-suite` creates fresh artifacts for each deterministic variant and writes a
suite report under:

```text
runs/suites/
```

Every shared-runner artifact now also receives normalized plugin-style `kpi_*`
metrics in `result.json`, such as altitude error, reach time, settle/recovery
time, path error, final-goal distance, speed and acceleration roughness, speed
limit violations, safety/geofence violations, sensor dropout/reacquire counts,
and measurement error when truth data is available. These metrics are
intentionally additive: existing backend-specific metrics and acceptance
contracts keep their original meaning. Whole-run KPI values include takeoff and
landing transients; `kpi_mission_*` values isolate the mission or offboard phase
when the backend labels that phase.

The lightweight demo backend supports deterministic degradation knobs for
algorithm robustness testing: `sensor_dropout`, `target_loss`, `sensor_latency`,
`sensor_noise`, `measurement_bias`, `measurement_bias_drift`,
`measurement_saturation`, `communication_interruption`, and
`control_saturation`. It also has a clearly labelled data-stream sensor fault
surface under `sensor_stream_faults` for GPS dropout, VIO scale drift, and IMU
noise bursts. PX4 SIH remains conservative: do not call a PX4 run a wind/fault
test unless that injection is backed by a real PX4-side mechanism.

For the fastest local sanity check, run only the built-in demo row:

```bash
python3 -m sim_plane live-smoke --profile fast
```

`live-smoke` is intentionally different from acceptance: it starts scenarios
again and writes new artifacts under `runs/`, while acceptance validates retained
reference/latest artifacts. Live-smoke reports are retained under:

```text
runs/live_smoke/
```

Run the repo-local custom algorithm template on PX4 SIH:

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_external_command_template.json --visualize --no-hold-open
```

Run an interface health check for that same control-algorithm ingress:

```bash
python3 -m sim_plane check-algorithm-ingress \
  --scenario scenarios/px4_sih_quadx_external_command_template.json
```

Generate a scenario for your own PX4-side control algorithm:

```bash
python3 -m sim_plane generate-scenario \
  --adapter external_command \
  --command "python3 /path/to/my_controller.py" \
  --name my_px4_controller
```

Generate and immediately health-check your own control algorithm:

```bash
python3 -m sim_plane check-algorithm-ingress \
  --adapter external_command \
  --command "python3 /path/to/my_controller.py" \
  --backend px4_sih
```

Run the repo-local ROS planner/perception template on top of MARSIM:

```bash
python3 -m sim_plane run scenarios/marsim_ros_command_template.json --rviz --visualize --no-hold-open
```

Generate a scenario for your own ROS planner/perception algorithm:

```bash
python3 -m sim_plane generate-scenario \
  --adapter ros_command \
  --backend marsim \
  --command "roslaunch my_pkg planner.launch" \
  --name my_ros_planner
```

Run the same ROS planner/perception template on top of FAST_LIO + MARSIM:

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim_ros_command_template.json --rviz --visualize --no-hold-open
```

Validate the frozen four-row planner acceptance baseline:

```bash
python3 -m sim_plane planner-acceptance
```

This also writes a timestamped acceptance report under:

```text
runs/acceptance/
```

Validate the latest matching planner artifacts against the same gate:

```bash
python3 -m sim_plane planner-acceptance --latest --artifact-root runs
```

Validate the frozen strict quadrotor platform baseline:

```bash
python3 -m sim_plane platform-acceptance
```

Validate the latest matching platform artifacts against the same gate:

```bash
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

Run fresh boot smoke separately from artifact acceptance:

```bash
python3 -m sim_plane live-smoke --profile fast
python3 -m sim_plane live-smoke
```

Normalize retained manual evidence and prune safe incomplete probe directories:

```bash
python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual --prune-safe
```

The stable machine-readable snapshots are:

```text
runs/acceptance/latest_reference.json
runs/acceptance/latest_latest.json
runs/acceptance/latest_reference_delta.json
runs/acceptance/latest_latest_delta.json
runs/acceptance/history_reference.jsonl
runs/acceptance/history_latest.jsonl
```

The platform-level stable snapshots are:

```text
runs/platform_acceptance/latest_reference.json
runs/platform_acceptance/latest_latest.json
runs/platform_acceptance/latest_reference_delta.json
runs/platform_acceptance/latest_latest_delta.json
runs/platform_acceptance/history_reference.jsonl
runs/platform_acceptance/history_latest.jsonl
```

The live smoke stable snapshots are:

```text
runs/live_smoke/latest_fast.json
runs/live_smoke/latest_default.json
runs/live_smoke/history_fast.jsonl
runs/live_smoke/history_default.jsonl
```

The default retention rule keeps only the newest 5 timestamped report
directories per mode. Use `--keep-last-reports 0` to disable pruning if you
explicitly want unbounded acceptance-report history.

Install an editable command if you want the `sim-plane` shell entrypoint:

```bash
python3 -m pip install -e .
sim-plane run scenarios/basic_takeoff.json --visualize
```

There is also a convenience script:

```bash
./scripts/run_demo_visual.sh
```

Run the real `PX4 SIH` path with the managed default PX4 checkout:

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx.json --visualize --qgc
```

Request the SIH 3D display-only viewer as well:

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_3d.json --visualize --qgc --jmavsim
```

Or use the convenience scripts:

```bash
./scripts/run_px4_sih_qgc.sh
./scripts/run_px4_sih_3d.sh
```

Run the real `PX4 + JSBSim` headless quadrotor path:

```bash
python3 -m sim_plane run scenarios/px4_jsbsim_quadx_headless.json --no-hold-open
```

Run the real `PX4 + JSBSim + FlightGear` visual quadrotor path:

```bash
python3 -m sim_plane run scenarios/px4_jsbsim_quadx_visual.json --visualize --no-hold-open
```

Run the repo-local `MAVSDK` action adapter on top of the light `PX4 SIH` path:

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_mavsdk_action.json --no-hold-open
```

Run the same repo-local `MAVSDK` action adapter on top of headless `PX4 + JSBSim`:

```bash
python3 -m sim_plane run scenarios/px4_jsbsim_quadx_mavsdk_action.json --no-hold-open
```

Run the same repo-local `MAVSDK` action adapter on top of `PX4 + JSBSim + FlightGear`:

```bash
python3 -m sim_plane run scenarios/px4_jsbsim_quadx_mavsdk_action_visual.json --visualize --no-hold-open
```

Run the real `PX4 + Gazebo Classic` headless quadrotor path:

```bash
python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_headless.json --no-hold-open
```

Run the real `PX4 + Gazebo Classic` native-GUI quadrotor path:

```bash
python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_visual.json --visualize --no-hold-open
```

Run the repo-local `MAVSDK` action adapter on top of headless `PX4 + Gazebo Classic`:

```bash
python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_mavsdk_action.json --no-hold-open
```

Run the same repo-local `MAVSDK` action adapter on top of native-GUI `PX4 + Gazebo Classic`:

```bash
python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_mavsdk_action_visual.json --visualize --no-hold-open
```

Run the validated `MARSIM` visual path:

```bash
python3 -m sim_plane run scenarios/marsim_single_visual.json --visualize --no-hold-open
```

Run the lighter headless `MARSIM` sensor-stack probe:

```bash
python3 -m sim_plane run scenarios/marsim_single.json --no-hold-open
```

Run the shared `FAST_LIO + MARSIM` headless estimation path:

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim.json --no-hold-open
```

Run the shared `FAST_LIO + MARSIM` visual estimation path:

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim_visual.json --visualize --no-hold-open
```

Run the shared `EGO-Planner + FAST_LIO + MARSIM` headless planner-on-estimator path:

```bash
python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim.json --no-hold-open
```

Run the same planner-on-estimator path with `MARSIM` RViz plus the local dashboard:

```bash
python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim_visual.json --visualize --no-hold-open
```

Run the shared `EGO-Planner-Swarm + FAST_LIO + MARSIM` headless planner-on-estimator path:

```bash
python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim.json --no-hold-open
```

Run the same swarm planner-on-estimator path with `MARSIM` RViz plus the local dashboard:

```bash
python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim_visual.json --visualize --no-hold-open
```

Run the first shared `EGO-Planner + MARSIM` headless planner-on-scene path:

```bash
python3 -m sim_plane run scenarios/ego_planner_marsim.json --no-hold-open
```

Run the same planner-on-scene path with `MARSIM` RViz plus the local dashboard:

```bash
python3 -m sim_plane run scenarios/ego_planner_marsim_visual.json --visualize --no-hold-open
```

Run the shared `EGO-Planner-Swarm + MARSIM` headless planner-on-scene path:

```bash
python3 -m sim_plane run scenarios/ego_planner_swarm_marsim.json --no-hold-open
```

Run the same swarm planner-on-scene path with `MARSIM` RViz plus the local dashboard:

```bash
python3 -m sim_plane run scenarios/ego_planner_swarm_marsim_visual.json --visualize --no-hold-open
```

Run the shared legacy `EGO-Planner` headless bounded-goal path:

```bash
python3 -m sim_plane run scenarios/ego_planner_single.json --no-hold-open
```

Run the shared legacy `EGO-Planner` visual bounded-goal path:

```bash
python3 -m sim_plane run scenarios/ego_planner_single_visual.json --visualize --no-hold-open
```

Or use the convenience scripts:

```bash
./scripts/run_marsim_single_visual.sh --no-hold-open
./scripts/run_marsim_single.sh
./scripts/run_px4_gazebo_classic_iris_headless.sh
./scripts/run_px4_gazebo_classic_iris_visual.sh --no-hold-open
./scripts/run_px4_gazebo_classic_iris_mavsdk_action.sh --no-hold-open
./scripts/run_px4_gazebo_classic_iris_mavsdk_action_visual.sh --no-hold-open
./scripts/run_px4_jsbsim_mavsdk_action.sh --no-hold-open
./scripts/run_px4_jsbsim_mavsdk_action_visual.sh --no-hold-open
./scripts/run_px4_jsbsim_quadx_visual.sh --no-hold-open
./scripts/run_px4_sih_mavsdk_action.sh
./scripts/run_fast_lio_marsim.sh
./scripts/run_fast_lio_marsim_visual.sh --no-hold-open
./scripts/run_ego_planner_fast_lio_marsim.sh
./scripts/run_ego_planner_fast_lio_marsim_visual.sh --no-hold-open
./scripts/run_ego_planner_swarm_fast_lio_marsim.sh
./scripts/run_ego_planner_swarm_fast_lio_marsim_visual.sh --no-hold-open
./scripts/run_ego_planner_single.sh
./scripts/run_ego_planner_single_visual.sh --no-hold-open
./scripts/run_ego_planner_marsim.sh
./scripts/run_ego_planner_marsim_visual.sh --no-hold-open
./scripts/run_ego_planner_swarm_marsim.sh
./scripts/run_ego_planner_swarm_marsim_visual.sh --no-hold-open
```

## Visualization Right Now

There is visualization now, but it is intentionally lightweight:

- top-down trajectory view,
- altitude timeline,
- live state cards,
- event stream,
- final result panel.

This local web dashboard is always available. For real `PX4 SIH`, there are now two auxiliary viewer paths:

- `QGroundControl`: flight state, instruments, map, mission-level visualization.
- `jMAVSim`: PX4 SIH's display-only 3D viewer path.

For ROS-based 3D scene work, there is now one validated path:

- `MARSIM + RViz`: obstacle-rich pointcloud scene, local sensing cloud, quadrotor state, and artifact-backed replay through the same runner.

For ROS-based estimation plus 3D scene work, there is now another validated path:

- `FAST_LIO + MARSIM + RViz`: estimator odometry on `/Odometry`, MARSIM local sensing input on `/quad0_pcl_render_node/sensor_cloud`, FAST_LIO RViz, and the same artifact-backed replay surface.

For ROS-based legacy planner visualization, there is now another validated path:

- `Legacy EGO-Planner + RViz`: bounded auto-goal execution on `/move_base_simple/goal`, live `/visual_slam/odom`, local sensing cloud on `/pcl_render_node/cloud`, RViz, and the same artifact-backed replay surface.

For ROS-based scene-backed planner visualization, there is now another validated path:

- `Legacy EGO-Planner + MARSIM + RViz`: bounded auto-goal execution on `/move_base_simple/goal`, MARSIM odometry on `/quad_0/lidar_slam/odom`, MARSIM scene cloud on `/quad0_pcl_render_node/cloud`, the shared cloud-only wrapper, MARSIM RViz, and the same artifact-backed replay surface.

For ROS-based scene-backed swarm-planner visualization, there is now another validated path:

- `EGO-Planner-Swarm + MARSIM + RViz`: bounded manual-goal execution on `/move_base_simple/goal`, MARSIM odometry on `/quad_0/lidar_slam/odom`, MARSIM scene cloud on `/quad0_pcl_render_node/cloud`, the shared direct-topic cloud-only wrapper, MARSIM RViz, and the same artifact-backed replay surface.

For flight-dynamics visualization without a ROS scene stack, there is now another validated path:

- `PX4 + JSBSim + FlightGear`: PX4 SITL, JSBSim dynamics, FlightGear as the 3D viewer, local dashboard replay, and the same artifact-backed runner surface.

The current 3D path is intentionally light:

- PX4 still runs in `SIH`,
- `jMAVSim` is used as the 3D display-only viewer,
- `MARSIM` covers the richer ROS1 pointcloud-style scene path,
- `FAST_LIO + MARSIM` covers the first shared estimator-on-scene path,
- and the local dashboard remains the stable artifact and replay surface.

Important boundary:

- `QGroundControl` is useful, but it is not a full 3D world animation engine.
- If you want obstacle-rich 3D scenes, camera-style views, and richer world interaction, that still requires a true 3D simulator backend such as `Gazebo`.

## JSBSim Integration Means What

`JSBSim` integration means:

- PX4 is still the flight stack,
- `JSBSim` provides the flight-dynamics simulation,
- `FlightGear` can be attached as the viewer for the quadrotor path,
- the platform runner starts and supervises that backend,
- telemetry, artifacts, and visualization stay on the same platform side.

This path is now real in the repo for both headless and visual runs. The current validated shape is:

- `quadrotor_x`: full takeoff scenario through the shared runner,
- `quadrotor_x + FlightGear`: full takeoff scenario through the shared runner with a 3D viewer,
- `QGroundControl`: optional auxiliary viewer,
- `FlightGear`: optional 3D viewer on the quadrotor path through a repo-local toolchain wrapper built by `./scripts/build_flightgear_toolchain.sh`.

It is mainly valuable for:

- better flight-dynamics realism than the simplest loop,
- and future dynamics-sensitive validation.

It is not the same thing as a rich obstacle-scene engine. `JSBSim` is about vehicle dynamics plus a viewer path, not the same product role as `MARSIM` or future `Gazebo` scene composition.

## Lab Stack Direction

The next expansion path is not "add more simulators first". It is:

- keep the core path as `PX4 SIH`,
- add one dedicated ROS1/catkin integration workspace under `/home/coco/sim_plane_ws`,
- and bring up lab stacks one at a time.

The first target is `ego-planner-swarm` single-drone mode because the upstream `ego-planner` README explicitly recommends it over legacy `ego-planner` and says to set `drone_id=0` for one drone.

Project-local helpers now exist for that path:

```bash
./scripts/build_ego_planner_swarm_ws.sh
./scripts/run_ego_planner_swarm_single.sh
./scripts/run_ego_planner_swarm_single_visual.sh
```

The same path is now exposed through the shared control surface:

```bash
python3 -m sim_plane run scenarios/ego_planner_swarm_single.json
python3 -m sim_plane run scenarios/ego_planner_swarm_single_visual.json --visualize --no-hold-open
```

The legacy `ego-planner` compatibility path is now also exposed through the shared control surface:

```bash
./scripts/build_ego_planner_ws.sh
./scripts/run_ego_planner_single.sh
./scripts/run_ego_planner_single_visual.sh --no-hold-open
python3 -m sim_plane run scenarios/ego_planner_single.json --no-hold-open
python3 -m sim_plane run scenarios/ego_planner_single_visual.json --visualize --no-hold-open
```

Each ROS run now stores isolated ROS logs under the run artifact in `ros_logs/`
instead of appending new noise under `~/.ros/log`.

The second ROS lab path is now `MARSIM` under its own dedicated workspace:

```bash
./scripts/build_marsim_ws.sh
./scripts/run_marsim_single.sh
./scripts/run_marsim_single_visual.sh --no-hold-open
```

The same `MARSIM` path is also exposed through the shared control surface:

```bash
python3 -m sim_plane run scenarios/marsim_single.json --no-hold-open
python3 -m sim_plane run scenarios/marsim_single_visual.json --visualize --no-hold-open
```

The third ROS lab path is now the shared `FAST_LIO + MARSIM` estimator stack:

```bash
./scripts/build_fast_lio_ws.sh
./scripts/run_fast_lio_marsim.sh
./scripts/run_fast_lio_marsim_visual.sh --no-hold-open
```

The same estimator path is also exposed through the shared control surface:

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim.json --no-hold-open
python3 -m sim_plane run scenarios/fast_lio_marsim_visual.json --visualize --no-hold-open
```

The platform wrapper for this path now disables FAST_LIO's default upstream
`PCD/scans.pcd` dump so run artifacts stay under `runs/` instead of polluting
the managed checkout.

## MVP Target

The first acceptable version should:

- start with one command,
- run at least one vehicle backend on this machine,
- expose telemetry and offboard control hooks,
- replay named scenarios,
- record evaluation results,
- and stay light enough that the host remains usable.
