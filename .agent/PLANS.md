# Execution Plan

## Platform Mainline Frontier (2026-06-04)

### Locked Facts

- `sim_plane` is a generic UAV algorithm simulation and evaluation platform.
- Project-specific branches from other repositories are no longer part of this repository's active platform surface.
- External business-project workspaces are out of scope for this repository unless the user explicitly reopens a separate project.
- Third-party simulator and algorithm workspaces remain under `/home/coco/sim_plane_ws`.
- The active platform surfaces are generic backends, generic algorithm adapters, artifacts, KPI/suite/fuzz/autotest, acceptance, and dashboard/console.

### Current Cleanup Contract

- Keep generic backends:
  - `demo`
  - `px4_sih`
  - `px4_jsbsim`
  - `px4_gazebo_classic`
  - `marsim`
  - `fast_lio_marsim`
  - `ego_planner*`
- Keep generic adapters:
  - `external_command`
  - `mavsdk_action_takeoff`
  - `mavsdk_failure_injection`
  - `ros_command`
- Do not keep project-specific adapters, acceptance matrices, scenarios, sync scripts, managed launch files, or collaboration ledgers in the platform mainline.

### Next Actions

1. Finish removing stale project-specific references from docs, CLI, matrices, tests, and control files.
2. Verify that `python3 -m sim_plane list-adapters` and dashboard command coverage expose only generic platform commands.
3. Run focused platform tests plus basic CLI smoke commands.
4. If verification passes, commit and push the cleaned platform state.

### Forbidden Actions

- Do not modify external business-project workspaces.
- Do not reintroduce project-specific platform entrypoints.
- Do not remove generic ROS lab backends just because they use ROS1; those are platform simulation capabilities, not project-specific user code.
- Do not change acceptance thresholds except to remove rows that referenced deleted project-specific surfaces.
