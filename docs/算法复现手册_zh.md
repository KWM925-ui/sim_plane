# 算法复现手册

## 1. 目的

这份文档只回答一个问题：  
**现在这个仓库里，哪些算法怎么复现，产物落到哪里，如何判断它是不是跑对了。**

## 2. 严格基线能力面的复现方式

### 2.1 顶层平台基线

直接跑：

```bash
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

如果这条命令通过，说明当前已经冻结到平台基线的能力面没有退化。

### 2.2 planner 基线

```bash
python3 -m sim_plane planner-acceptance --latest --artifact-root runs
```

### 2.3 human-follow Stage1 行为基线

```bash
python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root runs
```

如果这条命令通过，说明当前 human-follow 项目的 Stage1 跟踪/丢失/搜索/重捕获行为矩阵没有退化。

## 3. 常用标准入口

### 3.1 共享 runner 路径

- `./scripts/run_px4_sih_3d.sh`
- `./scripts/run_px4_jsbsim_quadx_visual.sh`
- `./scripts/run_px4_jsbsim_mavsdk_action.sh`
- `./scripts/run_px4_jsbsim_mavsdk_action_visual.sh`
- `./scripts/run_px4_gazebo_classic_iris_visual.sh`
- `./scripts/run_px4_gazebo_classic_iris_mavsdk_action.sh`
- `./scripts/run_marsim_single.sh`
- `./scripts/run_marsim_single_visual.sh`
- `./scripts/run_fast_lio_marsim.sh`
- `./scripts/run_fast_lio_marsim_visual.sh`
- `./scripts/run_ego_planner_single.sh`
- `./scripts/run_ego_planner_swarm_single.sh`
- `./scripts/run_ego_planner_marsim.sh`
- `./scripts/run_ego_planner_swarm_marsim.sh`
- `./scripts/run_ego_planner_fast_lio_marsim.sh`
- `./scripts/run_ego_planner_swarm_fast_lio_marsim.sh`

这些脚本最终都会落到 `runs/<artifact_name>/`，并受 acceptance gate 保护。

### 3.2 human-follow 用户算法受管入口

如果你要验证 `/home/coco/follwer_ws/src/human_follow_user` 里的用户规划入口已经被受管仿真工作区接住，直接跑：

```bash
./scripts/run_px4_sih_human_follow_user_planning_ingress.sh
```

这条脚本会自动做三件事：

- 同步 `/home/coco/follwer_ws/src/human_follow_*` 的最小必要文件面到受管工作区 `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`
- 保留受管工作区里仿真专用的 `stage1_px4_mavros.launch`、`stage1_px4_mavros_sitl.launch`、`mavros_px4_pluginlists_sitl.yaml`
- 重编受管工作区后，运行 `px4_sih_quadx_human_follow_user_planning_ingress`

当前 canonical 证据：

- `runs/px4_sih_quadx_human_follow_user_planning_ingress_20260505_151235/`

关键检查项：

- `result.json` 里 `status=passed`
- `result.json` 里 `algorithm_adapter_offboard_mode_reached=true`
- `result.json` 里 `algorithm_adapter_follow_state_name=follow`
- `external_controller_ingress_monitor` 日志里出现 `external ingress PASS controller_type=user_planning_node.py`

## 4. 前沿算法标准探针

### 4.1 `SUPER`

构建：

```bash
./scripts/build_super_ws.sh
```

运行：

```bash
./scripts/run_super_benchmark.sh
```

可选压力面：

```bash
./scripts/run_super_benchmark.sh --profile high_speed
```

默认行为：

- 自动使用受管 workspace `/home/coco/sim_plane_ws/workspaces/ros1_super`
- 自动选择空闲 ROS master
- 默认 stable profile 是 `dense`
- 产物落到 `runs/manual_probes/super_benchmark_dense_<timestamp>/`

关键检查项：

- `summary.json` 里的 `click_goal_seen=true`
- `summary.json` 里的 `pos_cmd_seen=true`
- `summary.json` 里的 `replan_success_count`
  用来确认规划链不是偶然抖一下就停
- `summary.json` 里的 `planner_warn_count`
  直接反映这次 `SUPER` 复现过程中真正保留在 warning 面上的数量
- `summary.json` 里的 `transient_replan_miss_count`
  记录 transient replan miss 的次数，但这类情况现在已经下沉到 probe 层，不再直接当成 warning 污染面
- `summary.json` 里的 `soft_optimizer_reject_count`
  记录内部候选轨迹被动态约束拒绝的次数
- `summary.json` 里的 `intensity_warn_count`
  单独记录那条已知的点云字段噪声
- `summary.json` 里的 `intensity_fallback_applied=true`
  表示这次运行已经自动补齐了缺失的 `intensity` 字段
- `fsm.log` 里出现 `FOLLOW_TRAJ`

### 4.2 `visPlanner`

构建：

```bash
./scripts/build_visplanner_ws.sh
```

运行：

```bash
./scripts/run_visplanner_tracking.sh
```

默认行为：

- 自动使用受管 workspace `/home/coco/sim_plane_ws/workspaces/ros1_visplanner`
- 自动选择空闲 ROS master
- 产物落到 `runs/manual_probes/visplanner_tracking_<timestamp>/`

关键检查项：

- `summary.json` 里的 `target_pos_cmd_seen=true`
- `summary.json` 里的 `tracker_pos_cmd_seen=true`
- `summary.json` 里的 `tracker_exec_traj=true`
- `summary.json` 里的 `target_bspline_drone_id_line="drone_id: 1"`
- `summary.json` 里的 `warn_count`
  用来记录这次 `visPlanner` 复现中的启动告警总数

## 5. 产物怎么看

### 5.1 `SUPER`

重点看：

- `summary.json`
- `mission.log`
- `fsm.log`
- `perfect_drone.log`
- `telemetry.jsonl`

当前默认 stable canonical 证据：

- `runs/manual_probes/super_benchmark_dense_20260429_153853/`

### 5.2 `visPlanner`

重点看：

- `summary.json`
- `launch.log`
- `target_bspline.yaml`
- `target_pos_cmd.yaml`
- `tracker_pos_cmd.yaml`
- `tracker_telemetry.jsonl`
- `target_telemetry.jsonl`

当前 canonical 证据：

- `runs/manual_probes/visplanner_tracking_20260429_153921/`

## 6. 何时算“复现稳定”

这里的“稳定复现”不是只看某次偶然成功，而是至少满足下面几点：

- 有固定脚本入口，不依赖临时手敲命令。
- 有隔离 ROS master，不和外部已有 ROS 环境串台。
- 有固定 artifact 目录结构。
- 有 `summary.json` 这种机器可读结果。
- 跑完之后，顶层 `platform-acceptance --latest` 仍然是绿的。
- 原本已经确认无伤的日志噪声，不能重新污染严格基线判断面。

## 7. 清理旧 probe

查看哪些旧 probe 只是历史中间态：

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs
```

直接清掉无引用的 superseded probe：

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs --prune-safe
```

这样可以保证 `runs/manual_probes/` 长期保持整洁，不会越积越乱。
