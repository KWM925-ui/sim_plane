# human-follow Stage2 受管仿真说明

## 1. 目标

这份说明只描述 `sim_plane` 侧如何把 `human-follow` 项目的真实 Stage2 主线，包装成一条受管、可复跑、可留证据的 `PX4 SIH + MAVROS` 仿真面。

这里的项目侧真实入口现在固定为：

- `/home/coco/follwer_ws/src/human_follow_bringup/launch/stage2_real_ego.launch`

这份说明明确不做两件事：

- 不把 `sim_plane` 仓内独立的 `ego_planner*` 能力面算作这个项目 Stage2 的进度
- 不把旧的 placeholder 证据误报成当前 Stage2 主线现状

## 2. 当前证据边界

当前这条受管 Stage2 面现在已经证明：

- `target_world -> Stage2 rolling follow goal`
- `target 丢失 -> Stage2 search goal`
- `goal -> Stage2 EGO topic adapter`
- `move_base_simple/goal -> waypoint_generator/waypoints`
- `waypoint_generator/waypoints -> real ego_planner -> PositionCommand`
- `PositionCommand -> Stage2 PX4 bridge -> Stage2 offboard gate -> real MAVROS -> real PX4 SIH`

当前这条受管 Stage2 面仍然不证明：

- detector-in-the-loop 图像检测
- real-fusion 真传感器链
- 更高层业务逻辑已经端到端封顶

## 3. 受管入口

Stage2 受管 launch：

- `sim_plane/sim_plane/ros/human_follow_stage2_real_ego_managed.launch`

Stage2 受管 scenario：

- `scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json`

Stage2 受管 adapter：

- `sim_plane/adapters/human_follow_ros_stage2.py`

Stage2 受管 probe：

- `scripts/ros_stage2_integrated_probe.py`

Stage2 受管 acceptance：

- `python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs`

## 4. 当前标准证据

当前冻结参考 artifact：

- `runs/px4_sih_quadx_human_follow_stage2_real_ego_20260508_062640/`

这条最新 clean rerun 已满足：

- `status=passed`
- `ever_armed=true`
- `algorithm_adapter_offboard_mode_reached=true`
- `algorithm_adapter_stage2_variant=real_ego`
- `algorithm_adapter_stage2_launch_name=human_follow_stage2_real_ego_managed.launch`
- `algorithm_adapter_stage2_search_goal_observed=true`
- `algorithm_adapter_stage2_real_ego_path_observed=true`
- `algorithm_adapter_stage2_waypoint_count=14`
- `algorithm_adapter_stage2_distinct_goal_count=6`
- `algorithm_adapter_stage2_distinct_ego_cmd_count=8`
- `algorithm_adapter_stage2_nonzero_mavros_setpoint_count=113`
- `events.jsonl` 为 `info`-only

## 5. 结构设计

当前 Stage2 受管面仍然故意拆成两半：

- 上半是“当前结构的真线输入生产”
- 下半是“项目侧真实 Stage2 链”

### 5.1 上半输入生产

受管 launch 里保留这些输入面：

- `human_truth_sequence_publisher`
- `truth_driven_scene_publisher`
- `tracker`
- `target_fusion`
- `target_frame_adapter`
- `target_world_projector`

这部分负责稳定产出：

- `/follow/fusion/target_world`
- `/follow/lidar/points`

同时通过：

- `odom_topic_relay_node.py`

把真实 MAVROS `local_position` 里出来的 odom 受管映射到：

- `/follow/lio/odom`

### 5.2 下半真实 Stage2 链

项目侧 Stage2 现在按真实主线运行：

- `stage2_follow_goal_generator`
- `stage2_ego_topic_adapter`
- `stage2_move_base_goal_to_waypoint_path`
- `ego_planner_node`
- `traj_server`
- `ego_position_command_bridge`
- `stage2_offboard_gate`

关键点是：

- OFFBOARD 不是由 `sim_plane` probe 主动切的
- probe 只负责 arm、观察链路、确认 OFFBOARD 最终是被项目侧 Stage2 gate 自己切进去的

## 6. 为什么这样设计

原因很简单：

- 如果直接把项目侧局部回归当成仿真完成证据，会缺真实 PX4 SIH + MAVROS 这半边
- 如果直接把 `sim_plane` 仓里的独立 `ego_planner` baseline 当成这个项目的 Stage2 证据，会把项目证据边界混掉

现在这条线的原则是：

- 上半尽量沿用你项目当前结构
- 下半严格切到项目侧 `stage2_real_ego.launch`
- `sim_plane` 只负责最小必要包装、观测、artifact 和 acceptance

## 7. 标准同步与构建

先同步：

```bash
python3 scripts/sync_human_follow_stage1_workspace.py
```

再重建：

```bash
./scripts/build_human_follow_stage1_ws.sh
```

注意：

- 现在同步面除了 `human_follow_*` 和 `quadrotor_msgs`，还必须包含最小 real-EGO vendor 包：
  - `ego_planner_vendor/plan_env`
  - `ego_planner_vendor/path_searching`
  - `ego_planner_vendor/bspline_opt`
  - `ego_planner_vendor/traj_utils`
  - `ego_planner_vendor/ego_planner`

## 8. 标准运行

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_human_follow_stage2_real_ego.json --artifact-root runs --no-hold-open
```

## 9. 当前最重要的判据

这条受管 real Stage2 proof 至少要满足：

- `algorithm_adapter_completed_successfully=true`
- `algorithm_adapter_armed=true`
- `algorithm_adapter_offboard_mode_reached=true`
- `algorithm_adapter_stage2_goal_count>=2`
- `algorithm_adapter_stage2_ego_cmd_count>=2`
- `algorithm_adapter_stage2_waypoint_count>=1`
- `algorithm_adapter_stage2_search_goal_observed=true`
- `algorithm_adapter_stage2_real_ego_path_observed=true`
- `algorithm_adapter_stage2_nonzero_mavros_setpoint_count>=10`
- `algorithm_adapter_stage2_gate_owned_offboard_inferred=true`

## 10. 标准验收

最新 artifact 验收：

```bash
python3 -m sim_plane human-follow-stage2-acceptance --latest --artifact-root runs
```

报告会落在：

```text
runs/human_follow_stage2_acceptance/
```

## 11. 已退休的旧结论

下面这些现在都不是当前主线：

- `human_follow_stage2_placeholder_managed.launch` 不是当前主入口
- `px4_sih_quadx_human_follow_stage2_placeholder` 不是当前主证据
- “managed Stage2 还没接真实 EGO”已经过时

placeholder 证据只作为历史 artifact 保留；仓库内不再保留可直接误用的 placeholder scenario/launch 入口。
