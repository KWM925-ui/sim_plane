# sim_plane Agent Guide

## Scope

- This repository is for a lightweight but capable UAV algorithm simulation platform.
- Stable upstream contracts live in official PX4, Gazebo, MAVSDK, and QGroundControl documentation.
- Local policy in this repo covers backend selection, scenario schema, evaluation rules, and adapter interfaces.

## Must Read Before Changing Code

- [README.md](/home/coco/sim_plane/README.md)
- [docs/platform_blueprint.md](/home/coco/sim_plane/docs/platform_blueprint.md)
- [docs/upstream_reference_matrix.md](/home/coco/sim_plane/docs/upstream_reference_matrix.md)
- [docs/ego_planner_swarm_integration.md](/home/coco/sim_plane/docs/ego_planner_swarm_integration.md) for the first ROS lab stack path
- [docs/ego_planner_integration.md](/home/coco/sim_plane/docs/ego_planner_integration.md) for the legacy planner baseline path
- [docs/fast_lio_marsim_integration.md](/home/coco/sim_plane/docs/fast_lio_marsim_integration.md) for the estimator stack path
- [.agent/PLANS.md](/home/coco/sim_plane/.agent/PLANS.md) for multi-round work

## Execution Rules

- Default to the light path first: `PX4 SIH` or `JSBSim` before heavier 3D stacks.
- Do not make ROS a mandatory runtime dependency in the core platform unless a requirement clearly cannot be met without it.
- Treat Ubuntu 20.04 compatibility and modest host resource use as first-class constraints unless the user explicitly upgrades the baseline.
- Before adding a simulator, middleware layer, or UI dependency, record why the current lighter path is insufficient.
- All third-party workspaces and cloned upstream repositories must stay under `/home/coco/sim_plane_ws` unless the repo explicitly changes that root later.
- For simulator-facing changes, report: host OS, backend, vehicle type, headless vs GUI mode, startup command, and pass/fail outcome.
- Use fresh local evidence for runtime claims and official upstream docs for support or version claims.

## Long-Running Work

- Update `.agent/PLANS.md` whenever the task spans multiple rounds, introduces a validation matrix, or splits into multiple backend options.
- Use the `execution-supervisor` workflow when work becomes debugging-heavy, validation-expensive, or vulnerable to branch drift.
- Keep facts, hypotheses, blockers, and next actions separate in project control docs.

## Do Not Put Here

- Run-by-run validation history
- Generated logs or large architecture dumps
- Temporary choices that belong in plans or decision notes
