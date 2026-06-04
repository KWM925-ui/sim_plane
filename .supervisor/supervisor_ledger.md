# sim_plane Supervisor Ledger

## Task Identity

- Project: `sim_plane`
- Workspace: `/home/coco/sim_plane`
- Current scope: generic UAV simulation/evaluation platform only

## Locked Facts

- The active repository goal is the `sim_plane` platform, not any external business project.
- External business-project workspaces are out of scope unless explicitly reopened by the user.
- The repository should keep generic platform capabilities: runner, scenarios, artifacts, dashboard, KPI/suite/fuzz/autotest, platform acceptance, PX4 SIH/JSBSim/Gazebo Classic, MARSIM, FAST_LIO, EGO-Planner paths, and generic algorithm adapters.
- The repository should not keep project-specific adapters, launch files, acceptance commands, scenarios, sync scripts, or collaboration ledgers as active platform surfaces.
- Current cleanup is allowed to modify `/home/coco/sim_plane` only.

## Current Frontier

- Remove project-specific coupling from the platform mainline.
- Preserve generic custom-algorithm ingress:
  - `external_command` for PX4-side host processes.
  - `ros_command` for ROS planner/perception processes.
  - `mavsdk_action_takeoff` and `mavsdk_failure_injection` for MAVSDK/PX4 surfaces.
- Keep frontend/backend command descriptions aligned with the actual CLI.

## Forbidden Actions

- Do not modify external business-project workspaces.
- Do not reintroduce project-specific commands or scenarios.
- Do not delete generic lab-stack support just because it was used in previous project-specific experiments.
- Do not claim a platform surface is available unless it exists in the current CLI/backend/adapter registry.

## Required Closeout

- Residual scan for project-specific references outside ignored `runs/`.
- Focused unit tests for dashboard, artifact hygiene, platform health, live smoke, and generic adapter listings.
- CLI smoke from repository root and a non-repository directory.
- JSON syntax validation for remaining `configs/` and `scenarios/`.
- Report PASS/FAIL and any remaining objective risk.
