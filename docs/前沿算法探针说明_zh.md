# 前沿算法探针说明

## 1. 作用

这份文档只覆盖当前还没有进入严格平台基线、但已经做成标准复现入口的前沿算法：

- `SUPER`
- `visPlanner`

它的目标不是讲论文背景，而是说明：

- 现在应该怎么复现；
- 哪个 profile 是默认稳定复现面；
- 剩余噪声是什么性质；
- 哪些 artifact 才是当前机器应该保留的标准证据。

## 2. `SUPER`

### 2.1 默认稳定复现面

入口：

```bash
./scripts/run_super_benchmark.sh
```

当前默认 stable profile：

- `dense`

默认行为：

- 自动构建受管 workspace `/home/coco/sim_plane_ws/workspaces/ros1_super`
- 自动选择空闲 ROS master 端口
- 如果显式指定 `SIM_PLANE_ROS_MASTER_PORT` 且端口已占用，脚本会直接失败
- 产物写到 `runs/manual_probes/super_benchmark_dense_<timestamp>/`

当前本机保留证据：

- `runs/manual_probes/super_benchmark_dense_20260429_153853/summary.json`

`runs/` 被 `.gitignore` 排除，因此这条路径只描述当前机器上的 retained
evidence，不是随仓库分发的可移植 baseline。新克隆需要重新运行上面的入口生成证据。

关键结果：

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

### 2.2 可选压力面

如果要保留更激进的压力测试，可以手动跑：

```bash
./scripts/run_super_benchmark.sh --profile high_speed
```

说明：

- `high_speed` 仍然保留，但不再作为默认稳定复现面
- 它更容易出现 transient replanning miss，因此更适合作为 stress probe

### 2.3 现在如何理解剩余噪声

当前 `SUPER dense` 已经收掉了两类主要非功能性噪声：

- PCD 缺失 `intensity` 字段不再触发那条 PCL warning
- 固定 ROS master 端口导致串台的风险已退休

剩余 summary 字段里比较重要的是：

- `transient_replan_miss_count`
  表示某一次 replan 没给出更好的新轨迹，但系统继续沿当前 committed trajectory 运行
- `soft_optimizer_reject_count`
  表示内部候选轨迹被动态约束或位置约束拒绝

这两类现在属于 probe 层显式记录，不再直接污染严格 acceptance 的 warning 面。

## 3. `visPlanner`

入口：

```bash
./scripts/run_visplanner_tracking.sh
```

默认行为：

- 自动构建受管 workspace `/home/coco/sim_plane_ws/workspaces/ros1_visplanner`
- 自动选择空闲 ROS master 端口
- 如果显式指定 `SIM_PLANE_ROS_MASTER_PORT` 且端口已占用，脚本会直接失败
- 产物写到 `runs/manual_probes/visplanner_tracking_<timestamp>/`

当前本机保留证据：

- `runs/manual_probes/visplanner_tracking_20260429_153921/summary.json`

这条证据同样位于被忽略的 `runs/` 中，只对保留该 artifact 的本机成立；
新克隆需要重新运行探针，不能把本页路径当成仓库自带的通过证据。

关键结果：

- `target_pos_cmd_seen=true`
- `tracker_pos_cmd_seen=true`
- `target_bspline_seen=true`
- `target_bspline_drone_id_line="drone_id: 1"`
- `tracker_left_wait_target=true`
- `tracker_exec_traj=true`
- `warn_count=5`

## 4. 清理与保留

这两类探针都走同一套保留规则：

- 最新成功 canonical probe 由 `probe_meta.json` 标记
- 检查命令：

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs
```

- 清理 superseded 旧 probe：

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs --prune-safe
```

这样可以保证：

- `runs/` 顶层保持干净
- `runs/manual_probes/` 只保留仍然有价值的标准证据
- 旧的中间态不会持续堆积
