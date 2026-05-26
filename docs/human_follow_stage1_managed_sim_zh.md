# human-follow Stage1 受管仿真说明

## 1. 目的

这份文档只描述 `sim_plane` 侧如何受管运行和维护 `human-follow` 项目的 Stage1 仿真支线。

它不负责定义项目本体算法逻辑，也不把 `sim_plane` 仓内独立的 `ego_planner*` 基线算作这个项目的进度或证据。

## 2. 三个边界

- 项目源码真源：`/home/coco/follwer_ws`
- 平台受管工作区：`/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`
- 平台包装与验收仓：`/home/coco/sim_plane`

职责划分：

- `follwer_ws`
  负责 follower 项目本体源码、当前主线 launch/topic/算法接入口。
- `ros1_human_follow_stage1`
  负责 `sim_plane` 侧稳定复跑所需的受管镜像。
- `sim_plane`
  负责共享 runner、PX4 SIH 包装、scenario、acceptance、artifact、降噪和中文说明。

## 3. 当前受管目标

当前 `sim_plane` 侧只把下面这条线当作 human-follow Stage1 的主要受管仿真面：

- `PX4 SIH + human_follow_ros_stage1 + stage1_truth_fusion_controller_regression.launch`

这条线当前已经有两类证据：

- 单条 full-chain truth proof
- 七条 Stage1 行为矩阵 proof

但这些证据和平台里独立的 `ego_planner*` 能力面没有关系，不能混用。

## 4. 受管同步规则

不要直接把整个 `/home/coco/follwer_ws` 粗暴覆盖到受管工作区。

只同步当前 Stage1 受管所需的最小包面：

- `human_follow_bringup`
- `human_follow_control`
- `human_follow_fusion`
- `human_follow_msgs`
- `human_follow_perception`
- `human_follow_px4_bridge`

当前明确保护、不能被项目侧直接覆盖的 sim 专属文件：

- `src/CMakeLists.txt`
- `src/human_follow_bringup/config/mavros_px4_pluginlists_sitl.yaml`
- `src/human_follow_bringup/launch/stage1_px4_mavros.launch`
- `src/human_follow_bringup/launch/stage1_px4_mavros_sitl.launch`

原因很简单：

- 这些文件承载的是 `sim_plane` 侧受管 SITL/MAVROS 合同
- 项目侧当前目标不一定和平台受管 SITL 合同完全一致
- 如果直接覆盖，容易把已经冻结的 sim 路径打坏

## 5. 标准同步与构建

先同步：

```bash
python3 scripts/sync_human_follow_stage1_workspace.py
```

只看将要发生什么，不落盘：

```bash
python3 scripts/sync_human_follow_stage1_workspace.py --dry-run
```

同步后重建：

```bash
./scripts/build_human_follow_stage1_ws.sh
```

## 6. 标准运行入口

### 6.1 full-chain 真线 proof

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_human_follow_truth_full_chain.json --artifact-root runs --px4-dir /home/coco/sim_plane_ws/src/core/PX4-Autopilot --no-hold-open
```

### 6.2 七行为矩阵

```bash
./scripts/run_px4_sih_human_follow_stage1_behavior_matrix.sh --no-hold-open
```

### 6.3 行为矩阵验收

```bash
python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root runs
```

## 7. 什么时候需要重新同步

出现下面任一情况时，应先同步再验证：

- `follwer_ws` 里的 `stage1_truth_fusion_controller_regression.launch` 变了
- `controller_slot` / `target_world_projector` / `follow_px4_bridge` 相关链路变了
- perception/fusion/control 的 topic 或参数合同变了
- 需要把项目侧新的 Stage1 真线行为带到 `sim_plane` 受管仿真里

下面这些情况先不要同步：

- 只是项目侧算法接入位 `human_follow_user` 变化
- 只是项目侧 live/hardware 路径变化
- 只是后续 EGO 路线草稿变化

因为当前 `sim_plane` 侧的主任务是稳住 Stage1 仿真真线，不是无条件镜像项目全部分支。

## 8. 关于 `human_follow_user`

当前项目侧存在：

- `/home/coco/follwer_ws/src/human_follow_user`

但受管工作区当前不默认同步它。

原因：

- 这个包是用户真实算法落点，不是当前 Stage1 平台仿真真线运行所必需
- 在真实算法还没正式落进来之前，把它同步进受管工作区没有平台收益，反而增加漂移面

只有在“要用 `sim_plane` 共享 runner 直接跑用户真实算法”这个目标被重新打开时，才应把它纳入最小同步面。

## 9. 降噪原则

human-follow 支线在 `sim_plane` 侧遵守这几条：

- 不把 `ego_planner*` 证据混入 human-follow 说明和验收
- 不把项目侧 live/hardware 试探日志当作 sim proof
- 不把 `__pycache__`、`.pyc`、临时 probe 输出留在受管源码面
- 不把 sim 专属 MAVROS 合同被项目侧覆盖这类问题拖到运行时才发现

## 10. 当前已知未完成项

当前 `sim_plane` 侧还没有做的事：

- 没把 `human_follow_user` 纳入受管工作区
- 没把 detector-in-the-loop image perception 纳入这条受管 proof 面
- 没把 real-fusion/live 路线纳入这条受管 proof 面

这些都不应伪装成“已经被当前 Stage1 受管仿真证明”。

