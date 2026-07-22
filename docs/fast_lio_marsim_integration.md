# FAST_LIO + MARSIM Integration

## Goal

Expose the landed `FAST_LIO + MARSIM` estimation stack through the shared
`sim_plane` runner without making ROS mandatory for the default core backends.

## Chosen Workspaces

- `MARSIM` upstream checkout:
  `/home/coco/sim_plane_ws/src/labs/HKU_MARS_Lab/MARSIM`
- `FAST_LIO` upstream checkout:
  `/home/coco/sim_plane_ws/src/labs/HKU_MARS_Lab/FAST_LIO`
- `livox_ros_driver` managed dependency:
  `/home/coco/sim_plane_ws/src/deps/Livox_SDK/livox_ros_driver`
- dedicated `MARSIM` workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_marsim`
- dedicated `FAST_LIO` workspace:
  `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`

The shared runner does not merge those workspaces into one catkin overlay.
`MARSIM` and `FAST_LIO` are launched with separate sourced environments so the
second workspace does not hide the first workspace's package visibility.

## Runtime Surface

Shared-runner scenarios:

```bash
python3 -m sim_plane run scenarios/fast_lio_marsim.json
python3 -m sim_plane run scenarios/fast_lio_marsim_visual.json --visualize --no-hold-open
```

Convenience scripts:

```bash
./scripts/run_fast_lio_marsim.sh
./scripts/run_fast_lio_marsim_visual.sh --no-hold-open
```

Both shapes write run artifacts under:

- `runs/`

Derived planner-on-estimator surfaces:

```bash
python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim.json --no-hold-open
python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim_visual.json --visualize --no-hold-open
python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim.json --no-hold-open
python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim_visual.json --visualize --no-hold-open
```

## Repo-Local Safety Wrapper

The runner uses the repo-local launch file:

- `sim_plane/ros/fast_lio_marsim.launch`

Why it exists:

- upstream `FAST_LIO/config/marsim.yaml` enables `pcd_save/pcd_save_en: true`
- upstream shutdown then writes `FAST_LIO/PCD/scans.pcd`
- that behavior is outside the platform artifact discipline and can grow disk
  usage quickly

The wrapper keeps the upstream mapping launch shape but forces:

- `pcd_save/pcd_save_en=false`
- `pcd_save/interval=-1`

The platform therefore keeps the estimator run bounded to the run artifact
instead of polluting the upstream checkout root.

## Initial Verified Evidence

On `2026-04-28` local time, the following were validated on this host:

- `./scripts/build_fast_lio_ws.sh` completed successfully in
  `/home/coco/sim_plane_ws/workspaces/ros1_fast_lio`.
- `python3 -m sim_plane run scenarios/fast_lio_marsim.json` passed at
  `runs/fast_lio_marsim_20260427_173428` with
  `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and
  `pcd_save_disabled=true`.
- `python3 -m sim_plane run scenarios/fast_lio_marsim_visual.json --visualize --no-hold-open`
  passed at `runs/fast_lio_marsim_visual_20260427_173600` with
  `telemetry_count=98`, `odometry_seen=true`, `pointcloud_seen=true`, and
  `launch_rviz=true`.
- the visual run kept the dashboard surface available at
  `http://127.0.0.1:8765` during execution.
- neither artifact stream contains `current scan saved to /PCD/`, so the
  wrapper blocked the default upstream PCD dump during both shared-runner runs.
- `python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim.json --no-hold-open`
  passed at `runs/ego_planner_fast_lio_marsim_20260427_194838` with
  `goal_reached=true` and `min_goal_distance_m=0.042`.
- `python3 -m sim_plane run scenarios/ego_planner_fast_lio_marsim_visual.json --visualize --no-hold-open`
  passed at `runs/ego_planner_fast_lio_marsim_visual_20260427_194947` with
  `goal_reached=true`, `launch_rviz=true`, and an info-only event stream.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim.json --no-hold-open`
  passed at `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903` with
  `goal_reached=true` and `min_goal_distance_m=0.03`.
- `python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim_visual.json --visualize --no-hold-open`
  passed at `runs/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020`
  with `goal_reached=true`, `launch_rviz=true`, and an info-only event stream.

## Planner-On-Estimator Adapter

Both planner-on-estimator surfaces reuse the repo-local adapter:

- `scripts/ros_align_odometry.py`

It:

- subscribes to FAST_LIO `/Odometry`,
- subscribes to `MARSIM` `/quad_0/lidar_slam/odom`,
- locks the first relative transform,
- republishes `/sim_plane/fast_lio_world_odom`,
- and keeps the planner contract in the same world frame as the scene cloud and
  manual goal surface.

## Residual Boundary

- The shared runner now validates the estimator contract through `/Odometry`
  plus `/quad0_pcl_render_node/sensor_cloud`.
- The raw estimator backend is still useful on its own as a lighter diagnostic
  surface even though planner-on-estimator closed loops are now also validated.
- Standalone `MARSIM` CPU and GPU local-sensing paths are validated in the
  platform. The `FAST_LIO + MARSIM` estimator combination documented here is
  still validated on the CPU `MARSIM` path only; it should not be advertised as
  a validated GPU estimator surface until that combination has its own artifact.
- Raw upstream stderr still prints harmless `FAST_LIO` warning text such as
  `No point, skip this scan!` at startup and `catch sig 2` on normal SIGINT,
  but the platform event stream now classifies them as informational noise.
