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

当前主线以四旋翼为准。外部 upstream 和 ROS workspace 固定放在 `/home/coco/sim_plane_ws`，本仓库只放平台代码、场景、配置、文档和统一入口。

它不应该被宣传成“高保真视觉无人机仿真平台”。真实光照、材质、动态遮挡、相机畸变、motion blur 这类能力不是当前主战场；当前主战场是四旋翼算法验证、可重复场景、KPI、故障/退化测试、日志复盘和实验管理。

## 2. 最常用命令

先看机器当前能跑什么：

```bash
python3 -m sim_plane doctor
```

跑最快的本机健康检查：

```bash
python3 -m sim_plane live-smoke --profile fast
```

跑本机一键复验包：

```bash
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

跑标准论文/项目式四旋翼实验闭环：

```bash
python3 -m sim_plane quadrotor-exam --artifact-root runs
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
- paper/project-style `quadrotor-exam`
- baseline algorithm catalog

`SUPER`、`visPlanner` 等前沿算法目前属于标准探针层，已有保留证据，但不等同于顶层严格基线。

## 6. 边界和风险

当前已经能解析 PX4 `.ulg`，但 fresh PX4 run 自动把 `.ulg` 收进每个 artifact 还没有做成默认能力。

demo backend 的 dropout、延迟、噪声、通信中断、限速等适合做轻量鲁棒性评测。新增的 `sensor_stream_faults` 能模拟数据流层面的 GPS dropout、VIO scale drift、IMU noise burst，但仍不能说成 PX4 原生物理故障。PX4 原生故障只以 `px4-failure-acceptance` 中已经 fresh 证明的项为准。

ROS1 Noetic 和 Gazebo Classic 都已经 EOL。当前因为主机是 Ubuntu 20.04，平台继续把它们作为可用受管路径保留，但后续迁移应作为独立大版本处理，不能在当前稳定线里硬切。

## 7. 出问题先跑什么

按这个顺序排查：

```bash
python3 -m sim_plane doctor --json
python3 -m sim_plane artifact-hygiene --artifact-root runs --json
python3 -m sim_plane live-smoke --profile fast
python3 -m sim_plane autotest-pack --profile fast --artifact-root runs
```

如果只是自己的算法接不上，优先跑：

```bash
python3 -m sim_plane check-algorithm-ingress --scenario <your_scenario.json>
```

如果是历史结果看不懂，优先打开：

```bash
python3 -m sim_plane serve runs
```
