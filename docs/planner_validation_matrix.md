# Planner Validation Matrix

## Goal

Freeze the currently landed planner surfaces into one quick acceptance view so
later sessions do not need to rediscover which combinations are already proven.

The canonical machine-readable source for this matrix now lives at:

- [configs/planner_acceptance_matrix.json](../configs/planner_acceptance_matrix.json)

Validate the frozen reference artifacts with:

```bash
python3 -m sim_plane planner-acceptance
```

Validate the latest matching artifacts under `runs/` against the same gate
with:

```bash
python3 -m sim_plane planner-acceptance --latest --artifact-root runs
```

Each acceptance invocation now also writes a durable report pack under:

```text
runs/acceptance/
```

including stable snapshots at:

```text
runs/acceptance/latest_reference.json
runs/acceptance/latest_latest.json
runs/acceptance/latest_reference_delta.json
runs/acceptance/latest_latest_delta.json
runs/acceptance/history_reference.jsonl
runs/acceptance/history_latest.jsonl
```

The default retention rule keeps only the newest 5 timestamped report
directories per mode while preserving the stable snapshots and append-only
history files. Pass `--keep-last-reports 0` if pruning must be disabled for a
specific audit round.

The current acceptance gate requires:

- `status=passed`
- `goal_reached=true`
- `min_goal_distance_m <= 0.1`
- `min_goal_distance_m` must not regress by more than `0.01 m` against the
  frozen reference artifact for that row and mode
- the copied `baseline_min_goal_distance_m` value in the matrix must match the
  frozen reference artifact metric, or the gate fails loudly
- `launch_rviz` matching the headless or visual mode
- `cloud_only=true`
- an info-only shared event surface

## Current Matrix

| Backend | Surface | Odom source | Obstacle source | Tracked headless baseline | Tracked visual baseline | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `ego_planner_marsim` | legacy planner on scene | `/quad_0/lidar_slam/odom` | `/quad0_pcl_render_node/cloud` | `baselines/artifacts/ego_planner_marsim_20260427_185547` | `baselines/artifacts/ego_planner_marsim_visual_20260427_185758` | passed |
| `ego_planner_swarm_marsim` | swarm planner on scene | `/quad_0/lidar_slam/odom` | `/quad0_pcl_render_node/cloud` | `baselines/artifacts/ego_planner_swarm_marsim_20260427_191923` | `baselines/artifacts/ego_planner_swarm_marsim_visual_20260427_192755` | passed |
| `ego_planner_fast_lio_marsim` | legacy planner on estimator | `/sim_plane/fast_lio_world_odom` | `/quad0_pcl_render_node/cloud` | `baselines/artifacts/ego_planner_fast_lio_marsim_20260607_221938_879736` | `baselines/artifacts/ego_planner_fast_lio_marsim_visual_20260427_194947` | passed |
| `ego_planner_swarm_fast_lio_marsim` | swarm planner on estimator | `/sim_plane/fast_lio_world_odom` | `/quad0_pcl_render_node/cloud` | `baselines/artifacts/ego_planner_swarm_fast_lio_marsim_20260607_222057_101517` | `baselines/artifacts/ego_planner_swarm_fast_lio_marsim_visual_20260427_200020` | passed |

## Key Metrics

| Backend | Headless goal reached | Headless min goal distance m | Visual goal reached | Visual min goal distance m | Event surface |
| --- | --- | --- | --- | --- | --- |
| `ego_planner_marsim` | `true` | `0.064` | `true` | `0.066` | info-only |
| `ego_planner_swarm_marsim` | `true` | `0.011` | `true` | `0.005` | info-only |
| `ego_planner_fast_lio_marsim` | `true` | `0.051` | `true` | `0.052` | info-only |
| `ego_planner_swarm_fast_lio_marsim` | `true` | `0.019` | `true` | `0.027` | info-only |

## Shared Constraints

- All four validated planner surfaces are intentionally cloud-only.
- None of the validated wrappers should reopen the retired dual-input
  `depth + cloud` branch without fresh contradictory evidence.
- The two planner-on-estimator surfaces both depend on the repo-local aligned
  odometry adapter:
  `scripts/ros_align_odometry.py`
- The aligned adapter anchors FAST_LIO `/Odometry` against the first
  `MARSIM` `/quad_0/lidar_slam/odom` sample and republishes
  `/sim_plane/fast_lio_world_odom`.

## Current Acceptance Boundary

- The platform now has four artifact-backed planner surfaces: two scene-backed
  and two estimator-backed.
- All four have both headless and RViz-assisted visual evidence.
- Shared event streams are clean for all four validated surfaces.
- The default comparison surface is now executable through
  `python3 -m sim_plane planner-acceptance`, not just the static markdown table.
- That executable gate now enforces both an absolute `0.1 m` goal-distance cap
  and a tighter per-row regression budget of `0.01 m`, anchored to the frozen
  reference artifacts instead of only the copied matrix values.
- The acceptance result is no longer terminal-only; each invocation now leaves a
  timestamped report pack plus stable latest snapshots and history files under
  `runs/acceptance/`.
- The compact previous-vs-current compare surface now also lives at
  `latest_reference_delta.json` and `latest_latest_delta.json`, and the CLI
  prints the same delta summary directly.
- Residual raw stderr lines such as `FAST_LIO` startup warnings and RViz
  shutdown escalation remain artifact-only upstream noise.
