# Human Follow Collaboration Ledger

## Purpose

- This file is the shared coordination surface for the human-follow simulation branch across separate Codex sessions.
- There is no direct cross-session chat channel. Coordination must happen through checked-in control files plus explicit session extracts when needed.

## Scope

- Project-side source of truth: `/home/coco/follwer_ws`
- Sim-platform source of truth: `/home/coco/sim_plane`
- Managed sim workspace: `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`

## Locked Facts

- The older managed Stage1 rows are already frozen and must not be treated as proof of the newer current-structure chain:
  - `px4_sih_quadx_human_follow_stage1`
  - `px4_sih_quadx_human_follow_stage1_armed`
- A separate newer sim proof surface already exists:
  - scenario: `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_truth_full_chain.json`
  - result: `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_truth_full_chain_20260505_141205/result.json`
- That newer proof surface has already passed with these key facts:
  - `status=passed`
  - `ever_armed=true`
  - `algorithm_adapter_offboard_mode_reached=true`
  - `algorithm_adapter_follow_state_name=follow`
  - `max_altitude_m=0.421`
  - `max_speed_mps=0.509`
- The newer proof surface is still only `truth-driven + current-structure follower sim`.
- The newer proof surface does not yet prove:
  - detector-in-the-loop image perception
  - `stage1_live_core_real_fusion.launch`
  - `stage1_live_px4_to_mavros_real_fusion.launch`
  - chain-internal autonomous OFFBOARD handoff without probe assistance
- The managed sim workspace must preserve its sim-specific MAVROS contract:
  - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/launch/stage1_px4_mavros.launch`
  - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/launch/stage1_px4_mavros_sitl.launch`
  - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/config/mavros_px4_pluginlists_sitl.yaml`
- The current project-side workspace contains a user-owned algorithm drop point at `/home/coco/follwer_ws/src/human_follow_user`.
- The latest extracted platform-side collaborator snapshot came from `/home/coco/.codex/sessions/2026/04/27/rollout-2026-04-27T18-00-51-019dce62-7308-7b21-8782-a5ad52531cee.jsonl`.
- That extracted latest completed round was timestamped `2026-05-05T13:26:01.124Z` and said the platform-side truth-visual-demo line was cleaned up and the next need was landing the real algorithm through the standard user ingress.
- The current human-follow branch and any later project-side EGO branch are not yet fused into one end-to-end simulation chain.
- In the project-side workspace, `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage2_placeholder.launch` still explicitly marks any later project-side EGO integration as blocked on Stage1 stability.
- The `sim_plane` repository contains its own independently validated `ego_planner*` baselines, but those baselines are unrelated to this human-follow project and must not be counted as project progress, project evidence, or project integration status.
- The `sim_plane` follower adapter now supports per-scenario `follow_launch_args` passthrough, so the managed SIH runner can drive `motion_mode`, `enable_case_validation`, and `validation_case` directly into the project Stage1 truth-regression launch instead of only the older generic smoke path.
- A project-specific Stage1 behavior validation matrix now exists as dedicated `sim_plane` scenarios:
  - `px4_sih_quadx_human_follow_case_acquire_center`
  - `px4_sih_quadx_human_follow_case_search_reacquire_right`
  - `px4_sih_quadx_human_follow_case_search_reacquire_left`
  - `px4_sih_quadx_human_follow_case_person_approach_retreat`
  - `px4_sih_quadx_human_follow_case_person_depart_follow`
  - `px4_sih_quadx_human_follow_case_lateral_left_track`
  - `px4_sih_quadx_human_follow_case_lateral_right_track`
- Fresh local evidence on `2026-05-05` shows all seven project-specific Stage1 behavior cases passed on `PX4 SIH` through the managed workspace:
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_acquire_center_20260505_143654/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_right_20260505_143802/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_search_reacquire_left_20260505_143831/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_approach_retreat_20260505_143859/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_person_depart_follow_20260505_143926/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_left_track_20260505_143952/result.json`
  - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_case_lateral_right_track_20260505_144019/result.json`
- Those fresh behavior-case artifacts are not just adapter-level passes; each one contains a `truth_case_validation PASS case=...` log from the project monitor node, proving the intended Stage1 behavior-specific conditions were actually satisfied.
- Fresh Stage1 managed acceptance refresh now also exists on `2026-05-09`:
  - full-chain artifact:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_truth_full_chain_20260509_161326/result.json`
  - behavior-matrix artifacts:
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
    - `selection_mode=latest`
    - `issues=[]`
- Fresh sim-plane-side reread on `2026-05-10` locked the later Stage1 acceptance failure as sim-plane acceptance noise, not a project-side behavior break:
  - report artifact was a now-removed intermediate failure report; the retained fact is the failure mode below:
  - locked failure facts:
    - `hf_stage1_acquire_center` reached `max_speed_mps=0.537` in PX4 `RTL` at telemetry sample `t=12.18`, after probe success and follower launch exit
    - `hf_stage1_lateral_left_track` reached `max_altitude_m=0.361` in PX4 `RTL` at telemetry sample `t=10.153`
    - `algorithm_adapter_follow_non_hold_count` drifted with managed startup timing and telemetry-window shape, so it was not a stable latest-vs-reference behavior metric on this surface
- Sim-plane-only Stage1 acceptance-noise cleanup is now landed:
  - Stage1 behavior scenarios `scenarios/px4_sih_quadx_human_follow_case_*.json` now set `backend_options.allow_early_stop_on_adapter_success=true`
  - `configs/human_follow_stage1_acceptance_matrix.json` now keeps only behavior-envelope regression budgets on `max_altitude_m` and `max_speed_mps`
  - `telemetry_count`, `mode_changes`, and `algorithm_adapter_follow_non_hold_count` are no longer used as latest-vs-reference regression budgets on this cleaned early-stop Stage1 surface
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
- A fresh managed detector/tracker-in-loop Stage1 full-chain proof now also exists on `2026-05-09`:
  - scenario:
    - `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_detector_tracker_full_chain.json`
  - first failure meaning:
    - detector, tracker, fusion, and controller were already alive
    - the earliest managed failure was bridge-side setpoint ingress
    - probe failed at `wait_ready` because `/mavros/setpoint_raw/local` saw `setpoint_count=0`
  - managed-only fix:
    - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/launch/stage1_truth_detector_tracker_controller_regression.launch`
    - now explicitly forwards `bridge_output_topic` into `stage1_truth_fusion_controller_regression.launch`
  - fresh passing artifact after that managed-only fix:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_detector_tracker_full_chain_20260509_163202/result.json`
- A managed-workspace user-owned planning ingress surface now exists and has fresh local passed evidence on `2026-05-05`:
  - scenario: `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_user_planning_ingress.json`
  - result: `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_user_planning_ingress_20260505_151235/result.json`
- That fresh managed `human_follow_user` ingress proof passed with these key facts:
  - `status=passed`
  - `ever_armed=true`
  - `algorithm_adapter_offboard_mode_reached=true`
  - `algorithm_adapter_follow_state_name=follow`
  - `algorithm_adapter_follow_launch_name=stage1_external_ingress_regression.launch`
- The managed workspace now contains `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_user`.
- The project-side external ingress chain needed one real source-side fix before that managed proof passed:
  - `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage1_external_ingress_regression.launch` now forwards `bridge_output_topic` into `stage1_truth_fusion_controller_regression.launch`
  - without that forward, the external ingress monitor passed but the Stage1 follow probe failed at `wait_ready` because `follow_px4_bridge` stayed on `/follow/offboard/setpoint` instead of the MAVROS setpoint topic
- On `2026-05-05`, the sim-platform side landed a dedicated managed-workspace sync and rebuild surface for the human-follow Stage1 branch:
  - sync script: `/home/coco/sim_plane/scripts/sync_human_follow_stage1_workspace.py`
  - build script: `/home/coco/sim_plane/scripts/build_human_follow_stage1_ws.sh`
  - managed sim doc: `/home/coco/sim_plane/docs/human_follow_stage1_managed_sim_zh.md`
- That new sync surface intentionally keeps the minimum managed package mirror narrower than the current managed workspace contents:
  - syncs only `human_follow_bringup`, `human_follow_control`, `human_follow_fusion`, `human_follow_msgs`, `human_follow_perception`, and `human_follow_px4_bridge`
  - does not newly mirror `human_follow_user` by default
  - preserves the sim-specific MAVROS contract files inside the managed workspace
- The managed workspace still currently contains `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_user`, but the new sim-platform sync policy does not treat that package as part of the minimum Stage1 truth-driven sim mirror until the real user algorithm is intentionally promoted into the shared runner path.
- The current managed sync surface now includes `/home/coco/follwer_ws/src/quadrotor_msgs`, so the project-side Stage2 `quadrotor_msgs/PositionCommand` contract can rebuild deterministically through the managed sim path.
- The current managed workspace also contains `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_user`, but the narrower sim-platform sync policy still treats that package as an optional promoted ingress surface instead of part of the minimum Stage1 mirror.
- Historical `sim_plane`-side managed `PX4 SIH` artifacts proved the older Stage2 placeholder chain on real MAVROS plus PX4, but those retired placeholder run artifacts have since been removed from `runs`.
- The retired latest clean placeholder rerun passed with these key facts:
  - `status=passed`
  - `ever_armed=true`
  - `algorithm_adapter_offboard_mode_reached=true`
  - `algorithm_adapter_stage2_goal_count=12`
  - `algorithm_adapter_stage2_ego_cmd_count=60`
  - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=102`
  - `algorithm_adapter_stage2_gate_owned_offboard_inferred=true`
- That older clean rerun also tightened the shared noise contract:
  - the removed placeholder artifact's `events.jsonl` was `info`-only
  - the earlier `failsafe activated` tail after probe success was retired by sim-plane-side cleanup hardening, without changing the Stage2 proof boundary
- The project-side Stage2 local regressions in `/home/coco/follwer_ws` were lower-half contract proof only; by themselves they did not provide managed sim evidence or real EGO completion evidence.
- Fresh project-side Stage2 local regression evidence now also exists above that lower-half note:
  - `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage2_ego_bridge_regression.launch`
  - `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage2_goal_adapter_regression.launch`
  - `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage2_placeholder_full_chain_regression.launch`
- Fresh project-side lower-half regression facts:
  - `timeout 25s roslaunch human_follow_bringup stage2_ego_bridge_regression.launch` passed
  - `ego bridge regression PASS`
  - `offboard_gate regression PASS`
- Fresh project-side upper-half regression facts:
  - `timeout 20s roslaunch human_follow_bringup stage2_goal_adapter_regression.launch` passed
  - `stage2 goal/adapter regression PASS ... distinct_goals=3`
  - this proves project-side rolling goal generation plus Stage2 adapter contracts inside `/home/coco/follwer_ws`
- Fresh project-side placeholder full-chain facts:
  - `timeout 25s roslaunch human_follow_bringup stage2_placeholder_full_chain_regression.launch` passed
  - `stage2 placeholder full-chain regression PASS distinct_goals=3 distinct_cmds=3 request_count=1`
  - this proves the project-side Stage2 skeleton now closes locally from:
    - `/follow/fusion/target_world`
    - `/follow/lio/odom`
    - `/follow/lidar/points`
    - through Stage2 goal generation, adapter, placeholder planner stub, bridge, and gate
    - into `/mavros/setpoint_raw/local`
- Those three project-side local Stage2 regressions are still bounded contract evidence only.
- Those three project-side local Stage2 regressions are NOT real EGO planner completion evidence.
- The first draft of the new Python sync script exposed a real sim-platform-only bug:
  - package-level `rsync --delete` on `human_follow_bringup` would delete the protected sim-specific MAVROS files unless those paths were also excluded from the package sync itself
  - that bug is now fixed by package-specific excludes for:
    - `config/mavros_px4_pluginlists_sitl.yaml`
    - `launch/stage1_px4_mavros.launch`
    - `launch/stage1_px4_mavros_sitl.launch`
- The sim-specific managed MAVROS contract was restored after that bug:
  - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/launch/stage1_px4_mavros.launch` is back on the `mavros/node.launch + pluginlists_yaml + px4_config.yaml` shape
  - `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1/src/human_follow_bringup/config/mavros_px4_pluginlists_sitl.yaml` is present again
- Fresh sim-platform verification on `2026-05-05` after the sync-surface hardening:
  - `python3 -m unittest /home/coco/sim_plane/tests/test_human_follow_ros_adapter.py /home/coco/sim_plane/tests/test_sync_human_follow_stage1_workspace.py` passed
  - `bash /home/coco/sim_plane/scripts/build_human_follow_stage1_ws.sh` passed
  - `python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root /home/coco/sim_plane/runs` passed again with no status or tracked-metric deltas versus the prior latest snapshot
- The managed sync surface is no longer Stage1-only for the active Stage2 frontier:
  - `/home/coco/sim_plane/scripts/sync_human_follow_stage1_workspace.py` now also mirrors the minimum project-side real-EGO vendor packages:
    - `ego_planner_vendor/plan_env`
    - `ego_planner_vendor/path_searching`
    - `ego_planner_vendor/bspline_opt`
    - `ego_planner_vendor/traj_utils`
    - `ego_planner_vendor/ego_planner`
- Fresh sim-plane-side managed real-EGO build evidence now exists on `2026-05-08`:
  - `python3 scripts/sync_human_follow_stage1_workspace.py` passed with the real-EGO vendor package mirror included
  - `bash scripts/build_human_follow_stage1_ws.sh` passed again in `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`
  - the managed workspace built:
    - `plan_env`
    - `path_searching`
    - `bspline_opt`
    - `traj_utils`
    - `ego_planner_node`
    - `traj_server`
- Fresh sim-plane-side managed real Stage2 evidence now exists:
  - managed launch:
    - `/home/coco/sim_plane/sim_plane/ros/human_follow_stage2_real_ego_managed.launch`
  - managed scenario:
    - `/home/coco/sim_plane/scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json`
  - latest clean artifact:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640/result.json`
  - fresh rerun refresh artifact:
    - `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_102052/result.json`
- The latest clean managed real-EGO artifact passed with these key facts:
  - `status=passed`
  - `ever_armed=true`
  - `algorithm_adapter_offboard_mode_reached=true`
  - `algorithm_adapter_stage2_launch_name=human_follow_stage2_real_ego_managed.launch`
  - `algorithm_adapter_stage2_variant=real_ego`
  - `algorithm_adapter_stage2_goal_count=13`
  - `algorithm_adapter_stage2_distinct_goal_count=6`
  - `algorithm_adapter_stage2_ego_cmd_count=376`
  - `algorithm_adapter_stage2_distinct_ego_cmd_count=8`
  - `algorithm_adapter_stage2_real_ego_path_observed=true`
  - `algorithm_adapter_stage2_waypoint_count=14`
  - `algorithm_adapter_stage2_search_goal_observed=true`
  - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=113`
  - `algorithm_adapter_stage2_gate_owned_offboard_inferred=true`
- The fresh rerun refresh artifact also passed and preserved the same proof boundary:
  - `status=passed`
  - `algorithm_adapter_stage2_search_goal_observed=true`
  - `algorithm_adapter_stage2_real_ego_path_observed=true`
  - `algorithm_adapter_stage2_waypoint_count=14`
  - `algorithm_adapter_stage2_distinct_goal_count=6`
  - `algorithm_adapter_stage2_distinct_ego_cmd_count=10`
  - `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs --json` also passed on top of this fresh rerun
- That latest clean managed real-EGO artifact also contains direct lower-level evidence for the three required Stage2 behaviors:
  - `follow`:
    - `stage2_follow_goal_generator state=follow`
  - `search goal`:
    - `stage2_follow_goal_generator state=search`
    - `algorithm_adapter_stage2_search_goal_observed=true`
  - `real EGO path`:
    - `/waypoint_generator/waypoints` had a live publisher from `stage2_move_base_goal_to_waypoint_path`
    - `/waypoint_generator/waypoints` had a live subscriber from `/ego_planner_node`
    - `algorithm_adapter_stage2_real_ego_path_observed=true`
- A real sim-plane-side observation bug was also exposed and retired in the same round:
  - the repo-local Stage2 probe originally failed to count search-goal observation because `/follow/sim/truth_phase` carries strings like `label=search_loss_right;visible=0;...`
  - the first real-EGO managed artifact at `/home/coco/sim_plane/runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_062547/result.json` already proved `real_ego_path_observed=true`, but falsely reported `search_goal_observed=false`
  - the landed sim-plane-only fix now parses the phase `label=` field correctly, and the clean rerun at `..._062640` retired that false negative
- The managed real-EGO proof is now the active Stage2 sim baseline.
- The older placeholder managed proof remains valid historical bounded evidence only; the sim-plane source tree no longer keeps a runnable placeholder scenario/managed launch entrypoint.

## Branch Objective

- This branch has one ordered product goal:
  - first make the tracking plus search portion complete and strict in simulation
  - then, if the project still wants it, integrate the project's own EGO route into that chain
  - then finish the complete end-to-end system simulation

## Current Frontier 2026-06-01

### 已锁定事实

- Windows/MATLAB 不是 Ubuntu Gazebo/RViz 仿真的前置条件；Windows 侧主要负责整理算法实验表格、图片和论文数据包。
- 当前可用的本地仿真平台候选是 `/home/coco/sim_plane`。
- `/home/coco/sim_plane` 已有 human-follow Stage2 real-EGO 受管入口：
  - `scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json`
  - `sim_plane/ros/human_follow_stage2_real_ego_managed.launch`
  - `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs`
- 既有记录证明的是 `PX4 SIH + MAVROS + Stage2 real-EGO` 受管链路；这不能自动等同于“Gazebo + RViz 严格全链路已经新鲜跑通”。

### 当前要解的问题

- 先判断 `/home/coco/sim_plane` 当前机器状态是否仍然可用，并确认它能否作为接下来 Gazebo/RViz 严格全链路仿真的主入口。

### 假设

- 如果 `doctor`、artifact hygiene、Stage2 latest acceptance 都通过，则可以进入“ fresh headless 受管 Stage2 rerun ”。
- 如果 headless rerun 通过，再升级到 Gazebo/RViz 或 visual 模式，避免一开始就被 GUI、显示、端口和旧进程问题干扰。

### 本轮不能做的事

- 不把 Windows/MATLAB 当成 Ubuntu 仿真的阻塞项。
- 不把历史 artifact 说成今天新跑通。
- 不直接宣称 Gazebo/RViz 严格全链路完成，除非有本轮新 artifact 支撑。
- 不改 EGO 内部、PX4、SLAM、detector、硬件标定或 acceptance 阈值。

### 下一步

- 跑轻量健康检查：
  - `python3 -m sim_plane doctor --json`
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json`
- 跑既有 Stage2 latest 验收：
  - `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs --json`
- 根据结果决定是否启动 fresh Stage2 受管 rerun，以及是否继续升级到 Gazebo/RViz 可视化链路。

### 本轮轻量检查结果

- `python3 -m sim_plane doctor --json` 通过：
  - `ready_backend_count=12`
  - `ready_adapter_count=6`
  - `px4_gazebo_classic=ready`
  - `px4_sih=ready`
  - `human_follow_ros_stage2=ready`
- `python3 -m sim_plane artifact-hygiene --artifact-root runs --json` 通过：
  - `status=clean`
  - `attention_count=0`
- `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs --json` 通过：
  - `status=passed`
  - latest artifact: `runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_102052`
  - `algorithm_adapter_stage2_real_ego_path_observed=true`
  - `algorithm_adapter_stage2_search_goal_observed=true`
- `python3 scripts/sync_human_follow_stage1_workspace.py --source-ws /home/coco/follower_paper_ws --dry-run` 显示当前论文线源同步到受管工作区为 `clean`。

### 本轮允许的下一步

- 可以从 `/home/coco/follower_paper_ws` 显式同步并重建受管工作区。
- 可以跑 fresh headless Stage2 real-EGO 受管链路，拿今天的新 artifact。
- 如果 fresh headless 通过，可以新增并验证 `px4_gazebo_classic + human_follow_ros_stage2` 场景；先 headless Gazebo，再 GUI/RViz。

### 本轮新增 Gazebo/RViz 证据

- 已从当前论文线显式同步受管工作区：
  - command: `python3 scripts/sync_human_follow_stage1_workspace.py --source-ws /home/coco/follower_paper_ws`
  - result: synced packages all `clean`; removed `2` pycache entries
- 已重建受管工作区：
  - command: `./scripts/build_human_follow_stage1_ws.sh`
  - result: PASS
- 已跑 fresh `PX4 SIH + MAVROS + Stage2 real-EGO`：
  - command: `python3 -m sim_plane run scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json --artifact-root runs --no-hold-open`
  - artifact: `runs/px4_sih_quadx_human_follow_stage2_real_ego_20260531_175457_993127`
  - result: `status=passed`
  - latest acceptance: `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs --json`
  - acceptance result: `status=passed`
- 已新增并验证 headless Gazebo 场景：
  - scenario: `scenarios/px4_gazebo_classic_iris_human_follow_stage2_real_ego.json`
  - command: `python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_human_follow_stage2_real_ego.json --artifact-root runs --no-hold-open`
  - artifact: `runs/px4_gazebo_classic_iris_human_follow_stage2_real_ego_20260531_180600_060153`
  - result: `status=passed`
  - key metrics:
    - `backend=px4_gazebo_classic`
    - `world=empty`
    - `model=iris`
    - `headless=true`
    - `gazebo_gui=false`
    - `ever_armed=true`
    - `algorithm_adapter_offboard_mode_reached=true`
    - `algorithm_adapter_stage2_real_ego_path_observed=true`
    - `algorithm_adapter_stage2_search_goal_observed=true`
    - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=82`
  - known residual warning:
    - `WARN  [commander] Connection to mission computer lost` after ROS/MAVROS shutdown; run still passed.
- 已新增并验证 Gazebo GUI + RViz 场景：
  - scenario: `scenarios/px4_gazebo_classic_iris_human_follow_stage2_real_ego_visual.json`
  - command: `python3 -m sim_plane run scenarios/px4_gazebo_classic_iris_human_follow_stage2_real_ego_visual.json --artifact-root runs --visualize --no-hold-open`
  - artifact: `runs/px4_gazebo_classic_iris_human_follow_stage2_real_ego_visual_20260531_180705_889048`
  - result: `status=passed`
  - dashboard: `http://127.0.0.1:8765` during run
  - key metrics:
    - `backend=px4_gazebo_classic`
    - `world=warehouse`
    - `model=iris`
    - `headless=false`
    - `gazebo_gui=true`
    - `ever_armed=true`
    - `algorithm_adapter_offboard_mode_reached=true`
    - `algorithm_adapter_stage2_real_ego_path_observed=true`
    - `algorithm_adapter_stage2_search_goal_observed=true`
    - `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=106`
  - RViz launch evidence:
    - adapter launch args included `rviz:=true`
    - roslaunch command included `rviz:=true`
  - known residual warning:
    - `WARN  [commander] Connection to mission computer lost` after ROS/MAVROS shutdown; run still passed.
    - `forcing process kill` for `human_follow_stage2_integrated_chain` during shutdown cleanup; run still passed.

### 新边界

- 现在可以说：当前论文线已经有 fresh Ubuntu 本地 `PX4 Gazebo Classic + MAVROS + Stage2 real-EGO + Gazebo GUI + RViz` 受管仿真证据。
- 仍不能说：
  - 已经实机安全；
  - detector、真实相机、真实 SLAM、硬件标定都已经端到端验证；
  - Gazebo Classic 代表未来所有 Gazebo/Harmonic 环境；
  - 所有论文指标都已经由 Gazebo 场景系统性扫参完成。
- "Complete and strict in simulation" for the pre-EGO branch means the branch should cover the Stage1 behavior target rather than only isolated platform plumbing:
  - target acquisition
  - follow
  - target loss
  - bounded search
  - reacquisition
  - stable command/output behavior under the current sim contract
- The current newer truth-full-chain pass is necessary evidence, but it is not yet the same thing as the whole branch objective being finished.
- The new seven-case behavior matrix substantially strengthens Phase 1 evidence, because it covers acquisition, search right, search left, approach/backoff, depart/follow, and both lateral directions under the managed `PX4 SIH` path.

## Ownership Split

- Project-side session owns:
  - deciding the minimum sync surface from `/home/coco/follwer_ws/src/human_follow_*`
  - current follower topic and launch contracts
  - the `human_follow_user` package contract
  - deciding whether the next user algorithm behaves as control-side or planning/perception-side ingress
- Sim-platform session owns:
  - `sim_plane` adapter behavior
  - scenario packaging
  - acceptance and artifact hygiene
  - managed workspace rebuilds and isolated PX4 SIH proofs

## Current Frontier

- Keep one bounded widening target only:
  - preserve the fresh green Stage1 truth-to-control managed acceptance on the cleaned early-stop surface
  - preserve the project-side detector/tracker local regression and the sim-plane single managed detector/tracker full-chain proof as separate evidence surfaces
  - do not reopen the retired `wait_ready` startup-flake, Stage1 reference-mismatch, or Stage2 branches as equal-priority work
  - if widened next, formalize detector/tracker-in-loop managed acceptance on sim-plane without modifying `/home/coco/follwer_ws`

## Phase Order

- Phase 1:
  - land the human-follow tracking and search simulation branch completely enough that it is not just a truth-driven smoke pass
- Phase 2:
  - if reopened by the project, integrate the project's own EGO route into the human-follow branch after Phase 1 is stable
- Phase 3:
  - prove the complete integrated system simulation and only then treat the sim branch as end-to-end complete

## Open Questions

- Should `sim_plane` now package a dedicated Stage1 detector/tracker managed acceptance command or matrix around `px4_sih_quadx_human_follow_detector_tracker_full_chain`?
- Does detector/tracker-in-loop need one bounded full-chain row first, or a smaller Stage1 behavior matrix, before it counts as managed acceptance?
- Should the detector/tracker surface inherit the same early-stop telemetry-window contract as the fresh truth-to-control Stage1 surface?

## Collaboration Protocol

- Before changing the human-follow sim branch, read this file plus `/home/coco/sim_plane/.supervisor/supervisor_ledger.md`.
- When a new fact is proven, write it here in the correct section before widening the branch again.
- Keep `facts`, `open questions`, and `ownership` separate.
- Do not use chat memory as the authority when this file disagrees.
- Do not reopen detector-in-the-loop, real-fusion, or acceptance-matrix widening until fresh evidence justifies it.
- Do not treat any existing `sim_plane` `ego_planner*` validation as if it were evidence for this project's human-follow branch.

## Next Handoff

- Project-side next useful contribution:
  - none required for the current sim-plane frontier unless detector/tracker launch or topic contracts change in `/home/coco/follwer_ws`
  - do not retune the Stage1 controller in reaction to the retired sim-plane acceptance-noise branch
- Sim-platform next useful contribution:
  - keep the fresh green Stage1 truth-to-control managed acceptance stable on the early-stop surface
  - if Stage1 is widened next, build detector/tracker-in-loop managed acceptance as a separate Stage1 evidence surface
  - do not reopen Stage2 or historical placeholder packaging while Stage1 is the active sim-plane frontier
