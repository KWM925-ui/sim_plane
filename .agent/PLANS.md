# Execution Plan

## Platform Mainline Frontier (2026-06-06)

### Locked Facts

- `sim_plane` is a generic UAV algorithm simulation and evaluation platform.
- Project-specific branches from other repositories are no longer part of this repository's active platform surface.
- External business-project workspaces are out of scope for this repository unless the user explicitly reopens a separate project.
- Third-party simulator and algorithm workspaces remain under `/home/coco/sim_plane_ws`.
- The active platform surfaces are generic backends, generic algorithm adapters, artifacts, KPI/suite/fuzz/autotest, acceptance, and dashboard/console.

### Current Understanding / Validation Contract

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
- Rebuild the platform explanation from current code and reports, not from previous chat memory.
- Prefer light validation first, then latest-report acceptance, then only heavier backend runs if evidence says they are necessary.
- Treat frontend coverage as an accuracy surface: buttons must map to real CLI commands and hidden commands must state a concrete reason.

### Next Actions

1. Commit or otherwise resolve the current tracked dirty files before claiming a fully clean repository state.
2. Keep using `platform-health`, `live-smoke --profile fast`, `autotest-pack --profile fast`, and `platform-acceptance --latest` as the light-to-medium validation ladder.
3. For the next functional optimization round, prefer guided user workflows over adding another heavy backend:
   - dashboard-guided scenario generation,
   - dashboard-guided algorithm ingress health check,
   - baseline selection/run from the console,
   - artifact-detail flight-log analysis.
4. For the next deeper technical validation round, continue from the landed PX4 `.ulg` collection surface by tightening artifact-local ULog selection and flight-log KPI replay alignment.

### Forbidden Actions

- Do not modify external business-project workspaces.
- Do not reintroduce project-specific platform entrypoints.
- Do not remove generic ROS lab backends just because they use ROS1; those are platform simulation capabilities, not project-specific user code.
- Do not change acceptance thresholds except to remove rows that referenced deleted project-specific surfaces.

### Latest Round Result

- Fresh validation on `2026-06-06` passed under the light-to-medium platform surface:
  - `python3 -m unittest` -> `154` tests OK.
  - `python3 -m sim_plane doctor` -> `12` ready backends and `4` ready adapters.
  - frontend console coverage -> `23` CLI commands = `16` surfaced + `7` intentionally hidden.
  - fresh demo run -> `runs/basic_takeoff_20260606_092943_510944`.
  - live smoke fast -> `runs/live_smoke/live_smoke_fast_20260606_092948_597930/report.json`.
  - demo degradation suite -> `runs/suites/demo_degradation_suite_20260606_092944_030682/report.json`.
  - seeded scenario fuzz -> `runs/scenario_fuzz/demo_seeded_fuzz_7_20260606_092944_053485/report.json`.
  - autotest fast -> `runs/autotest/sim_plane_autotest_fast_20260606_093026_205815/report.json`, `8/8` steps passed.
  - platform latest acceptance -> `runs/platform_acceptance/platform_acceptance_baseline_latest_20260606_093021_620514/report.json`, `21/21` rows passed.
  - external command ingress check -> `runs/px4_sih_quadx_external_command_template_20260606_094241_725253`, all ingress checks passed.
  - artifact hygiene -> clean.
  - platform health -> `warning` only because git has four tracked dirty files.

### Corrective Understanding Round Result

- The previous closeout did not fully satisfy the user's original request because it was too compressed around health status.
- A corrective round re-audited the system with four read-only subagents:
  - architecture and usage model;
  - tests and acceptance surfaces;
  - frontend/CLI alignment;
  - next optimization priorities.
- The platform should be explained as an evidence pipeline:
  - `CLI -> scenario -> runner -> backend/adapter -> artifact -> KPI -> suite/fuzz/acceptance -> dashboard/console`.
- The current frontend is accurate but preset-oriented:
  - `23` CLI subcommands total;
  - `16` fixed frontend console commands;
  - `7` intentionally hidden commands that need user/context parameters.
- Additional fresh validation passed:
  - default live smoke with fresh PX4 SIH path -> `runs/live_smoke/live_smoke_default_20260606_100359_889875/report.json`, `2/2` rows passed.
  - sequential `autotest-pack --profile fast` -> `runs/autotest/sim_plane_autotest_fast_20260606_100230_918824/report.json`, `8/8` steps passed.
- Process risk discovered:
  - Running `artifact-hygiene`, `autotest-pack`, or `platform-health` in parallel with a command that is still writing under `runs/` can produce a real but temporary incomplete-artifact failure.

### Optimization Direction From System Analysis

1. PX4 `.ulg` auto-collection and artifact indexing.
2. PX4-native failure injection expansion, one officially supported failure surface at a time.
3. Dashboard/report consolidation around artifact details, health, suite/fuzz ranking, and flight-log replay.
4. Guided frontend workflows for `run-baseline`, `generate-scenario`, `check-algorithm-ingress`, and `flight-log-analyze`.
5. Baseline comparison hardening after the above evidence flows are less manual.

### Productized Console Round Result

- External reference direction:
  - PX4 MAVSDK integration testing, PX4 failure injection, PX4 ULog, ArduPilot AutoTest, safe-control-gym, and gym-pybullet-drones all reinforce the same platform shape: named repeatable tasks, explicit evidence/logs, and metric/report surfaces.
  - The immediate optimization target is user-facing workflow clarity, not another simulator backend or acceptance-threshold changes.
- Implemented dashboard console taxonomy:
  - `1 基础确认`
  - `2 Fresh 运行`
  - `3 KPI 评测`
  - `4 回归验收`
  - `5 算法接入`
- Implemented evidence taxonomy:
  - `只读检查`
  - `Fresh 运行证据`
  - `历史证据回归`
  - `混合一键复验`
- Every surfaced console command now exposes:
  - exact CLI command;
  - workflow and workflow goal;
  - evidence type and evidence freshness;
  - output path;
  - concurrency policy.
- Surfaced two previously hidden but valuable guided actions:
  - `run-baseline pid_position_demo`
  - `check-algorithm-ingress --scenario scenarios/px4_sih_quadx_external_command_template.json`
- Current console coverage:
  - `23` CLI subcommands total;
  - `18` frontend surfaced commands;
  - `5` intentionally hidden commands: `flight-log-analyze`, `generate-scenario`, `planner-acceptance`, `serve`, `show-scenario`.
- Validation:
  - `python3 -m unittest tests.test_console_commands tests.test_dashboard_replay` -> `11` tests OK.
  - `python3 -m unittest` -> `157` tests OK.
  - `git diff --check` -> passed.
  - `python3 -m py_compile sim_plane/console_commands.py` -> passed.
- Locked lesson:
  - Do not run `platform-health`, `artifact-hygiene`, `platform-acceptance`, or `autotest-pack` while another long task is actively writing under `runs/`.

### PX4 ULog Evidence Closure Round Result

- Implemented PX4-family artifact-local `.ulg` collection for:
  - `px4_sih`
  - `px4_jsbsim`
  - `px4_gazebo_classic`
- Added `sim_plane/px4_ulog.py` as the shared ULog discovery, before/after snapshot, collection, manifest update, metrics, note, and dashboard-summary helper.
- Collection is deliberately non-gating:
  - it writes `px4_ulog/index.json` with `collected`, `missing`, `disabled`, or `failed`;
  - it updates `manifest.json` under `files.px4_ulog_index` and `manifest.px4_ulog`;
  - it adds result metrics such as `px4_ulog_collected`, `px4_ulog_count`, and `px4_ulog_total_bytes` when a backend result exists;
  - collection failure does not change the simulation verdict.
- Dashboard artifact summaries now include optional `px4_ulog` status while keeping older artifacts without `px4_ulog/index.json` compatible.
- Documentation and `platform-health` objective boundaries now reflect the new reality:
  - PX4-family backends attempt artifact-local `.ulg` collection by default;
  - actual availability is determined by each artifact's `px4_ulog/index.json`;
  - artifact replay and `.ulg` replay remain distinct analysis inputs.
- Fresh validation completed:
  - `python3 -m unittest tests.test_px4_ulog tests.test_px4_sih_backend tests.test_px4_jsbsim_backend tests.test_px4_gazebo_classic_backend tests.test_dashboard_replay tests.test_platform_health` -> `43` tests OK.
  - `python3 -m py_compile sim_plane/px4_ulog.py sim_plane/backends/px4_sih.py sim_plane/backends/px4_jsbsim.py sim_plane/backends/px4_gazebo_classic.py sim_plane/web.py sim_plane/platform_health.py` -> passed.
  - `python3 -m unittest` -> `163` tests OK.
  - `git diff --check` -> passed.
  - Fresh `python3 -m sim_plane run scenarios/px4_sih_quadx_headless.json --artifact-root runs --no-hold-open` passed at `runs/px4_sih_quadx_headless_20260606_124503_774339`.
  - That artifact collected `runs/px4_sih_quadx_headless_20260606_124503_774339/px4_ulog/12_45_07.ulg`, wrote `px4_ulog/index.json`, and recorded `px4_ulog_collected=true`, `px4_ulog_count=1`, `px4_ulog_total_bytes=7517823`.
  - `python3 -m sim_plane flight-log-analyze runs/px4_sih_quadx_headless_20260606_124503_774339/px4_ulog/12_45_07.ulg --report-root runs/flight_log_analysis --json` passed and wrote `runs/flight_log_analysis/ulog_12_45_07_20260606_124655_228127/report.json`.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json` passed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260606_124727_417603/report.json`, `21/21` rows passed.
  - `python3 -m sim_plane platform-health --artifact-root runs --json` wrote `runs/platform_health/sim_plane_platform_health_20260606_124840_286175/report.json`; status is `warning` only because git is dirty, with `issues=[]`.
- Current next technical frontier:
  - use artifact-local `px4_ulog/index.json` to make `flight-log-analyze` easier to trigger from artifact context;
  - map PX4 numeric nav/arming states into clearer labels;
  - keep PX4-native failure expansion separate and evidence-gated.

### Git Closure Result

- Implementation commit pushed to `origin/main`:
  - `124c00e Add PX4 ULog evidence and console metadata`
- Post-push health check:
  - `python3 -m sim_plane platform-health --artifact-root runs --json`
  - report: `runs/platform_health/sim_plane_platform_health_20260606_135621_978938/report.json`
  - status: `passed`
  - components: `8/8`
  - warnings: `0`
  - issues: `0`
- Post-push repository state:
  - local `HEAD` and `origin/main` matched at `124c00e` before this ledger-only closure update;
  - `git status --short` was clean;
  - `runs/` remained ignored and was not committed.
- Continuation boundary:
  - next work should open one bounded platform frontier from current evidence;
  - do not reopen external project branches;
  - do not change acceptance semantics without fresh evidence and an explicit gate.
