# 自定义算法接入指南

## 1. 平台接入定位

这套仓库不是只启动仿真器的脚本集合，而是统一编排和评测层。它把
`PX4 / JSBSim / Gazebo Classic / MARSIM / FAST_LIO / EGO-Planner` 等能力面
收敛到同一套 runner、scenario、artifact、KPI、acceptance 和 dashboard
流程里。

自定义算法接入的目标是：让你的程序通过稳定 adapter 挂到这条流程上，
跑完后自动留下可复查 artifact 和指标，而不是靠肉眼看一次窗口效果。

## 2. 现在新增了什么

现在有两条真正属于“你自己”的接入面：

- `external_command`
- `ros_command`

两者共同点是：

1. 仿真后端由平台负责启动
2. 你的算法由平台负责启动
3. 平台把连接信息、topic 契约、artifact 路径通过稳定环境变量交给你的算法
4. 你的算法退出后，平台把它的结果并回统一 artifact

差别是：

- `external_command`
  - 适合宿主机普通进程
  - 更偏 `MAVSDK / MAVROS / 控制 / 决策 / 任务逻辑`
- `ros_command`
  - 适合本身就是 ROS 节点或 ROS launch 的算法
  - 更偏 `订阅 odom/cloud/map，发布 traj/cmd`

## 3. 控制类算法接入

如果你的算法本质上是：

- Python / C++ 自己的进程
- 通过 `MAVSDK`、`MAVLink`、`ROS`、socket 或其他方式跟仿真对象通信

那么优先走 `external_command`。

推荐先用生成器创建你自己的场景，不要手抄 JSON：

```bash
python3 -m sim_plane generate-scenario \
  --adapter external_command \
  --command "python3 /path/to/my_controller.py" \
  --name my_px4_controller
```

生成后直接跑：

```bash
python3 -m sim_plane run scenarios/my_px4_controller.json --visualize --no-hold-open
```

现成模板场景：

- [px4_sih_quadx_external_command_template.json](/home/coco/sim_plane/scenarios/px4_sih_quadx_external_command_template.json)

现成模板算法：

- [mavsdk_takeoff_template.py](/home/coco/sim_plane/examples/user_algorithms/mavsdk_takeoff_template.py)

直接跑：

```bash
python3 -m sim_plane run scenarios/px4_sih_quadx_external_command_template.json --visualize --no-hold-open
```

这条命令的意义不是“跑一个新官方 demo”，而是验证：

- 平台启动了 `PX4 SIH`
- 平台再启动了你自己的外部算法进程
- 你的算法通过平台给的连接信息接入 PX4
- 整个运行仍然写入统一 `runs/<artifact>/`

## 4. ROS 规划/感知类算法接入

如果你的算法本身就是 ROS 图里的一部分，比如：

- 订阅 `odom / cloud / map`
- 发布 `/planning/pos_cmd`、`traj`、`cmd`
- 需要 `rosrun` 或 `roslaunch` 直接拉起

那么现在优先走 `ros_command`。

推荐先用生成器创建你自己的 ROS 场景：

```bash
python3 -m sim_plane generate-scenario \
  --adapter ros_command \
  --backend marsim \
  --command "roslaunch my_pkg planner.launch" \
  --name my_ros_planner
```

如果你的算法需要自己指定 ready 检查 topic，可以显式写：

```bash
python3 -m sim_plane generate-scenario \
  --adapter ros_command \
  --backend fast_lio_marsim \
  --command "roslaunch my_pkg planner.launch" \
  --name my_fast_lio_planner \
  --required-subscribed-topics "/Odometry,/quad0_pcl_render_node/sensor_cloud,/map_generator/global_cloud" \
  --required-published-topics "/quad_0/planning/pos_cmd"
```

现成模板场景：

- [marsim_ros_command_template.json](/home/coco/sim_plane/scenarios/marsim_ros_command_template.json)
- [fast_lio_marsim_ros_command_template.json](/home/coco/sim_plane/scenarios/fast_lio_marsim_ros_command_template.json)

现成模板算法：

- [ros_position_command_template.py](/home/coco/sim_plane/examples/user_algorithms/ros_position_command_template.py)

先确认 ROS 场景后端当前是 `ready`：

```bash
python3 -m sim_plane doctor
python3 -m sim_plane list-backends
```

如果 `marsim` 或 `fast_lio_marsim` 显示 `scaffolded`，说明平台入口存在，
但当前机器的 ROS workspace 还没准备好。先按 `doctor` 提示运行对应 build
脚本，再执行下面两条模板命令。

直接跑 `MARSIM` 版本：

```bash
python3 -m sim_plane run scenarios/marsim_ros_command_template.json --rviz --visualize --no-hold-open
```

直接跑 `FAST_LIO + MARSIM` 版本：

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim_ros_command_template.json --rviz --visualize --no-hold-open
```

这两条命令验证的不是“官方 planner 还能不能跑”，而是：

- 平台启动了 `MARSIM` 或 `FAST_LIO + MARSIM`
- 平台再启动了你自己的 ROS 算法进程
- 你的算法直接吃平台暴露出来的 `odom / cloud / map`
- 你的算法直接往 MARSIM 控制链发布 `PositionCommand`
- 整个过程仍然落到统一的 `runs/<artifact>/`

## 5. 平台会给你的算法什么

`external_command` 和 `ros_command` 都会自动注入这些环境变量：

- `SIM_PLANE_BACKEND`
- `SIM_PLANE_VEHICLE`
- `SIM_PLANE_SCENARIO_NAME`
- `SIM_PLANE_TELEMETRY_ENDPOINT`
- `SIM_PLANE_PREFERRED_TELEMETRY_PORT`
- `SIM_PLANE_SYSTEM_ADDRESS`
- `SIM_PLANE_TARGET_ALTITUDE_M`
- `SIM_PLANE_EXPECTED_DURATION_S`
- `SIM_PLANE_ARTIFACT_DIR`
- `SIM_PLANE_ADAPTER_RESULT_JSON`
- `SIM_PLANE_ROS_MASTER_URI`
- `SIM_PLANE_ROS_HOSTNAME`
- `SIM_PLANE_ROS_IP`
- `SIM_PLANE_ODOM_TOPIC`
- `SIM_PLANE_POINTCLOUD_TOPIC`
- `SIM_PLANE_COMMAND_TOPIC`
- `SIM_PLANE_MAP_TOPIC`
- `SIM_PLANE_GOAL_TOPIC`
- `SIM_PLANE_ROS_SETUP`
- `SIM_PLANE_ROS_WORKSPACE_SETUPS`

其中最关键的是：

- `SIM_PLANE_SYSTEM_ADDRESS`
  - 对 PX4 路径，默认是 `udp://127.0.0.1:14580`
  - 如果你的算法走 `MAVSDK` 控制，这个就是最该直接拿来连的地址
- `SIM_PLANE_TELEMETRY_ENDPOINT`
  - 这是平台自己的共享遥测面，通常是 `14550`
  - 不建议你的控制算法直接拿它当 MAVSDK 控制口
- `SIM_PLANE_ADAPTER_RESULT_JSON`
  - 你的算法可以把自己的运行结果写到这个 JSON 里，平台会自动收进去
- `SIM_PLANE_ODOM_TOPIC / SIM_PLANE_POINTCLOUD_TOPIC / SIM_PLANE_COMMAND_TOPIC / SIM_PLANE_MAP_TOPIC`
  - 对 ROS 类算法，这是最重要的一组接口契约
  - 你的算法不需要再去猜 topic 名字
- `SIM_PLANE_ROS_MASTER_URI`
  - `ros_command` 会自动把你的算法接到当前这轮仿真的 ROS master 上

## 6. 你的算法最少要做什么

最少只要做到两件事：

1. 能被命令行启动
2. 退出码为 `0` 表示成功

这样平台就已经能把它当成一个算法任务跑起来。

如果你想更完整一点，再多做一步：

把结果写到 `SIM_PLANE_ADAPTER_RESULT_JSON` 指向的文件，比如：

```json
{
  "success": true,
  "metrics": {
    "my_metric": 1.23
  },
  "notes": [
    "my algorithm completed normally"
  ]
}
```

如果你的场景使用 `backend_options.success_criteria="adapter_takeoff"`，
也就是要证明外部算法真的完成了起飞控制，不只是进程正常退出，那么
`metrics` 里必须明确写：

```json
{
  "success": true,
  "metrics": {
    "algorithm_adapter_target_altitude_reached": true
  }
}
```

平台会同时检查后端遥测里的 `target_altitude_reached=true`。这两个条件都满足，
这次 run 才会被判定为 `adapter_takeoff` 通过。

## 7. 什么时候该走哪条路

### 7.1 适合 `external_command`

- 你的算法是飞控外的控制/决策/任务逻辑
- 你的算法已经能自己跑，只是缺一个仿真对象
- 你的算法能通过 `MAVSDK` / `MAVROS` / socket / 自己的接口去连仿真对象

### 7.2 适合 `ros_command`

- 你的算法本身就是 ROS planner 节点
- 它输入必须是 `odom + pointcloud + map + traj topic`
- 输出也是 ROS topic，比如 `/planning/pos_cmd`
- 你的算法需要跟当前仿真共用同一个 ROS master
- 你的算法启动方式天然就是 `rosrun` / `roslaunch`

这时不需要一上来就自己写专用 backend。

先用 `ros_command` 把你的算法拉进平台统一生命周期里。

只有遇到下面这种更深耦合情况，才需要继续下沉到 repo-local backend/wrapper：

- 你的算法必须跟仿真器内部 launch 图深度重写
- 你的算法不只是发布命令，还要替换整个 controller / bridge / goal 触发链
- 你的算法依赖一组 repo-local remap、wrapper launch、对齐节点才能成立

## 8. 你自己的算法到底该怎么选路

可以直接按这个判断：

### A 类：MAVSDK / MAVROS / 控制类算法

走：

- `PX4 SIH`
- `PX4 + JSBSim`
- `PX4 + Gazebo Classic`
- 再配 `external_command`

这是现在最适合你快速起步的路径。

### B 类：ROS 规划 / 感知 / 建图类算法

走：

- `MARSIM`
- `FAST_LIO + MARSIM`
- 再配 `ros_command`

前置条件是 `doctor` 里对应 backend 已经是 `ready`；如果还是
`scaffolded`，不要直接跑业务算法，先补 workspace。

如果你的算法需要可视化：

- 加 `--rviz`
- 加 `--visualize`

这样你能同时看到：

- `RViz` 里的点云、模型、ROS 侧 3D 画面
- 网页仪表盘里的统一遥测、事件、artifact 入口

### C 类：纯 Python 逻辑，还没接飞行接口

先别碰大 ROS 图。

先把它改成：

- 能读取 `SIM_PLANE_SYSTEM_ADDRESS`
- 能自己连 PX4
- 能返回结果 JSON

然后先在 `PX4 SIH + external_command` 上跑通。

## 9. 对你现在这句话的直接回答

如果只看之前的状态，你说得对：

- 它还不够像“我自己的四旋翼仿真平台”
- 更像“我把很多成熟上游系统统一调起来了”

但从现在开始，平台已经不是只有“统一编排”了，而是多了两条真正可反复复用的用户入口：

- **控制类算法可以直接通过 `external_command` 进 PX4 路径**
- **ROS 规划/感知类算法在对应 backend ready 后，可以通过 `ros_command` 进 `MARSIM / FAST_LIO + MARSIM` 路径**

如果你下一步把你自己的算法入口给我，我现在不是再去解释平台怎么想，而是可以直接把它接到这两条现成通路里。
