# sim_plane Supervisor Ledger

## Task Identity

- Project: `sim_plane`
- Workspace: `/home/coco/sim_plane`
- Primary child session: `(not set yet)`

## Current Frontier 2026-06-01

### 已锁定事实

- 当前主线是通用 `sim_plane` 无人机仿真平台，不是 `/home/coco/follwer_ws`。
- 平台已经具备多后端、artifact、KPI、suite、dashboard、live-smoke、custom algorithm ingress、PX4-native motor failure、flight-log replay、scenario fuzz 和 autotest pack。
- 当前工作区有大量已实现但未提交的改动；继续扩新功能前必须先封版固化。

### 当前要解的问题

- 把当前平台状态整理成一个干净、可复验、可回滚的 baseline。
- 只补交付和使用入口，不改变已有仿真逻辑或验收语义。

### 本轮不能做的事

- 不碰 `/home/coco/follwer_ws`。
- 不重开 human-follow Stage1/Stage2。
- 不改 platform/planner/human-follow/PX4 failure acceptance 阈值或语义。
- 不新增 AirSim/Isaac/Gazebo Harmonic 等重后端。
- 不把 demo fuzz/dropout 说成 PX4 原生故障。

### 本轮输出方式

- 最终只汇报：改了什么、跑了什么、PASS/FAIL、commit/tag/push 状态、仍然客观存在的边界。

### 封版验证结果 2026-05-31

- 新增中文总入口：`docs/平台总入口_zh.md`。
- 清理生成残留：提交前删除 `__pycache__` / `*.pyc`，这些文件由 Python 验证命令自动再生成但被 `.gitignore` 排除。
- 静态与单测：
  - `python3 -m unittest discover -s tests`: PASS，`152` tests。
  - `python3 -m compileall -q sim_plane scripts tests examples`: PASS。
  - `find scripts -maxdepth 1 -type f -name '*.sh' -print0 | xargs -0 -r bash -n`: PASS。
  - JSON syntax check: PASS，`63` scenario/config JSON files。
  - `git diff --check`: PASS。
- 平台状态：
  - `python3 -m sim_plane doctor --json`: PASS，`12` ready backends，`6` ready adapters。
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: PASS，`status=clean`，`attention_count=0`。
  - `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --json`: PASS，`status=clean`。
- 封版复验：
  - `python3 -m sim_plane autotest-pack --profile fast --artifact-root runs --report-root runs/autotest --json`: PASS。
  - report: `runs/autotest/sim_plane_autotest_fast_20260531_163336_692041/report.json`。
  - 包含：doctor、artifact hygiene、live-smoke fast、demo degradation suite、scenario fuzz、flight-log artifact replay、PX4 failure latest、platform latest。
- 独立 latest acceptance：
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`: PASS。
  - report: `runs/acceptance/planner_acceptance_baseline_latest_20260531_163431_695941/report.json`。
  - `python3 -m sim_plane px4-failure-acceptance --latest --artifact-root runs --json`: PASS。
  - report: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260531_163431_662417/report.json`。
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: PASS，`23/23` rows。
  - report: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260531_163431_910880/report.json`。
- 客观边界保持不变：
  - fresh PX4 `.ulg` 自动收集到每个 artifact 仍未实现；
  - demo fuzz/degradation 不是 PX4-native physical failure；
  - PX4-native failure acceptance 当前只证明 `SYSTEM_MOTOR/OFF/OK`。

## Locked Facts

- The repository now contains project-local control docs and a platform blueprint.
- The host environment does not currently expose ready-to-use `px4` or `uv` commands.
- The user explicitly wants visualization in the platform, not a headless-only MVP.
- The current machine baseline still favors a lightweight default path over a heavy 3D-first stack.
- The repository now contains a runnable Python MVP skeleton with a backend interface, artifact writing, a built-in demo backend, and a local web dashboard.
- A fresh local visual run succeeded and held the dashboard open at `http://127.0.0.1:8876`.
- A fresh local replay run succeeded at `http://127.0.0.1:8877`.
- `QGroundControl.AppImage` was found at `/home/coco/桌面/QGroundControl.AppImage`.
- `gazebo` and `gz` commands are available on the host.
- `pymavlink` and `pyulog` are available in Python.
- A real `px4_sih` adapter now exists in the repo and supports PX4 path discovery, process supervision, MAVLink telemetry ingestion, artifact logging, and optional `QGroundControl` and `jMAVSim` launch.
- `python3 -m sim_plane list-backends` now reports `demo: ready`, `ego_planner: ready`, `ego_planner_fast_lio_marsim: ready`, `ego_planner_marsim: ready`, `ego_planner_swarm: ready`, `ego_planner_swarm_fast_lio_marsim: ready`, `ego_planner_swarm_marsim: ready`, `fast_lio_marsim: ready`, `marsim: ready`, `px4_jsbsim: ready`, and `px4_sih: ready`.
- The managed PX4 checkout now exists at `/home/coco/sim_plane_ws/src/core/PX4-Autopilot`.
- The local `jMAVSim` toolchain now exists under `/home/coco/sim_plane_ws/toolchains/jdk-17` and `/home/coco/sim_plane_ws/toolchains/apache-ant-1.10.17`.
- `java` and `ant` are not guaranteed on the system PATH, but the backend can resolve them from the managed toolchain root adjacent to the PX4 checkout.
- A fresh live headless SIH run passed at `runs/px4_sih_quadx_headless_20260427_114632/result.json` with `max_altitude_m=5.958`, `target_altitude_reached=true`, and `ever_armed=true`.
- A fresh default-path `QGroundControl` script run passed at `runs/px4_sih_quadx_20260427_120430/result.json` with `max_altitude_m=5.569`, `target_altitude_reached=true`, and `ever_armed=true`.
- A fresh default-path SIH 3D script run passed at `runs/px4_sih_quadx_3d_20260427_120519/result.json`.
- The 3D artifact event stream confirms repeated `commander takeoff`, PX4 mode changes into `TAKEOFF` and `LOITER`, and the final pass result.
- The managed upstream set is now cloned under `/home/coco/sim_plane_ws/src`.
- The local `ego-planner` README recommends `ego-planner-swarm` and says single-drone use should set `drone_id=0`.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`.
- A fresh `./scripts/build_ego_planner_swarm_ws.sh` run completed successfully.
- A fresh `roslaunch ego_planner single_run_in_sim.launch` run started the expected single-drone nodes and published live `/drone_0_visual_slam/odom`.
- A fresh `roslaunch ego_planner rviz.launch` run started the RViz viewer path.
- The main `sim_plane` control surface now exposes `ego_planner_swarm` as a first-class backend, and project-local helpers still exist for the same lab stack: `scripts/build_ego_planner_swarm_ws.sh`, `scripts/run_ego_planner_swarm_single.sh`, and `scripts/run_ego_planner_swarm_single_visual.sh`.
- `ego_planner_swarm` is part of the current shared backend set reported by `python3 -m sim_plane list-backends`.
- A fresh headless `ego_planner_swarm` main-surface run passed at `runs/ego_planner_swarm_single_20260427_140645/result.json` with `telemetry_count=89`, `max_altitude_m=1.675`, `max_speed_mps=2.321`, `target_altitude_reached=true`, and `position_cmd_seen=true`.
- The retained manual visual probe for the first swarm viewer path now lives under `runs/manual_probes/ego_planner_swarm_single_visual_20260427_202122`, while top-level `runs/` is reserved for complete artifacts plus reserved report roots.
- The host `cmake` is `4.2.3`, so the ROS1 workspace build requires `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
- The earliest source-side blocker in `ego-planner-swarm` was a typo in `multi_map_server/CMakeLists.txt`, now corrected from `multi_map_server_messages_cpp` to `multi_map_server_generate_messages_cpp`.
- `local_sensing` compiled successfully in CPU mode despite `package.xml` still listing `svo_msgs` and `vikit_ros`.
- The ROS telemetry probe now exits cleanly on shutdown without a `KeyboardInterrupt` traceback.
- The project-local ROS shutdown sequence now lets `roslaunch` own normal teardown, with node-kill fallback reserved for timeout recovery.
- The upstream `local_sensing` `pointcloud_render_node` now shuts down cleanly in normal runs without the prior `boost::wrapexcept<boost::lock_error>`.
- The upstream `random_forest_sensing` node now honors the configured launch seed instead of always reseeding from `random_device`.
- Fresh headless evidence at `runs/ego_planner_swarm_single_20260427_141747/result.json` passed with clean shutdown and no `pcl_render_node` crash.
- Fresh visual evidence at `runs/ego_planner_swarm_single_visual_20260427_142328/result.json`, `runs/ego_planner_swarm_single_visual_20260427_142410/result.json`, and `runs/ego_planner_swarm_single_visual_20260427_142608/result.json` passed through the main control surface.
- ROS logs for the lab backend are now isolated under each artifact's `ros_logs/` directory instead of accumulating under `~/.ros/log`.
- Cosmetic RViz warnings about an older hummingbird mesh and a missing material still appear in visual runs, but they do not block passed outcomes.
- The managed local JSBSim toolchain now exists at `/home/coco/sim_plane_ws/toolchains/jsbsim` and includes headers, `bin/JSBSim`, and `lib/libJSBSim.a`.
- PX4's JSBSim `ExternalProject` needed two host-side compatibility fixes on this machine: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` for `cmake 4.2.3`, and propagation of the reconstructed local `JSBSIM_ROOT_DIR` into the child configure step.
- PX4's `Tools/simulation/jsbsim/sitl_run.sh` now guards headless cleanup so shutdown no longer errors on empty `FGFS_PID`.
- A fresh direct headless `sitl_run.sh` probe for `quadrotor_x` produced MAVLink heartbeat on `udpin:127.0.0.1:14540`, accepted `commander takeoff`, and settled in `LOITER`.
- A historical direct headless `sitl_run.sh` probe for `rascal` produced MAVLink heartbeat on `udpin:127.0.0.1:14540`, accepted shell-injected overrides for `SYS_HAS_NUM_ASPD=0` and `NAV_DLL_ACT=0`, and then armed successfully without force-arm; its run artifact has since been removed because fixed-wing is outside the current mainline.
- The shared control surface now exposes `px4_jsbsim` as a first-class backend for the current quadrotor scenario set.
- Fresh artifact-backed JSBSim quadrotor evidence now exists at `runs/px4_jsbsim_quadx_headless_20260427_153027`.
- The user has now explicitly narrowed the product scope to quadrotor work. Fixed-wing is no longer an active investment direction for this platform.
- The old `px4_jsbsim_rascal_smoke` scenario entry and retained run artifact have both been removed from the current platform-mainline surface.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_marsim`.
- The earliest `MARSIM` build blocker was `glfw3` package discovery in `local_sensing/CMakeLists.txt`; a local patch now falls back to raw library lookup and disables `opengl_render_node` when `glfw3` is absent so the CPU `pcl_render_node` path remains available.
- The earliest `MARSIM` runtime blocker was `quad0_pcl_render_node` aborting on `SIGINT` with `boost::wrapexcept<boost::lock_error>`; a local shutdown hardening patch now stops timers, shuts down ROS interfaces explicitly, and exits cleanly under `roslaunch`.
- The `MARSIM` launch file now exposes overridable `use_gpu_` and `launch_rviz` args, which lets the shared runner switch between a lighter headless path and the RViz-assisted 3D path.
- Project-local helpers now exist for the `MARSIM` path: `scripts/build_marsim_ws.sh`, `scripts/run_marsim_single.sh`, and `scripts/run_marsim_single_visual.sh`.
- The shared control surface now exposes `marsim`, and `python3 -m sim_plane list-backends` reports `demo: ready`, `ego_planner_swarm: ready`, `marsim: ready`, `px4_jsbsim: ready`, and `px4_sih: ready`.
- Fresh artifact-backed main-surface `marsim` evidence now exists at `runs/marsim_single_visual_20260427_163908` and `runs/marsim_single_20260427_164011`.
- The `MARSIM` CPU sensing path now handles missing `intensity` fields on both the UAV mesh PCD and the incoming `global_map` cloud without warning, and the normal startup markers were downgraded from warning noise to informational logs.
- The former `cascadePID` naming warning chain is retired: the package is now `cascade_pid`, its internal package-path lookup matches that name, and fresh main-surface `marsim` runs no longer emit the old naming warning.
- Fresh post-cleanup shared-runner evidence exists at `runs/marsim_single_20260427_170126` and `runs/marsim_single_visual_20260427_170213`; both passed and no longer contain the retired `intensity` or package-name warning chain.
- The managed upstream set now also includes the official `livox_ros_driver` dependency at `/home/coco/sim_plane_ws/src/deps/Livox_SDK/livox_ros_driver`.
- The managed `FAST_LIO` entry is now recursive, so its upstream `include/ikd-Tree` submodule is present instead of failing the build on a missing source file.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`, and a project-local helper exists at `scripts/build_fast_lio_ws.sh`.
- A fresh `./scripts/build_fast_lio_ws.sh` run completed successfully and built both `livox_ros_driver_node` and `fast_lio/fastlio_mapping`.
- A fresh manual smoke launch of `MARSIM` plus `roslaunch fast_lio mapping_marsim.launch rviz:=false` produced live `/Odometry` output, so the upstream `mapping_marsim.launch` contract is satisfied by the current `MARSIM` topics.
- The shared control surface now exposes `fast_lio_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- A repo-local wrapper launch now exists at `sim_plane/ros/fast_lio_marsim.launch`, which disables `pcd_save/pcd_save_en` so shared-runner `FAST_LIO` runs stay inside the platform artifact discipline.
- A fresh headless shared-runner `FAST_LIO + MARSIM` pass now exists at `runs/fast_lio_marsim_20260427_173428/result.json` with `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and `pcd_save_disabled=true`.
- A fresh visual shared-runner `FAST_LIO + MARSIM` pass now exists at `runs/fast_lio_marsim_visual_20260427_173600/result.json` with `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and `launch_rviz=true`.
- The historical `FAST_LIO/PCD/scans.pcd` artifact was confirmed to predate the wrapper-backed passes and was removed from the managed upstream checkout after the new artifact logs proved there were no fresh `/PCD/` writes.
- The managed `Fast-Planner` reference lives under `/home/coco/sim_plane_ws/src/references/HKUST_Aerial_Robotics/Fast-Planner`, not under the `labs/` tree.
- The upstream `Fast-Planner` README requires a manual `NLopt v2.7.1` install step in addition to `libarmadillo-dev`, while the upstream legacy `ego-planner` README on Ubuntu 20.04 only calls out `libarmadillo-dev` plus `catkin_make`.
- On the current host and workspace policy, legacy `ego-planner` is therefore the lighter next planner-integration target; `Fast-Planner` remains demoted until its dependency plan is bounded.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner`, and a project-local helper exists at `scripts/build_ego_planner_ws.sh`.
- The legacy `ego-planner` `pointcloud_render_node` now reads `map/resolution`, uses `ros::spin()`, and explicitly shuts down ROS interfaces so normal shared-runner teardown no longer aborts with `boost::wrapexcept<boost::lock_error>`.
- The shared control surface now exposes `ego_planner`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- Fresh shared-runner headless legacy `ego_planner` evidence now exists at `runs/ego_planner_single_20260427_182825/result.json` with `goal_reached=true`, `min_goal_distance_m=0.118`, `pointcloud_seen=true`, and clean return to `WAIT_TARGET`.
- Fresh shared-runner visual legacy `ego_planner` evidence now exists at `runs/ego_planner_single_visual_20260427_182852/result.json` with `goal_reached=true`, `min_goal_distance_m=0.123`, `pointcloud_seen=true`, and `launch_rviz=true`.
- The shared legacy `ego_planner` scenarios now use the bounded auto-goal `(2.5, 0.0, 1.0)` because a farther `(5.0, 0.0, 1.0)` goal produced unnecessary late replanning noise on this host.
- The new `ego_planner_marsim` shared backend now composes `/home/coco/sim_plane_ws/workspaces/ros1_marsim` and `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner` through the repo-local wrapper `sim_plane/ros/ego_planner_marsim.launch`.
- The earliest `legacy ego_planner + MARSIM` source-side blocker was a ROS MD5 mismatch on `quadrotor_msgs/PositionCommand`; the legacy workspace message definition now matches the `MARSIM` superset and both workspaces report MD5 `d008e86de36e11deb1e4033ac2c394a9`.
- The earliest `legacy ego_planner + MARSIM` runtime blocker after that message fix was dual-feeding both `depth` and `cloud` into the legacy `GridMap`; the cloud-only wrapper plus `grid_map/use_depth_filter=false` retired the repeated false-obstacle and `EMERGENCY_STOP` churn.
- Fresh headless shared-runner `ego_planner_marsim` evidence now exists at `runs/ego_planner_marsim_20260427_185547/result.json` with `goal_reached=true`, `min_goal_distance_m=0.064`, and info-only event output.
- Fresh visual shared-runner `ego_planner_marsim` evidence now exists at `runs/ego_planner_marsim_visual_20260427_185758/result.json` with `goal_reached=true`, `launch_rviz=true`, and info-only event output.
- The shared control surface now exposes `ego_planner_swarm_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- The earliest `ego_planner_swarm + MARSIM` source-side blocker was the same ROS MD5 mismatch on `quadrotor_msgs/PositionCommand`; the swarm workspace message definition and `traj_server.cpp` now match the `MARSIM` superset and both workspaces report MD5 `d008e86de36e11deb1e4033ac2c394a9`.
- The first repo-local `ego_planner_swarm_marsim` wrapper attempt falsely relied on chained remaps through `advanced_param.xml`; the planner stayed in `FSM INIT` printing `no odom.` until the wrapper switched to direct `MARSIM` odom and cloud remaps.
- The final repo-local wrapper at `sim_plane/ros/ego_planner_swarm_marsim.launch` now launches `drone_0_ego_planner_node` directly in manual-goal mode, disables `grid_map/use_depth_filter`, leaves depth unused, and publishes `/quad_0/planning/pos_cmd` without starting the upstream swarm simulator stack or `waypoint_generator`.
- Fresh headless shared-runner `ego_planner_swarm_marsim` evidence now exists at `runs/ego_planner_swarm_marsim_20260427_191923/result.json` with `goal_reached=true`, `min_goal_distance_m=0.011`, and direct `MARSIM` odometry plus pointcloud remaps.
- Fresh visual shared-runner `ego_planner_swarm_marsim` evidence now exists at `runs/ego_planner_swarm_marsim_visual_20260427_192755/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event stream.
- Normal visual-stop `MARSIM` shutdown markers are now downgraded to info in the shared event surface; raw upstream `roslaunch` stderr still records the RViz `SIGTERM` escalation line as an artifact-only residual.
- The first direct `legacy ego_planner <- FAST_LIO /Odometry` adapter attempt exposed a frame-origin mismatch between FAST_LIO's local `camera_init` odometry and the MARSIM world-frame obstacle plus goal contract.
- A repo-local aligned-odometry adapter now exists at `scripts/ros_align_odometry.py`; it anchors FAST_LIO's `/Odometry` to the first MARSIM `/quad_0/lidar_slam/odom` sample and republishes `/sim_plane/fast_lio_world_odom`.
- The shared control surface now exposes `ego_planner_fast_lio_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- Fresh headless shared-runner `ego_planner_fast_lio_marsim` evidence now exists at `runs/ego_planner_fast_lio_marsim_20260427_194838/result.json` with `goal_reached=true`, `min_goal_distance_m=0.042`, and an info-only event stream.
- Fresh visual shared-runner `ego_planner_fast_lio_marsim` evidence now exists at `runs/ego_planner_fast_lio_marsim_visual_20260427_194947/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event stream.
- The aligned-odometry adapter locked a startup transform of about `dz=1.002 m` and retired the prior `z≈0` versus `z≈1` split that put the planner start pose inside obstacles.
- The aligned FAST_LIO world-odom adapter is now also proven on the swarm planner branch through `ego_planner_swarm_fast_lio_marsim`.
- Fresh headless shared-runner `ego_planner_swarm_fast_lio_marsim` evidence now exists at `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903/result.json` with `goal_reached=true`, `min_goal_distance_m=0.03`, and an info-only event stream.
- Fresh visual shared-runner `ego_planner_swarm_fast_lio_marsim` evidence now exists at `runs/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event stream.
- A repo-local acceptance summary now exists at `docs/planner_validation_matrix.md` and freezes the four currently landed planner surfaces.

## Newly Locked This Round

- On `2026-05-26`, the active work frontier moved back to the generic `sim_plane`
  platform mainline.
- The human-follow Stage1/Stage2 managed surfaces remain retained evidence and
  optional integrations, but they are not the current feature frontier.
- Current platform-mainline bounded action:
  - improve the user-facing environment/onboarding entry surface;
  - keep the lightweight default path first;
  - make control-algorithm and ROS planner/perception next commands obvious;
  - remove non-functional readiness noise from the platform doctor output.
- Forbidden in this round:
  - modifying human-follow acceptance semantics;
  - changing Stage1 or Stage2 matrices, thresholds, or scenario behavior;
  - widening into a new simulator or project-specific algorithm branch.
- Result of this platform-mainline hygiene/onboarding round:
  - `sim_plane/doctor.py` now separates template-adapter notes from real blocking issues.
  - `python3 -m sim_plane doctor` now also recommends latest platform acceptance and artifact hygiene commands.
  - `sim_plane/artifact_hygiene.py` now treats all formal acceptance report roots as reserved roots, including Stage1 detector/tracker and Stage2 integrated human-follow report roots.
  - The two report roots that were briefly migrated by the older hygiene classification were restored:
    - `runs/human_follow_stage1_detector_tracker_acceptance`
    - `runs/human_follow_stage2_integrated_acceptance`
  - Verification passed:
    - `python3 -m unittest tests.test_doctor tests.test_artifact_hygiene`
    - `python3 -m sim_plane doctor`
    - `python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual`
    - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`

## Current Audit Frontier 2026-05-26

### Locked Facts

- The active branch is the generic `sim_plane` platform mainline.
- The user asked for a full inspection for harmful defects, stale leftovers, and
  redundant platform parts before further widening.
- No new feature widening is allowed during this audit.
- Absolute proof that no unknown defect exists is not achievable from static and
  bounded runtime evidence; the audit must report verified evidence, found
  issues, and remaining uncertainty explicitly.

### Current Frontier

- Build a platform hygiene/redundancy/defect inventory using:
  - static code/config/doc scans;
  - scenario/backend/adapter registry consistency checks;
  - current tests;
  - platform acceptance;
  - artifact hygiene;
  - run-output and report-root inspection.

### Forbidden Actions

- Do not change acceptance semantics or thresholds during the audit.
- Do not delete artifacts or source files before classifying them.
- Do not touch `/home/coco/follwer_ws`.
- Do not treat human-follow project-specific progress as platform-mainline
  completion evidence.

### Audit Findings 2026-05-26

#### Verified Clean Surfaces

- `python3 -m unittest discover -s tests` passed: `95` tests.
- `python3 -m compileall -q sim_plane scripts examples tests` passed.
- Shell syntax check passed for all `scripts/*.sh`.
- JSON syntax check passed for all `59` scenario/config JSON files.
- Scenario registry consistency passed:
  - `52` scenario files;
  - no unknown backend references;
  - no unknown adapter references;
  - no duplicate scenario names.
- Current platform readiness passed:
  - `python3 -m sim_plane doctor --json` reports `12` ready backends and `5`
    ready adapters.
- Artifact hygiene passed:
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs`
  - `attention=0`, `complete=245`, `reserved_roots=7`.
- Manual probe hygiene passed:
  - `python3 -m sim_plane manual-probe-hygiene --artifact-root runs`
  - `attention=0`, `retained=7`, `stale=0`.
- Acceptance passed:
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`
  - `python3 -m sim_plane platform-acceptance`
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs`
  - latest platform report:
    `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_152745_649516/report.json`

#### Classified Noise / Redundancy Candidates

- Python cache files exist under source/test/example/script directories despite
  `.gitignore` ignoring `__pycache__/` and `*.pyc`; these are safe cleanup
  candidates.
- `scripts/run_px4_sih_human_follow_user_planning_ingress.sh` is documented as
  directly executable but lacks execute permission; `scripts/process_cleanup.sh`
  also lacks execute permission, but that one is a sourced library and is fine.
- `scenarios/px4_sih_quadx_human_follow_stage2_real_ego_visual_demo.json` was a
  low-reference orphan scenario outside acceptance and has been removed.
- Historical Stage2 placeholder run artifacts have been removed from `runs/`;
  the placeholder scenario/managed-launch source entrypoints were already
  removed.
- Legacy fixed-wing run artifacts have been removed from `runs/`, and fixed-wing
  backend model mappings remain as compatibility code only; fixed-wing
  scenarios were removed from the current source entry set.
- `runs/` contains `38` non-passed complete artifacts and several top-level
  `*probe*` artifacts. They do not break artifact hygiene because they are
  complete artifacts, but they are history/debug noise for a user trying to
  understand the current platform.
- Hygiene cleanup on `2026-05-26` removed current-source entrypoints that were
  no longer part of the platform mainline:
  - the legacy fixed-wing demo scenarios
  - the legacy Stage2 placeholder scenario and managed launch
  - `scenarios/px4_sih_quadx_human_follow_stage2_real_ego_visual_demo.json`
- The current Stage2 adapter default is the real-EGO managed launch; explicit
  non-real-EGO launch paths are classified as `custom`, not as platform
  mainline evidence.
- Fixed-wing backend model mappings remain as code compatibility only; the
  current scenario set and strict platform baseline are quadrotor mainline.
- Historical fixed-wing and Stage2 placeholder run artifacts have been removed
  from `runs/`; only control-ledger conclusions remain.

#### Current Conclusion

- No current strict-baseline functional defect was found.
- The confirmed issues are hygiene/noise/redundancy issues, not acceptance
  failures.
- Absolute absence of unknown defects cannot be proven; this audit only proves
  the checked surfaces above.

#### Hygiene Closure 2026-05-26

- Current source entry set was cleaned to the quadrotor platform mainline:
  - removed legacy fixed-wing scenario files;
  - removed Stage2 placeholder scenario and managed launch entrypoints;
  - removed the orphan Stage2 real-EGO visual-demo scenario.
- Stage2 adapter semantics are now explicit:
  - default launch is `human_follow_stage2_real_ego_managed.launch`;
  - explicit non-real-EGO launch paths are classified as `custom`;
  - no placeholder source entrypoint remains in the current platform surface.
- Non-functional generated residue was removed:
  - Python `__pycache__` / `*.pyc`;
  - obsolete invalid manual smoke probe;
  - stale superseded `SUPER` and `visPlanner` manual-probe directories.
- Historical failed top-level artifacts were removed after confirming they were
  not referenced by any acceptance matrix:
  - failed top-level artifact count went from `38` to `0`;
  - complete top-level artifacts now count `207`;
  - retained manual probes now count `4`;
  - `runs/` now occupies about `1.0G`.
- Current retained manual probes:
  - `ego_planner_swarm_single_visual_20260427_202122`
  - `super_benchmark_dense_20260429_153853`
  - `visplanner_tracking_20260429_153921`
- Final validation after cleanup:
  - `python3 -m unittest discover -s tests`: `96` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - Scenario/config JSON parse: `55` files, all valid.
  - Scenario registry: `48` scenarios, no unknown backend/adapter refs, no duplicates.
  - Acceptance matrix references: no missing scenario or reference artifact.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
  - Artifact hygiene: clean, `attention_count=0`.
  - Manual probe hygiene: clean, `attention_count=0`.
  - All `runs/**/*.json`: valid JSON.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_160826_488627/report.json`.
  - `python3 -m sim_plane platform-acceptance --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_reference_20260526_160322_599704/report.json`.
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs`: passed at `runs/acceptance/planner_acceptance_baseline_latest_20260526_160826_335631/report.json`.
  - `python3 -m sim_plane planner-acceptance --artifact-root runs`: passed at `runs/acceptance/planner_acceptance_baseline_reference_20260526_160322_976874/report.json`.
  - `python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root runs`: passed at `runs/human_follow_stage1_acceptance/human_follow_stage1_acceptance_latest_20260526_160323_016805/report.json`.
  - `python3 -m sim_plane human-follow-stage1-detector-tracker-acceptance --latest --artifact-root runs`: passed at `runs/human_follow_stage1_detector_tracker_acceptance/human_follow_stage1_detector_tracker_acceptance_latest_20260526_160826_432590/report.json`.
  - `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs`: passed at `runs/human_follow_stage2_acceptance/human_follow_stage2_acceptance_latest_20260526_160012_506217/report.json`.
  - `python3 -m sim_plane human-follow-stage2-integrated-acceptance --latest --artifact-root runs`: passed at `runs/human_follow_stage2_integrated_acceptance/human_follow_stage2_integrated_acceptance_latest_20260526_160826_436011/report.json`.
- Remaining intentional historical references:
  - fixed-wing and Stage2 placeholder are mentioned only as retired branches,
    not as current runnable source surfaces or retained run artifacts;
  - fixed-wing backend model mappings remain as compatibility code but are not active product scope.

- New platform-mainline inspection frontier on `2026-05-26`:
  - goal: find and classify "pests" and redundant parts in the current
    platform before any new feature work;
  - scope: `/home/coco/sim_plane` plus only reference checks into
    `/home/coco/sim_plane_ws` when needed for path validity;
  - current phase: detection and classification first, no cleanup patch until
    evidence separates confirmed issues from harmless historical residue.
- Inspection facts/hypotheses separation:
  - locked fact at that time: the repository was not yet a git repository, so file-change
    accounting used explicit scans rather than git diff;
  - locked fact: formal platform acceptance passed on latest artifacts at
    `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_162128_671607`;
  - hypothesis: likely redundant residue includes Python `__pycache__`,
    obsolete placeholder naming, legacy fixed-wing scenario/docs references,
    old repeated run artifacts, and helper scripts now superseded by CLI entrypoints;
  - forbidden until classification is complete: deleting artifacts, changing
    acceptance matrices, changing scenario behavior, or editing managed
    upstream workspaces.

- Platform inspection results on `2026-05-26`:
  - dynamic checks passed:
    - `python3 -m unittest discover -s tests`: `95` tests passed;
    - `python3 -m sim_plane doctor`: `12` ready backends and `5` ready adapters;
    - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs`: passed;
    - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_162128_671607`;
    - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean;
    - `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --json`: clean.
  - static checks passed:
    - all `59` scenario/config JSON files parsed;
    - `52` scenarios reference known backends and known adapters;
    - `6` acceptance matrices reference existing scenarios and artifacts;
    - `36` `run_*.sh` scripts reference existing scenarios;
    - internal `sim_plane.*` imports resolve;
    - Python compileall passed for `sim_plane`, `scripts`, `examples`, and `tests`;
    - shell syntax check passed for `scripts/*.sh`.
  - confirmed issues/pests:
    - two markdown links in `docs/前沿算法探针说明_zh.md` use `summary.json:1` as if it were a normal path, so markdown link validation fails even though the target `summary.json` files exist;
    - `scripts/process_cleanup.sh` and `scripts/run_px4_sih_human_follow_user_planning_ingress.sh` have shell shebangs but lack executable bits.
  - confirmed non-functional residue/redundancy:
    - Python `__pycache__` directories and `*.pyc` files exist in `sim_plane`, `scripts`, `examples`, and `tests`;
    - `runs/` contains `245` complete artifacts, including `38` historical failed artifacts; this is evidence history, not a runtime failure;
    - `runs/` is about `1.3G`, with large FlightGear `navdata_2019_1.cache` files and large manual-probe telemetry logs;
    - report roots contain retained timestamp directories beyond the current default retention shape, especially `runs/acceptance` and `runs/platform_acceptance` with `10` timestamp directories each.
  - retained-but-potentially-confusing legacy surfaces:
    - legacy/fixed-wing artifacts have been removed from `runs`, and the
      fixed-wing scenario entries were removed from the current scenario set;
    - historical Stage2 placeholder artifacts have been removed from `runs`,
      and the placeholder scenario/launch entrypoints were removed from the
      current source surface.
  - inventory mismatch / non-blocking:
    - `configs/upstreams.json` lists `14` upstream entries; `5` P2/P3 reference-only repos are not currently cloned under `/home/coco/sim_plane_ws`: `TopoTraj`, `flightmare`, `gym-pybullet-drones`, `rotors_simulator`, and `PegasusSimulator`;
    - no PX4/Gazebo/ROS/RViz/QGC/FlightGear process residue was observed;
    - checked common TCP ports `11311`, `11351`, `14540`, `14550`, `14580`, `8765`, `8876`, and `8877`; none were open as TCP listeners;
    - no shallow `/home/coco/sim_plane_ws` `.pcd`, `.bag`, or `.ulg` pollution files were found.

- Fresh platform inspection refresh on `2026-05-26` after the user's
  "pests/redundancy" request:
  - Reconfirmed clean mainline behavior:
    - `python3 -m unittest discover -s tests`: `95` tests passed.
    - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
    - `bash -n scripts/*.sh`: passed.
    - `python3 -m sim_plane doctor`: `12` ready backends, `5` ready adapters.
    - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs`: passed at `runs/acceptance/planner_acceptance_baseline_latest_20260526_151431_059152`.
    - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_151431_221235`.
    - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean.
    - `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --json`: clean.
  - Reconfirmed static consistency:
    - `52` scenario JSON files parse and have unique names.
    - All scenario `backend` and `algorithm_adapter.type` values resolve to registered platform names.
    - All acceptance matrix scenario/artifact references exist.
    - Local markdown links checked by the current validator have no missing target.
  - Confirmed issues/pests still present:
    - An obsolete manual smoke probe JSON had a prepended ROS master warning line before the JSON object; that obsolete manual smoke probe directory was removed during hygiene cleanup.
    - `docs/前沿算法探针说明_zh.md` has two local links using `summary.json:1` path suffixes; the actual files exist, but this is not a normal file path outside renderers that understand `:line`.
    - Six shebang scripts lack executable bits:
      - `scripts/process_cleanup.sh`
      - `scripts/ros_stage2_integrated_probe.py`
      - `scripts/ros_telemetry_probe.py`
      - `scripts/run_px4_sih_human_follow_user_planning_ingress.sh`
      - `scripts/select_ros_master_port.py`
      - `scripts/sync_human_follow_stage1_workspace.py`
    - Python generated files are present under `__pycache__` directories in `sim_plane`, `scripts`, `examples`, and `tests`.
  - Confirmed redundancy / retained history:
    - `runs/` has `245` complete top-level artifacts: `207` passed and `38` failed.
    - `runs/` has no incomplete top-level artifact directories.
    - Largest retained files are FlightGear `navdata_2019_1.cache` copies and large manual-probe telemetry logs.
    - Acceptance report roots contain more timestamped report dirs than a minimal retained set; this is retention redundancy, not runtime failure.
  - Confirmed non-blocking inventory mismatch:
    - `configs/upstreams.json` still lists five P2/P3 reference-only repos not currently cloned:
      - `TopoTraj`
      - `flightmare`
      - `gym-pybullet-drones`
      - `rotors_simulator`
      - `PegasusSimulator`
  - Runtime residue check:
    - No PX4/Gazebo/ROS/RViz/QGC/FlightGear residue was observed beyond this inspection's own commands.
    - TCP checks for `11311`, `11351`, `14540`, `14550`, `14580`, `8765`, `8876`, and `8877` were closed.

- Fresh sim-plane-only reread on `2026-05-10` locked the then-current Stage1 latest-acceptance failures as acceptance-noise on the sim-plane side, not `/home/coco/follwer_ws` behavior regressions:
  - `hf_stage1_acquire_center` artifact `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_acquire_center_20260509_181725/result.json` hit `max_speed_mps=0.537` in PX4 `RTL` at telemetry sample `t=12.18`, after probe success and follower launch exit.
  - `hf_stage1_lateral_left_track` artifact `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_left_track_20260509_181941/result.json` hit `max_altitude_m=0.361` in PX4 `RTL` at telemetry sample `t=10.153`.
  - `algorithm_adapter_follow_non_hold_count` was also observed to drift with managed startup timing and telemetry-window shape, so it is not a stable latest-vs-reference regression budget on this cleaned Stage1 surface.
- Sim-plane-only Stage1 acceptance-noise cleanup is now landed:
  - Stage1 behavior scenarios `scenarios/px4_sih_quadx_human_follow_case_*.json` now set `backend_options.allow_early_stop_on_adapter_success=true`.
  - `configs/human_follow_stage1_acceptance_matrix.json` now keeps only behavior-envelope regression budgets on `max_altitude_m` and `max_speed_mps`; it no longer uses `telemetry_count`, `mode_changes`, or `algorithm_adapter_follow_non_hold_count` as latest-vs-reference budgets on this early-stop-managed Stage1 surface.
- Fresh Stage1 seven-case managed rerun after that cleanup now exists:
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_acquire_center_20260509_183047/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_right_20260509_183059/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_left_20260509_183113/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_approach_retreat_20260509_183126/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_depart_follow_20260509_183140/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_left_track_20260509_183154/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_right_track_20260509_183207/result.json`
- Fresh latest Stage1 managed acceptance after that cleanup now passes:
  - report:
    - `/home/coco/sim_plane/runs/human_follow_stage1_acceptance/human_follow_stage1_acceptance_latest_20260509_183513_866342/report.json`
  - PASS facts:
    - `status=passed`
    - `issues=[]`

- The Stage1 truth-to-control managed acceptance refresh is green again on fresh `2026-05-09` evidence:
  - full-chain artifact:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_truth_full_chain_20260509_161326/result.json`
  - seven-case behavior matrix rerun artifacts:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_acquire_center_20260509_161431/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_right_20260509_161457/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_left_20260509_161526/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_approach_retreat_20260509_161554/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_depart_follow_20260509_161620/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_left_track_20260509_161647/result.json`
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_right_track_20260509_161713/result.json`
  - latest acceptance report was later superseded by the cleaned Stage1 report:
    - `/home/coco/sim_plane/runs/human_follow_stage1_acceptance/human_follow_stage1_acceptance_latest_20260509_183513_866342/report.json`
  - PASS facts:
    - `status=passed`
    - `issues=[]`
- A new managed Stage1 detector/tracker-in-loop single full-chain proof now exists entirely on the sim-plane side:
  - scenario:
    - `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_detector_tracker_full_chain.json`
  - earliest locked failure layer on the first run:
    - `bridge`
  - failure meaning:
    - detector, tracker, fusion, and controller were already alive
    - `follow_command_count=387` while `/mavros/setpoint_raw/local` had `setpoint_count=0`
    - probe failed at `wait_ready`
  - managed-only fix:
    - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/launch/stage1_truth_detector_tracker_controller_regression.launch`
    - explicitly forward `bridge_output_topic` into the included `stage1_truth_fusion_controller_regression.launch`
  - fresh passing artifact after the fix:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_detector_tracker_full_chain_20260509_163202/result.json`
  - PASS facts:
    - `status=passed`
    - detector/tracker-in-loop path stayed inside the project-side launch contract
    - the sim-plane widening remained bounded to one managed full-chain proof only
- The Stage1 detector/tracker-in-loop path is now also packaged as its own formal managed acceptance surface on the sim-plane side:
  - matrix:
    - `/home/coco/sim_plane/configs/human_follow_stage1_detector_tracker_acceptance_matrix.json`
  - acceptance module:
    - `/home/coco/sim_plane/sim_plane/human_follow_stage1_detector_tracker_acceptance.py`
  - CLI command:
    - `python3 -m sim_plane human-follow-stage1-detector-tracker-acceptance --latest --artifact-root runs --json`
  - report root:
    - `/home/coco/sim_plane/runs/human_follow_stage1_detector_tracker_acceptance/`
  - fresh formal acceptance report:
    - `/home/coco/sim_plane/runs/human_follow_stage1_detector_tracker_acceptance/human_follow_stage1_detector_tracker_acceptance_latest_20260509_191701_296089/report.json`
  - fresh runtime artifact validated by that report:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_detector_tracker_full_chain_20260509_191613/result.json`
  - current status:
    - `passed`
  - meaning:
    - detector/tracker-in-loop is no longer only a one-off scenario run
    - it now coexists with the frozen truth-driven Stage1 acceptance surface as a separate managed acceptance surface

- The managed human-follow Stage2 real-EGO integration is no longer blocked by missing packages in the sim-plane managed workspace:
  - `scripts/sync_human_follow_stage1_workspace.py` now mirrors the minimum real-EGO vendor package set from `/home/coco/follwer_ws/src/ego_planner_vendor`
  - fresh managed build evidence on `2026-05-08` proves `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1` now builds:
    - `plan_env`
    - `path_searching`
    - `bspline_opt`
    - `traj_utils`
    - `ego_planner_node`
    - `traj_server`
- A repo-local managed real-EGO Stage2 shell now exists at:
  - `/home/coco/sim_plane/sim_plane/ros/human_follow_stage2_real_ego_managed.launch`
- A repo-local real-EGO managed Stage2 scenario now exists at:
  - `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json`
- Fresh managed real-EGO Stage2 evidence now exists at:
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640/result.json`
  - fresh rerun refresh:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_102052/result.json`
- That fresh managed real-EGO artifact passed with:
  - `status=passed`
  - `algorithm_adapter_stage2_launch_name=human_follow_stage2_real_ego_managed.launch`
  - `algorithm_adapter_stage2_variant=real_ego`
  - `algorithm_adapter_stage2_goal_count=13`
  - `algorithm_adapter_stage2_distinct_goal_count=6`
  - `algorithm_adapter_stage2_ego_cmd_count=376`
  - `algorithm_adapter_stage2_distinct_ego_cmd_count=8`
  - `algorithm_adapter_stage2_waypoint_count=14`
  - `algorithm_adapter_stage2_real_ego_path_observed=true`
  - `algorithm_adapter_stage2_search_goal_observed=true`
  - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=113`
  - `algorithm_adapter_offboard_mode_reached=true`
- The fresh rerun refresh at `..._102052` also passed and preserved the managed real-EGO proof surface with:
  - `status=passed`
  - `algorithm_adapter_stage2_search_goal_observed=true`
  - `algorithm_adapter_stage2_real_ego_path_observed=true`
  - `algorithm_adapter_stage2_waypoint_count=14`
  - `algorithm_adapter_stage2_distinct_goal_count=6`
  - `algorithm_adapter_stage2_distinct_ego_cmd_count=10`
  - latest acceptance refresh:
    - `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs --json`
    - `status=passed`
- The same fresh managed artifact contains direct evidence for all three required Stage2 managed claims:
  - `follow`:
    - `stage2_follow_goal_generator state=follow`
  - `search goal`:
    - `stage2_follow_goal_generator state=search`
    - `algorithm_adapter_stage2_search_goal_observed=true`
  - `real EGO path`:
    - `/waypoint_generator/waypoints` publisher from `stage2_move_base_goal_to_waypoint_path`
    - `/waypoint_generator/waypoints` subscriber from `/ego_planner_node`
    - `algorithm_adapter_stage2_real_ego_path_observed=true`
- The first clean managed real-EGO artifact at `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_062547/result.json` exposed a sim-plane-only probe bug:
  - project-side `stage2_follow_goal_generator` already entered `state=search`
  - real-EGO path was already observed
  - but the repo-local probe misparsed `/follow/sim/truth_phase` strings such as `label=search_loss_right;visible=0;...` and falsely reported `search_goal_observed=false`
- That probe bug is now retired by a sim-plane-only fix in the current Stage2 integrated probe, and the clean rerun at `..._062640` proved the false negative is gone.
- The Stage2 real-EGO branch now also has a stricter integrated managed acceptance surface on the sim-plane side, separate from the older Stage2 existence-proof surface:
  - integrated scenario:
    - `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_stage2_real_ego_integrated.json`
  - integrated acceptance matrix:
    - `/home/coco/sim_plane/configs/human_follow_stage2_integrated_acceptance_matrix.json`
  - integrated acceptance implementation:
    - `/home/coco/sim_plane/sim_plane/human_follow_stage2_integrated_acceptance.py`
  - integrated acceptance CLI:
    - `python3 -m sim_plane human-follow-stage2-integrated-acceptance --latest --artifact-root runs --json`
  - fresh integrated artifact:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_integrated_20260509_200452/result.json`
  - fresh integrated latest acceptance report:
    - `/home/coco/sim_plane/runs/human_follow_stage2_integrated_acceptance/human_follow_stage2_integrated_acceptance_latest_20260509_200559_527102/report.json`
  - fresh integrated reference acceptance report:
    - `/home/coco/sim_plane/runs/human_follow_stage2_integrated_acceptance/human_follow_stage2_integrated_acceptance_reference_20260509_200559_522848/report.json`
  - integrated status:
    - `passed`
  - integrated managed contract now explicitly locks:
    - rolling follow goals observed
    - search goals observed after target loss
    - lost/hold behavior observed after search timeout
    - real EGO waypoint/path generation observed
    - PositionCommand and MAVROS setpoint flow preserved
  - the only new bug encountered during this packaging round was sim-plane-side:
    - the integrated probe initially exited too early and then undercounted `search_goal_count` during `long_loss`
    - both were retired by sim-plane-only fixes in the current Stage2 integrated probe
- The user explicitly redirected the human-follow branch away from Stage1 packaging questions and toward the current project-side Stage2 managed simulation integration surface.
- For this Stage2 round, only the following sources are authoritative:
  - `/home/coco/follwer_ws`
  - `/home/coco/follwer_ws/STAGE2_EGO_FRONTIER.txt`
  - `/home/coco/sim_plane/.supervisor/human_follow_collab_ledger.md`
  - `/home/coco/.codex/sessions/2026/04/27/rollout-2026-04-27T18-00-51-019dce62-7308-7b21-8782-a5ad52531cee.jsonl`
- The project-side Stage2 local green regressions prove only the Stage2 lower-half contract surfaces:
  - `stage2_ego_bridge_regression.launch`
  - `stage2_goal_adapter_regression.launch`
  - `stage2_placeholder_full_chain_regression.launch`
- Those project-side Stage2 green regressions do not prove real EGO planner integration.
- The current managed human-follow sync surface in `sim_plane` now mirrors the Stage1 package set plus `/home/coco/follwer_ws/src/quadrotor_msgs`, so the project-side `quadrotor_msgs/PositionCommand` contract can rebuild deterministically through the managed sim path.
- The existing repo-local adapter `human_follow_ros_stage1` is Stage1-specific and cannot be treated as Stage2 completion evidence because its probe semantics, success criteria, and launch assumptions are built around `FollowCommand` / `FollowState`, not the Stage2 goal-adapter / PositionCommand chain.
- The current Stage2 project-side bridge and gate responsibility split is now locked:
  - project-side Stage2 code owns `goal -> EGO adapter -> PositionCommand bridge -> OFFBOARD mode request`
  - sim-plane must still add the managed arm/probe/report wrapper needed to prove the chain against real PX4 SIH plus MAVROS
- The sim-plane side has now landed that Stage2-specific managed arm/probe/report wrapper:
  - adapter: `/home/coco/sim_plane/sim_plane/adapters/human_follow_ros_stage2.py`
  - probe: `/home/coco/sim_plane/scripts/ros_stage2_integrated_probe.py`
  - managed launch: `/home/coco/sim_plane/sim_plane/ros/human_follow_stage2_real_ego_managed.launch`
  - scenario: `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json`
- Historical managed `PX4 SIH` Stage2 placeholder artifacts existed on real MAVROS plus PX4, but they were retired and removed from `runs`; they are not current entrypoints.
- The retired latest clean rerun passed with:
  - `status=passed`
  - `algorithm_adapter_completed_successfully=true`
  - `ever_armed=true`
  - `algorithm_adapter_offboard_mode_reached=true`
  - `algorithm_adapter_stage2_goal_count=12`
  - `algorithm_adapter_stage2_ego_cmd_count=60`
  - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=102`
  - `algorithm_adapter_stage2_gate_owned_offboard_inferred=true`
- The sim-plane side also landed bounded cleanup hardening for this Stage2 surface only:
  - `px4_sih` now supports scenario-gated early stop on adapter success
  - the Stage2 managed launch now stretches the gate retry interval so the cleanup path does not immediately re-request `OFFBOARD`
  - the latest placeholder artifact was `info`-only before removal
- The monitored artifact at `/home/coco/follwer_ws/.codex/artifacts/manual_nav_goal_sessions/20260505_165935_hidden_search_recheck/monitor_all` never left the visible phase: `phase.csv` contains exactly one phase value, `label=manual_nav_goal;visible=1;display_visible=1;truth_valid=1;phase_index=0`, across all `365` samples.
- That same artifact still contains a real `search -> target_acquired -> follow` chain while remaining visible, so this round's observed search event was not caused by a successful `hidden` toggle. The first visible-phase search begins at `follow_state.csv` line `21` (`1777971970.342`), the first search command appears at `cmd_body.csv` line `21`, and reacquisition begins at `follow_state.csv` line `50` (`1777971971.791`).
- For the first visible-phase loss in that artifact, the earliest upstream dropout is fusion invalidation after a large RViz nav-goal relocation, not a controller-side spontaneous search: first nav goal at `nav_goal.csv` line `2` (`1777971970.047`), first fused-target invalid sample at `fusion.csv` line `17` (`1777971970.139`), first tracker hold at `tracker.csv` line `20` (`1777971970.288`), first tracker timeout at `tracker.csv` line `26` (`1777971970.589`).
- The same monitored run has no `manual panel toggled visibility`, `manual panel reset target`, or `manual panel cleared status note` log lines in `human_truth_keyboard_teleop-5.log`; it only shows accepted nav goals. So this artifact cannot be used as direct proof that `V` was processed successfully during the sampled interval.
- The controller did perform a real bounded search motion during the first loss interval even though the aircraft may have looked nearly stationary in RViz: between `1777971970.342` and `1777971971.791`, `cmd_body.csv` stays in `search_yaw_only` with `yaw_rate_rps=0.25`, odometry rotates by about `0.325 rad` while translating only about `0.276 m`.
- The first ROS lab path is no longer script-only knowledge; it is integrated into the shared backend registry and runner with repeated passed evidence.
- The previously open `ego_planner_swarm` shutdown and flakiness defects are now retired as active blockers.
- The stable baseline for the first lab path now includes clean probe shutdown, clean `pcl_render_node` teardown, per-artifact ROS logs, and deterministic map seeding.
- The previously open "choose `JSBSim` or `MARSIM` next" frontier is retired; `JSBSim` is now the landed widening target.
- The stable baseline includes `px4_jsbsim` with current quadrotor scenarios under the shared runner; fixed-wing smoke is now historical ledger-only context.
- The fixed-wing branch is now demoted out of the active product scope.
- `MARSIM` is no longer only a manual ROS launch path; it is now buildable, launchable, and exposed through the shared runner with both visual and headless scenarios.
- The `MARSIM` CPU sensing path now exits cleanly under `roslaunch` teardown and no longer aborts with `boost::wrapexcept<boost::lock_error>`.
- The stable quadrotor baseline now includes `marsim_single_visual` and `marsim_single` with artifact-backed pointcloud and odometry evidence.
- The previously open `MARSIM` warning-noise chain is retired; the shared-runner headless and visual paths now pass without the old `intensity` or `cascadePID` warnings.
- `FAST_LIO` has won the next-target choice over `Fast-Planner` on the current host because it composes directly with the landed `MARSIM` stack and no longer needs unmanaged dependencies once `livox_ros_driver` and `ikd-Tree` are synced.
- The first `FAST_LIO` workspace path is no longer just a thought experiment; it is buildable at `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio` and has a fresh manual smoke launch against `MARSIM`.
- `FAST_LIO + MARSIM` is no longer only a manual build-and-smoke path; it is now exposed through the shared runner with headless and visual scenarios, a repo-local safety wrapper, and artifact-backed evidence.
- The `FAST_LIO` default PCD-dump risk is retired for shared-runner usage, and the old upstream-root `PCD` pollution was cleaned after confirmation that the wrapper prevented fresh writes.
- Legacy `ego-planner` is no longer only a dedicated workspace or manual smoke path; it is now exposed through the shared runner with bounded auto-goal headless and visual scenarios.
- The legacy `ego-planner` teardown crash is retired for the shared-runner path.
- `legacy ego_planner + MARSIM` is no longer only a manual composition experiment; it is now exposed through the shared runner with headless and RViz scenarios, a repo-local cloud-only wrapper, and artifact-backed passed evidence.
- The `legacy ego_planner + MARSIM` false-obstacle and emergency-stop chain is retired for the shared-runner path when the wrapper stays cloud-only.
- `ego_planner_swarm + MARSIM` is no longer only a bounded widening idea; it is now exposed through the shared runner with headless and RViz scenarios, a repo-local direct-topic wrapper, and artifact-backed passed evidence.
- The `ego_planner_swarm + MARSIM` MD5 mismatch is retired for the shared-runner path.
- The `ego_planner_swarm + MARSIM` `FSM INIT -> no odom.` chain is retired for the direct-remap wrapper.
- Visual `MARSIM` shutdown warnings no longer pollute the shared event surface; the remaining RViz `SIGTERM` line is now confined to raw upstream stderr artifacts.
- `ego_planner + FAST_LIO + MARSIM` is no longer only a bounded widening idea; it is now exposed through the shared runner with headless and RViz scenarios, a repo-local aligned-odometry adapter, and artifact-backed passed evidence.
- The earliest planner-on-`fast_lio_marsim` frame-origin blocker is retired for the legacy `ego_planner` branch.
- The shared event surface stays clean for the new planner-on-estimator backend: both headless and visual runs emitted only `info` events.
- `ego_planner_swarm + FAST_LIO + MARSIM` is no longer only a bounded reuse question; it is now exposed through the shared runner with headless and RViz scenarios, the same repo-local aligned-odometry adapter, and artifact-backed passed evidence.
- The aligned FAST_LIO world-odom adapter reuse question is retired; it is now proven on both legacy and swarm planner branches.
- The current planner acceptance baseline now has four validated rows instead of three.
- The machine-readable acceptance matrix at `configs/planner_acceptance_matrix.json` is now executable through `python3 -m sim_plane planner-acceptance`, both frozen-reference and latest-artifact validation passed on `2026-04-28`, the gate now rejects `min_goal_distance_m` regressions larger than `0.01 m` relative to each frozen reference artifact baseline while failing loudly if the copied matrix baseline drifts from that reference artifact metric, and each invocation now persists timestamped reports plus stable latest snapshots, history trails, and compact previous-vs-current delta snapshots under `runs/acceptance/` while keeping only the newest 5 timestamped report directories per mode by default.
- A strict quadrotor platform acceptance matrix now exists at `configs/platform_acceptance_matrix.json`, and both frozen-reference and latest-artifact validation now run through `python3 -m sim_plane platform-acceptance`.
- Fresh `2026-04-28` strict platform reference artifacts now exist at `runs/px4_sih_quadx_headless_20260428_130601`, `runs/px4_sih_quadx_3d_20260428_130651`, `runs/px4_jsbsim_quadx_headless_20260428_130736`, `runs/marsim_single_20260428_130820`, `runs/marsim_single_visual_20260428_130846`, `runs/marsim_single_gpu_20260428_143322`, `runs/marsim_single_gpu_visual_20260428_143543`, `runs/fast_lio_marsim_20260428_130913`, and `runs/fast_lio_marsim_visual_20260428_131215`.
- The GPU local sensing `MARSIM` path is no longer an unlanded capability: `runs/marsim_single_gpu_20260428_143322/result.json` and `runs/marsim_single_gpu_visual_20260428_143543/result.json` both passed with `use_gpu=true`, and the shared event surfaces are now `info`-only after repo-local `opengl_render_node.cpp` shutdown hardening plus the GPU+RViz `roslaunch` wait-window bump in `sim_plane/backends/marsim.py`.
- The strict platform gate keeps those nine core rows on an `info`-only shared event surface and nests the frozen four-row planner acceptance gate instead of duplicating planner rows or weakening the top-level contract with row-specific warning exceptions.
- The transient PX4 `heading estimate invalid` startup preflight line is now classified as informational in the shared event surface because the accepted SIH and JSBSim runs continue into successful arming and takeoff on the same artifact.
- The visual `fast_lio_marsim` shutdown timeout window is now widened to `20.0 s` so the accepted reference artifact no longer emits the prior `roslaunch did not exit after SIGINT` warning in the shared event surface.
- Fresh `2026-04-28` upstream single-run planner reference artifacts now also exist at `runs/ego_planner_single_20260428_142011`, `runs/ego_planner_single_visual_20260428_142039`, `runs/ego_planner_swarm_single_20260428_141841`, and `runs/ego_planner_swarm_single_visual_20260428_141921`.
- The prior `ego_planner_swarm_single` warning flood is retired from the shared event surface: the upstream retry chatter around `a star error`, `Ran out of pool`, and `Unable to handle the initial or end point` is now classified as informational while true `EMERGENCY_STOP` transitions still remain warnings.
- The strict top-level platform baseline is no longer seven rows; it now includes fourteen quadrotor rows, adding the newly validated `PX4 + JSBSim + FlightGear` visual row on top of the upstream single-run legacy and swarm planner demo surfaces plus the GPU `MARSIM` headless and visual rows.
- The `px4_jsbsim` backend now validates the requested `jsbsim_bridge/scene/<WORLD>.xml` before launch, so unsupported world names fail early instead of collapsing later into a heartbeat timeout.
- The managed PX4 checkout now carries the minimal `sitl_run.sh` fix that honors an explicit `FG_BINARY` override, which keeps the repo-local FlightGear wrapper usable without patching the system PATH.
- The managed PX4 checkout's Gazebo Classic ExternalProject now also carries `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, which retires the host `cmake 4.2.3` configure-time blocker in `external/OpticalFlow` without widening the patch surface beyond the Gazebo Classic build hook.
- The shared control surface now exposes `px4_gazebo_classic` as a first-class backend with two fresh artifact-backed quadrotor rows: `runs/px4_gazebo_classic_iris_headless_20260428_152015` and `runs/px4_gazebo_classic_iris_visual_20260428_152300`.
- The transient PX4 startup lines `Preflight Fail: ekf2 missing data` and `Preflight Fail: system power unavailable` are now classified as informational on the shared `px4_gazebo_classic` event surface because the same artifacts continue into successful arming and takeoff.
- The strict top-level platform baseline is no longer fourteen rows; it now includes sixteen quadrotor rows by adding the clean `PX4 + Gazebo Classic` headless and native-GUI surfaces on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 + JSBSim`, `MARSIM` CPU plus GPU, and `FAST_LIO + MARSIM` rows.
- The first repo-local `MAVSDK` algorithm adapter is now landed as `mavsdk_action_takeoff`, `python3 -m sim_plane list-adapters` reports it as ready on this host, and the fresh `PX4 SIH` control-surface artifact at `runs/px4_sih_quadx_mavsdk_action_20260428_160345` passed with `algorithm_adapter_completed_successfully=true`, `algorithm_adapter_target_altitude_reached=true`, `algorithm_adapter_landed=true`, and an info-only shared event surface.
- The same repo-local `MAVSDK` adapter is now also proven on headless `PX4 + JSBSim` at `runs/px4_jsbsim_quadx_mavsdk_action_20260428_161256`, and the earliest failed attempt locked the real source-side constraint: once MAVSDK owns JSBSim's onboard `14540/14580` pair, the shared telemetry surface must move to the `Normal`-mode `14550` port.
- The same repo-local `MAVSDK` adapter is now also proven on FlightGear-visual `PX4 + JSBSim` at `runs/px4_jsbsim_quadx_mavsdk_action_visual_20260428_170517`, where the shared telemetry surface stayed clean on the `Normal`-mode `14550` port while FlightGear remained attached as the 3D viewer.
- Fresh local dependency evidence showed the current `mavsdk 3.x` wheels were import-broken on this Python `3.8` host because their generated gRPC code demanded `grpcio>=1.71.0` while that grpc wheel line was unavailable here, so the repo now pins `mavsdk>=2.8.4,<3`.
- The strict top-level platform baseline is no longer sixteen rows; it now includes seventeen quadrotor rows by adding the clean `PX4 SIH + MAVSDK` action surface on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 + JSBSim`, `PX4 + Gazebo Classic`, `MARSIM` CPU plus GPU, and `FAST_LIO + MARSIM` rows.
- The strict top-level platform baseline is no longer seventeen rows; it now includes eighteen quadrotor rows by adding the clean headless `PX4 + JSBSim + MAVSDK` action surface on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 SIH + MAVSDK`, `PX4 + JSBSim`, `PX4 + Gazebo Classic`, `MARSIM` CPU plus GPU, and `FAST_LIO + MARSIM` rows.
- The follower ROS dependency is no longer only an external `/home/coco/follwer_ws` assumption; a managed workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`, it rebuilds cleanly under `catkin_make`, and the repo-local adapter now prefers that managed root before the legacy fallback.
- The managed `human_follow_bringup` MAVROS launch now uses a local plugin list that blacklists `mount_control`, which retired the prior raw artifact noise about missing `negate_measured_*`, `debounce_s`, and `err_threshold_deg` mount parameters without changing the shared event surface contract.
- The clean disarmed `PX4 SIH + human_follow_ros_stage1` preflight artifact at `runs/px4_sih_quadx_human_follow_stage1_20260428_164845` is now frozen into the strict top-level platform gate; it proves the optional follower ROS boundary can reach `OFFBOARD`, emit valid non-hold setpoints, return PX4 to `AUTO.LOITER`, stay within a bounded low-altitude preflight envelope, and keep the shared event surface `info`-only.
- The clean armed `PX4 SIH + human_follow_ros_stage1` handoff artifact at `runs/px4_sih_quadx_human_follow_stage1_armed_20260428_164920` is now also frozen into the strict top-level platform gate; it proves the same managed follower chain can arm, cut into `OFFBOARD`, return to `AUTO.LOITER`, and remain bounded below a takeoff-grade envelope while keeping the shared event surface `info`-only.
- The strict top-level platform baseline is no longer nineteen rows; it now includes twenty quadrotor rows by adding the clean managed `PX4 SIH + human_follow_ros_stage1` armed-handoff surface on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 SIH + MAVSDK`, `PX4 + JSBSim`, `PX4 + Gazebo Classic`, `MARSIM` CPU plus GPU, `FAST_LIO + MARSIM`, and the already-landed managed disarmed follower row.
- The strict top-level platform baseline is no longer twenty rows; it now includes twenty-one quadrotor rows by adding the clean visual `PX4 + JSBSim + FlightGear + MAVSDK` action surface on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 SIH + MAVSDK`, `PX4 + JSBSim`, `PX4 + Gazebo Classic`, `MARSIM` CPU plus GPU, `FAST_LIO + MARSIM`, and the managed Stage1 follower rows.
- The shared `px4_gazebo_classic` backend now defaults each run to a dedicated local `GAZEBO_MASTER_URI`, which retired the cross-workspace Gazebo Classic pollution risk that invalidated the earlier blocker candidate.
- The repo-local `MAVSDK` action adapter now closes its aiogrpc streams explicitly, which retired the prior `WrappedIterator.__del__` thread-join traceback noise on successful PX4 adapter runs.
- The strict top-level platform baseline is no longer twenty-one rows; it now includes twenty-three quadrotor rows by adding clean headless and native-GUI `PX4 + Gazebo Classic + MAVSDK` action surfaces on top of the previously landed upstream planner demos, `PX4 SIH`, `PX4 SIH + MAVSDK`, `PX4 + JSBSim`, `PX4 + Gazebo Classic`, `MARSIM` CPU plus GPU, `FAST_LIO + MARSIM`, and the managed Stage1 follower rows.
- The formerly active `PX4 + Gazebo Classic + MAVSDK` blocker is retired: fresh official artifacts `runs/px4_gazebo_classic_iris_mavsdk_action_20260428_172653` and `runs/px4_gazebo_classic_iris_mavsdk_action_visual_20260428_172755` both passed on an `info`-only shared event surface once the contract locked dedicated local `GAZEBO_MASTER_URI` isolation plus separate onboard `14580` and GCS-facing `14550` UDP ports.
- The strict platform gate no longer only catches absolute threshold failures: it now rejects tracked metric regressions versus the frozen reference artifacts, with global budgets on `telemetry_count` and PX4-family `mode_changes`, plus tighter Stage1 follower budgets on `max_altitude_m` and `max_speed_mps`.
- ROS cleanup semantics are now unified behind a shared helper: stale-node cleanup emits `info` when it succeeds and escalates to `warning` only when `rosnode kill` fails or nodes remain live after the cleanup window. This retires the earlier risk that benign preflight hygiene could contaminate the shared acceptance surface.
- Artifact-root hygiene is now also explicit: repo-referenced incomplete manual probes belong under `runs/manual_probes/`, while unreferenced incomplete probe directories under `runs/` are stale noise and should be pruned by `python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual --prune-safe`.
- The managed `SUPER` probe now defaults to the cleaner `dense` profile, auto-selects a free ROS master port by default, fails fast if an explicitly requested port is occupied, and retained canonical evidence at `runs/manual_probes/super_benchmark_dense_20260429_153853` with `planner_warn_count=3`, `intensity_warn_count=0`, and `replan_success_count=166`.
- The managed `visPlanner` probe now also auto-selects a free ROS master port by default, fails fast on an occupied explicitly requested port, and retained canonical evidence at `runs/manual_probes/visplanner_tracking_20260429_153921` with both tracker and target command streams present and `warn_count=5`.
- Fresh serial follower-stage external planning ingress validation now exists on the local true line outside the main `sim_plane` runner surface: `stage1_external_ingress_regression.launch` passed with `planning_algorithm_template_node.py`, including explicit monitor evidence for `states=['follow','idle','lost','search','target_acquired']`, `nonzero_commands=345+`, `planning_paths=132`, `target_world_valid=124`, `odom=553+`, and `nonempty_pointcloud=93`.
- The follower-stage external planning ingress contract is now tighter than before: `stage1_controller_slot.launch` forwards `target_world`, `odom`, `pointcloud`, and `require_pointcloud`; the truth regression line now sets `controller_require_pointcloud=true`; and the live real-fusion line now forwards `/follow/lio/odom` plus the configured real pointcloud topic into the same controller slot.
- The follower-stage planning template no longer passes ingress only by consuming `target_world`; it is now exercised with `require_cloud=true` and proved against fresh nonempty pointcloud evidence on the true line.
- A user-owned follower-stage algorithm package now exists at `/home/coco/follwer_ws/src/human_follow_user`, with `user_control_node.py`, `user_planning_node.py`, and `README_CN.txt` as the single standard drop point for future user algorithms.
- Fresh serial follower-stage user-package ingress validation now exists on the local true line: `stage1_external_ingress_regression.launch external_controller_pkg:=human_follow_user external_controller_type:=user_planning_node.py require_planning_path:=true` passed with the same full monitor surface, proving that the user-owned package path is wired end-to-end instead of only the template package.
- The managed follower workspace now also contains `human_follow_user`, and a fresh shared-runner SIH artifact at `runs/px4_sih_quadx_human_follow_user_planning_ingress_20260505_151235` passed with `ever_armed=true`, `algorithm_adapter_offboard_mode_reached=true`, and `algorithm_adapter_follow_state_name=follow`, proving the user-owned planning ingress is no longer only a local true-line proof outside the main `sim_plane` runner surface.
- Direct autonomous communication with the separate follower-project Codex session is not available; for the human-follow simulation branch, cross-session coordination must happen through shared repo files plus explicit session extracts.
- A dedicated shared cross-session coordination surface now exists at `/home/coco/sim_plane/.supervisor/human_follow_collab_ledger.md`; any round that touches the human-follow simulation branch should read and update it alongside this supervisor ledger.
- The sim-plane side now has a dedicated managed follower sync/build/doc surface for the Stage1 branch:
  - sync script: `/home/coco/sim_plane/scripts/sync_human_follow_stage1_workspace.py`
  - build script: `/home/coco/sim_plane/scripts/build_human_follow_stage1_ws.sh`
  - Chinese managed-sim doc: `/home/coco/sim_plane/docs/human_follow_stage1_managed_sim_zh.md`
- The first draft of that Python sync script exposed and then retired a real sim-plane-only regression risk:
  - package-level `rsync --delete` on `human_follow_bringup` would delete the protected sim-specific MAVROS launch/pluginlist files unless those paths were excluded inside the bringup package sync itself
  - the landed fix now protects `config/mavros_px4_pluginlists_sitl.yaml`, `launch/stage1_px4_mavros.launch`, and `launch/stage1_px4_mavros_sitl.launch` both as managed-workspace invariants and as `human_follow_bringup` package-sync excludes
- After that sync-surface hardening, fresh sim-plane verification passed again on `2026-05-05`:
  - `python3 -m unittest /home/coco/sim_plane/tests/test_human_follow_ros_adapter.py /home/coco/sim_plane/tests/test_sync_human_follow_stage1_workspace.py`
  - `bash /home/coco/sim_plane/scripts/build_human_follow_stage1_ws.sh`
  - `python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root /home/coco/sim_plane/runs`
- The current narrower sim-plane sync policy for the human-follow managed workspace now mirrors only:
  - `human_follow_bringup`
  - `human_follow_control`
  - `human_follow_fusion`
  - `human_follow_msgs`
  - `human_follow_perception`
  - `human_follow_px4_bridge`
- The managed workspace still currently contains `human_follow_user`, but the new sim-plane sync policy does not treat that package as part of the minimum Stage1 truth-driven mirror until a real user algorithm is intentionally promoted into the shared runner path again.

## Newly Demoted This Round

- "The remaining Stage1 blocker is still managed `wait_ready` startup instability." is demoted.
- "The remaining Stage1 latest-acceptance failures still point to follower behavior regressions inside `/home/coco/follwer_ws`." is demoted.
- "`telemetry_count`, `mode_changes`, and `algorithm_adapter_follow_non_hold_count` are still trustworthy latest-vs-reference regression metrics on the cleaned early-stop Stage1 surface." is demoted.
- "The active human-follow frontier for sim-plane is still Stage2 real-EGO packaging." is demoted.

- "The current sim-plane Stage2 managed frontier is still placeholder-only" is demoted.
- "The managed workspace mirror is still insufficient for project-side real EGO Stage2" is demoted.
- "The earliest blocker is still whether real EGO vendor packages can build inside the managed workspace" is demoted.
- "Managed Stage2 can prove real EGO path only after a broader architectural rewrite" is demoted.
- "The search-goal part of the real Stage2 managed line is still unobservable in sim-plane" is demoted.
- "The project-side Stage2 real-EGO branch is green locally but still lacks any managed PX4 SIH proof" is demoted.
- "The current human-follow frontier is still whether to promote the newer Stage1 truth/full-chain evidence into a formal Stage1 acceptance surface" is demoted.
- "The current managed human-follow sync surface is already sufficient for the next human-follow widening target" is demoted.
- "A fresh Stage2 managed proof could reuse the Stage1 adapter semantics unchanged" is demoted.
- "This specific artifact directly proves that hidden mode failed to trigger search" is demoted.
- "This specific artifact contains a successful `V -> hidden` toggle event" is demoted.
- "The visible-phase search seen in this artifact must have been caused by controller logic alone" is demoted.
- "The current frontier is still how to expose `ego-planner-swarm` through the main control surface" is demoted.
- "The `boost::lock_error` is only a generic manual-interrupt artifact with no stronger timing evidence" is demoted.
- "The first ROS lab path still needs shutdown or repeatability triage before widening" is demoted.
- "The next bounded expansion is still undecided between `JSBSim` and `MARSIM`" is demoted.
- "Fixed-wing remains an equal-priority capability target" is demoted.
- "MARSIM still needs manual shell launch because the shared runner cannot drive it yet" is demoted.
- "MARSIM teardown still crashes in the CPU `pcl_render_node` path" is demoted.
- "The next official lab target is still undecided between `Fast-Planner` and `FAST_LIO`" is demoted.
- "The missing `ikd-Tree.cpp` in `FAST_LIO` is an upstream source defect" is demoted.
- "The current frontier is still how to formalize `FAST_LIO + MARSIM` through the main control surface" is demoted.
- "The upstream-root `FAST_LIO/PCD/scans.pcd` growth risk is still active for shared-runner usage" is demoted.
- "The next planner frontier is still undecided between `Fast-Planner` and legacy `ego-planner`" is demoted.
- "Legacy `ego-planner` still needs dedicated-workspace build or runtime triage before it can enter the shared control surface" is demoted.
- "`legacy ego_planner + MARSIM` is still blocked by a message-contract mismatch on `quadrotor_msgs/PositionCommand`" is demoted.
- "`legacy ego_planner + MARSIM` still needs dual-input depth-plus-cloud triage before it can become a shared backend" is demoted.
- "`ego_planner_swarm + MARSIM` is still blocked by a message-contract mismatch on `quadrotor_msgs/PositionCommand`" is demoted.
- "`ego_planner_swarm + MARSIM` still needs dual-input depth-plus-cloud triage before it can become a shared backend" is demoted.
- "The repo-local `ego_planner_swarm_marsim` wrapper can safely rely on chained remaps through `advanced_param.xml`" is demoted.
- "The next bounded question is still whether to choose `ego_planner_swarm + MARSIM` or keep hardening `ego_planner_marsim` first" is demoted.
- "The platform still has no validated planner stack running on top of the shared `fast_lio_marsim` estimation contract" is demoted.
- "The direct `/Odometry` planner wrapper is geometrically aligned enough to reuse without a world-frame adapter" is demoted.
- "The current frontier is still whether any planner branch can run on top of `fast_lio_marsim` at all" is demoted.
- "The aligned FAST_LIO world-odom adapter may be too legacy-specific to reuse in the swarm planner branch" is demoted.
- "The current frontier is still whether swarm can run on top of `fast_lio_marsim` at all" is demoted.
- "The upstream single-run `ego_planner_single` and `ego_planner_swarm_single` demo surfaces are too noisy to be part of the strict top-level platform gate" is demoted.
- "GPU `MARSIM` is still an unlanded capability surface" is demoted.
- "Real `Gazebo Classic` composition is still an unlanded capability surface" is demoted.
- "The platform still has no validated MAVSDK control surface" is demoted.
- "`PX4 + JSBSim + MAVSDK` can safely keep the shared telemetry collector on `14540` while MAVSDK is active" is demoted.
- "`PX4 + JSBSim + FlightGear + MAVSDK` still needs a separate visual validation surface" is demoted.
- "The Stage1 follower-preflight surface is runtime-valid but not yet part of the frozen platform acceptance matrix" is demoted.
- "The human-follow adapter still depends only on the unmanaged /home/coco/follwer_ws path" is demoted.
- "`PX4 + Gazebo Classic + MAVSDK` is still an unlanded control surface" is demoted.
- "Simply switching Gazebo Classic shared telemetry to `14550` is still insufficient after source-side cleanup" is demoted.
- "The follower-stage planning ingress still needs an explicit PASS capture" is demoted.
- "The follower-stage planning ingress may be succeeding without real pointcloud participation" is demoted.
- "The follower-stage user algorithm path still needs a dedicated package entrypoint before real user code can land cleanly" is demoted.

## Current Frontier

- Current active frontier is the generic `sim_plane` platform hygiene and objective optimization assessment.
- The human-follow Stage1/Stage2 surfaces are retained optional integration evidence, not the current feature frontier.
- Current source surface is quadrotor-mainline only; retired fixed-wing and Stage2 placeholder run artifacts have been removed from `runs/`.
- Cleanup is allowed only for classified generated residue, retired artifacts, stale report/probe directories, and stale control-doc references.
- Feature widening is paused until the platform structure and hygiene state are documented cleanly.

## Only Question Next Round

Only valid next question:

- after the cleaned platform audit, which platform-mainline gaps should be optimized or strengthened first, based on current evidence rather than human-follow project momentum?

## Forbidden Next Round

- No modifying `/home/coco/follwer_ws`.
- No reopening human-follow Stage1 or Stage2 as the current frontier unless the user explicitly switches back to that branch.
- No acceptance semantic or threshold changes during platform hygiene.
- No deleting source, scenarios, matrices, docs, or artifacts unless they are first classified as generated residue, retired non-mainline history, or stale duplicate evidence.

- No broad multi-lab parallel bring-up
- No parallel runs of the same legacy `ego_planner` stack under identical ROS node names
- No `sudo`-assumed install plan treated as already acceptable
- No building directly inside cloned upstream roots when a separate workspace can hold the integration
- No making ROS mandatory for the default `demo`, `px4_sih`, or `px4_jsbsim` paths
- No heavy 3D frontend or web framework introduction without need
- No backend-specific hacks that bypass the common runner and artifact schema
- No reopening the retired shutdown chain without fresh contradictory evidence
- No reopening the retired `MARSIM` build or teardown branches without fresh contradictory evidence
- No reopening the retired `FAST_LIO + MARSIM` formalization branch unless fresh contradictory evidence appears
- No reopening `Fast-Planner` as an equal-priority branch unless fresh evidence removes the `NLopt` dependency blocker or otherwise falsifies the lighter-path choice
- No reopening the retired `(5.0, 0.0, 1.0)` legacy `ego_planner` auto-goal branch unless fresh evidence shows the bounded `(2.5, 0.0, 1.0)` goal is insufficient
- No reopening the retired dual-input `depth + cloud` `ego_planner_marsim` wrapper shape unless fresh contradictory evidence shows the cloud-only wrapper is insufficient
- No reopening the retired chained-remap `ego_planner_swarm_marsim` wrapper shape unless fresh contradictory evidence shows the direct-remap wrapper is insufficient
- No reopening the failed direct-`/Odometry` planner wrapper shape unless fresh contradictory evidence shows the aligned-odometry adapter is unnecessary
- No reopening demoted branches as equal-priority
- No broad architectural summaries when the frontier is narrower
- No treating a local follower-stage bootstrap package as if the real user algorithm were already integrated
- No blind full-directory overwrite of the managed sim workspace without preserving the sim-specific `stage1_px4_mavros.launch` plus `config/mavros_px4_pluginlists_sitl.yaml` contract
- No package-level `rsync --delete` on `human_follow_bringup` without the landed bringup-specific exclude set for the sim MAVROS files
- No claiming "full follower sim is already landed" unless a fresh managed-workspace artifact proves the newer truth-driven/current-structure launch, not only the older synthetic Stage1 launch
- No new backend widening until `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` passes and leaves a clean `runs/platform_acceptance/latest_latest.json` snapshot plus `latest_latest_delta.json` and `history_latest.jsonl` entry, while the nested planner gate also stays green under the `0.01 m` regression budget
- Do not reopen Stage1-only acceptance promotion questions before fresh contradictory evidence appears
- Do not claim real EGO planner Stage2 completion from any placeholder planner, fake MAVROS harness, or independent `sim_plane` planner baseline
- Do not reopen the already-retired "missing real EGO package mirror" branch unless fresh contradictory evidence appears in the managed workspace
- Do not treat the first `..._062547` real-EGO artifact's `search_goal_observed=false` as project-side behavior failure; that was a retired sim-plane probe bug

## Promotion Gate

Promotion from this frontier is allowed only if one of the following is
true:

- the fresh Stage1 truth-to-control managed acceptance stays green on the cleaned early-stop surface, and the next widening is a separate Stage1 detector/tracker-in-loop managed acceptance surface with its own fresh evidence and without modifying `/home/coco/follwer_ws`
- or fresh contradictory evidence reopens a narrower sim-plane-only blocker inside the Stage1 managed chain

## Platform Hygiene Closure 2026-05-27

### Locked Facts

- Active frontier is generic `sim_plane` platform hygiene and objective optimization assessment.
- `/home/coco/follwer_ws` was not modified.
- No acceptance semantics, thresholds, or scenario behavior were changed.
- At the time of this hygiene closure, the repository was not yet a git repository; change accounting used explicit scan and command output.

### Newly Locked This Round

- Removed generated Python `__pycache__` / `*.pyc` residue and the empty `.codex` placeholder.
- Removed `93` unreferenced duplicate passed top-level artifacts while preserving referenced evidence and each scenario's latest artifact.
- Removed retired non-mainline run artifacts:
  - fixed-wing `px4_jsbsim_rascal_smoke` artifact;
  - retired Stage2 placeholder artifacts;
  - obsolete `SUPER` high-speed manual probe artifact.
- Control docs were updated so deleted artifacts are not described as current retained evidence.
- Post-cleanup `runs/` state before final verification report reruns:
  - `110` complete top-level artifacts, all `passed`;
  - `7` reserved report roots;
  - `3` retained manual probes;
  - `attention_count=0` in artifact hygiene and manual-probe hygiene.

### Newly Demoted This Round

- "Historical fixed-wing and Stage2 placeholder artifacts should stay in `runs/` as retained evidence" is demoted.
- "The old `SUPER` high-speed manual probe should remain retained alongside the cleaner dense probe" is demoted.
- "The current supervisor frontier is still human-follow Stage1 detector/tracker packaging" is demoted for this platform-mainline round.

### Current Frontier

- Objectively assess what platform-mainline areas should be optimized or strengthened next after hygiene, without widening into a project-specific branch.

### Only Question Next Round

- Which platform-mainline improvements have the best value-to-risk ratio now that the source surface and artifact root are clean?

### Forbidden Next Round

- No modifying `/home/coco/follwer_ws`.
- No reopening human-follow Stage1 or Stage2 unless explicitly requested.
- No acceptance semantic or threshold changes unless a fresh functional defect requires a narrowly justified fix.
- No deleting artifacts or files before classifying them as generated residue, retired non-mainline history, stale duplicate evidence, or stale control-doc references.

### Final Verification This Round

- `python3 -m unittest discover -s tests`: `96` tests passed.
- `python3 -m compileall -q sim_plane scripts examples tests`: passed.
- `bash -n scripts/*.sh`: passed.
- Scenario/config JSON parse: `55` files, all valid.
- Run-reference scan: `0` missing `runs/` references outside `runs/`.
- `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters, no backend issues, no adapter blocking issues.
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `110` complete artifacts, `7` reserved roots, `attention_count=0`.
- `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --json`: clean, `3` retained manual probes, `attention_count=0`.
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_162735_791020/report.json`.
- `python3 -m sim_plane platform-acceptance --artifact-root runs`: passed at `runs/platform_acceptance/platform_acceptance_baseline_reference_20260526_162736_347902/report.json`.
- `python3 -m sim_plane planner-acceptance --latest --artifact-root runs`: passed at `runs/acceptance/planner_acceptance_baseline_latest_20260526_162736_600525/report.json`.
- `python3 -m sim_plane planner-acceptance --artifact-root runs`: passed at `runs/acceptance/planner_acceptance_baseline_reference_20260526_162737_609649/report.json`.

### Promotion Gate

- Final hygiene, test, and acceptance checks are green on the cleaned artifact root; platform-mainline optimization assessment may proceed without reopening retired branches.

## Live Smoke Suite Frontier 2026-05-27

### Locked Facts

- Git/GitHub baseline is now established on `main` at `KWM925-ui/sim_plane`.
- Existing platform and planner acceptance commands mostly validate retained artifacts and reference/latest report consistency; they are not a fresh boot proof by themselves.
- The next platform-mainline gap is a one-command live smoke suite that restarts at least the light platform path and one real PX4 path.
- Current implementation work is limited to `/home/coco/sim_plane`; `/home/coco/follwer_ws` is out of scope.

### Current Frontier

- Add a repo-local `live-smoke` command with a small formal matrix, JSON/text reports, and retained report root under `runs/live_smoke/`.
- Default profile must stay lightweight and should not open GUI windows.
- Wire the existing draft `configs/live_smoke_matrix.json` and `sim_plane/live_smoke.py` into CLI, docs, tests, and artifact hygiene without changing acceptance semantics.

### Forbidden Actions

- No acceptance threshold or semantic changes.
- No human-follow branch changes.
- No heavy GUI/default simulator widening in the default smoke command.

### Closure

- Landed `python3 -m sim_plane live-smoke` as the platform-mainline fresh boot suite.
- Added `configs/live_smoke_matrix.json` with `fast`, `default`, and `core` profiles.
- Added durable reports under `runs/live_smoke/` and marked that root as artifact-hygiene reserved.
- Fresh default run passed on `2026-05-26`:
  - `demo_basic_takeoff`: `passed`, artifact `runs/basic_takeoff_20260526_170606`;
  - `px4_sih_headless`: `passed`, artifact `runs/px4_sih_quadx_headless_20260526_170611`;
  - report: `runs/live_smoke/live_smoke_default_20260526_170648_765446/report.json`.
- Verification:
  - `python3 -m unittest discover -s tests`: `100` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
  - `python3 -m sim_plane live-smoke --profile fast ...`: passed.
  - `python3 -m sim_plane live-smoke --artifact-root runs --report-root runs/live_smoke`: passed.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `8` reserved roots.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_170704_481002/report.json`.

### Next Frontier

- Dashboard/replay artifact browsing and trajectory/metric comparison is now the highest-value remaining platform-mainline hardening item.

## Dashboard Replay Comparison Frontier 2026-05-27

### Locked Facts

- The existing dashboard is lightweight and static: `sim_plane/web.py` serves `index.html`, `app.js`, `styles.css`, plus live/replay JSON endpoints.
- Current replay entrypoint can serve exactly one complete artifact directory.
- Existing artifact schema already has `manifest.json`, `scenario.json`, `result.json`, `telemetry.jsonl`, and `events.jsonl`.
- Latest platform acceptance reports already contain per-row `artifact_dir`, `reference_artifact_dir`, metrics, reference metrics, and metric regression deltas.

### Current Frontier

- Add artifact browsing and comparison to the existing lightweight dashboard without adding frontend/backend framework dependencies.
- Preserve existing `python3 -m sim_plane serve runs/<artifact>` behavior.
- Add a root-browser path for `python3 -m sim_plane serve runs` so the user can inspect retained artifacts from the same UI.
- Expose latest-vs-reference comparison data from existing acceptance report snapshots instead of changing acceptance semantics.

### Forbidden Actions

- No acceptance threshold or semantic changes.
- No generated artifact cleanup during this feature unless generated cache files are created by tests.
- No heavy frontend framework or always-on service.

### Closure

- Landed root artifact browsing through the existing dashboard:
  - `python3 -m sim_plane serve runs` now opens a dashboard over the artifact root;
  - `python3 -m sim_plane serve runs/<artifact>` still replays one artifact as before.
- Added backend JSON endpoints:
  - `/api/artifacts`
  - `/api/artifact?name=...`
  - `/api/compare?left=...&right=...`
  - `/api/platform-acceptance/latest`
- Added UI panels for artifact list, two-run comparison, metric deltas, trajectory deltas, and latest platform acceptance deltas.
- No acceptance gate, scenario behavior, or runtime backend semantics were changed.
- Verification:
  - `python3 -m unittest discover -s tests`: `103` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `8` reserved roots, `112` complete artifacts.
  - HTTP smoke on `python3 -m sim_plane serve runs --port 8879`: `/`, `/app.js`, `/styles.css`, `/api/meta`, `/api/artifacts?limit=5`, `/api/compare?...`, and `/api/platform-acceptance/latest` all returned successfully.

### Next Frontier

- Strengthen custom algorithm onboarding around `external_command` and `ros_command` with scenario generation and parameter guidance.

## Custom Algorithm Onboarding Frontier 2026-05-27

### Locked Facts

- Existing generic user ingress is already functional through:
  - `external_command` on PX4-family backends;
  - `ros_command` on `marsim` and `fast_lio_marsim`.
- Current examples require manually copying and editing JSON scenario files.
- The platform should lower first-use friction without changing adapter runtime semantics.

### Current Frontier

- Add a CLI scenario generator/parameter guide for `external_command` and `ros_command`.
- Keep generated scenario files explicit JSON under `scenarios/` or a user-specified output path.
- Do not change the existing template scenarios or adapter contracts except through additive documentation.

### Forbidden Actions

- No runtime adapter semantic changes unless tests expose a generator-only defect.
- No acceptance matrix changes.
- No `/home/coco/follwer_ws` changes.

### Closure

- Landed `python3 -m sim_plane generate-scenario`.
- Supported generator paths:
  - `--adapter external_command` for PX4-side control/decision algorithms on `px4_sih`, `px4_jsbsim`, and `px4_gazebo_classic`;
  - `--adapter ros_command` for ROS planner/perception algorithms on `marsim` and `fast_lio_marsim`.
- Added dry-run JSON preview, explicit output path, force overwrite, shell command mode, backend selection, workdir, duration/altitude overrides, RViz/GPU toggles, and ROS ready-topic overrides.
- Updated README and Chinese custom algorithm guide with generator-first workflows.
- No adapter runtime semantics, acceptance matrices, or project-specific human-follow files were changed.
- Verification:
  - `python3 -m unittest discover -s tests`: `108` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `8` reserved roots, `112` complete artifacts.
  - `generate-scenario --adapter external_command --dry-run` piped through `json.tool` and `show-scenario`: passed.
  - `generate-scenario --adapter ros_command --output /tmp/...` followed by `show-scenario`: passed.

### Next Frontier

- User rejected retaining the ROS2/Gazebo migration roadmap document.
- The roadmap document was reverted in commit `0b4046a`.
- The current frontier is not functional widening yet; first decide whether structural/small-issue hardening is objectively complete enough to permit functional work.

## Structural Gate Refresh 2026-05-27

### Locked Facts

- Active frontier is generic `sim_plane`, not human-follow.
- `/home/coco/follwer_ws` remains out of scope.
- Git/GitHub, `live-smoke`, dashboard artifact comparison, and `generate-scenario` are landed.
- The user does not want the ROS2/Gazebo migration roadmap retained now.
- A stale control-doc frontier still pointed to the rejected roadmap after the revert; this was a structural documentation defect, not a runtime defect.
- Test execution can regenerate Python `__pycache__`; those generated files must be removed before reporting a clean structural gate.

### Current Frontier

- Close the remaining structural/small-issue gate before any functional simulation widening.

### Forbidden Actions

- No functional widening until the structural gate is clean.
- No acceptance semantic or threshold changes.
- No `/home/coco/follwer_ws` changes.
- No re-adding the ROS2/Gazebo roadmap document unless explicitly requested.

### Closure Criteria

- No stale rejected-roadmap frontier references remain in active control docs.
- Git working tree is clean except for the intentional structural-doc cleanup before commit.
- Unit tests, doctor, and artifact hygiene are green.
- Generated Python cache residue is removed.

### Newly Locked This Round

- The reverted ROS2/Gazebo roadmap file remains absent, and active docs contain
  no runnable link to it.
- `.agent/PLANS.md` does not expose the old human-follow branch as current
  `Next Bounded Action`; it is retained only as historical context.
- Scenario registry consistency passed:
  - `48` scenarios;
  - all scenario names unique;
  - no unknown backend references;
  - no unknown adapter references.
- Documentation link consistency passed:
  - no missing local markdown links in README, AGENTS, or `docs/*.md`;
  - no local markdown links using renderer-specific `:line` path suffixes.
- Script hygiene passed:
  - all shebang scripts under `scripts/` are executable;
  - `bash -n scripts/*.sh` passed.
- Source hygiene passed:
  - JSON parse passed for all `scenarios/*.json` and `configs/*.json`;
  - Python AST parse passed for `sim_plane`, `scripts`, `examples`, and `tests`;
  - no generated `__pycache__` / `*.pyc` residue after cleanup;
  - no secret-token pattern hit outside ignored `runs/` artifacts;
  - no oversized source-tree files above `20M` outside `.git` and `runs`.
- Runtime residue check passed:
  - no lingering PX4/Gazebo/ROS/RViz/QGroundControl/FlightGear/jMAVSim process
    residue found after checks;
  - common ports `11311`, `11351`, `14540`, `14550`, `14580`, `8765`, `8876`,
    `8877`, and `8879` were closed as TCP listeners.

### Final Verification This Round

- `python3 -m unittest discover -s tests`: `108` tests passed.
- `python3 -m compileall -q sim_plane scripts examples tests`: passed.
- `bash -n scripts/*.sh`: passed.
- `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean,
  `reserved_root_count=8`, `complete_artifact_count=114`,
  `attention_count=0`.
- `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --json`:
  clean, `retained_manual_probe_count=3`, `attention_count=0`.
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`:
  `status=passed`.
- `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`:
  `status=passed`.
- `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`:
  `status=passed`, artifact `runs/basic_takeoff_20260527_133452`.
- `python3 -m sim_plane live-smoke --artifact-root runs --report-root runs/live_smoke --json`:
  `status=passed`, artifacts `runs/basic_takeoff_20260527_133755` and
  `runs/px4_sih_quadx_headless_20260527_133800`.
- `python3 -m sim_plane platform-acceptance --artifact-root runs --json`:
  `status=passed`.
- `python3 -m sim_plane planner-acceptance --artifact-root runs --json`:
  `status=passed`.
- Post-default-smoke artifact hygiene remained clean with
  `complete_artifact_count=116` and `attention_count=0`.

### Current Conclusion

- The structural/small-issue gate is clean based on the checked surfaces above.
- No functional simulation widening was performed in this round.
- Absolute absence of unknown future defects is not provable, but no current
  blocker was found that should prevent moving to functional work next.

### Only Question Next Round

- Choose the next functional simulation capability to widen; do not continue
  structural cleanup unless fresh evidence shows a new defect.

### Forbidden Next Round

- Do not reopen the ROS2/Gazebo roadmap document unless explicitly requested.
- Do not touch `/home/coco/follwer_ws` unless the user explicitly reopens that
  project-specific branch.
- Do not change acceptance semantics or thresholds without a fresh, narrowly
  scoped defect.

## Functional Simulation Capability Frontier 2026-05-27

### Locked Facts

- Structural/small-issue gate is clean and pushed at commit `5ca5090`.
- Current branch is the generic `sim_plane` platform mainline.
- `/home/coco/follwer_ws` is out of scope unless explicitly reopened.
- Current scenario execution is mostly one scenario per run; the platform lacks a first-class experiment surface for running controlled variants and comparing metrics.
- The built-in `demo` backend is the safest first backend for adding deterministic environmental factors because it is lightweight, fast, and covered by unit tests.

### Current Frontier

- Add the first functional simulation capability after structural cleanup: deterministic disturbance-aware scenarios plus a batch experiment runner/report surface.
- Start with the `demo` backend for zero-heavy-dependency proof, then keep the schema generic so later PX4/MARSIM mappings can reuse it.

### Hypotheses

- A small `disturbances` schema with wind, measurement noise, and initial offset can materially improve scenario expressiveness without touching heavy backends.
- A `run-suite` command over scenario variants will be more useful for algorithm validation than another single hard-coded scenario.

### Forbidden Actions

- Do not change existing acceptance thresholds or semantics.
- Do not touch `/home/coco/follwer_ws`.
- Do not add a heavy simulator or dependency for this first functional widening.
- Do not make ROS mandatory for the core platform.

### Promotion Gate

- New capability must have tests, docs, a runnable sample suite, artifact/report output, and no regression in the structural gate.

### Implementation Locked

- Added deterministic `disturbances` handling to the `demo` backend:
  - `wind`;
  - `measurement_noise`;
  - `initial_offset`;
  - deterministic `seed`.
- Added `python3 -m sim_plane run-suite`.
- Added `configs/demo_disturbance_suite.json`.
- Added `configs/px4_sih_takeoff_suite.json` for the first real PX4 SIH
  suite surface.
- Added suite report root `runs/suites/` to artifact hygiene reserved roots.
- Added per-variant `required_metrics` and `metric_thresholds` gates to
  `run-suite`, including configuration-shape validation for unsupported or
  non-numeric threshold fields.
- No existing acceptance semantics or thresholds were changed.
- Local PX4 source inspection did not find a direct SIH wind-field injection
  contract in the managed `px4_sih` path; PX4-side suite variants are therefore
  takeoff/metric variants, not fake wind variants.

### Fresh Evidence

- `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_disturbance_suite.json --artifact-root runs --report-root runs/suites --json` passed at `runs/suites/demo_disturbance_suite_20260527_150819_289292/report.json`.
- Suite variants passed:
  - `baseline`: `max_horizontal_error_m=0.0`, `max_altitude_error_m=0.0`;
  - `crosswind_light`: `max_horizontal_error_m=4.025`;
  - `sensor_noise_light`: `max_horizontal_error_m=0.192`, `max_altitude_error_m=0.071`;
  - `initial_offset`: `max_altitude_error_m=0.2`.
- `python3 -m sim_plane run-suite scenarios/px4_sih_quadx_headless.json --suite configs/px4_sih_takeoff_suite.json --artifact-root runs --report-root runs/suites --json` passed at `runs/suites/px4_sih_takeoff_suite_20260527_150949_000816/report.json`.
- PX4 SIH suite variants passed:
  - `takeoff_3m`: artifact `runs/px4_sih_quadx_headless_takeoff_3m_20260527_150840`, `max_altitude_m=3.107`, `target_altitude_reached=true`, `ever_armed=true`;
  - `takeoff_5m`: artifact `runs/px4_sih_quadx_headless_takeoff_5m_20260527_150911`, `max_altitude_m=5.963`, `target_altitude_reached=true`, `ever_armed=true`.
- Validation:
  - `python3 -m unittest tests.test_run_suite tests.test_px4_sih_backend`: `13` tests passed.
  - `python3 -m unittest discover -s tests`: `112` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `reserved_root_count=9`, `complete_artifact_count=139`, `attention_count=0`.
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260527_151020_994778/report.json`.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260527_151021_091399/report.json`.
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`: `status=passed`, artifact `runs/basic_takeoff_20260527_150955`, report `runs/live_smoke/live_smoke_fast_20260527_151000_216105/report.json`.
  - Stale simulator-process check found no lingering PX4/Gazebo/ROS/RViz/QGC/FlightGear/jMAVSim/MAVROS processes beyond the check command itself.

### Current Conclusion

- First functional simulation capability widening is complete on both the
  lightweight `demo` path and the real `PX4 SIH` flight-stack path.
- The platform now has a repeatable suite surface for controlled experiment
  batches, per-variant metric gates, durable reports, and metric spread
  summaries.
- PX4 SIH coverage is intentionally takeoff/metric-variant coverage, not fake
  wind coverage.

## Functional Parameter Sweep Frontier 2026-05-27

### Locked Facts

- The generic `run-suite` surface is landed and pushed at commit `334227f`.
- Existing suite configs still require hand-written variants.
- `/home/coco/follwer_ws` remains out of scope.
- PX4 SIH does not currently have a managed direct wind-field injection
  contract; do not represent PX4 SIH sweeps as real wind tests unless that
  contract is added later.

### Current Frontier

- Add a backend-agnostic parameter-sweep layer to `run-suite` so a suite can
  define axes and generate deterministic variant combinations automatically.
- Prove it first on the lightweight `demo` backend.

### Forbidden Actions

- Do not change existing acceptance semantics or thresholds.
- Do not add a new heavy simulator, middleware dependency, or ROS requirement.
- Do not touch `/home/coco/follwer_ws`.
- Do not fake unsupported PX4 physics.

### Promotion Gate

- Tests cover matrix expansion, variant naming, metric gates, and invalid
  sweep config.
- A runnable sample sweep config exists.
- Fresh local evidence includes the sample sweep report plus the normal
  regression checks.

### Implementation Locked

- `run-suite` now accepts either hand-written `variants` or generated `sweep`,
  never both in the same suite.
- Sweep suites support:
  - `base_overrides`;
  - `sweep.axes[].name`;
  - `sweep.axes[].path`;
  - `sweep.axes[].values`;
  - inherited suite-level `required_metrics`;
  - inherited suite-level `metric_thresholds`.
- Sweep axis paths use dotted JSON paths such as
  `disturbances.wind.y_mps`.
- Duplicate generated or hand-written variant names now fail before running.
- Variant names that collide after artifact-safe sanitizing now also fail before
  running.
- Added sample config `configs/demo_parameter_sweep_suite.json`.

### Fresh Evidence

- `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_parameter_sweep_suite.json --artifact-root runs --report-root runs/suites --json` passed at `runs/suites/demo_parameter_sweep_suite_20260527_153012_415445/report.json`.
- Generated variants passed:
  - `alt_4_0_wind_y_0_0`;
  - `alt_4_0_wind_y_-0_2`;
  - `alt_6_0_wind_y_0_0`;
  - `alt_6_0_wind_y_-0_2`.
- Sweep metric summary:
  - `max_altitude_m.spread=2.0`;
  - `max_horizontal_error_m.spread=2.0`.
- Validation:
  - `python3 -m unittest tests.test_run_suite`: `8` tests passed.
  - `python3 -m unittest discover -s tests`: `116` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `reserved_root_count=9`, `complete_artifact_count=153`, `attention_count=0`.
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260527_153059_935091/report.json`.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260527_153100_044647/report.json`.
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`: `status=passed`, artifact `runs/basic_takeoff_20260527_153108`, report `runs/live_smoke/live_smoke_fast_20260527_153113_509793/report.json`.
  - Narrow simulator-process check found no sim_plane-owned PX4/Gazebo/ROS/RViz/QGC/FlightGear/jMAVSim/MAVROS process left running.

### Current Conclusion

- The platform now has a first-class parameter sweep surface for automatically
  expanding controlled experiment matrices.
- This materially reduces manual scenario duplication when testing algorithms
  across altitude, disturbance, timeout, controller, or adapter-parameter
  variants.

## Functional Suite Analysis Frontier 2026-05-27

### Locked Facts

- `run-suite` already writes per-row metrics and global metric spreads.
- Generated sweep variants currently do not preserve machine-readable factor
  metadata in the report.
- Without factor metadata, a user still needs manual inspection to know which
  axis value caused a metric change.

### Current Frontier

- Add suite-level factor analysis for generated sweeps:
  - preserve factor names, paths, and values per generated row;
  - group numeric metrics by each factor value;
  - compute per-factor metric spread/effect ranges.

### Forbidden Actions

- Do not change existing acceptance semantics or thresholds.
- Do not add new runtime dependencies.
- Do not touch `/home/coco/follwer_ws`.
- Do not build dashboard UI before the machine-readable report surface exists.

### Promotion Gate

- Tests prove factor metadata and grouped metric analysis.
- Existing hand-written suite behavior remains compatible.
- Fresh sample sweep report and normal regression checks pass.

### Implementation Locked

- Generated sweep variants now carry per-row `factors` metadata with:
  - factor `name`;
  - dotted `path`;
  - concrete `value`.
- Suite reports now include `factor_analysis`, grouped by factor and value.
- `factor_analysis` computes numeric metric `count`, `min`, `max`, `mean`, and
  `spread` for each factor value.
- Suite reports now include `top_metric_effects`, sorted by factor-driven metric
  mean spread so the strongest parameter/metric relationships are visible
  without manually reading all rows.
- Hand-written non-sweep suites keep `factor_analysis={}`.

### Fresh Evidence

- `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_parameter_sweep_suite.json --artifact-root runs --report-root runs/suites --json` passed at `runs/suites/demo_parameter_sweep_suite_20260527_154528_204275/report.json`.
- `top_metric_effects` in that report identified:
  - `alt -> max_altitude_m`, `mean_spread=2.0`;
  - `wind_y -> max_horizontal_error_m`, `mean_spread=2.0`.
- Validation:
  - `python3 -m unittest tests.test_run_suite`: `8` tests passed.
  - `python3 -m unittest discover -s tests`: `116` tests passed.
  - `python3 -m compileall -q sim_plane scripts examples tests`: passed.
  - `bash -n scripts/*.sh`: passed.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: clean, `reserved_root_count=9`, `complete_artifact_count=161`, `attention_count=0`.
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260527_154611_659916/report.json`.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: `status=passed`, report `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260527_154611_784826/report.json`.
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`: `status=passed`, artifact `runs/basic_takeoff_20260527_154628`, report `runs/live_smoke/live_smoke_fast_20260527_154633_575043/report.json`.

### Current Conclusion

- Suite/sweep output is now diagnostic, not just archival: it can show which
  swept parameter value is associated with metric movement.
- This is the minimum machine-readable basis for future dashboard-side
  parameter-effect visualization.

## Dashboard KPI Suite Replay Closure 2026-05-28

### Locked Facts

- The active branch is the generic `sim_plane` platform mainline.
- `/home/coco/follwer_ws` is out of scope for this round.
- KPI evaluation, deterministic demo degradations, degradation suite reporting,
  and dashboard suite/KPI visibility were already landed in the working tree.
- Current local inspection found no duplicate adjacent `const item` declaration
  in `sim_plane/static/app.js`, but the dashboard JavaScript should still be
  guarded because browser-side syntax is not executed by Python unit tests.

### Current Frontier

- Close the dashboard KPI/suite replay widening without changing acceptance
  semantics:
  - simplify the suite rendering JavaScript;
  - add a dependency-free static guard for the dashboard bundle;
  - rerun project tests, compile checks, hygiene, latest acceptance, and fast
    live smoke.

### Forbidden Actions

- Do not touch `/home/coco/follwer_ws`.
- Do not change existing acceptance thresholds or scenario semantics.
- Do not add a heavyweight frontend framework or a new simulator backend.
- Do not reopen Stage1/Stage2 human-follow branches.

### Promotion Gate

- Dashboard static guard passes.
- Full unit tests pass.
- Compile and shell syntax checks pass.
- `doctor`, artifact hygiene, latest planner acceptance, latest platform
  acceptance, and fast live smoke pass.

### Implementation Locked

- `sim_plane/static/app.js` suite rendering was simplified to avoid nested
  template-expression fragments in the new suite panel.
- `tests/test_dashboard_replay.py` now includes a dependency-free dashboard
  JavaScript static guard for:
  - unterminated strings/templates/comments;
  - unbalanced `()`, `[]`, `{}`;
  - duplicate same-scope `const` / `let` bindings.
- Acceptance semantics, scenario behavior, and matrix thresholds were not
  changed.

### Fresh Evidence

- `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_degradation_suite.json --artifact-root runs --report-root runs/suites --json`
  passed at `runs/suites/demo_degradation_suite_20260528_055519_209876/report.json`.
- `python3 -m unittest tests.test_dashboard_replay` passed: `5` tests.
- `python3 -m unittest discover -s tests` passed: `123` tests.
- `python3 -m compileall -q sim_plane scripts tests` passed.
- `find scripts -maxdepth 1 -type f -name '*.sh' -print0 | xargs -0 -r bash -n`
  passed.
- Dashboard suite API smoke returned `demo_degradation_suite passed` with
  `4/4` rows.
- `python3 -m sim_plane doctor --json` reported `12` ready backends and `5`
  ready adapters.
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --json` returned
  `status=clean`.
- `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`
  passed at
  `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260528_055610_860265/report.json`.
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`
  passed at
  `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_055610_964248/report.json`
  with `changed_rows_count=0`.
- `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`
  passed at
  `runs/live_smoke/live_smoke_fast_20260528_055615_402373/report.json`.

### Current Conclusion

- The KPI/degradation functional widening and dashboard suite replay surface
  are closed cleanly for the current platform mainline.
- The new dashboard panel exposes latest suite/KPI evidence without changing
  acceptance semantics or adding frontend dependencies.
- There is no current blocker on this functional widening.

## Functional Simulation Capability Pack 2026-05-28

### Locked Facts

- The active branch is the generic `sim_plane` platform mainline.
- The user requested completion of five platform-level functional补强 lines:
  KPI evaluation, real degradation/fault injection, standardized scenario task
  library, dashboard comparison/replay enhancement, and custom algorithm
  ingress acceptance templates.
- Current KPI/degradation/dashboard basics already exist and passed.
- `/home/coco/follwer_ws` is out of scope for this round.
- PX4 SIH fault/wind support must not be faked; only metrics from real PX4
  telemetry or explicitly proven backend knobs may be used.

### Current Frontier

- Land a dependency-free functional capability pack over the existing platform:
  - make KPI calculation plugin-like and broaden the metric surface;
  - standardize lightweight demo fault/degradation knobs and task-family suites;
  - expose suite KPI ranking and strongest factor effects through dashboard API/UI;
  - add a one-command custom algorithm ingress check that runs a generated or
    existing scenario and reports interface health.

### Forbidden Actions

- Do not touch `/home/coco/follwer_ws`.
- Do not change existing platform/human-follow acceptance semantics or
  thresholds.
- Do not add AirSim/Isaac/Pegasus/Gazebo migration or another heavy backend.
- Do not label PX4 SIH suite variants as wind/fault tests unless backed by a
  real PX4-side contract.

### Promotion Gate

- Unit tests cover new KPI metrics, demo degradation knobs, suite/task configs,
  dashboard ranking, and custom ingress check behavior.
- Fresh demo task/fault suite evidence exists under `runs/suites/`.
- Normal repo validation passes: tests, compileall, shell syntax, doctor,
  artifact hygiene, latest planner/platform acceptance, and fast live smoke.

### Resume Frontier 2026-05-28

#### 已锁定事实

- 本轮只做通用 `sim_plane` 平台功能性补强，不回到 `/home/coco/follwer_ws`。
- 工作树里已经落下 KPI 插件化、demo 退化注入、任务族 suite、dashboard KPI ranking、`check-algorithm-ingress` 的主体实现。
- 还不能把本轮视为完成，直到中文文档、台账和完整验证全部收口。
- PX4 SIH 仍保持保守边界：不把 demo 里的风、dropout、通信中断等伪装成 PX4 物理故障。

#### 当前要解的问题

- 补齐中文维护文档对新能力的说明。
- 核查新增实现是否有基础接口或语义暗病。
- 刷新 demo degradation/task-family suite 与 algorithm ingress 证据。
- 跑完整验证并清理生成缓存。

#### 本轮不能做的事

- 不改 `/home/coco/follwer_ws`。
- 不新增重型仿真后端。
- 不改已有 platform/planner/human-follow acceptance 阈值或语义。
- 不把一次性 demo 证据说成真实 PX4 故障注入证据。

#### 本轮输出方式

- 只报告已实现的五条能力、对应价值、关键 artifact/report、验证 PASS/FAIL、剩余客观限制。

### Implementation Locked 2026-05-28

- `sim_plane.evaluation` 现在以插件式 `KPI_PLUGINS` 计算统一 `kpi_*`
  指标，并在共享 runner / suite runner 写入 `result.json` 前追加 KPI。
- KPI 面覆盖高度误差、超调、到达时间、稳定/恢复时间、路径误差、最终目标距离、速度/加速度峰值、速度/加速度粗糙度、速度限制违规、安全/geofence 违规、目标丢失与重捕获、传感器恢复时间和 truth-vs-measurement 误差。
- 修复了 KPI 高度时间统计的潜在错位问题：现在按“样本 + 高度值”成对计算，不会因为中间样本缺 altitude 字段而把时间戳错配。
- `sim_plane/backends/demo.py` 扩展了确定性退化/故障 knobs：
  `sensor_dropout`、`target_loss`、`sensor_latency`、`sensor_noise`、
  `measurement_bias`、`measurement_bias_drift`、
  `measurement_saturation`、`communication_interruption`、
  `control_saturation`。
- demo backend 现在可选运行 `algorithm_adapter`，并把 adapter metrics 合并到 result；adapter 失败会让 demo run 失败。
- 新增 `configs/demo_degradation_suite.json` 和
  `configs/demo_task_family_suite.json`，作为轻量鲁棒性测试和标准任务族“考试卷”。
- `run-suite` 报告新增 `kpi_rankings`，dashboard API/UI 会展示 suite KPI 排名和关键退化指标。
- 新增 `sim_plane/algorithm_ingress_check.py` 和 CLI
  `python3 -m sim_plane check-algorithm-ingress`，用于一键检查自定义算法进程/adapter/telemetry/control/KPI 是否闭环。
- `runs/algorithm_ingress` 已加入 artifact hygiene 的 reserved roots。
- `sim_plane/artifacts.py` 的 artifact 目录名现在使用微秒级时间戳，并在极端碰撞时追加序号；同时清理场景名里的路径分隔符，避免并发 suite 或异常名称污染证据目录。
- 中文维护文档和 README 已补齐功能说明、命令和边界。

### Fresh Evidence 2026-05-28

- 定向测试：
  - `python3 -m unittest tests.test_evaluation tests.test_algorithm_ingress_check tests.test_demo_run tests.test_run_suite tests.test_dashboard_replay`: `25` tests passed。
  - `python3 -m unittest tests.test_artifact_hygiene`: `6` tests passed。
- Fresh suite：
  - `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_degradation_suite.json --artifact-root runs --report-root runs/suites --json`
    passed at `runs/suites/demo_degradation_suite_20260528_070636_064192/report.json`。
  - `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_task_family_suite.json --artifact-root runs --report-root runs/suites --json`
    passed at `runs/suites/demo_task_family_suite_20260528_070642_918611/report.json`。
- Algorithm ingress：
  - demo `external_command` ingress passed at
    `runs/demo_cli_ingress_20260528_070701_928706`。
  - PX4 SIH `external_command` ingress passed at
    `runs/px4_sih_quadx_external_command_template_20260528_070701_903805`，
    with `telemetry_count=198`, `ever_armed=true`,
    `template_reached_altitude_m=3.803`, `kpi_sample_count=198`。
- Full validation:
  - `python3 -m unittest discover -s tests`: `131` tests passed。
  - `python3 -m compileall -q sim_plane scripts tests`: passed。
  - `find scripts -maxdepth 1 -type f -name '*.sh' -print0 | xargs -0 -r bash -n`: passed。
  - JSON syntax check: `61` files passed。
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `5` ready adapters。
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: `status=clean`, `attention_count=0`。
  - `python3 -m sim_plane planner-acceptance --latest --artifact-root runs --json`: passed at `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260528_070829_407378/report.json`。
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: passed at `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_070829_749673/report.json`, `changed_rows_count=0`。
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --report-root runs/live_smoke --json`: passed at `runs/live_smoke/live_smoke_fast_20260528_070859_544327/report.json`。

### Current Conclusion

- 五条功能性补强已落地并通过 fresh 验证。
- 本轮没有改变既有 platform/planner/human-follow acceptance 阈值或语义。
- 当前真实限制仍然是：PX4 SIH 故障注入保持保守，不伪造 demo 风/传感器故障为真实 PX4 物理故障；真实 PX4 故障注入后续需要逐项以 PX4 支持机制证明。

## External Test-Method Research Frontier 2026-05-28

### 已锁定事实

- 本轮是外部调研和方法论评估，不是代码实现轮。
- 研究开始时间：`2026-05-28 18:06:52 CST`。
- 当前平台已有：artifact、KPI、suite、dashboard、live-smoke、acceptance、
  PX4 SIH/JSBSim/Gazebo Classic/MARSIM/FAST_LIO/EGO-Planner 证据。
- 当前限制仍然是：不伪造 PX4 SIH 不支持的风或故障；真实故障注入必须有真实 backend 机制支撑。

### 当前要解的问题

- 网上、论文、GitHub、论坛里专业无人机仿真/算法测试通常怎么做。
- 哪些方法能直接用于当前轻量平台，哪些需要以后再做。
- 当前 `sim_plane` 到底有没有工程价值，缺口在哪里。

### 本轮不能做的事

- 不改代码。
- 不把网上项目的宣传当作本地已完成事实。
- 不把重型仿真框架当成立刻要迁移的结论。

### 本轮输出方式

- 给出来源类别、专业方法清单、和当前平台逐项对照。
- 给出下一步最值得做的测试方法建议，不写空泛路线图。

### Research Closure 2026-05-28

#### 已查方向

- PX4 官方 `MAVSDK` integration testing、SITL/CI、failure injection、failsafe simulation、ULog/Flight Review。
- ArduPilot `autotest` 框架、DataFlash/tlog 产物、可本地复现实验失败的测试组织方式。
- 论文/开源仿真器方向：Flightmare、FlightGoggles、RotorS、gym-pybullet-drones、safe-control-gym、Aerial Gym、Agilicious、Pegasus/Isaac Sim。
- 场景生成/反例搜索方向：Scenic、VerifAI、Avis、Aerialist 等 simulation-based testing / falsification / fault-injection 方法。
- 生命周期风险：Gazebo Classic EOL、ROS1 Noetic EOL、AirSim archived、Gazebo Harmonic/现代 Gazebo 的系统约束。

#### 外部方法结论

- 专业无人机仿真测试的核心不是单一重型 3D 后端，而是：
  - 可重复场景；
  - 真实飞控闭环；
  - 一键运行与日志收集；
  - KPI/安全指标；
  - latest-vs-reference 回归；
  - 故障/退化注入；
  - flight-log 级别复盘；
  - CI/live-smoke；
  - 必要时再使用高保真视觉/物理后端。
- PX4 官方推荐 MAVSDK integration testing 作为端到端集成测试路径，测试 runner 负责启动 PX4/Gazebo 并收集日志。
- PX4 failure injection 是真实故障注入的首选下一步，但必须受 `SYS_FAILURE_EN`、模拟器支持范围、failure type 支持范围限制，不能把 demo dropout/wind 冒充 PX4 真实故障。
- ArduPilot `autotest` 强调本地复现、标准日志、flight track 和 failure bisect，这提示 `sim_plane` 后续应加强自动 artifact 复盘和日志指标提取。
- safe-control-gym/gym-pybullet-drones 这类 benchmark 提示控制算法评测应重点看轨迹跟踪、约束/扰动、控制器对比和仿真加速，而不只是 pass/fail。
- Flightmare/FlightGoggles 等高保真视觉仿真器说明视觉/感知算法需要更强 sensor realism，但不应立刻替代当前轻量默认路径。
- Gazebo Classic 与 ROS1 Noetic 的 EOL 风险属实，但当前主机仍以 Ubuntu 20.04 为约束，不建议立即迁移导致平台失稳。

#### 对当前平台的客观判断

- 当前 `sim_plane` 是有用的，而且方向基本对：
  - 已有统一 runner、artifact、KPI、suite、dashboard、live-smoke、acceptance、PX4 SIH/JSBSim/Gazebo Classic/MARSIM/FAST_LIO/EGO-Planner 能力面；
  - 已具备专业测试平台所需的重复性、集成验证、指标评估和轻量退化测试雏形。
- 当前还不是“最终专业封顶版”：
  - PX4-native failure injection acceptance 尚未成为正式验收面；
  - ULog/flight-log 自动 KPI 与 latest-vs-reference 趋势还不够深；
  - 场景 fuzz/sweep/反例搜索还没系统化；
  - 高保真视觉/传感器 realism 只在 MARSIM/ROS 路径上有基础，不等同于 Flightmare/FlightGoggles 级别视觉仿真；
  - CI 化打包可以继续加强。

#### 下一步最值钱方向

1. PX4-native failure-injection acceptance：只用 PX4 官方支持的 `failure`/MAVSDK failure plugin/真实 failsafe 参数，先覆盖 gps/gyro/baro/mavlink_signal 等可证明项。
2. ULog/flight-log KPI replay：把 PX4 `.ulg` 或 telemetry artifact 转成统一 KPI、异常事件、模式切换、failsafe 证据和 latest-vs-reference 趋势。
3. Scenario fuzz/sweep generator：围绕初始位姿、目标点、延迟、dropout、速度限制、通信中断做可复现实验矩阵，自动找最差 case。
4. CI/live smoke pack：把本机一键 smoke、latest acceptance、artifact hygiene、关键 suite 固化成更接近官方 autotest/CI 的标准入口。
5. 视觉/感知 realism 只在有具体视觉算法需求时推进，不现在盲目换重后端。

## PX4 Native Failure Injection Frontier 2026-05-28

### 已锁定事实

- 当前主线回到通用 `sim_plane` 平台，不碰 `/home/coco/follwer_ws`。
- 上一轮外部调研结论已经锁定：下一步优先补真实 PX4 failure-injection 验收面，而不是换重型后端。
- 本机 `mavsdk.failure` 模块可 import。
- 当前 PX4 源码包含 `MAV_CMD_INJECT_FAILURE=420`、failure unit/type 枚举，且 POSIX `rcS` 默认设置 `SYS_FAILURE_EN=1`。
- 当前 `px4_sih` backend 已支持 `algorithm_adapter`，但没有 PX4-native failure injection adapter 或独立 acceptance surface。

### 当前要解的问题

- 新增一个独立、平台通用的 PX4-native failure-injection 能力面：
  - 使用 MAVSDK failure plugin 或等价 MAVLink 命令；
  - 记录注入是否被 PX4 接受；
  - 记录注入前后健康/模式/飞行状态指标；
  - 形成独立 scenario、acceptance matrix、CLI/report root；
  - 不污染现有 `platform-acceptance`。

### 本轮不能做的事

- 不改 `/home/coco/follwer_ws`。
- 不改现有 platform/planner/human-follow acceptance 阈值或语义。
- 不把 demo backend 的 dropout/wind 等伪装成 PX4 真实故障。
- 不强行要求 PX4 在每一种 failure 上都触发同一种 failsafe；只有本轮 fresh artifact 能证明的行为才能进验收。
- 不新增 AirSim/Isaac/Gazebo Harmonic 等重后端。

### 验收门槛

- 新 adapter 有单元测试覆盖地址解析、failure enum 解析、环境校验。
- 新 acceptance 能检查独立 failure-injection artifact。
- Fresh `px4_sih` failure-injection scenario 跑通，且报告里明确 `failure_injection_accepted=true`。
- 常规项目验证至少覆盖相关单测、compileall、JSON 语法、doctor、artifact hygiene、latest platform acceptance。

### Implementation Locked 2026-05-28

- 新增通用 MAVSDK failure adapter：
  - `sim_plane/adapters/mavsdk_failure.py`
  - adapter type: `mavsdk_failure_injection`
  - 使用 MAVSDK failure plugin 发送 PX4 `MAV_CMD_INJECT_FAILURE`
  - 记录 `failure_injection_accepted`、`failure_injection_reset_accepted`、failure unit/type/instance、注入前后 health/flight mode。
- 新增独立场景：
  - `scenarios/px4_sih_quadx_mavsdk_failure_motor.json`
  - backend: `px4_sih`
  - adapter: `mavsdk_failure_injection`
  - 当前锁定的已证明组合：`SYSTEM_MOTOR/OFF`，instance `1`，随后 `SYSTEM_MOTOR/OK` 复位。
- 新增独立验收面：
  - matrix: `configs/px4_failure_injection_acceptance_matrix.json`
  - module: `sim_plane/px4_failure_acceptance.py`
  - CLI: `python3 -m sim_plane px4-failure-acceptance --latest --artifact-root runs`
  - report root: `runs/px4_failure_injection_acceptance/`
- 新增通用验收 helper：
  - `sim_plane/acceptance_common.py`
  - 避免平台通用 PX4 验收反向依赖 human-follow 专用模块。
- `runs/px4_failure_injection_acceptance` 已加入 artifact hygiene reserved roots。
- README 和中文维护文档已说明：
  - 这是真 PX4 failure injection，不是 demo dropout/wind；
  - 当前只证明 motor failure path；
  - `gps`、`rc_signal`、`mavlink_signal` 等其它 failure unit 必须逐项 fresh 证明后才能进入正式矩阵。

### Fresh Evidence 2026-05-28

- 反证/边界探针：
  - 临时 shell probe `failure rc_signal off` 在当前 SIH 上出现 `Timeout waiting for ack`，因此未进入正式验收。
  - 临时 shell probe `failure motor off -i 1` 可触发 PX4 日志 `CMD_INJECT_FAILURE, motor 1 off/ok`，但临时 probe artifact 已清理，只保留结论。
- 正式 fresh artifact：
  - `runs/px4_sih_quadx_mavsdk_failure_motor_20260528_105546_340839/result.json`
  - `status=passed`
  - `failure_injection_backend=px4_mavsdk_failure_plugin`
  - `failure_injection_command=MAV_CMD_INJECT_FAILURE`
  - `failure_injection_unit=SYSTEM_MOTOR`
  - `failure_injection_type=OFF`
  - `failure_injection_instance=1`
  - `failure_injection_accepted=true`
  - `failure_injection_reset_type=OK`
  - `failure_injection_reset_accepted=true`
  - `event_levels={"info": 19}`
  - PX4 backend log contains `CMD_INJECT_FAILURE, motor 1 off` and `CMD_INJECT_FAILURE, motor 1 ok`.
- Acceptance:
  - `python3 -m sim_plane px4-failure-acceptance --artifact-root runs --json`: passed at
    `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_reference_20260528_105636_585354/report.json`
  - latest refresh passed at
    `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260528_105935_086917/report.json`
- Verification:
  - `python3 -m unittest tests.test_mavsdk_failure_adapter tests.test_px4_failure_acceptance`: passed, `11` tests.
  - targeted suite passed, `31` tests.
  - `python3 -m unittest discover -s tests`: passed, `142` tests.
  - `python3 -m compileall -q sim_plane scripts tests`: passed.
  - JSON syntax check: `63` scenario/config JSON files passed.
  - `python3 -m sim_plane list-adapters`: `mavsdk_failure_injection: ready`.
  - `python3 -m sim_plane doctor --json`: `12` ready backends, `6` ready adapters.
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`: `status=clean`, `attention_count=0`.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`: passed at
    `runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_105935_241492/report.json`, `changed_rows_count=0`.

### Current Conclusion

- PX4-native failure injection 已经从“建议方向”变成正式平台能力面。
- 这条能力面当前只证明 `PX4 SIH + MAVSDK failure plugin + SYSTEM_MOTOR/OFF/OK`。
- 还不能声称所有 PX4 failure unit 都可用；下一步若继续扩展，应按 `gps`、`baro`、`mavlink_signal` 等逐项 fresh probe，再把被接受的组合加入矩阵。

## Professional Test Surface Closure Frontier 2026-05-28

### 已锁定事实

- 本轮用户要求把上一轮外部专业测试方法对照中提到的剩余项继续做完并测试。
- 当前通用平台主线已经具备：KPI、suite、dashboard、live-smoke、algorithm ingress、PX4-native motor failure acceptance。
- `runs/` 下当前没有 `.ulg`，但 PX4 build root 下存在 historical `.ulg`，且本机 Python 可 import `pyulog`。
- 真实 PX4 failure injection 不能扩大成未经 fresh 证明的故障类型。

### 当前要解的问题

- 把剩余专业测试能力做成正式平台入口：
  - `flight-log` / artifact telemetry KPI replay；
  - reproducible scenario fuzz/sweep 和最差 case 排名；
  - CI/autotest-like 一键测试包；
  - dashboard 可看这些新报告。

### 本轮不能做的事

- 不碰 `/home/coco/follwer_ws`。
- 不迁移到 AirSim/Isaac/Gazebo Harmonic。
- 不改现有 platform/planner/human-follow/PX4 failure acceptance 语义。
- 不把 demo backend 的 disturbance/fuzz 说成 PX4 原生物理故障。
- 不把 PX4 build root 下的历史 `.ulg` 当成当前 artifact 已经自动采集的证明。

### 验收门槛

- 新能力都有 CLI 标准命令、报告根目录、单元测试。
- 新报告根目录纳入 artifact hygiene reserved roots。
- 至少用现有本地 artifact fresh 跑通 flight-log/artifact replay。
- 至少 fresh 跑通一个 fuzz/sweep 报告，并能产出 worst-case/KPI 排名。
- 至少 fresh 跑通 fast profile 的 autotest pack。
- 最后跑 targeted tests、compileall、JSON 检查、doctor、artifact hygiene、platform latest acceptance。

### Implementation Locked 2026-05-28

- 新增 flight-log / artifact replay：
  - module: `sim_plane/flight_log_analysis.py`
  - CLI: `python3 -m sim_plane flight-log-analyze <artifact-or-ulg>`
  - report root: `runs/flight_log_analysis/`
  - artifact 输入读取 `telemetry.jsonl` / `result.json` / `events.jsonl`
  - `.ulg` 输入通过 `pyulog` 解析 `vehicle_local_position`、`vehicle_status`、日志 warning/dropout 等。
- 新增 deterministic scenario fuzz：
  - module: `sim_plane/scenario_fuzz.py`
  - CLI: `python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast --seed 20260528`
  - report root: `runs/scenario_fuzz/`
  - 报告保存 `generated_suite.json`、fresh variant artifacts、`worst_cases`。
- 新增 CI/autotest-like fast pack：
  - module: `sim_plane/autotest_pack.py`
  - CLI: `python3 -m sim_plane autotest-pack --profile fast`
  - report root: `runs/autotest/`
  - fast pack 串联 doctor、artifact hygiene、live-smoke fast、demo degradation suite、scenario fuzz、flight-log artifact replay、PX4 failure latest acceptance、platform latest acceptance。
- `run-suite` 现在支持内存生成的 `suite_definition`，避免 fuzz 运行前制造临时 suite 文件。
- dashboard 后端/前端新增 `Professional Test Surfaces`，展示 PX4 failure、flight-log、scenario fuzz、autotest 的 latest report 摘要。
- 新 report roots 已加入 artifact hygiene reserved roots：
  - `flight_log_analysis`
  - `scenario_fuzz`
  - `autotest`

### Fresh Evidence 2026-05-28

- `python3 -m unittest tests.test_flight_log_analysis tests.test_scenario_fuzz tests.test_autotest_pack tests.test_run_suite tests.test_dashboard_replay tests.test_artifact_hygiene` passed: `32` tests。
- `python3 -m sim_plane flight-log-analyze runs/px4_sih_quadx_mavsdk_failure_motor_20260528_105546_340839 --report-root runs/flight_log_analysis --json` passed:
  - `runs/flight_log_analysis/artifact_px4_sih_quadx_mavsdk_failure_motor_20260528_105546_340839_20260528_112327_129051/report.json`
  - source_type=`artifact`, telemetry_count=`41`, mode_change_count=`1`, anomaly_event_count=`0`。
- `python3 -m sim_plane flight-log-analyze /home/coco/sim_plane_ws/src/core/PX4-Autopilot/build/px4_sitl_default/rootfs/log/2026-04-28/17_28_07.ulg --report-root runs/flight_log_analysis --json` passed:
  - `runs/flight_log_analysis/ulog_17_28_07_20260528_112503_012345/report.json`
  - source_type=`ulog`, ulog_dropout_count=`0`, nav_state_change_count=`4`, arming_state_change_count=`2`, ulog_warning_message_count=`2`。
- `python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast --seed 20260528 --variants 6 --artifact-root runs --report-root runs/scenario_fuzz --json` passed:
  - `runs/scenario_fuzz/demo_seeded_fuzz_20260528_20260528_112342_404826/report.json`
  - rows=`7`, status=`passed`, worst cases include measurement error/dropout/roughness/acceleration/path-error metrics。
- First `autotest-pack` run exposed a wrapper status normalization bug:
  - artifact hygiene returned `status=clean`
  - pack step initially treated only `passed` as success
  - fixed with `is_success_status({"passed","clean"})` and test coverage.
- Refreshed `python3 -m sim_plane autotest-pack --profile fast --artifact-root runs --report-root runs/autotest --json` passed:
  - `runs/autotest/sim_plane_autotest_fast_20260528_112450_660913/report.json`
  - all `8/8` steps passed。

### Current Conclusion

- 上一轮外部专业测试方法中“最值钱”的平台侧测试面已经落到正式命令和报告：
  - PX4-native failure acceptance 已完成；
  - flight-log/artifact replay 已完成；
  - scenario fuzz/worst-case ranking 已完成；
  - CI/autotest fast pack 已完成；
  - dashboard test-surface visibility 已完成。
- 仍需客观保留的边界：
  - `.ulg` 解析能力已证明，但 fresh PX4 run 自动收集 `.ulg` 到 artifact 还未实现；
  - demo fuzz 是轻量可复现鲁棒性测试，不是 PX4 原生故障；
  - PX4 failure surface 仍只证明 `SYSTEM_MOTOR/OFF/OK`。

### Final Validation 2026-05-28

- `python3 -m unittest tests.test_flight_log_analysis tests.test_scenario_fuzz tests.test_autotest_pack tests.test_run_suite tests.test_dashboard_replay tests.test_artifact_hygiene tests.test_px4_failure_acceptance tests.test_mavsdk_failure_adapter` passed: `44` tests。
- `python3 -m unittest discover -s tests` passed: `152` tests。
- `python3 -m compileall -q sim_plane scripts tests` passed。
- Shell syntax check passed:
  - `find scripts -maxdepth 1 -type f -name '*.sh' -print0 | xargs -0 -r bash -n`
- JSON syntax check passed: `63` scenario/config JSON files。
- `python3 -m sim_plane doctor --json` passed:
  - `12` ready backends
  - `6` ready adapters。
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --json` passed:
  - `status=clean`
  - `reserved_root_count=14`
  - `complete_artifact_count=241`
  - `attention_count=0`。
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json` passed:
  - `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_112901_884254/report.json`
  - `changed_rows_count=0`。
- Dashboard API smoke passed:
  - `list_test_surface_reports('runs')` returned `5` latest surfaces:
    PX4 failure, flight log artifact, ULog, scenario fuzz, autotest; all `passed`。
- Non-functional cleanup:
  - compile-generated `__pycache__` / `*.pyc` under `sim_plane scripts tests` were removed.
