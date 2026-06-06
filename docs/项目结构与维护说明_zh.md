# 项目结构与维护说明

## 1. 项目定位

`sim_plane` 是一个以当前这台 Ubuntu 20.04 主机为第一落点、面向算法验证的无人机仿真评测平台。
设计原则不是“先堆最重的全家桶”，而是：

- 先保证能跑、能看、能复现。
- 先把轻路径和统一控制面做稳。
- 再逐步接入更重的 3D、感知和规划算法。
- 不把当前平台宣传成 AirSim / Isaac Sim / Flightmare / FlightGoggles 那类高保真视觉仿真器。

当前平台已经分成两层：

- 严格基线层：已经纳入 `platform-acceptance` / `planner-acceptance` 的能力面。
- 扩展探针层：已经能稳定构建和复现，但暂时还放在 `runs/manual_probes/`，不直接污染顶层严格基线。

## 2. 目录结构

### 2.1 仓库内

- `sim_plane/`
  平台主代码，包含 CLI、runner、acceptance、artifact hygiene。
- `scripts/`
  统一入口脚本。已冻结能力面和前沿算法的标准运行脚本都放这里。
- `scenarios/`
  走共享 runner 的 JSON 场景定义。
- `configs/`
  上游仓库清单、平台验收矩阵、planner 验收矩阵。
- `docs/`
  文档目录。现在中文操作文档也统一放这里。
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
- `runs/platform_health/`
  全平台总健康报告，聚合 git、doctor、卫生检查、latest acceptance、suite/fuzz/flight-log/autotest 摘要和下一阶段候选计划
- `runs/suites/`
  `run-suite` 功能套件报告，包括退化测试、任务族测试、参数扫描和 KPI 排名
- `runs/algorithm_ingress/`
  自定义算法接入体检产生的临时场景和报告入口
- `runs/flight_log_analysis/`
  artifact telemetry 或 PX4 `.ulg` 飞行日志复盘报告
- `runs/scenario_fuzz/`
  可复现 seed fuzz/sweep 报告、最差 case 排名和生成出的 suite JSON
- `runs/autotest/`
  本机 CI/autotest-like 一键复验报告

### 3.3 手工探针产物

- `runs/manual_probes/`
  暂未纳入严格基线、但已经做过标准化复现的探针算法产物

这类目录现在也有专门的清理口，不再靠人工判断。

## 4. 日常维护命令

### 4.1 检查严格基线

```bash
python3 -m sim_plane platform-health --artifact-root runs
python3 -m sim_plane planner-acceptance
python3 -m sim_plane planner-acceptance --latest --artifact-root runs
python3 -m sim_plane platform-acceptance
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

`platform-health` 是进入维护工作的总入口。它不重新跑重仿真，也不放宽任何验收语义；它读取现有报告和 artifact，把当前状态、风险边界、下一阶段候选计划汇总到：

```text
runs/platform_health/
```

如果它失败，先看失败组件；如果它通过但有 warning，通常说明工作区未提交或存在需要人工确认的非功能风险。

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

### 4.4 功能退化与 KPI 套件

轻量 demo 后端现在支持可复现的退化/故障字段：

- `disturbances`：风、测量噪声、初始偏移等轻量扰动。
- `degradations`：传感器 dropout、目标丢失、延迟、噪声、测量 bias、bias 漂移、测量饱和、通信中断、控制限速/饱和。
- `kpi_*`：统一追加到 `result.json` 的评价指标，包括高度误差、超调、到达时间、稳定时间、恢复时间、轨迹误差、最终目标距离、速度/加速度峰值、速度/加速度粗糙度、传感器丢失/重捕获次数、安全边界违规、测量误差等。
- `kpi_mission_*`：只统计 mission/offboard 阶段，避免把起飞、降落瞬态误读成巡航或跟踪质量。

标准退化套件：

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_degradation_suite.json
```

标准轻量任务族套件：

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_task_family_suite.json
```

这套“考试卷”覆盖：

- 起飞/降落
- 航点跟踪
- 目标丢失与重捕获
- 感知退化
- 通信中断
- 控制饱和/限速
- fail-safe hold
- 安全边界检查

这些指标是追加层，不改变旧的 backend metrics 和现有 acceptance contract。
PX4 SIH 路径仍只使用真实支持的参数/命令，不把 demo 里的 wind 或 dropout
伪装成 PX4 物理故障。

### 4.4.1 标准论文 / 项目实验闭环

标准四旋翼实验闭环入口：

```bash
python3 -m sim_plane quadrotor-exam --artifact-root runs
```

标准四旋翼实验回归验收入口：

```bash
python3 -m sim_plane quadrotor-exam-acceptance --latest --artifact-root runs
```

默认使用：

```text
configs/paper_quadrotor_exam_suite.json
```

当前固定场景包括：

- `hover`
- `waypoint`
- `obstacle_avoidance_proxy`
- `corridor`
- `sensor_dropout`
- `dynamic_target`
- `failure_motor_proxy`
- `planner_compare`

每个场景都会产出统一 `kpi_*` 指标，报告里额外有 `exam.success_rate` 和关键 KPI 汇总，便于做论文表格、项目验收表和版本对比。

`quadrotor-exam-acceptance` 不重新跑仿真，而是读取最新 suite report 并和冻结 reference report 对比。它检查成功率、场景全集、每个场景状态，以及轨迹长度、速度、加速度、控制平滑度、安全违规、最终误差、恢复时间等 KPI 是否退化。

### 4.4.2 数据流层面传感器故障

轻量 demo backend 现在还支持 `sensor_stream_faults`：

- `gps_dropout`
- `vio_scale_drift`
- `imu_noise_burst`

标准入口：

```bash
python3 -m sim_plane run-suite scenarios/basic_takeoff.json \
  --suite configs/demo_sensor_stream_fault_suite.json
```

边界必须明确：这属于仿真数据流层面的传感器退化测试，不是 PX4-native
`MAV_CMD_INJECT_FAILURE`。PX4 原生命令级故障仍然只以
`px4-failure-acceptance` 为准。

### 4.4.3 Baseline 算法库入口

查看当前可用 baseline：

```bash
python3 -m sim_plane list-baselines
```

运行一个 baseline：

```bash
python3 -m sim_plane run-baseline pid_position_demo --artifact-root runs
```

当前 baseline catalog 里区分 `ready` 和 `planned`。`planned` 只表示后续值得实现，不会被平台冒充成已跑通能力。

打开 dashboard 时也能直接看到最新 suite 摘要、KPI 行和
`kpi_rankings` / `top_metric_effects`，同时也会展示最新专业测试面报告：
PX4 failure、flight-log replay、scenario fuzz、autotest pack。

```bash
python3 -m sim_plane serve runs
```

这里的价值是：以后接入新算法时，不只看“有没有跑通”，还可以看
“误差多大、控制平不平、恢复慢不慢、是否越界、哪一个退化因素让指标变差”。

### 4.5 PX4 原生故障注入验收

现在有一条独立的 PX4 原生故障注入验收面：

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_mavsdk_failure_motor.json \
  --artifact-root runs --no-hold-open

python3 -m sim_plane px4-failure-acceptance --latest --artifact-root runs
```

这条线验证的是：

- 平台启动真实 `PX4 SIH`。
- adapter 通过 MAVSDK failure plugin 发送 PX4 `MAV_CMD_INJECT_FAILURE`。
- 当前已证明的首个受管故障是 `SYSTEM_MOTOR/OFF`，随后用 `SYSTEM_MOTOR/OK` 复位。
- artifact 里必须出现 `failure_injection_accepted=true` 和
  `failure_injection_reset_accepted=true`。
- 报告保存在 `runs/px4_failure_injection_acceptance/`。

边界必须说清楚：

- 这不是 demo backend 的 dropout/noise/wind。
- 这不是“所有 PX4 故障都已覆盖”。
- 当前 PX4 源码显示这版通用 failure injector 首先稳定支持 `SYSTEM_MOTOR`
  路径，所以首个验收面只锁这个已经 fresh 证明的组合。
- `gps`、`rc_signal`、`mavlink_signal` 等其它 failure unit 后续要逐个用
  fresh artifact 证明 PX4 接受后，才能进入正式矩阵。

### 4.6 自定义算法接入体检

已有场景可以直接做接入体检：

```bash
python3 -m sim_plane check-algorithm-ingress \
  --scenario scenarios/px4_sih_quadx_external_command_template.json
```

也可以临时生成并体检一个 PX4 侧控制算法：

```bash
python3 -m sim_plane check-algorithm-ingress \
  --adapter external_command \
  --backend px4_sih \
  --command "python3 /path/to/my_controller.py"
```

ROS 规划/感知算法同理：

```bash
python3 -m sim_plane check-algorithm-ingress \
  --adapter ros_command \
  --backend marsim \
  --command "roslaunch my_pkg planner.launch"
```

体检会检查：

- 场景是否跑完并通过
- adapter 是否存在
- adapter 是否报告成功
- 是否有 telemetry
- 是否观察到控制/命令输出
- 是否生成 `kpi_*` 指标

这条命令的目标不是替代完整验收，而是在你第一次接自己的算法时，
快速指出失败点到底是进程没起来、topic/端口没通、没有发控制，还是跑完但没有指标。

### 4.7 飞行日志 / artifact KPI 复盘

可以把一次 `sim_plane` run artifact 复盘成统一 KPI 报告：

```bash
python3 -m sim_plane flight-log-analyze runs/<artifact_dir>
```

也可以直接解析 PX4 `.ulg`：

```bash
python3 -m sim_plane flight-log-analyze /path/to/log.ulg
```

报告保存在：

```text
runs/flight_log_analysis/
```

它会提取：

- duration
- 最大/最小高度
- 最大/平均速度
- 路径长度
- mode/nav state 变化
- arming state 变化
- PX4 日志 warning/fail/error
- replay 后的 `kpi_*`

边界要分清：

- artifact replay 读的是 `telemetry.jsonl`、`result.json`、`events.jsonl`。
- `.ulg` replay 读的是真 PX4 ULog。
- PX4-family 后端会默认尝试把新生成或变化过的 `.ulg` 收进 artifact 的 `px4_ulog/` 目录；是否收集成功以 `px4_ulog/index.json` 的 `status` 为准。
- 不能把普通 artifact replay 等同于 `.ulg` replay；只有实际存在 artifact-local `.ulg` 文件或直接传入 `.ulg` 文件时，才是在读 PX4 原始日志。

### 4.8 可复现 fuzz / 最差 case 搜索

跑一组固定 seed 的场景扰动、退化、限速、通信中断组合：

```bash
python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json \
  --profile demo_fast \
  --seed 20260528 \
  --variants 6
```

报告保存在：

```text
runs/scenario_fuzz/
```

每次报告会保存：

- 生成出的 `generated_suite.json`
- 每个变体的 artifact
- `kpi_rankings`
- `top_metric_effects`
- `worst_cases`

这件事的价值是：以后你接入一个新算法，不只是跑一条正常场景，而是自动扫一批可复现难例，直接看哪种条件让指标最差。

当前 `demo_fast` 是 demo backend 的轻量退化/扰动 fuzz，不是 PX4 原生故障注入。PX4 原生故障仍以 `px4-failure-acceptance` 为准。

### 4.9 一键 autotest pack

快速本机复验：

```bash
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

报告保存在：

```text
runs/autotest/
```

`fast` profile 当前包括：

- `doctor`
- `artifact-hygiene`
- `live-smoke --profile fast`
- demo degradation suite
- seeded scenario fuzz
- flight-log artifact replay
- PX4 failure acceptance latest
- platform acceptance latest

这件事的价值是：关机重启后，不需要手动挑命令，可以一条命令验证“平台还健康、artifact 还干净、核心测试面还绿”。

## 5. 现在的运行分层

### 5.1 已冻结到严格基线的能力面

- `PX4 SIH`
- `PX4 + JSBSim`
- `PX4 + Gazebo Classic`
- `PX4 + MAVSDK`
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

但还没有直接放进顶层严格 21 行平台基线，因为它们的噪声 contract 还没有像共享 runner 那样完全冻结。

## 6. 当前维护原则

- 任何新的算法 widening，先保证 `platform-acceptance --latest` 不退化。
- `runs/` 顶层只放完整 artifact 和保留的报告根目录。
- 还没正式进共享 runner 的实验性算法，一律放到 `runs/manual_probes/`。
- frontier probe 如果显式指定了 `SIM_PLANE_ROS_MASTER_PORT`，端口必须空闲；如果不指定，脚本会自动选空闲端口，避免串到旧 master。
- 新增日志噪声如果已经确认无伤，要么从源头修掉，要么隔离到 probe 层，不能回流污染严格 acceptance 面。
