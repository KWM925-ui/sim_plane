# Execution Plan

## Comprehensive Platform Audit Frontier (2026-06-07)

### Locked Facts

- Scope is only `/home/coco/sim_plane`.
- Current repository starts clean at `main`/`origin/main` before this audit frontier update.
- This is a generic UAV simulation/evaluation platform audit, not an external business-project branch.
- Valid `runs/` evidence is not cleanup trash.

### Current Frontier

- Run the broadest practical sequential audit of the current platform:
  - static repository and JSON checks;
  - Python compile and unit tests;
  - CLI/frontend/backend/adapter/scenario alignment checks;
  - fresh lightweight runtime evidence;
  - suite, fuzz, quadrotor exam, custom-algorithm ingress, acceptance, flight-log replay, artifact hygiene, and platform health;
  - bounded heavier probes only when prerequisites are present.
- Fix only current-repo defects backed by fresh evidence.

### Forbidden Actions

- Do not modify external workspaces.
- Do not change acceptance thresholds or semantics to force a pass.
- Do not add a new simulator backend.
- Do not delete valid historical artifacts under `runs/`.
- Do not run artifact inspectors while another command is actively writing under `runs/`.

### Promotion Gate

- Full audit commands are recorded with PASS/FAIL/SKIP.
- All discovered source defects are fixed or explicitly left blocked with artifact-backed evidence.
- Final validation includes full unit tests, fresh runtime evidence, acceptance/hygiene/health, and explicit git status.

### Result Snapshot

- Fixed evidence-backed local defects without changing acceptance semantics:
  - dashboard local HTTP tests now bypass host proxy settings for `127.0.0.1`;
  - `list-adapters` output now matches `doctor` ready/note classification;
  - MAVSDK action timeout errors are labeled;
  - Gazebo Classic MAVSDK action land timeout was raised to `36.0s` based on fresh land/disarm timing evidence;
  - MAVSDK adapter shutdown is best-effort and guarded against a confirmed `aiogrpc` destructor noise;
  - algorithm adapter reports are type-checked so non-dict reports fail clearly;
  - the MAVSDK action adapter tuple-return regression was fixed.
- Fresh PASS evidence:
  - `171` unit tests OK;
  - JSON syntax check OK for `48` config/scenario files;
  - compileall OK;
  - `git diff --check` OK;
  - `basic_takeoff`: `runs/basic_takeoff_20260607_133513_329398`;
  - `live-smoke fast`: `runs/live_smoke/live_smoke_fast_20260607_133530_395961/report.json`;
  - `live-smoke default`: `runs/live_smoke/live_smoke_default_20260607_133621_223841/report.json`;
  - `scenario-fuzz seed 17`: `runs/scenario_fuzz/demo_seeded_fuzz_17_20260607_134044_504532/report.json`;
  - `run-baseline pid_position_demo`: `runs/basic_takeoff_20260607_134121_835980`;
  - `check-algorithm-ingress`: `runs/px4_sih_quadx_external_command_template_20260607_134155_460434`;
  - `px4_gazebo_classic_iris_mavsdk_action`: `runs/px4_gazebo_classic_iris_mavsdk_action_20260607_135304_884798`;
  - `px4_sih_quadx_mavsdk_failure_motor`: `runs/px4_sih_quadx_mavsdk_failure_motor_20260607_134908_368063`;
  - `px4_jsbsim_quadx_mavsdk_action`: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_135738_918250`;
  - `px4-failure-acceptance --latest`: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_141916_641710/report.json`;
  - `quadrotor-exam-acceptance --latest`: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_141916_804154/report.json`;
  - `flight-log-analyze`: `runs/flight_log_analysis/artifact_px4_jsbsim_quadx_mavsdk_action_20260607_135738_918250_20260607_142004_531245/report.json`;
  - `artifact-hygiene`: clean;
  - `manual-probe-hygiene`: clean.
- Remaining FAIL:
  - `planner-acceptance --latest`: `runs/acceptance/planner_acceptance_baseline_latest_20260607_141916_429525/report.json`;
  - only failing surface: `ego_planner_swarm_fast_lio_marsim` headless;
  - repeated fresh runs pass behavior but exceed the frozen latest-vs-reference `min_goal_distance_m` regression budget:
    - reference `0.030m`;
    - fresh repeated values `0.062m`, `0.071m`, `0.065m`, `0.066m`;
  - logs contain EGO-Planner-Swarm solver warnings `Solver error. Return = -1008 ... Skip this planning.`;
  - `platform-acceptance`, `autotest-pack`, and `platform-health` inherit this same planner acceptance failure.

### Next Decision

- Do not weaken acceptance in this frontier.
- The next round must explicitly decide whether to:
  - fix or stabilize `ego_planner_swarm_fast_lio_marsim` runtime/planner behavior; or
  - open a separate acceptance-contract review for the planner latest-vs-reference budget.

### Follow-up Resolution

- The `ego_planner_swarm_fast_lio_marsim` blocker was fixed by tightening the runtime goal condition in the scenario, not by changing acceptance semantics.
- Updated file:
  - `scenarios/ego_planner_swarm_fast_lio_marsim.json`
  - added `goal_reach_tolerance_m=0.04`;
  - added `goal_settle_hold_s=0.0`.
- Rationale:
  - backend default `goal_reach_tolerance_m=0.6` was coarser than planner acceptance's `0.1m` absolute threshold and `0.01m` regression budget;
  - this caused early success/early sampling stop before the planner had to meet the finer acceptance target.
- Fresh proof:
  - `python3 -m sim_plane run scenarios/ego_planner_swarm_fast_lio_marsim.json --artifact-root runs --no-hold-open`
  - artifact: `runs/ego_planner_swarm_fast_lio_marsim_20260607_150339_456246`
  - result: passed;
  - `min_goal_distance_m=0.016`;
  - `goal_reached=true`;
  - no warning event levels.
- Recovered acceptance:
  - `planner-acceptance --latest`: `runs/acceptance/planner_acceptance_baseline_latest_20260607_150421_976435/report.json`, `4/4` passed;
  - `platform-acceptance --latest`: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_150422_832468/report.json`, `21/21` passed;
  - `autotest-pack --profile fast`: `runs/autotest/sim_plane_autotest_fast_20260607_150428_694335/report.json`, `8/8` passed;
  - `platform-health`: `runs/platform_health/sim_plane_platform_health_20260607_150430_059298/report.json`, command passed, `issues=[]`, warning only from dirty git.
- Final checks:
  - JSON syntax: `48` files OK;
  - compileall: passed;
  - unit tests: `171` OK;
  - `git diff --check`: passed;
  - `artifact-hygiene`: clean;
  - repo-local Python cache residue removed.

### Current State

- Functional audit status: green under current evidence.
- Repository state: intentionally dirty until the audit fixes are reviewed/committed.
- Remaining non-functional warning: dirty git only.

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

### Hygiene Cleanup Frontier

- Scope:
  - only `/home/coco/sim_plane`;
  - no external workspace cleanup;
  - no deletion under `runs/` unless `artifact-hygiene` marks an entry safe to prune.
- Fresh scan result:
  - `git status --short` was clean before cleanup;
  - no untracked non-ignored files were present;
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json` reported `status=clean`, `stale_incomplete_directory_count=0`, `empty_directory_count=0`, and `attention_count=0`;
  - ignored local dirt was limited to `sim_plane.egg-info/` and Python `__pycache__`/`.pyc` files in `sim_plane/`, `sim_plane/backends/`, `sim_plane/adapters/`, and `tests/`.
- Allowed cleanup:
  - remove `sim_plane.egg-info/`;
  - remove repo-local `__pycache__` directories and `.pyc` files outside `runs/`.
- Forbidden cleanup:
  - do not delete valid `runs/` artifacts;
  - do not remove generic platform backends, adapters, scenarios, reports, or docs;
  - do not modify acceptance thresholds.

### Hygiene Cleanup Result

- Removed ignored local build/cache residue:
  - `sim_plane.egg-info/`
  - `sim_plane/__pycache__/`
  - `sim_plane/backends/__pycache__/`
  - `sim_plane/adapters/__pycache__/`
  - `tests/__pycache__/`
- Preserved:
  - all tracked source, docs, configs, scenarios, and tests;
  - all valid `runs/` artifacts and reserved report roots.
- Validation after cleanup:
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest` -> `163` tests OK;
  - `git diff --check` -> passed;
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane platform-health --artifact-root runs --json` -> functional surfaces passed, with only the expected git dirty warning from this ledger update before commit.
