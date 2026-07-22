# sim_plane 平台总入口

这份文档只回答三个问题：现在有什么、平时怎么用、出问题先看哪里。更细的结构和维护规则见 `docs/项目结构与维护说明_zh.md`，自定义算法接入细节见 `docs/自定义算法接入指南_zh.md`。

## 1. 当前平台是什么

`sim_plane` 现在是一个轻量优先、面向算法验证的无人机仿真评测平台。它不是只包官方 launch 的脚本集合，核心价值在于统一了：

- 仿真后端启动
- 算法进程接入
- telemetry / event / result artifact
- KPI 评价
- suite / fuzz / failure injection
- dashboard 回放和报告查看
- acceptance / live-smoke / autotest 复验

主链路可以压缩成一句：

```text
CLI -> scenario -> backend/adapter -> artifact -> KPI -> suite/fuzz/acceptance -> dashboard
```

当前主线以四旋翼为准。外部 upstream 和 ROS workspace 固定放在 `/home/coco/sim_plane_ws`，本仓库只放平台代码、场景、配置、文档和统一入口。

它不应该被宣传成“高保真视觉无人机仿真平台”。真实光照、材质、动态遮挡、相机畸变、motion blur 这类能力不是当前主战场；当前主战场是四旋翼算法验证、可重复场景、KPI、故障/退化测试、日志复盘和实验管理。

## 2. 最常用命令

先看机器当前能跑什么：

```bash
python3 -m sim_plane doctor
```

从系统全局看当前平台是否健康、证据是否干净、已知能力边界是什么：

```bash
python3 -m sim_plane platform-health --artifact-root runs
```

跑最快的内置 demo 链体检（只证明 runner、artifact、基础 KPI，不启动 PX4/ROS）：

```bash
python3 -m sim_plane live-smoke --profile fast
```

跑本机一键复验包：

```bash
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

跑内置 demo backend 的四旋翼轻量 KPI/proxy 闭环：

```bash
python3 -m sim_plane quadrotor-exam --artifact-root runs
```

检查最新四旋翼实验是否相对冻结 reference 退化：

```bash
python3 -m sim_plane quadrotor-exam-acceptance --latest --artifact-root runs
```

查看内置 baseline 算法入口：

```bash
python3 -m sim_plane list-baselines
```

检查当前严格基线有没有退化：

```bash
python3 -m sim_plane platform-acceptance --latest --artifact-root runs
```

检查 artifact 目录是否干净：

```bash
python3 -m sim_plane artifact-hygiene --artifact-root runs
```

打开 dashboard 浏览、回放、对比 artifact 和报告：

```bash
python3 -m sim_plane serve runs
```

在完整 checkout 中执行过 `python3 -m pip install -e .`，或显式设置 `SIM_PLANE_HOME` 指向完整 checkout 后，这条命令才支持从任意目录启动。平台不会修改当前进程的工作目录；`runs`、`scenarios`、`configs` 等平台相对路径会统一解析到该仓库根目录。普通 wheel 不包含这些仓库资源，不是自包含运行形态。安装后的简写命令可用：

```bash
sim-plane serve runs
```

这个网页现在也是本地平台控制台。页面里的 `Platform Console` 会列出一组白名单操作按钮；每个按钮都显示准确命令、适用场景、输出位置、风险说明、证据类型、证据新鲜度和并发规则。点击运行时，后端只按白名单 ID 执行对应命令，不接受网页传入任意 shell 命令。

前端按钮按工作流分成五类：

- `1 基础确认`：确认机器、仓库和已有证据是否可信。
- `2 Fresh 运行`：重新启动真实运行链并新建 artifact。
- `3 KPI 评测`：批量跑固定任务或扰动，输出指标、排名和最差 case。
- `4 回归验收`：读取已有 latest artifact/report，对照冻结 reference 判断是否退化。
- `5 算法接入`：查看或运行标准算法入口，先验证接口再接复杂算法。

这里最容易误用的是 `Fresh 运行证据` 和 `历史证据回归`。前者会重新跑场景，后者只读取已有 artifact/report。平台会通过锁和 `.running`/`.complete` 跳过活动 artifact，不会把它当成已完成证据；但并发运行仍可能争用仿真端口和主机资源，而且 latest 检查可能仍指向上一条已完成证据。需要验收本轮结果时，应等 fresh 运行完成后再执行读取类检查。

`python3 -m unittest ...` 是开发自检命令，只会输出测试结果，不会打开网页。要看到前端，运行上面的 `serve` 命令。

## 3. 接自己的算法怎么选

控制类算法走 `external_command`。典型对象是 MAVSDK、MAVROS、MAVLink、普通 Python/C++ 控制程序：

```bash
python3 -m sim_plane check-algorithm-ingress \
  --adapter external_command \
  --backend px4_sih \
  --command "python3 /path/to/my_controller.py"
```

ROS 规划/感知类算法走 `ros_command`。典型对象是订阅 odom/cloud/map，发布 traj/cmd/PositionCommand 的 ROS 节点或 launch：

```bash
python3 -m sim_plane check-algorithm-ingress \
  --adapter ros_command \
  --backend marsim \
  --command "roslaunch my_pkg planner.launch"
```

第一次接入不要直接追求复杂场景，先让体检命令告诉你：进程是否起来、topic/端口是否通、是否发出控制、是否产生 KPI。

## 4. 看仿真和结果

轻量网页可视化和 artifact 浏览：

```bash
python3 -m sim_plane serve runs
```

需要 ROS 3D 内容时，用支持 RViz 的场景，例如：

```bash
python3 -m sim_plane run scenarios/marsim_ros_command_template.json --rviz --visualize --no-hold-open
```

PX4/QGroundControl/JSBSim/Gazebo Classic 路径仍是可选视觉面，不是所有测试都必须打开 GUI。默认优先用轻路径跑评测，只有需要观察 3D 传感器、规划轨迹或模型时再打开 RViz/Gazebo/QGC。

## 5. 当前正式能力面

已经整理成正式平台面的能力包括：

- `PX4 SIH`
- `PX4 + JSBSim`
- `PX4 + Gazebo Classic`
- `MARSIM`
- `FAST_LIO + MARSIM`
- `EGO-Planner` / `EGO-Planner-Swarm`
- `MAVSDK` 控制 adapter
- `external_command` / `ros_command` 自定义算法接入
- KPI 插件评价
- demo degradation suite
- task-family suite
- deterministic scenario fuzz
- PX4-native `SYSTEM_MOTOR/OFF/OK` failure injection acceptance
- artifact / `.ulg` flight-log replay
- local `autotest-pack`
- demo-backend KPI/proxy `quadrotor-exam`
- 对应的 latest-vs-reference `quadrotor-exam-acceptance`
- baseline algorithm catalog

注意：这里的“正式能力面”表示平台里有统一 scenario、backend/adapter、
artifact 和验收入口，不等于当前机器此刻全部 `ready`。当前能不能直接跑，
必须以这两条命令为准：

```bash
python3 -m sim_plane doctor
python3 -m sim_plane list-backends
```

如果某个 ROS / MARSIM / FAST_LIO / EGO backend 显示 `scaffolded`，先按
`doctor` 输出补建对应 workspace，再跑下方命令。

`SUPER`、`visPlanner` 等前沿算法目前属于标准探针层，已有保留证据，但不等同于顶层严格基线。

## 6. 边界和风险

PX4-family 后端会默认尝试把新生成或变化过的 PX4 `.ulg` 收进每个 run artifact 的 `px4_ulog/` 目录。是否真的收到了日志，以该 artifact 内的 `px4_ulog/index.json` 为准；找不到新日志时只记录 `missing`，不改变仿真本身的 PASS/FAIL。

demo backend 的 dropout、延迟、噪声、通信中断、限速等适合做轻量鲁棒性评测。新增的 `sensor_stream_faults` 能模拟数据流层面的 GPS dropout、VIO scale drift、IMU noise burst，但仍不能说成 PX4 原生物理故障。PX4 原生故障只以 `px4-failure-acceptance` 中已有 latest/reference 证据的项为准。

ROS1 Noetic 和 Gazebo Classic 都已经 EOL。当前因为主机是 Ubuntu 20.04，平台继续把它们作为可用受管路径保留，但后续迁移应作为独立大版本处理，不能在当前稳定线里硬切。

## 7. 出问题先跑什么

按这个顺序排查：

```bash
python3 -m sim_plane platform-health --artifact-root runs --json
python3 -m sim_plane doctor --json
python3 -m sim_plane artifact-hygiene --artifact-root runs --json
python3 -m sim_plane live-smoke --profile fast
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

`platform-health` 不替代真正的仿真运行，也不改变任何 acceptance 阈值。它的作用是把 git 状态、doctor、artifact hygiene、manual probe hygiene、latest acceptance、suite/fuzz/flight-log/autotest 报告和当前客观边界聚合到一个报告里，方便每次优化前先判断平台整体状态。

如果只是自己的算法接不上，优先跑：

```bash
python3 -m sim_plane check-algorithm-ingress --scenario <your_scenario.json>
```

如果是历史结果看不懂，优先打开：

```bash
python3 -m sim_plane serve runs
```
