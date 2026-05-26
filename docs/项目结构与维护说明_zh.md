# 项目结构与维护说明

## 1. 项目定位

`sim_plane` 是一个以当前这台 Ubuntu 20.04 主机为第一落点的无人机算法仿真平台。  
设计原则不是“先堆最重的全家桶”，而是：

- 先保证能跑、能看、能复现。
- 先把轻路径和统一控制面做稳。
- 再逐步接入更重的 3D、感知和规划算法。

当前平台已经分成两层：

- 严格基线层：已经纳入 `platform-acceptance` / `planner-acceptance` 的能力面。
- 扩展探针层：已经能稳定构建和复现，但暂时还放在 `runs/manual_probes/`，不直接污染顶层严格基线。

## 2. 目录结构

### 2.1 仓库内

- `sim_plane/`
  平台主代码，包含 CLI、runner、acceptance、artifact hygiene。
- `scripts/`
  统一入口脚本。已冻结能力面和前沿算法的标准运行脚本都放这里。
  human-follow Stage1 的受管同步和构建脚本也放这里。
- `scenarios/`
  走共享 runner 的 JSON 场景定义。
- `configs/`
  上游仓库清单、平台验收矩阵、planner 验收矩阵。
- `docs/`
  文档目录。现在中文操作文档也统一放这里。
  human-follow 项目的平台侧受管仿真说明见 `docs/human_follow_stage1_managed_sim_zh.md`。
- `runs/`
  运行产物根目录。

### 2.2 工作空间外部根

所有上游仓库和 ROS workspace 都固定放在：

```text
/home/coco/sim_plane_ws
```

这里再分成几类：

- `src/core/`
  核心飞控类上游，例如 `PX4-Autopilot`
- `src/labs/`
  实验室算法和仿真器，例如 `MARSIM`、`FAST_LIO`、`SUPER`、`visPlanner`
- `workspaces/`
  受管 catkin workspace，例如 `ros1_marsim`、`ros1_super`、`ros1_visplanner`
- `toolchains/`
  本地补齐的第三方工具链，例如 `glfw`、`jdk`、`apache-ant`

## 3. 运行产物约定

### 3.1 严格基线产物

- `runs/<artifact_name>/`
  完整共享 runner 产物，至少包含：
  - `manifest.json`
  - `result.json`
  - `events.jsonl`

### 3.2 验收报告

- `runs/acceptance/`
  planner 验收报告
- `runs/platform_acceptance/`
  平台顶层验收报告
- `runs/human_follow_stage1_acceptance/`
  human-follow 项目专用 Stage1 行为验收报告

### 3.3 手工探针产物

- `runs/manual_probes/`
  暂未纳入严格基线、但已经做过标准化复现的探针算法产物

这类目录现在也有专门的清理口，不再靠人工判断。

### 3.4 human-follow 受管同步工具

- `scripts/sync_human_follow_stage1_workspace.py`
  human-follow Stage1 受管同步的唯一主入口
- `scripts/sync_human_follow_stage1_workspace.sh`
  兼容包装，内部直接转调 Python 主入口，不再保留独立同步逻辑
- `scripts/build_human_follow_stage1_ws.sh`
  重编 `/home/coco/sim_plane_ws/workspaces/ros1_human_follow_stage1`

同步时明确保留仿真专用契约：

- `src/human_follow_bringup/launch/stage1_px4_mavros.launch`
- `src/human_follow_bringup/launch/stage1_px4_mavros_sitl.launch`
- `src/human_follow_bringup/config/mavros_px4_pluginlists_sitl.yaml`

## 4. 日常维护命令

### 4.1 检查严格基线

```bash
python3 -m sim_plane planner-acceptance
python3 -m sim_plane planner-acceptance --latest --artifact-root runs
python3 -m sim_plane human-follow-stage1-acceptance
python3 -m sim_plane human-follow-stage1-acceptance --latest --artifact-root runs
python3 -m sim_plane platform-acceptance
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

### 4.2 检查 artifact 根目录整洁性

```bash
python3 -m sim_plane artifact-hygiene --artifact-root runs
```

需要自动迁移和清理时：

```bash
python3 -m sim_plane artifact-hygiene \
  --artifact-root runs \
  --migrate-retained-manual \
  --prune-safe
```

### 4.3 检查 `manual_probes` 整洁性

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs
```

清掉无引用、已被更新结果替代的旧 probe：

```bash
python3 -m sim_plane manual-probe-hygiene --artifact-root runs --prune-safe
```

## 5. 现在的运行分层

### 5.1 已冻结到严格基线的能力面

- `PX4 SIH`
- `PX4 + JSBSim`
- `PX4 + Gazebo Classic`
- `PX4 + MAVSDK`
- `PX4 + human_follow_ros_stage1`
- `MARSIM` CPU / GPU
- `FAST_LIO + MARSIM`
- `EGO-Planner`
- `EGO-Planner-Swarm`
- `EGO-Planner + MARSIM`
- `EGO-Planner-Swarm + MARSIM`
- `EGO-Planner + FAST_LIO + MARSIM`
- `EGO-Planner-Swarm + FAST_LIO + MARSIM`

### 5.2 已整理为标准探针、但暂不进严格基线的前沿算法

- `SUPER`
- `visPlanner`

它们已经具备：

- 受管 workspace
- 标准 build 脚本
- 标准 run 脚本
- 自动选择空闲的隔离 ROS master
- 固定 artifact 结构
- 中文说明文档

但还没有直接放进顶层严格 23 行平台基线，因为它们的噪声 contract 还没有像共享 runner 那样完全冻结。

## 6. 当前维护原则

- 任何新的算法 widening，先保证 `platform-acceptance --latest` 不退化。
- `runs/` 顶层只放完整 artifact 和保留的报告根目录。
- 还没正式进共享 runner 的实验性算法，一律放到 `runs/manual_probes/`。
- frontier probe 如果显式指定了 `SIM_PLANE_ROS_MASTER_PORT`，端口必须空闲；如果不指定，脚本会自动选空闲端口，避免串到旧 master。
- 新增日志噪声如果已经确认无伤，要么从源头修掉，要么隔离到 probe 层，不能回流污染严格 acceptance 面。
