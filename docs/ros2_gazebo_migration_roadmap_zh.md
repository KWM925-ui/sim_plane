# ROS2 / Gazebo 迁移路线图

## 1. 结论先行

当前不建议立刻把平台从 `ROS1 Noetic + Gazebo Classic` 切到
`ROS2 + Gazebo Harmonic`。

原因不是新栈不好，而是当前平台的已验证能力面大量落在 Ubuntu 20.04、
ROS1 Noetic、Gazebo Classic、MARSIM、FAST_LIO、EGO-Planner 和 PX4
现有路径上。直接迁移会把已经跑通的无人机算法仿真平台重新变成大规模
 bring-up 工程，风险和收益不匹配。

正确做法是：

- 当前机器继续保留稳定的 Ubuntu 20.04 主线。
- ROS2 / Gazebo Harmonic 作为并行新后端路线推进。
- 新路线先通过最小 smoke，再通过严格 acceptance，最后才替换旧路线。

## 2. 当前稳定基线

当前平台的主线基线是：

- 系统：Ubuntu 20.04。
- 轻量飞控路径：`PX4 SIH`。
- 动力学路径：`PX4 + JSBSim`。
- 过渡 3D 路径：`PX4 + Gazebo Classic`。
- ROS1 感知/规划路径：`MARSIM`、`FAST_LIO + MARSIM`、`EGO-Planner`
  系列。
- 用户算法接入：`external_command` 和 `ros_command`。
- 验收体系：`live-smoke`、`platform-acceptance`、`planner-acceptance`
  以及若干可选项目专用 acceptance surface。

这条线的定位是：先保证当前机器上能跑、能看、能复现、能接自定义算法。

## 3. 已确认的长期风险

这些风险是真实存在的，但不等于必须今天迁移。

- `ROS1 Noetic` 已在 2025-05-31 EOL。EOL 后不再有官方新功能、安全更新、
  bug fix 或二进制更新。
- `Gazebo Classic / Gazebo 11` 已在 2025-01 EOL。
- `Gazebo Harmonic` 官方二进制支持集中在 Ubuntu 22.04 和 Ubuntu 24.04，
  不是当前 Ubuntu 20.04 的自然升级项。
- 长期继续依赖 ROS1/Gazebo Classic 会增加安全、维护和新硬件/新算法生态
  对接成本。

官方参考：

- ROS 官方 Noetic EOL 说明：<https://www.ros.org/blog/noetic-eol/>
- ROS Index Noetic EOL 说明：<https://index.ros.org/r/ros/>
- Gazebo Classic EOL 说明：<https://classic.gazebosim.org/distributions/gazebo/releases/>
- Gazebo Harmonic Ubuntu 安装说明：<https://gazebosim.org/docs/harmonic/install_ubuntu/>
- Gazebo / ROS 兼容组合说明：<https://gazebosim.org/docs/harmonic/ros_installation/>

## 4. 为什么现在不直接迁移

现在直接迁移会带来几个明确问题：

- 当前 Ubuntu 20.04 不是 Gazebo Harmonic 的主推荐二进制平台。
- ROS1 实验室算法栈很多不是简单替换 `roslaunch` 就能变成 ROS2。
- `MARSIM`、`FAST_LIO`、`EGO-Planner` 这些路径已经形成可复现 evidence，
  迁移后需要重新建立 topic、frame、消息、时间同步和评估合同。
- 当前平台目标是轻量、能用、可接入，而不是为了追新栈牺牲稳定性。
- 一次性替换会污染现有 acceptance 语义，破坏已经冻结的回归基线。

所以，迁移应该是并行后端，而不是原地覆盖。

## 5. 目标技术方向

长期目标可以这样定义：

- 操作系统测试线：Ubuntu 22.04 或 Ubuntu 24.04。
- ROS2 线：
  - Ubuntu 22.04 优先考虑 ROS2 Humble。
  - Ubuntu 24.04 优先考虑 ROS2 Jazzy。
- Gazebo 线：Gazebo Harmonic。
- PX4 线：PX4 现代 Gazebo / `gz sim` 路径。
- 平台策略：
  - 保留 `PX4 SIH` 作为轻量默认 smoke。
  - 把 ROS2/Gazebo Harmonic 做成新增 backend，不替换现有 backend。
  - 先完成 adapter 合同，再接复杂算法。

## 6. 分阶段迁移计划

### Phase 0：冻结当前合同

目标：确保旧线在迁移期间不会被误伤。

要做：

- 保持 `platform-acceptance` 和 `planner-acceptance` 现有语义不变。
- 保持 `PX4 SIH` 作为默认轻量路径。
- 保持 `external_command` / `ros_command` 的用户算法接入合同稳定。
- 不在旧线里强塞 ROS2 依赖。

通过标准：

- `python3 -m sim_plane live-smoke --profile fast` 通过。
- `python3 -m sim_plane platform-acceptance --latest --artifact-root runs` 通过。
- artifact hygiene 无污染。

### Phase 1：建立并行系统环境

目标：在不破坏 Ubuntu 20.04 主线的前提下建立新栈试验环境。

推荐方式：

- 优先使用独立系统、双系统、单独磁盘、容器或 VM。
- 不建议在当前 20.04 主系统上混装会破坏 ROS1/Gazebo Classic 的包。
- 新环境工作区仍然按平台约定放到 `/home/coco/sim_plane_ws` 下的明确子目录，
  或在新系统中复用同样的目录约定。

通过标准：

- 新环境能独立启动 `gz sim`。
- 新环境能构建或运行 PX4 对应的现代 Gazebo SITL 路径。
- 旧环境的 `live-smoke` 和 acceptance 不受影响。

### Phase 2：新增 Gazebo Harmonic backend

目标：只新增 backend，不改旧 backend。

要做：

- 新增类似 `px4_gazebo_harmonic` 的 backend。
- 先只做 quadrotor headless smoke。
- 产物仍写入统一 `runs/<artifact>/`。
- 指标仍使用现有 runner 可以理解的最小字段：
  - startup success
  - telemetry flow
  - arm/takeoff
  - mode / state
  - event severity

通过标准：

- 新 backend 能被 `python3 -m sim_plane list-backends` 识别。
- 一条 headless quadrotor scenario fresh PASS。
- 不改变 `px4_gazebo_classic` 旧路径结果。

### Phase 3：ROS2 adapter 最小闭环

目标：让 ROS2 算法像现在的 ROS1 算法一样容易挂进来。

要做：

- 新增 ROS2 版用户算法入口，例如 `ros2_command`。
- 提供稳定环境变量：
  - artifact 路径
  - ROS domain
  - topic contract
  - command topic / odom topic / cloud topic
- 先做最小示例节点，不急着接大型实验室算法。

通过标准：

- 示例 ROS2 算法能被平台启动和关闭。
- 示例节点能订阅状态并发布控制/目标输出。
- 结果能并入统一 artifact。

### Phase 4：迁移一个真实算法面

目标：只迁移一个高价值算法面，不同时迁移全部。

推荐顺序：

1. 先迁移控制/任务类算法，因为依赖更少。
2. 再迁移轻量 ROS2 planner 示例。
3. 最后迁移复杂感知/建图/规划组合。

不建议第一步就迁移：

- `MARSIM + FAST_LIO + EGO-Planner` 全链。
- 多机 swarm。
- 含大量自定义 message 和 frame 假设的历史 ROS1 栈。

通过标准：

- 新算法面有独立 scenario。
- 有独立 acceptance surface。
- 有 latest-vs-reference 或最小可重复 smoke。
- 旧 ROS1 对应能力仍可回退。

### Phase 5：基线切换

目标：只有新线稳定后，才把默认推荐从旧线切过去。

切换条件：

- 新栈至少覆盖：
  - 轻量 smoke
  - PX4 quadrotor headless
  - 一条 GUI/3D 可视化路径
  - 一条用户算法接入路径
  - 一条 planner/perception 路径
- 新栈连续多轮 fresh run 稳定。
- 新栈 artifact 与 dashboard/replay/acceptance 全部接通。
- 旧线保留为 fallback，直到新线覆盖所有常用能力面。

## 7. Go / No-Go 判断

可以开始新栈迁移的条件：

- 有 Ubuntu 22.04 或 24.04 测试环境。
- 当前 20.04 主线 git clean。
- 当前 `live-smoke` 和 `platform-acceptance --latest` 是绿的。
- 已明确本轮只新增一个 backend 或一个 adapter。

不应该开始迁移的情况：

- 当前主线 acceptance 还红。
- 当前机器需要继续高频使用 ROS1/MARSIM/EGO-Planner。
- 没有隔离环境，只能在 20.04 主系统上混装。
- 目标是“一次性全量替换”。

## 8. 回滚策略

迁移期间必须保留回滚能力：

- 旧 scenario 不改名、不复用新语义。
- 新 backend 使用新名字，不覆盖 `px4_gazebo_classic`。
- 新 adapter 使用新名字，不覆盖 `ros_command`。
- 新 acceptance report 使用新 report root。
- 如果新栈不稳定，直接停止使用新 scenario，不影响旧线。

## 9. 当前推荐动作

短期：

- 继续使用当前 Ubuntu 20.04 主线。
- 使用 `PX4 SIH` 做轻量控制迭代。
- 使用 `MARSIM` / `FAST_LIO + MARSIM` 做 ROS1 感知规划验证。
- 使用 `live-smoke` 做重启后真实启动检查。
- 使用 dashboard 做 artifact 浏览和对比。

中期：

- 准备一个 Ubuntu 22.04 或 24.04 隔离测试环境。
- 在新环境里只验证 PX4 + Gazebo Harmonic 最小 quadrotor 场景。
- 不碰旧 acceptance。

长期：

- 新增 ROS2/Gazebo Harmonic 并行 backend。
- 新增 ROS2 用户算法接入 adapter。
- 用独立 acceptance surface 逐步替换旧线能力。

## 10. 对当前平台的影响

这份路线图本身不改变任何运行语义。

它只锁定一条工程原则：

> 当前稳定平台继续服务你的算法仿真；ROS2/Gazebo Harmonic 是下一代并行路线，
> 不能用未验证的新路线覆盖已验证的旧路线。
