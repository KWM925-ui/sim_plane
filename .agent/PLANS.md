# Execution Plan

## Platform Mainline Frontier (2026-05-26)

- The current active frontier is back on the generic `sim_plane` platform itself, not on the project-specific `human-follow` branch.
- The `human-follow` Stage1/Stage2 managed surfaces remain retained evidence and optional integrations, but they are not the product-mainline feature target for this round.
- Git/GitHub baseline is established on `main` at `KWM925-ui/sim_plane`.
- The one-command live smoke suite is now landed:
  - `python3 -m sim_plane live-smoke --profile fast` runs only the built-in demo row for the fastest sanity check;
  - `python3 -m sim_plane live-smoke` runs the default fresh boot proof over `demo_basic_takeoff` plus headless `PX4 SIH`;
  - reports are retained under `runs/live_smoke/`;
  - this is distinct from acceptance because it creates fresh run artifacts instead of only checking retained reference/latest artifacts.
- The bounded platform onboarding step is now landed:
  - `python3 -m sim_plane doctor` reports which backends and adapters are ready on the current machine;
  - template adapter missing-command messages are shown as notes, not blocking readiness issues;
  - it recommends the lightest control-algorithm path, the ROS planner/perception path, the visual demo path, latest platform acceptance, and artifact hygiene commands;
  - it prints exact next commands the user can run.
- This step did not change any existing acceptance semantics, matrix thresholds, or project-specific scenario behavior.
- Fresh verification on `2026-05-26`:
  - `python3 -m unittest tests.test_doctor tests.test_artifact_hygiene` passed.
  - `python3 -m sim_plane doctor` reports `12` ready backends and `5` ready adapters.
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_162128_671607`.
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual` reports clean with retained report roots after artifact deduplication.
- The artifact hygiene reserved-root set now includes the formal Stage1 detector/tracker and Stage2 integrated human-follow acceptance report roots, so those report roots are retained as report roots rather than migrated into `manual_probes`.
- The artifact hygiene reserved-root set now also includes `live_smoke`.
- Next mainline options should stay platform-generic:
  - add a non-human-follow sample planner/control algorithm that exercises the generic adapters;
- Dashboard/replay comparison UX is now landed:
  - `python3 -m sim_plane serve runs` opens the artifact browser;
  - the dashboard can compare two artifacts by metrics and trajectory;
  - it can show the latest platform acceptance delta snapshot.
- Custom algorithm scenario authoring is now landed:
  - `python3 -m sim_plane generate-scenario --adapter external_command ...`;
  - `python3 -m sim_plane generate-scenario --adapter ros_command ...`;
  - generated JSON remains explicit and reviewable under `scenarios/` or a user-selected output path.

## Objective

- Deliver a lightweight but strong UAV algorithm simulation platform that can run on the current machine and stay easy to operate, integrate, and extend.
- Keep the initial platform focused on a practical MVP rather than a maximal full-stack simulator.

## Current Facts

- The repository has been bootstrapped with control and design documents and now includes a runnable Python MVP skeleton.
- The workspace is a git repository with a GitHub remote at `KWM925-ui/sim_plane`.
- Host OS: `Ubuntu 20.04.6 LTS`.
- CPU threads: `16`.
- RAM observed on `2026-04-27`: `14 GiB total`, about `7.2 GiB available`.
- Disk free under the workspace mount: about `84 GiB`.
- GPUs observed on `2026-04-27`: `NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB)` and integrated AMD graphics.
- PX4 official docs describe `SIH` as a lightweight, headless simulator with zero external dependencies, with examples for `sihsim_quadx` and `sihsim_airplane`.
- PX4 official docs show `JSBSim` supports `Plane`, `Quadrotor`, and `Hexarotor`.
- PX4 official docs show `Gazebo Classic` supports multiple vehicle types and can run headless with fewer resources.
- Gazebo Harmonic official binary installation currently targets Ubuntu `22.04` and `24.04`, not `20.04`.
- Open Robotics states Gazebo Classic reached end-of-life in `January 2025`.
- ROS states ROS 1 Noetic reached end-of-life on `2025-05-31`.
- PX4 docs recommend `MAVSDK` as easier to learn than `ROS 2` and suitable for low-bandwidth command/control.
- QGroundControl current `master` and `v5.0` docs target Ubuntu `22.04` and `24.04`, while `v4.4.3` docs still document Ubuntu `20.04` and later. The docs recommend at least `8 GiB RAM`.
- The repository now contains a runnable Python MVP skeleton with a backend interface, a demo backend, artifact output, and a local web dashboard.
- A fresh local run succeeded with `python3 -m sim_plane run scenarios/basic_takeoff.json --visualize` and wrote artifacts under `runs/basic_takeoff_20260427_104415`.
- A fresh local replay succeeded with `python3 -m sim_plane serve runs/basic_takeoff_20260427_104415 --port 8877`.
- `px4_sih` is now implemented with PX4 path discovery, process supervision, MAVLink telemetry ingestion through `pymavlink`, artifact logs, and optional `QGroundControl` / `jMAVSim` launch.
- `QGroundControl.AppImage` exists at `/home/coco/桌面/QGroundControl.AppImage`.
- `gazebo` and `gz` are installed on the host.
- `python3 -m sim_plane list-backends` now reports `demo: ready`, `ego_planner: ready`, `ego_planner_fast_lio_marsim: ready`, `ego_planner_marsim: ready`, `ego_planner_swarm: ready`, `ego_planner_swarm_fast_lio_marsim: ready`, `ego_planner_swarm_marsim: ready`, `fast_lio_marsim: ready`, `marsim: ready`, `px4_jsbsim: ready`, and `px4_sih: ready`.
- The managed PX4 checkout now exists at `/home/coco/sim_plane_ws/src/core/PX4-Autopilot`.
- The local `jMAVSim` toolchain now exists under `/home/coco/sim_plane_ws/toolchains/jdk-17` and `/home/coco/sim_plane_ws/toolchains/apache-ant-1.10.17`.
- `java` and `ant` are still not guaranteed on the system PATH, but the backend can resolve them from the local toolchain root next to the managed PX4 checkout.
- A fresh live headless SIH run succeeded with `python3 -m sim_plane run scenarios/px4_sih_quadx_headless.json --artifact-root /home/coco/sim_plane/runs --px4-dir /home/coco/sim_plane_ws/src/core/PX4-Autopilot --no-hold-open` and wrote `runs/px4_sih_quadx_headless_20260427_114632/result.json` with `status=passed`, `max_altitude_m=5.958`, `target_altitude_reached=true`, and `ever_armed=true`.
- A fresh default-path `QGroundControl` script run succeeded with `./scripts/run_px4_sih_qgc.sh --artifact-root /home/coco/sim_plane/runs --no-hold-open` and wrote `runs/px4_sih_quadx_20260427_120430/result.json` with `status=passed`, `max_altitude_m=5.569`, `target_altitude_reached=true`, and `ever_armed=true`.
- A fresh default-path SIH 3D script run succeeded with `./scripts/run_px4_sih_3d.sh --artifact-root /home/coco/sim_plane/runs --no-hold-open` and wrote `runs/px4_sih_quadx_3d_20260427_120519/result.json` with `status=passed`, `QGroundControl` launch, and `jMAVSim` launch.
- The 3D SIH evidence is artifact-backed in `runs/px4_sih_quadx_3d_20260427_120519/events.jsonl`, including repeated `commander takeoff`, PX4 mode changes into `TAKEOFF` and `LOITER`, and the final pass result.
- The managed upstream reference set is now cloned under `/home/coco/sim_plane_ws/src`, including `PX4-Autopilot`, `ego-planner`, `ego-planner-swarm`, `Fast-Planner`, `MARSIM`, `FAST_LIO`, and `livox_ros_driver`.
- The `ego-planner` upstream README explicitly recommends `ego-planner-swarm` as the more robust target and states that single-drone use should set `drone_id=0`.
- The current `MARSIM` checkout is on the upstream `ubuntu20` branch, and its README still points to ROS1 launch entrypoints such as `roslaunch test_interface single_drone_avia.launch`.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_marsim`.
- A fresh `catkin_make -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -j1` run completed successfully in `/home/coco/sim_plane_ws/workspaces/ros1_marsim`.
- The earliest `MARSIM` source-side blocker was `glfw3` package discovery in `local_sensing/CMakeLists.txt`; the local patch now falls back to raw library lookup and disables `opengl_render_node` when `glfw3` is absent so the CPU `pcl_render_node` path remains available.
- The earliest `MARSIM` runtime blocker was `quad0_pcl_render_node` aborting on `SIGINT` with `boost::wrapexcept<boost::lock_error>`; the local shutdown hardening now stops timers, shuts down ROS interfaces explicitly, and returns cleanly under `roslaunch` teardown.
- The `MARSIM` launch file now treats `use_gpu_` and `launch_rviz` as overridable args, which allows the shared runner to choose visual or headless launch shapes cleanly.
- Project-local helpers now exist for the `MARSIM` path: `scripts/build_marsim_ws.sh`, `scripts/run_marsim_single.sh`, and `scripts/run_marsim_single_visual.sh`.
- The main control surface now exposes `marsim`, and `python3 -m sim_plane list-backends` reports `demo: ready`, `ego_planner_swarm: ready`, `marsim: ready`, `px4_jsbsim: ready`, and `px4_sih: ready`.
- A fresh main-surface visual `marsim` run passed at `runs/marsim_single_visual_20260427_163908/result.json` with `telemetry_count=89`, `pointcloud_seen=true`, `max_pointcloud_width=20303`, and `launch_rviz=true`.
- A fresh main-surface headless `marsim` run passed at `runs/marsim_single_20260427_164011/result.json` with `telemetry_count=89`, `pointcloud_seen=true`, `max_pointcloud_width=20315`, and `launch_rviz=false`.
- The `MARSIM` CPU sensing path now loads both the UAV mesh PCD and the incoming `global_map` cloud without emitting the prior missing-`intensity` warning by assigning a synthetic fallback intensity only when the source fields omit it.
- The `cascadePID` ROS package has been normalized to `cascade_pid`, the internal `ros::package::getPath(...)` call now matches that package name, and the prior package-naming warning chain is retired.
- Fresh shared-runner `MARSIM` evidence after the noise cleanup now exists at `runs/marsim_single_20260427_170126/result.json` and `runs/marsim_single_visual_20260427_170213/result.json`; both passed and their event streams no longer contain the prior `intensity` or `cascadePID` warning noise.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_ego_swarm`.
- A fresh `./scripts/build_ego_planner_swarm_ws.sh` run completed successfully and rebuilt the workspace in place.
- A fresh `roslaunch ego_planner single_run_in_sim.launch` run started the expected nodes and published live `/drone_0_visual_slam/odom`.
- A fresh `roslaunch ego_planner rviz.launch` run started the RViz viewer path.
- Project-local helpers now exist for the first lab stack: `scripts/build_ego_planner_swarm_ws.sh`, `scripts/run_ego_planner_swarm_single.sh`, and `scripts/run_ego_planner_swarm_single_visual.sh`.
- The retained manual visual probe for the first swarm viewer path now lives under `runs/manual_probes/ego_planner_swarm_single_visual_20260427_202122`, while top-level `runs/` is reserved for complete artifacts plus reserved report roots.
- The main control surface now exposes `ego_planner_swarm`, and that capability is part of the current shared backend set reported by `python3 -m sim_plane list-backends`.
- A fresh headless main-surface `ego_planner_swarm` run passed at `runs/ego_planner_swarm_single_20260427_141747/result.json` with `telemetry_count=90`, `max_altitude_m=1.81`, `target_altitude_reached=true`, and `position_cmd_seen=true`.
- Fresh visual main-surface `ego_planner_swarm` runs passed at `runs/ego_planner_swarm_single_visual_20260427_142328/result.json`, `runs/ego_planner_swarm_single_visual_20260427_142410/result.json`, and `runs/ego_planner_swarm_single_visual_20260427_142608/result.json`.
- The ROS telemetry probe now exits cleanly on shutdown without a `KeyboardInterrupt` traceback.
- `pointcloud_render_node` teardown was hardened in the upstream lab checkout and no longer emits the prior `boost::wrapexcept<boost::lock_error>` crash during normal shutdown.
- ROS launch logs for the lab backend are now isolated under each run artifact's `ros_logs/` directory.
- The random map generator now honors the configured launch seed, which removed the earlier visual-run flakiness caused by unconditional `random_device` reseeding.
- The current host `cmake` is `4.2.3`, so the ROS1 workspace build requires `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
- The first source-side blocker in `ego-planner-swarm` was fixed in `src/uav_simulator/Utils/multi_map_server/CMakeLists.txt` by changing `multi_map_server_messages_cpp` to `multi_map_server_generate_messages_cpp`.
- `local_sensing` compiled successfully in the default CPU path despite `package.xml` still listing `svo_msgs` and `vikit_ros`.
- Cosmetic upstream viewer noise still exists in RViz about an older hummingbird mesh and a missing material, but it did not block repeated passed runs.
- The managed local JSBSim toolchain now exists at `/home/coco/sim_plane_ws/toolchains/jsbsim` and includes headers, `bin/JSBSim`, and `lib/libJSBSim.a`.
- PX4's JSBSim `ExternalProject` needed two host-side compatibility fixes on this machine: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` for `cmake 4.2.3`, and propagation of the reconstructed local `JSBSIM_ROOT_DIR` into the child configure step.
- PX4's `Tools/simulation/jsbsim/sitl_run.sh` now guards headless cleanup so shutdown no longer errors on empty `FGFS_PID`.
- A fresh direct headless `sitl_run.sh` probe for `quadrotor_x` produced MAVLink heartbeat on `udpin:127.0.0.1:14540`, accepted `commander takeoff`, and settled in `LOITER`.
- A historical direct headless `sitl_run.sh` probe for `rascal` produced MAVLink heartbeat on `udpin:127.0.0.1:14540`, accepted shell-injected overrides for `SYS_HAS_NUM_ASPD=0` and `NAV_DLL_ACT=0`, and then armed successfully without force-arm; its run artifact has since been removed because fixed-wing is outside the current mainline.
- The main control surface now exposes `px4_jsbsim` as a first-class backend with shared artifact capture and MAVLink telemetry ingestion.
- Fresh main-surface JSBSim quadrotor evidence exists at `runs/px4_jsbsim_quadx_headless_20260427_153027/result.json`.
- The user has now explicitly narrowed the product scope to quadrotor work. Fixed-wing is no longer an active investment direction for this platform.
- The old `px4_jsbsim_rascal_smoke` scenario entry and retained run artifact have both been removed from the current platform-mainline surface.
- The official `livox_ros_driver` dependency is now managed under `/home/coco/sim_plane_ws/src/deps/Livox_SDK/livox_ros_driver`.
- The managed `FAST_LIO` entry now syncs recursively so the upstream `include/ikd-Tree` submodule is present instead of failing the build on a missing `ikd_Tree.cpp`.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`.
- A project-local helper now exists for the estimator stack: `scripts/build_fast_lio_ws.sh`.
- A fresh `./scripts/build_fast_lio_ws.sh` run completed successfully and built both `livox_ros_driver_node` and `fast_lio/fastlio_mapping` in `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`.
- A fresh manual smoke launch of `roslaunch test_interface single_drone_avia.launch launch_rviz:=false use_gpu_:=false` plus `roslaunch fast_lio mapping_marsim.launch rviz:=false` produced live `/Odometry` output from `FAST_LIO`, confirming that the current `MARSIM` topics satisfy the upstream `mapping_marsim.launch` contract.
- The shared control surface now exposes `fast_lio_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- A repo-local wrapper launch now exists at `sim_plane/ros/fast_lio_marsim.launch` and forces `pcd_save/pcd_save_en=false` so shared-runner `FAST_LIO` runs do not dump `FAST_LIO/PCD/scans.pcd` into the managed upstream checkout.
- A fresh headless shared-runner `FAST_LIO + MARSIM` pass now exists at `runs/fast_lio_marsim_20260427_173428/result.json` with `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and `pcd_save_disabled=true`.
- A fresh visual shared-runner `FAST_LIO + MARSIM` pass now exists at `runs/fast_lio_marsim_visual_20260427_173600/result.json` with `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and `launch_rviz=true`.
- The first `FAST_LIO/PCD/scans.pcd` pollution artifact was confirmed to predate the shared-runner wrapper and was cleaned from the upstream checkout after the wrapper-backed passes proved there were no new `/PCD/` writes in the artifact logs.
- The managed `Fast-Planner` reference lives under `/home/coco/sim_plane_ws/src/references/HKUST_Aerial_Robotics/Fast-Planner`, not under the `labs/` tree.
- The upstream `Fast-Planner` README requires a manual `NLopt v2.7.1` install step in addition to `libarmadillo-dev`, while the upstream legacy `ego-planner` README on Ubuntu 20.04 only calls out `libarmadillo-dev` plus `catkin_make`.
- On the current host and workspace policy, legacy `ego-planner` is therefore the lighter next planner-integration target; `Fast-Planner` remains a demoted reference until its dependency story is bounded without widening the managed runtime.
- A dedicated ROS1/catkin workspace now exists at `/home/coco/sim_plane_ws/workspaces/ros1_ego_planner`, and a project-local helper exists at `scripts/build_ego_planner_ws.sh`.
- The legacy `ego-planner` `pointcloud_render_node` now reads `map/resolution`, uses `ros::spin()`, and explicitly shuts down ROS interfaces so normal shared-runner teardown no longer aborts with `boost::wrapexcept<boost::lock_error>`.
- The shared control surface now exposes `ego_planner`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- Fresh shared-runner headless legacy `ego_planner` evidence now exists at `runs/ego_planner_single_20260427_182825/result.json` with `goal_reached=true`, `min_goal_distance_m=0.118`, `pointcloud_seen=true`, and clean return to `WAIT_TARGET`.
- Fresh shared-runner visual legacy `ego_planner` evidence now exists at `runs/ego_planner_single_visual_20260427_182852/result.json` with `goal_reached=true`, `min_goal_distance_m=0.123`, `pointcloud_seen=true`, and `launch_rviz=true`.
- The shared legacy `ego_planner` scenarios now use the bounded auto-goal `(2.5, 0.0, 1.0)` because a farther `(5.0, 0.0, 1.0)` goal produced unnecessary late replanning noise on this host.
- The new `ego_planner_marsim` shared backend now composes the dedicated `MARSIM` and legacy `ego-planner` workspaces through the repo-local wrapper `sim_plane/ros/ego_planner_marsim.launch`.
- The earliest `legacy ego_planner + MARSIM` source-side blocker was a ROS MD5 mismatch on `quadrotor_msgs/PositionCommand`; the legacy workspace message definition now matches the `MARSIM` superset and both workspaces report the same MD5 `d008e86de36e11deb1e4033ac2c394a9`.
- The earliest `legacy ego_planner + MARSIM` runtime blocker after that message fix was dual-feeding both `depth` and `cloud` into the legacy `GridMap`; the cloud-only wrapper plus `grid_map/use_depth_filter=false` retired the repeated false-obstacle and `EMERGENCY_STOP` churn.
- Fresh shared-runner headless planner-on-scene evidence now exists at `runs/ego_planner_marsim_20260427_185547/result.json` with `goal_reached=true`, `min_goal_distance_m=0.064`, and info-only event output.
- Fresh shared-runner visual planner-on-scene evidence now exists at `runs/ego_planner_marsim_visual_20260427_185758/result.json` with `goal_reached=true`, `launch_rviz=true`, and info-only event output.
- The shared control surface now exposes `ego_planner_swarm_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- The earliest `ego_planner_swarm + MARSIM` source-side blocker was the same ROS MD5 mismatch on `quadrotor_msgs/PositionCommand`; the swarm workspace message definition and `traj_server.cpp` now match the `MARSIM` superset and both workspaces report MD5 `d008e86de36e11deb1e4033ac2c394a9`.
- The first repo-local `ego_planner_swarm_marsim` wrapper attempt falsely relied on chained remaps through `advanced_param.xml`; the planner stayed in `FSM INIT` printing `no odom.` until the wrapper switched to direct `MARSIM` odom and cloud remaps.
- The final repo-local wrapper at `sim_plane/ros/ego_planner_swarm_marsim.launch` now launches `drone_0_ego_planner_node` directly in manual-goal mode, disables `grid_map/use_depth_filter`, leaves depth unused, and publishes `/quad_0/planning/pos_cmd` without starting the upstream swarm simulator stack or `waypoint_generator`.
- Fresh shared-runner headless `ego_planner_swarm_marsim` evidence now exists at `runs/ego_planner_swarm_marsim_20260427_191923/result.json` with `goal_reached=true`, `min_goal_distance_m=0.011`, and direct `MARSIM` odometry plus pointcloud remaps.
- Fresh shared-runner visual `ego_planner_swarm_marsim` evidence now exists at `runs/ego_planner_swarm_marsim_visual_20260427_192755/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event stream.
- Normal visual-stop `MARSIM` shutdown markers are now downgraded to info in the shared event surface; raw upstream `roslaunch` stderr still records the RViz `SIGTERM` escalation line as an artifact-only residual.
- The first direct `planner <- /Odometry` adapter attempt exposed a frame-origin mismatch between FAST_LIO's local `camera_init` odometry and MARSIM's world-frame obstacle cloud plus goal surface.
- The repo now contains a thin aligned-odometry adapter at `scripts/ros_align_odometry.py`, which anchors FAST_LIO's `/Odometry` to the first MARSIM `/quad_0/lidar_slam/odom` sample and republishes `/sim_plane/fast_lio_world_odom`.
- The shared control surface now exposes `ego_planner_fast_lio_marsim`, and `python3 -m sim_plane list-backends` reports it as ready on this host.
- Fresh shared-runner headless `ego_planner_fast_lio_marsim` evidence now exists at `runs/ego_planner_fast_lio_marsim_20260427_194838/result.json` with `goal_reached=true`, `min_goal_distance_m=0.042`, and info-only event output.
- Fresh shared-runner visual `ego_planner_fast_lio_marsim` evidence now exists at `runs/ego_planner_fast_lio_marsim_visual_20260427_194947/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event output.
- The aligned FAST_LIO world-odom adapter is no longer proven only on the legacy branch; the shared control surface now also exposes `ego_planner_swarm_fast_lio_marsim`.
- Fresh shared-runner headless `ego_planner_swarm_fast_lio_marsim` evidence now exists at `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903/result.json` with `goal_reached=true`, `min_goal_distance_m=0.03`, and info-only event output.
- Fresh shared-runner visual `ego_planner_swarm_fast_lio_marsim` evidence now exists at `runs/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020/result.json` with `goal_reached=true`, `launch_rviz=true`, `dashboard_url=http://127.0.0.1:8765`, and an info-only event output.
- A repo-local planner validation matrix now exists at `docs/planner_validation_matrix.md` and freezes the four currently landed planner surfaces.
- A machine-readable planner acceptance matrix now exists at `configs/planner_acceptance_matrix.json`, and `python3 -m sim_plane planner-acceptance` plus `python3 -m sim_plane planner-acceptance --latest --artifact-root runs` both passed on `2026-04-28`; the gate now also rejects `min_goal_distance_m` regressions larger than `0.01 m` relative to each frozen reference artifact baseline, fails loudly if the copied matrix baseline drifts from that reference artifact metric, persists timestamped reports plus stable latest snapshots under `runs/acceptance/`, appends to `history_reference.jsonl` / `history_latest.jsonl`, emits compact `latest_reference_delta.json` / `latest_latest_delta.json` compare snapshots, and defaults to keeping only the newest 5 timestamped report directories per mode.
- The managed PX4 checkout's Gazebo Classic ExternalProject now carries `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`, which retires the host `cmake 4.2.3` configure-time blocker without loosening the rest of the PX4 build.
- The shared control surface now also exposes `px4_gazebo_classic`, with fresh headless evidence at `runs/px4_gazebo_classic_iris_headless_20260428_152015/result.json` and fresh native-GUI evidence at `runs/px4_gazebo_classic_iris_visual_20260428_152300/result.json`; both passed with info-only shared event output after demoting the transient `ekf2 missing data` and `system power unavailable` startup chatter.
- The first repo-local `MAVSDK` algorithm adapter is now landed as `mavsdk_action_takeoff`, `python3 -m sim_plane list-adapters` reports it as ready on this host, and the validated `PX4 SIH` control surface at `runs/px4_sih_quadx_mavsdk_action_20260428_160345/result.json` now proves arm, takeoff, target-altitude reach, and landing through MAVSDK while keeping telemetry on PX4's GCS UDP port 14550.
- A second repo-local algorithm adapter now exists as `human_follow_ros_stage1`; `python3 -m sim_plane list-adapters` now reports both `human_follow_ros_stage1: ready` and `mavsdk_action_takeoff: ready` on this host.
- The managed Stage1 follower preflight gate now passed at `runs/px4_sih_quadx_human_follow_stage1_20260428_164845/result.json`, where the repo-local ROS adapter launched `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`, drove nonzero raw setpoints into MAVROS, satisfied the estimator gate, switched PX4 SIH into `OFFBOARD` while disarmed, returned PX4 to `AUTO.LOITER`, and kept the shared event stream `info`-only.
- The next bounded widening on the same managed Stage1 follower chain now passed at `runs/px4_sih_quadx_human_follow_stage1_armed_20260428_164920/result.json`, where the same adapter armed PX4 SIH, cut into `OFFBOARD`, returned to `AUTO.LOITER`, and still stayed below the bounded preflight envelope instead of drifting into a takeoff-grade contract.
- The earliest blocker on that follower path was host-side MAVROS runtime hygiene rather than PX4 or follower logic:
  - the local MAVROS overlay script needed to preserve the sourced catkin workspace and export `/home/coco/.local/ros_noetic_overlay/usr/lib/x86_64-linux-gnu`
  - the Stage1 bridge needed to stop ignoring `VZ` so PX4 SITL no longer warned `SET_POSITION_TARGET_LOCAL_NED invalid`
- The same repo-local `MAVSDK` adapter is now also proven on headless `PX4 + JSBSim` at `runs/px4_jsbsim_quadx_mavsdk_action_20260428_161256/result.json` and on FlightGear-visual `PX4 + JSBSim` at `runs/px4_jsbsim_quadx_mavsdk_action_visual_20260428_170517/result.json`; the earliest failed attempt on `14540` showed that JSBSim's onboard `14540/14580` pair cannot double as the clean shared telemetry surface once MAVSDK is active, while moving dashboard telemetry to the `Normal`-mode `14550` port retires that drift for both headless and visual JSBSim control surfaces.
- The `mavsdk` dependency is now pinned to the `2.x` line in `pyproject.toml` because fresh local evidence on this Python `3.8` host showed the current `3.x` wheels import broken generated gRPC code that demands `grpcio>=1.71.0`, while wheels for that grpc line were not available here.
- A machine-readable strict quadrotor platform acceptance matrix now exists at `configs/platform_acceptance_matrix.json`, `python3 -m sim_plane platform-acceptance` plus `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` now validate it, and the gate currently freezes twenty-three fresh `2026-04-28` reference artifacts: `ego_planner_single_20260428_142011`, `ego_planner_single_visual_20260428_142039`, `ego_planner_swarm_single_20260428_141841`, `ego_planner_swarm_single_visual_20260428_141921`, `px4_sih_quadx_headless_20260428_130601`, `px4_sih_quadx_3d_20260428_130651`, `px4_sih_quadx_mavsdk_action_20260428_160345`, `px4_sih_quadx_human_follow_stage1_20260428_164845`, `px4_sih_quadx_human_follow_stage1_armed_20260428_164920`, `px4_jsbsim_quadx_headless_20260428_130736`, `px4_jsbsim_quadx_mavsdk_action_20260428_161256`, `px4_jsbsim_quadx_mavsdk_action_visual_20260428_170517`, `px4_jsbsim_quadx_visual_20260428_145759`, `px4_gazebo_classic_iris_headless_20260428_152015`, `px4_gazebo_classic_iris_visual_20260428_152300`, `px4_gazebo_classic_iris_mavsdk_action_20260428_172653`, `px4_gazebo_classic_iris_mavsdk_action_visual_20260428_172755`, `marsim_single_20260428_130820`, `marsim_single_visual_20260428_130846`, `marsim_single_gpu_20260428_143322`, `marsim_single_gpu_visual_20260428_143543`, `fast_lio_marsim_20260428_130913`, and `fast_lio_marsim_visual_20260428_131215`.
- The strict platform gate is intentionally quadrotor-only, keeps the shared event surface `info`-only for all twenty-three rows, and nests the frozen four-row planner acceptance gate underneath it.
- The previously open `PX4 + Gazebo Classic + MAVSDK` source-side blocker is now retired for the shared runner: fresh official artifacts at `runs/px4_gazebo_classic_iris_mavsdk_action_20260428_172653/result.json` and `runs/px4_gazebo_classic_iris_mavsdk_action_visual_20260428_172755/result.json` both passed after the backend locked a dedicated local `GAZEBO_MASTER_URI` per run and the MAVSDK contract stayed on PX4's onboard `14580` plus a separate shared telemetry port such as `14550`.
- The earlier polluted Gazebo Classic MAVSDK probe is no longer canonical truth for that backend; the source-side root cause was cross-workspace Gazebo master pollution rather than a surviving control-path defect.
- The strict platform gate no longer only checks absolute thresholds. It now also rejects tracked metric regressions versus each frozen platform reference artifact: `telemetry_count` cannot drop by more than `10`, PX4-family `mode_changes` cannot regress below the frozen count, and the two managed Stage1 follower rows also enforce tighter reference-based `max_altitude_m` and `max_speed_mps` budgets.
- ROS cleanup semantics are now unified under a repo-local helper: stale-node detection plus successful cleanup stays on the shared `info` surface, while only failed or incomplete cleanup escalates to `warning`. This retires the prior risk that benign preflight hygiene could pollute future acceptance runs.
- The repo-local FlightGear toolchain wrapper now exists under `/home/coco/sim_plane_ws/toolchains/flightgear`, the managed PX4 checkout now honors an explicit `FG_BINARY` override in `Tools/simulation/jsbsim/sitl_run.sh`, and the shared `px4_jsbsim` backend now validates the requested bridge scene XML before launch so an unsupported world fails early instead of degrading into a late heartbeat timeout.
- The bounded visual-showcase request was previously closed with all nine visual surfaces opened successfully; the bulky showcase aggregate artifact has since been removed, while the canonical `SUPER` and `visPlanner` retained probes remain under `runs/manual_probes/`.
- The showcase runner is now more platform-grade than before: repo-local `run_algorithm_visual_showcase.sh` assigns isolated dashboard ports `8765..8771` per visual surface and performs bounded one-shot retries only inside the manual-showcase layer, which retires the prior fixed-port and repeat-run flake without weakening strict acceptance.
- Auxiliary viewer teardown is now normalized as informational hygiene for the legacy `ego_planner` and `ego_planner_swarm` RViz paths, so forced RViz shutdown no longer pollutes the strict platform gate with non-functional `warning` noise; a fresh replacement artifact at `runs/ego_planner_swarm_single_visual_20260429_074202/result.json` restored the latest strict platform baseline to green.
- Fresh repo-wide hygiene is also back to clean: `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` passed most recently at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260526_162128_671607/report.json`, `python3 -m sim_plane manual-probe-hygiene --artifact-root runs --prune-safe` pruned stale superseded probe directories, and `python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual --prune-safe` returned `artifact hygiene: clean`.
- The repo now has a first generic user-algorithm ingress instead of only built-in algorithm examples: `sim_plane/adapters/external_command.py` launches a user-owned host process, injects stable `SIM_PLANE_*` environment variables such as `SIM_PLANE_SYSTEM_ADDRESS`, and merges `SIM_PLANE_ADAPTER_RESULT_JSON` back into the unified run artifact.
- That ingress is already proven locally on the light quadrotor path: `python3 -m sim_plane run scenarios/px4_sih_quadx_external_command_template.json --no-hold-open` passed at `runs/px4_sih_quadx_external_command_template_20260429_080209/result.json`, where the external template command `python3 examples/user_algorithms/mavsdk_takeoff_template.py` connected through the injected PX4 onboard MAVSDK address, reached takeoff altitude, landed, and reported adapter metrics back into the shared artifact.
- The repo now also has a generic ROS-native user-algorithm ingress instead of only lab-specific planner wrappers: `sim_plane/adapters/ros_command.py` sources ROS plus workspace overlays, launches a user-owned ROS process, waits for required topic bindings, and then shuts it down cleanly under the same unified run artifact.
- That ROS-native ingress is already proven locally on `MARSIM`: `python3 -m sim_plane run scenarios/marsim_ros_command_template.json --no-hold-open` passed at `runs/marsim_ros_command_template_20260429_083036/result.json`, where the repo-local sample node subscribed `odom/cloud/map`, published `PositionCommand` into the native MARSIM control chain, and returned `algorithm_adapter_completed_successfully=true` with `position_cmd_seen=true`.
- The same ROS-native ingress is also proven on `FAST_LIO + MARSIM`: `python3 -m sim_plane run scenarios/fast_lio_marsim_ros_command_template.json --no-hold-open` passed at `runs/fast_lio_marsim_ros_command_template_20260429_083251/result.json`, and the earliest failed attempt exposed a real overlay-order defect where sourcing `ros1_fast_lio` after `ros1_marsim` hid `quadrotor_msgs`; the landed default now sources `ros1_fast_lio` first and `ros1_marsim` last so control-chain message definitions stay available to user algorithms.
- This closes the earlier gap where the project behaved more like an upstream-launch orchestrator than a user-owned algorithm platform for both PX4-side control logic and ROS-side planner/perception logic.

## Open Questions

- Should the next bounded step build a stronger formal comparison pack around the twenty-three-row platform baseline, or should the platform keep widening into another still-unlanded control surface?
- Should the next widening prioritize another reusable adapter surface, or should the platform spend the next round on a stricter comparison surface above the current twenty-three-row baseline first?

## Constraints

- The default path must run on the current Ubuntu 20.04 machine without requiring a heavier OS upgrade first.
- The platform should remain easy to install, easy to operate, and easy to extend.
- The core should avoid unnecessary always-on services, containers, or middleware layers.
- Current support drift must be handled explicitly: some newer upstream combinations now target Ubuntu 22.04 or newer.

## Phase Plan

1. Lock the baseline architecture and selection criteria.
2. Build the MVP around the lightest backend that still preserves flight-stack realism.
3. Harden the validated PX4 SIH entrypoints and keep the local 3D viewer path easy to launch.
4. Add a dedicated ROS1/catkin lab-integration workspace under `/home/coco/sim_plane_ws` instead of building directly in upstream roots.
5. Bring up one lab algorithm stack at a time, starting with `ego-planner-swarm` single-drone mode and locking the earliest blocker before widening.
6. Promote the proven single-drone lab path into a durable control surface so it does not live only as manual shell history.
7. Add a richer flight-dynamics backend for airplane and mixed-vehicle validation.
8. Land `MARSIM` as the first heavier 3D sensor backend while keeping the default core path light.
9. Land `FAST_LIO + MARSIM` as the next official estimation stack after the stable `PX4 SIH + px4_jsbsim + ego_planner_swarm + marsim` baseline.
10. Bring up one planner stack on top of the ROS lab baseline without reopening heavyweight simulator branches.
11. Land and harden the second scene-backed planner branch without reopening retired dual-input or heavyweight simulator branches.
12. Build acceptance packaging for the four landed planner branches, then decide whether the next bounded target is another estimator-facing widening or optional ROS/HIL integration.

## Evidence Plan

- Record the chosen backend, vehicle type, and startup path for each validation round.
- Track install friction, cold-start time, and whether the host remains responsive.
- Treat successful takeoff, telemetry flow, offboard control loop, and repeatable scenario replay as MVP success signals.
- Treat dependency breakage, unsupported OS combinations, or high idle resource use as regressions.

## Rollback Plan

- If a backend proves too heavy or too fragile on Ubuntu 20.04, demote it to optional status and keep the lighter core path as the default.
- If ROS or a GUI dependency complicates the MVP path, move it behind an adapter boundary instead of keeping it in the core runtime.

## Current Blocker

- There is no active runtime blocker on the strict quadrotor platform baseline. The current acceptance bottleneck is retired for the landed `ego_planner`, `ego_planner_swarm`, `px4_sih`, `px4_sih + MAVSDK`, `px4_jsbsim`, `px4_jsbsim + MAVSDK`, `px4_gazebo_classic`, `marsim` CPU plus GPU, `fast_lio_marsim`, and the four nested planner surfaces: the repo now has both a nested four-row planner gate under `runs/acceptance/` and a top-level strict platform gate under `runs/platform_acceptance/`.
- The Stage1 follower chain is no longer tied to the unmanaged `/home/coco/follwer_ws` path. The repo now defaults to the managed workspace at `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`, the disarmed preflight row and the bounded armed-handoff row are both frozen into the platform acceptance matrix, and the next bottleneck moves to whichever still-unlanded capability surface can widen without regressing the twenty-three-row baseline.
- The Stage1 detector/tracker-in-loop follower branch is now also formalized as its own managed acceptance surface under `runs/human_follow_stage1_detector_tracker_acceptance/`, separate from the frozen truth-driven Stage1 matrix; use `python3 -m sim_plane human-follow-stage1-detector-tracker-acceptance --latest --artifact-root runs --json` instead of treating `px4_sih_quadx_human_follow_detector_tracker_full_chain` as a one-off probe.
- The previously open `PX4 + Gazebo Classic + MAVSDK` blocker is retired for the shared runner: the source-side issue was a shared Gazebo master plus ambiguous telemetry split, and the landed contract is now dedicated local `GAZEBO_MASTER_URI` isolation together with a separate GCS-facing telemetry port such as `14550`.
- The currently locked baseline contract is now stricter than before: any new candidate latest artifact that keeps `status=passed` but drops too far on tracked telemetry/mode counts or expands the Stage1 follower envelope will fail platform acceptance before widening is allowed.
- The currently locked noise contract is also stricter than before: ROS-family backends may pre-clean stale nodes, but a successful cleanup is now informational hygiene rather than shared warning noise.
- The current artifact-hygiene contract is also explicit now: repo-referenced incomplete manual probes belong under `runs/manual_probes/`, while unreferenced incomplete probe directories under `runs/` are stale noise and should be pruned by `python3 -m sim_plane artifact-hygiene --artifact-root runs --migrate-retained-manual --prune-safe`.
- Additional frontier-algorithm widening is now proven on fresh isolated ROS1 workspaces outside the strict baseline: `SUPER` and `visPlanner` both have managed build scripts, managed probe scripts, canonical `probe_meta.json` retention under `runs/manual_probes/`, and fresh successful reproductions where `SUPER` publishes `/planning/pos_cmd` and `visPlanner` leaves `WAIT_TARGET`, receives `drone_id: 1` target trajectories, and emits `/drone_0_planning/pos_cmd`.
- The `SUPER` probe now defaults to the cleaner `dense` profile instead of the noisier `high_speed` stress shape, auto-selects a free ROS master port, and retained canonical evidence at `runs/manual_probes/super_benchmark_dense_20260429_153853` with `planner_warn_count=3`, `intensity_warn_count=0`, and `replan_success_count=166`.
- The `visPlanner` probe now also auto-selects a free ROS master port, and retained canonical evidence at `runs/manual_probes/visplanner_tracking_20260429_153921` still produced both tracker and target command streams with `warn_count=5`.
- The current visual-showcase blocker is retired: the repo now has fresh all-green serial showcase evidence plus a clean post-showcase artifact root, and the `SUPER` / `visPlanner` results remain retained `manual_probes` evidence rather than strict platform rows.
- There is no active blocker on the new custom-algorithm ingress surfaces: the generic `external_command` adapter is landed and locally proven on `px4_sih`, and the generic `ros_command` adapter is landed and locally proven on both `marsim` and `fast_lio_marsim`.

## Historical Human-Follow Notes

- This section is retained as historical context only; it is not the current
  `sim_plane` platform frontier.
- The human-follow branch must not be reopened from this plan unless the user
  explicitly asks to return to that project-specific integration.
- The former human-follow synchronization and Stage1/Stage2 acceptance notes
  are superseded by the current generic platform hygiene gate below.
- For any future platform widening, keep
  `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` and
  `python3 -m sim_plane artifact-hygiene --artifact-root runs` as the default
  pre-widening checks.
- If the user brings a new control/decision algorithm next, default to the new
  `external_command` ingress on `px4_sih` first and only widen to heavier
  backends after the algorithm's I/O contract is clear and the light path is
  proven.
- If the user brings a new ROS planner/perception algorithm next, default to the
  new `ros_command` ingress on `marsim` first, then widen to `fast_lio_marsim`
  only when estimator-side coupling is actually required.

## Platform Hygiene Closure 2026-05-27

- Current active frontier remains the generic `sim_plane` platform, not the project-specific human-follow branch.
- Hygiene cleanup performed on `2026-05-27`:
  - removed generated Python `__pycache__` / `*.pyc` residue;
  - removed the empty `.codex` placeholder file;
  - removed `93` unreferenced duplicate passed top-level artifacts while preserving referenced evidence and each scenario's latest artifact;
  - removed retired non-mainline artifacts: fixed-wing `px4_jsbsim_rascal_smoke`, Stage2 placeholder artifacts, and obsolete `SUPER` high-speed manual probe evidence;
  - updated control docs so they no longer point to deleted artifacts as current evidence.
- Post-cleanup artifact root state:
  - top-level complete artifacts: `110`, all `passed`;
  - reserved report roots: `7`;
  - retained manual probes: `3`;
  - `runs/` size: about `608M` before final report reruns.
- Current retained manual probes:
  - `ego_planner_swarm_single_visual_20260427_202122`
  - `super_benchmark_dense_20260429_153853`
  - `visplanner_tracking_20260429_153921`
- The current objective optimization/frontier after hygiene is platform-generic:
  - decide whether to formalize `SUPER` or `visPlanner` as a future optional surface, but not both at once and not inside the strict platform baseline until their noise contracts are explicit.
- The one-command smoke/health suite is now covered by `python3 -m sim_plane live-smoke`; future work should improve it only if fresh evidence shows a missing smoke surface.
- Dashboard/replay comparison is now covered by `python3 -m sim_plane serve runs`; future work should refine visualization only after the adapter onboarding gap is reduced.
- The adapter onboarding gap is reduced by `generate-scenario`.
- Per user direction, do not keep a ROS2/Gazebo migration roadmap as a landed document now; treat ROS1 Noetic and Gazebo Classic EOL as a known long-term risk to revisit only when a concrete migration target is explicitly reopened.
- Before any functional widening, re-run the structural gate:
  - clean git status;
  - unit tests;
  - compileall and shell syntax;
  - `doctor --json`;
  - `live-smoke --profile fast`;
  - `platform-acceptance --latest`;
  - `planner-acceptance --latest`;
  - artifact hygiene;
  - no stale frontier text that points to a reverted or user-rejected task.

## Functional Disturbance Suite Frontier 2026-05-27

- First functional widening after structural cleanup:
  - deterministic disturbance-aware scenario fields on the lightweight `demo`
    backend;
  - `python3 -m sim_plane run-suite` for batch variant execution;
  - `configs/demo_disturbance_suite.json` as the first reproducible wind/noise/
    initial-offset suite;
  - `configs/px4_sih_takeoff_suite.json` as the first real PX4 SIH suite using
    repeated takeoff variants and metric gates;
  - reports retained under `runs/suites/`.
- `run-suite` now supports per-variant `required_metrics` and
  `metric_thresholds` so a batch can fail for a real metric miss instead of only
  a raw scenario status miss.
- This intentionally starts on the light backend so the schema, artifact shape,
  and comparison workflow can stabilize before mapping similar factors into PX4
  or MARSIM.
- PX4 SIH does not currently expose a direct SIH wind-field injection in the
  managed path; do not label PX4 SIH suite variants as wind tests unless a real
  PX4-side wind injection contract is added.
- Fresh evidence:
  - demo disturbance suite PASS at
    `runs/suites/demo_disturbance_suite_20260527_150819_289292/report.json`;
  - PX4 SIH takeoff suite PASS at
    `runs/suites/px4_sih_takeoff_suite_20260527_150949_000816/report.json`;
  - final full validation PASS: `112` tests, compileall, shell syntax,
    `doctor --json`, artifact hygiene, latest planner acceptance, latest
    platform acceptance, and fast live smoke.

## Functional Parameter Sweep Frontier 2026-05-27

- Next functional widening: add a lightweight parameter-sweep layer on top of
  `run-suite`.
- Goal: let users define experiment axes once and auto-generate variant
  combinations instead of hand-writing repetitive suite rows.
- Scope boundaries:
  - keep the core dependency-free and backend-agnostic;
  - start with the fast `demo` backend for proof;
  - do not change existing acceptance semantics or thresholds;
  - do not touch `/home/coco/follwer_ws`;
  - do not fake PX4 SIH wind or other unsupported physics contracts.
- Promotion gate:
  - tests for matrix expansion, variant naming, metric gates, and invalid config;
  - a runnable sample sweep config;
  - fresh suite report under `runs/suites/`;
  - no regression in unit tests, compileall, doctor, artifact hygiene, and latest
    acceptance.
- Landed shape:
  - `run-suite` accepts either hand-written `variants` or generated `sweep`;
  - sweep axes use dotted JSON paths and auto-expand to deterministic variant
    combinations;
  - suite-level `required_metrics` and `metric_thresholds` are inherited by
    generated variants;
  - duplicate variant names and artifact-safe name collisions are rejected
    before running.
- Fresh evidence:
  - parameter sweep PASS at
    `runs/suites/demo_parameter_sweep_suite_20260527_153012_415445/report.json`;
  - final full validation PASS: `116` tests, compileall, shell syntax,
    `doctor --json`, artifact hygiene, latest planner acceptance, latest
    platform acceptance, and fast live smoke.

## Functional Suite Analysis Frontier 2026-05-27

- Next functional widening: make suite reports explain parameter effects, not
  only list rows.
- Goal: after a sweep, report grouped metric summaries per factor value so the
  user can see which parameter is driving altitude, error, speed, or telemetry
  changes.
- Scope boundaries:
  - keep analysis local to `run-suite` reports;
  - no new dependencies;
  - no acceptance threshold changes;
  - do not touch `/home/coco/follwer_ws`;
  - do not add heavy visualization before the machine-readable analysis exists.
- Promotion gate:
  - generated sweep rows carry factor metadata;
  - reports include per-factor grouped metrics and metric effect ranges;
  - hand-written variants keep existing behavior;
  - tests and normal validation pass.
- Landed shape:
  - generated sweep rows include `factors`;
  - reports include `factor_analysis` grouped by factor value;
  - reports include sorted `top_metric_effects`.
- Fresh evidence:
  - suite analysis PASS at
    `runs/suites/demo_parameter_sweep_suite_20260527_154528_204275/report.json`;
  - top effects include `alt -> max_altitude_m` and
    `wind_y -> max_horizontal_error_m`, both with `mean_spread=2.0`;
  - final validation PASS: `116` tests, compileall, shell syntax,
    `doctor --json`, artifact hygiene, latest planner acceptance, latest
    platform acceptance, and fast live smoke.

## Functional KPI And Degradation Frontier 2026-05-28

- Current functional widening after external reference review:
  - add a backend-agnostic KPI evaluation layer that reads recorded telemetry
    and appends normalized algorithm-quality metrics into each artifact result;
  - extend the lightweight demo backend with deterministic degradation/fault
    knobs that are safe to test without pretending PX4 SIH supports fake wind;
  - let `run-suite` gate on these normalized KPI metrics so scenario batches can
    judge quality, not only raw pass/fail.
- Scope boundaries:
  - do not add AirSim, Isaac/Pegasus, or another heavy simulator backend now;
  - do not change existing acceptance semantics or thresholds;
  - do not touch `/home/coco/follwer_ws`;
  - keep the first implementation dependency-free and usable on the current
    Ubuntu 20.04 host;
  - do not label PX4 SIH variants as wind/fault tests unless the fault is backed
    by a real PX4-side contract.
- Promotion gate:
  - unit tests for KPI calculations, result enrichment, degradation behavior,
    and suite thresholding;
  - one runnable demo degradation suite that proves the surface;
  - README/docs mention the new command path and the value of the metrics;
  - final validation through unit tests, compileall, doctor, artifact hygiene,
    latest acceptance, and fast live smoke.
- Landed shape:
  - `sim_plane.evaluation` appends backend-agnostic `kpi_*` metrics to each
    shared-runner `result.json`;
  - `kpi_mission_*` isolates mission/offboard quality from takeoff and landing
    transients when the backend labels that phase;
  - the demo backend supports deterministic `degradations` for sensor dropout,
    latency, measurement bias, and measurement saturation;
  - hand-written suite variants now inherit suite-level `base_overrides`, like
    generated sweep variants already did;
  - `configs/demo_degradation_suite.json` provides the first reusable
    degradation/KPI-gated suite.
- Fresh evidence:
  - degradation suite PASS at
    `runs/suites/demo_degradation_suite_20260528_044024_950793/report.json`;
  - fast live smoke PASS at
    `runs/live_smoke/live_smoke_fast_20260528_044113_006224/report.json`;
  - final validation PASS: `121` tests, compileall, shell syntax,
    `doctor --json`, artifact hygiene, latest planner acceptance, latest
    platform acceptance, and fast live smoke.

## Dashboard KPI And Suite Replay Frontier 2026-05-28

- Next functional widening: make the already-created KPI/suite evidence visible
  in the local dashboard instead of requiring manual JSON inspection.
- Scope boundaries:
  - keep the dashboard dependency-free and served by the existing local HTTP
    server;
  - do not change suite or acceptance semantics;
  - do not add a heavyweight frontend framework;
  - do not touch `/home/coco/follwer_ws`.
- Landed shape:
  - `/api/suites/latest` summarizes `runs/suites/latest_*.json`;
  - the dashboard now has a `Latest Suites` panel with suite status, row counts,
    key KPI rows, and top factor effects;
  - run comparison prioritizes important KPI deltas before dumping all numeric
    metrics;
  - dashboard JavaScript now has a dependency-free static guard test for
    balanced delimiters, unterminated strings/templates/comments, and duplicate
    same-scope `const` / `let` bindings.
- Promotion gate:
  - dashboard replay tests cover suite summary extraction;
  - static smoke confirms the current `runs/suites/` reports expose KPI data.
- Fresh evidence:
  - degradation suite refreshed and passed at
    `runs/suites/demo_degradation_suite_20260528_055519_209876/report.json`;
  - suite dashboard API smoke returned `demo_degradation_suite passed` with
    `4/4` rows passed;
  - final validation PASS: `123` tests, compileall, shell syntax,
    `doctor --json`, artifact hygiene, latest planner acceptance, latest
    platform acceptance, and fast live smoke;
  - latest reports:
    - `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260528_055610_860265/report.json`;
    - `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_055610_964248/report.json`;
    - `runs/live_smoke/live_smoke_fast_20260528_055615_402373/report.json`.

## Functional Capability Pack Closure 2026-05-28

- Five platform-level functional hardening lines are now landed on the generic
  `sim_plane` mainline:
  - plugin-style KPI evaluation over recorded telemetry;
  - deterministic lightweight degradation/fault injection for the demo backend;
  - standard demo task-family suite;
  - suite KPI ranking and dashboard visibility;
  - one-command custom algorithm ingress health check.
- Scope stayed bounded:
  - no changes to `/home/coco/follwer_ws`;
  - no Stage1/Stage2 human-follow reopening;
  - no platform/planner acceptance semantic or threshold change;
  - no new heavy simulator backend;
  - no fake PX4 SIH wind/fault injection.
- Landed implementation:
  - `sim_plane.evaluation` appends normalized `kpi_*` metrics through
    `KPI_PLUGINS`;
  - altitude timing KPI now ignores samples without altitude instead of
    misaligning time stamps;
  - demo backend supports `sensor_dropout`, `target_loss`, `sensor_latency`,
    `sensor_noise`, `measurement_bias`, `measurement_bias_drift`,
    `measurement_saturation`, `communication_interruption`, and
    `control_saturation`;
  - demo backend can exercise `algorithm_adapter` and propagate adapter metrics;
  - `configs/demo_degradation_suite.json` and
    `configs/demo_task_family_suite.json` define reusable lightweight
    robustness/task exams;
  - `run-suite` emits `kpi_rankings`;
  - dashboard API/UI exposes latest suite KPI summaries and rankings;
  - `python3 -m sim_plane check-algorithm-ingress` runs existing or generated
    custom algorithm scenarios and checks adapter, telemetry, control evidence,
    and KPI generation;
  - artifact directory allocation now uses microsecond stamps plus collision
    fallback and path-safe scenario names.
- Fresh evidence:
  - degradation suite PASS:
    `runs/suites/demo_degradation_suite_20260528_070636_064192/report.json`;
  - task-family suite PASS:
    `runs/suites/demo_task_family_suite_20260528_070642_918611/report.json`;
  - demo ingress PASS:
    `runs/demo_cli_ingress_20260528_070701_928706`;
  - PX4 SIH external command ingress PASS:
    `runs/px4_sih_quadx_external_command_template_20260528_070701_903805`;
  - `python3 -m unittest discover -s tests` PASS: `131` tests;
  - compileall, shell syntax, and `61` JSON files PASS;
  - `doctor --json` PASS: `12` ready backends and `5` ready adapters;
  - artifact hygiene PASS: `status=clean`, `attention_count=0`;
  - planner latest acceptance PASS:
    `/home/coco/sim_plane/runs/acceptance/planner_acceptance_baseline_latest_20260528_070829_407378/report.json`;
  - platform latest acceptance PASS:
    `/home/coco/sim_plane/runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_070829_749673/report.json`,
    `changed_rows_count=0`;
  - fast live smoke PASS:
    `runs/live_smoke/live_smoke_fast_20260528_070859_544327/report.json`.
- Remaining objective limit:
  - current standardized degradation/fault injection is intentionally proven
    first on the lightweight demo backend;
  - PX4 SIH fault injection must remain conservative and only be widened when a
    real PX4-side injection mechanism is separately proven.

## Professional Test Surface Closure 2026-05-28

- The external-method review follow-up is now implemented as platform-native
  test surfaces instead of a roadmap:
  - `python3 -m sim_plane flight-log-analyze <artifact-or-ulg>`;
  - `python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast`;
  - `python3 -m sim_plane autotest-pack --profile fast`;
  - dashboard `Professional Test Surfaces` panel over latest PX4 failure,
    flight-log, fuzz, and autotest reports.
- Scope stayed bounded:
  - no changes to `/home/coco/follwer_ws`;
  - no Stage1/Stage2 reopening;
  - no existing acceptance semantic or threshold changes;
  - no AirSim/Isaac/Gazebo Harmonic migration;
  - demo fuzz remains clearly separated from PX4-native failure injection.
- Landed implementation:
  - `sim_plane.flight_log_analysis` analyzes either a complete run artifact or
    a real PX4 `.ulg` through `pyulog`, producing duration, altitude/speed,
    path distance, mode/nav changes, armed transitions, anomaly/warning counts,
    and replay `kpi_*`;
  - `sim_plane.scenario_fuzz` creates deterministic seed-based fuzz suites in
    memory, saves the generated suite JSON with the report, and ranks
    `worst_cases`;
  - `sim_plane.autotest_pack` composes doctor, artifact hygiene, live-smoke
    fast, demo degradation suite, seeded fuzz, flight-log artifact replay, PX4
    failure latest acceptance, and platform latest acceptance;
  - `runs/flight_log_analysis`, `runs/scenario_fuzz`, and `runs/autotest` are
    reserved artifact-hygiene roots;
  - dashboard API/UI now lists professional test-surface report summaries.
- Fresh evidence:
  - artifact replay PASS:
    `runs/flight_log_analysis/artifact_px4_sih_quadx_mavsdk_failure_motor_20260528_105546_340839_20260528_112327_129051/report.json`;
  - `.ulg` replay PASS over historical PX4 build-root log:
    `runs/flight_log_analysis/ulog_17_28_07_20260528_112503_012345/report.json`;
  - seeded fuzz PASS:
    `runs/scenario_fuzz/demo_seeded_fuzz_20260528_20260528_112342_404826/report.json`;
  - autotest fast PASS:
    `runs/autotest/sim_plane_autotest_fast_20260528_112450_660913/report.json`;
  - autotest fast latest platform acceptance nested PASS:
    `runs/platform_acceptance/platform_acceptance_baseline_latest_20260528_112450_656432/report.json`;
  - autotest fast latest PX4 failure acceptance nested PASS:
    `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260528_112450_470300/report.json`.
- Remaining objective limit:
  - current `.ulg` proof parses an existing PX4 build-root log; automatic copy
    of fresh PX4 `.ulg` into each run artifact is still a future enhancement,
    not claimed as completed here.

## Platform Baseline Release Closure 2026-06-01

- Current frontier: freeze the current generic `sim_plane` platform into a
  clean, documented, locally reproducible baseline instead of widening into a
  new simulator, new algorithm family, or human-follow branch.
- Scope:
  - stay inside `/home/coco/sim_plane`;
  - do not touch `/home/coco/follwer_ws`;
  - do not change existing acceptance semantics, matrices, thresholds, or
    scenario behavior;
  - do not add a new heavy backend;
  - keep unresolved limits explicit instead of presenting them as completed.
- Required closure work:
  - add a single Chinese platform entry document for daily use and debugging;
  - rerun the current validation pack from the actual workspace;
  - clean generated residue such as `__pycache__` / `*.pyc`;
  - commit the landed platform capabilities and tag a rollback point.
- Locked remaining objective limits:
  - fresh PX4 `.ulg` files are not yet automatically copied into every run
    artifact;
  - demo degradation/fuzz remains a lightweight robustness surface, not
    PX4-native physical failure;
  - PX4-native failure acceptance currently proves only
    `SYSTEM_MOTOR/OFF/OK`.
