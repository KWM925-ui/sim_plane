# Execution Plan

## Saturation Platform Audit Frontier (2026-06-08)

### Locked Facts

- Scope is only `/home/coco/sim_plane`.
- This repository is the generic UAV simulation/evaluation platform; external business-project workspaces are out of scope.
- The current `main` branch is synced with `origin/main` at the start of this frontier.
- Valid historical artifacts under `runs/` are evidence, not cleanup trash.
- Existing acceptance semantics must not be weakened to manufacture a pass.

### Current Frontier

- Run the broadest practical sequential audit of the current platform:
  - repository structure, ignored residue, and project-specific contamination scan;
  - scenario/config JSON validity and command/schema-style consistency;
  - Python syntax, import, and full unit tests;
  - CLI/backend/adapter/dashboard-console alignment;
  - fresh lightweight runtime evidence;
  - suite, fuzz, quadrotor exam, algorithm ingress, PX4 failure, flight-log, artifact hygiene, and platform-health surfaces;
  - bounded PX4/JSBSim/Gazebo/MARSIM/planner probes only when prerequisites are present and runs are not allowed to pollute each other.
- Fix only current-repo defects backed by fresh evidence.

### Forbidden Actions

- Do not modify external workspaces.
- Do not reintroduce project-specific commands, scenarios, or ledgers.
- Do not delete valid `runs/` evidence unless a hygiene command explicitly marks it safe.
- Do not run `artifact-hygiene`, `platform-health`, or `autotest-pack` while another command is actively writing under `runs/`.
- Do not change acceptance thresholds or semantics just to force green results.

### Promotion Gate

- Commands and artifacts are recorded with PASS/FAIL/SKIP.
- Any failure is classified to the earliest local cause before patching.
- All patches, if any, are minimal and project-local.
- Final validation includes static checks, full unit tests, fresh runtime evidence, acceptance/hygiene/health, and git status.

### Interruption Resume Closure - 2026-06-08

- Scope stayed limited to `/home/coco/sim_plane`; no external workspace was modified.
- Acceptance semantics were not weakened.
- Valid `runs/` artifacts were preserved.
- Fresh defects fixed in this frontier:
  - planner goal-reach logic now handles `goal_settle_hold_s=0.0` without requiring a second in-tolerance sample;
  - planner goal-reach comparison now uses the same 3-decimal precision as the artifact metric surface, avoiding verdict/report mismatch around strict centimeter gates;
  - ROS composite backends no longer silently inherit the default `localhost:11311` master after sourcing ROS setup, but still preserve an explicit non-default `ROS_MASTER_URI`;
  - strict planner acceptance scenarios now sample at `20 Hz` and use runtime goal gates no looser than their frozen latest-vs-reference acceptance surface.
- Fresh planner repeatability evidence:
  - `ego_planner_swarm_fast_lio_marsim` repeated `10/10` PASS after ROS master isolation;
  - refreshed strict planner artifacts passed for `ego_planner_marsim`, `ego_planner_swarm_marsim`, `ego_planner_fast_lio_marsim`, and `ego_planner_swarm_fast_lio_marsim`.
- Final fresh validation after interruption:
  - JSON syntax: `48` files OK.
  - Python source syntax: `92` files OK.
  - Full unit suite: `179` tests OK.
  - `list-backends`: `12/12` ready.
  - `list-adapters`: `4/4` ready.
  - `planner-acceptance --latest`: `runs/acceptance/planner_acceptance_baseline_latest_20260607_174542_496071/report.json`, `4/4` passed.
  - `platform-acceptance --latest`: latest report under `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_174339_295017/report.json`, passed.
  - `px4-failure-acceptance --latest`: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_174312_970303/report.json`, `1/1` passed.
  - `quadrotor-exam-acceptance --latest`: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_174323_166482/report.json`, `8/8` passed.
  - `autotest-pack --profile fast`: `runs/autotest/sim_plane_autotest_fast_20260607_174339_301360/report.json`, `8/8` passed.
  - `artifact-hygiene --artifact-root runs`: `clean`.
  - `manual-probe-hygiene --artifact-root runs`: `clean`.
  - `platform-health --artifact-root runs`: `runs/platform_health/sim_plane_platform_health_20260607_174408_466729/report.json`, status `warning` only because git is dirty; `issues=[]`.
  - `git diff --check`: passed.
  - Repo-local cache/build residue scan outside `runs/`: no `__pycache__`, `.pyc`, or `.egg-info` residue found.
- Current conclusion:
  - Functionally green under the saturation audit evidence above.
  - The only remaining non-functional warning is dirty git state from uncommitted audit fixes and ledger updates.

### Continuation Saturation Pass - No Commit Yet

- User instruction:
  - do not commit yet;
  - continue a deeper and broader platform audit/test/correction pass;
  - spend runtime where useful;
  - keep this about the generic `sim_plane` platform only.
- Boundary:
  - no external workspace edits;
  - no acceptance weakening;
  - no deletion of valid `runs/` evidence;
  - no concurrent artifact inspectors while a runtime command is writing under `runs/`.
- Execution shape:
  - recheck structure, contamination, static syntax, unit tests, CLI/backend/adapter/frontend alignment;
  - rerun fresh lightweight runtime, suite, fuzz, quadrotor exam, baseline, algorithm ingress, PX4 failure, planner/platform acceptance, hygiene, and health;
  - run bounded heavy headless backend probes only where prerequisites are currently ready;
  - fix only evidence-backed current-repo defects.

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

## Saturation Audit Resume Result - 2026-06-08

- Scope stayed limited to `/home/coco/sim_plane`.
- No external project workspace was edited.
- No valid `runs/` artifact was deleted.
- Subagent/session resume evidence identified three real local defects or broken surfaces:
  - `planner_goal` could treat `NaN`/`inf` as in-tolerance when `goal_settle_hold_s=0.0`;
  - composite ROS lab-stack backends could prepare multiple envs without explicitly sharing one `ROS_MASTER_URI`;
  - `px4_jsbsim_mavsdk_action` intermittently failed because the MAVSDK adapter only used local NED altitude while backend KPI already used the max of local and global-relative altitude.
- Fixes made:
  - added finite-value guards and tests in `sim_plane/backends/planner_goal.py`;
  - added strict/default/shared ROS master helpers in `sim_plane/ros_master.py`;
  - made composite MARSIM/FAST_LIO/EGO backends share a single `ROS_MASTER_URI` before launch;
  - hardened `sim_plane/adapters/mavsdk_action.py` to accept either local NED or relative altitude for takeoff reach and report max altitude diagnostics on timeout;
  - repaired `configs/quadrotor_exam_acceptance_matrix.json` to reference the earliest present passed frozen report, `runs/suites/paper_quadrotor_exam_suite_20260601_050941_402055/report.json`, because the old `20260531_183803` report path was missing locally.
- Static/unit validation:
  - Python syntax check: `92` files OK;
  - JSON syntax check: `48` files OK;
  - full unit suite: `186` tests OK;
  - targeted new tests: `tests.test_planner_goal tests.test_ros_master tests.test_mavsdk_action_adapter` -> `22` tests OK;
  - `git diff --check` -> passed;
  - repo-local `__pycache__`/`.pyc` residue -> none after cleanup.
- Fresh runtime and acceptance evidence:
  - fresh JSBSim MAVSDK action run passed: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190013_547706`;
  - additional JSBSim MAVSDK action repeatability: `5/5` passed:
    - `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190257_188948`
    - `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190352_623145`
    - `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190447_595313`
    - `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190542_476995`
    - `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190637_072036`
  - `planner-acceptance --latest`: `runs/acceptance/planner_acceptance_baseline_latest_20260607_190826_693506/report.json`, passed `4/4`;
  - `px4-failure-acceptance --latest`: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_190836_653994/report.json`, passed `1/1`;
  - `quadrotor-exam-acceptance --latest`: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_190845_606436/report.json`, passed `8/8`;
  - `platform-acceptance --latest`: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_190857_692882/report.json`, passed `21/21`;
  - `autotest-pack --profile fast`: `runs/autotest/sim_plane_autotest_fast_20260607_190919_385660/report.json`, passed `8/8`;
  - latest JSBSim artifact replay: `runs/flight_log_analysis/artifact_px4_jsbsim_quadx_mavsdk_action_20260607_190637_072036_20260607_190930_754702/report.json`, passed;
  - latest JSBSim `.ulg` replay: `runs/flight_log_analysis/ulog_19_06_43_20260607_190953_595099/report.json`, passed.
- Final hygiene/health:
  - `artifact-hygiene --artifact-root runs`: clean, `899` complete artifacts, `0` stale/incomplete/attention;
  - `manual-probe-hygiene --artifact-root runs`: clean, `2` retained manual probes, `0` stale;
  - `platform-health --artifact-root runs`: `runs/platform_health/sim_plane_platform_health_20260607_191018_060417/report.json`, status `warning`, `issues=[]`, only warning is dirty git state.
- Current remaining state:
  - functionally green under this audit evidence;
  - repository intentionally dirty until the user asks to commit/push this audit batch.

## Pre-Commit Final Saturation Audit Result - 2026-06-08

- Scope stayed limited to `/home/coco/sim_plane`.
- No external business-project workspace was edited.
- No valid `runs/` artifact was deleted.
- No acceptance threshold or semantic gate was weakened.
- The user has not approved commit/push yet, so the worktree remains intentionally dirty.
- Latest fixes in this pass:
  - PX4 log parser demotes shutdown-stage `Preflight Fail: height estimate not stable` to info-level transient noise;
  - console `run_suite_basic` explicitly uses `configs/demo_degradation_suite.json`;
  - console `scenario_fuzz_basic` uses canonical seed `20260528`;
  - console read-only actions disclose that frontend execution still writes console logs;
  - console output detection compares `(mtime_ns, size, type)` signatures;
  - planner, quadrotor exam, console command, and PX4 SIH tests cover the latest-selection/output-detection risks fixed in this pass.
- Static/unit validation from the latest completed pass:
  - targeted tests: `tests.test_console_commands tests.test_planner_acceptance tests.test_quadrotor_exam_acceptance tests.test_px4_sih_backend` -> `62` tests OK;
  - JSON syntax: `48` config/scenario files OK;
  - Python syntax: `96` Python files OK;
  - full unit suite: `240` tests OK;
  - `git diff --check` -> passed.
- Fresh runtime/suite/fuzz/exam/ingress evidence:
  - `basic_takeoff`: `runs/basic_takeoff_20260607_225155_170044`, passed;
  - `live-smoke fast`: `runs/live_smoke/live_smoke_fast_20260607_225211_695491/report.json`, passed;
  - `live-smoke default`: `runs/live_smoke/live_smoke_default_20260607_225300_785457/report.json`, passed `2/2`, including fresh `px4_sih_headless`;
  - `demo_degradation_suite`: `runs/suites/demo_degradation_suite_20260607_225307_876550/report.json`, passed;
  - `scenario-fuzz seed 20260528`: `runs/scenario_fuzz/demo_seeded_fuzz_20260528_20260607_225322_790893/report.json`, passed;
  - `quadrotor-exam`: `runs/suites/paper_quadrotor_exam_suite_20260607_225341_991835/report.json`, passed `8/8`;
  - `run-baseline pid_position_demo`: `runs/basic_takeoff_20260607_225350_951155`, passed;
  - `check-algorithm-ingress`: `runs/px4_sih_quadx_external_command_template_20260607_225402_620359`, passed;
  - PX4 native failure run: `runs/px4_sih_quadx_mavsdk_failure_motor_20260607_225456_602956`, passed;
  - JSBSim MAVSDK action: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_224522_578964`, passed.
- Latest formal reports:
  - planner acceptance: `runs/acceptance/planner_acceptance_baseline_latest_20260607_225542_459862/report.json`, `4/4` passed;
  - PX4 failure acceptance: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_225542_344794/report.json`, `1/1` passed;
  - quadrotor exam acceptance: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_225542_347975/report.json`, `8/8` passed;
  - platform acceptance: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_225617_503216/report.json`, `21/21` passed;
  - autotest fast pack: `runs/autotest/sim_plane_autotest_fast_20260607_225617_514420/report.json`, `8/8` passed.
- Flight-log evidence:
  - artifact replay: `runs/flight_log_analysis/artifact_px4_sih_quadx_external_command_template_20260607_225402_620359_20260607_225517_429261/report.json`, passed;
  - direct `.ulg` parse: `runs/flight_log_analysis/ulog_22_54_05_20260607_225529_969756/report.json`, passed.
- Hygiene/health:
  - artifact hygiene: clean;
  - manual probe hygiene: clean;
  - platform health: `runs/platform_health/sim_plane_platform_health_20260607_225652_210555/report.json`, `warning` only because git is dirty, `issues=[]`;
  - no repo-local `__pycache__`, `.pyc`, or `.egg-info` residue outside `runs/`;
  - no active `sim_plane`, PX4, ROS, Gazebo, or MAVSDK process remained.
- Current remaining state:
  - functionally green under the latest saturation evidence;
  - repository intentionally dirty until the user asks to commit/push this audit batch.
- Next candidate frontier, if optimization continues before commit:
  - PX4 ULog semantic enhancement: map numeric PX4 nav/arming states to readable labels and improve warning classification;
  - dashboard/report consolidation for health, suite, fuzz, acceptance, and flight-log evidence;
  - PX4-native failure expansion one official surface at a time.

## Structural Foundation Stabilization Frontier - 2026-07-18

### Locked Facts

- Scope is only `/home/coco/sim_plane`.
- Existing backend names, adapter names, scenario behavior, metric definitions, and acceptance thresholds are frozen during this structural pass.
- Heavy simulator expansion is paused until the repository foundation is portable and internally consistent.
- The current source checkout is clean at `main` / `origin/main` commit `a680858` before this frontier starts.

### Current Frontier

- Make frozen acceptance references reproducible from the repository instead of depending on ignored local `runs/` data.
- Introduce one resource/path contract instead of deriving repository roots independently and changing the process working directory globally.
- Version and validate scenario contracts, then remove duplicated visual/headless scenario bodies through explicit inheritance.
- Give artifacts an explicit running/complete lifecycle with atomic metadata writes and cross-process coordination.
- Extract shared PX4, ROS-composition, and acceptance infrastructure without changing runtime or gate semantics.
- Remove known dead/duplicated code and separate objective health reporting from hard-coded roadmap advice.

### Forbidden Actions

- Do not weaken acceptance thresholds or replace real PX4 failures with demo degradation.
- Do not change topic contracts, launch behavior, mission goals, timing values, or backend success criteria during structural extraction.
- Do not modify `/home/coco/sim_plane_ws` or any external project workspace.
- Do not delete valid historical `runs/` artifacts.
- Do not begin a ROS2/Gazebo migration or add another simulator backend.

### Promotion Gates

- Each phase must preserve backward compatibility for existing scenario and matrix files until their checked-in replacements are complete.
- Version-controlled baseline bundles must include source artifact identity and content checksums.
- Resource lookup must work from the repository, editable install, and explicit `SIM_PLANE_HOME`; unsupported installed layouts must fail clearly.
- Scenario validation must reject unknown or invalid contract fields before a backend process starts.
- Artifact readers must distinguish active runs from incomplete stale directories without relying on user timing discipline.
- Shared runtime extraction must be incremental and covered by focused tests before removing old helpers.

### Progress - 2026-07-18

- Completed repository-tracked compact acceptance baselines with source identity and checksums.
- Completed the unified workspace/path layer and removed process-wide working-directory mutation.
- Completed scenario contract v1:
  - strict top-level, backend-option, adapter-option, nested type, and range validation;
  - relative recursive inheritance with cycle detection and deep object merge/list replacement;
  - all 35 checked-in scenarios explicitly declare schema v1;
  - 16 duplicate visual/headless scenario bodies now inherit without changing effective values;
  - suite variants are validated after overrides and before backend startup;
  - generator options now use the `headless` field consumed by JSBSim and Gazebo Classic.
- Completed managed artifact lifecycle:
  - atomic directory allocation, JSON replacement, and line-safe JSONL append;
  - process-held artifact lock plus `.running` and `.complete` markers;
  - active, complete, legacy-complete, and stale-incomplete states;
  - hygiene and latest acceptance skip active artifacts while preserving crashed managed evidence.
- Completed incremental runtime extraction without changing backend contracts:
  - shared PX4 process, telemetry, shell-command, and log helpers live in `px4_common.py`;
  - shared ROS environment and shutdown helpers live in `ros_runtime.py`;
  - EGO, MARSIM, FAST_LIO, and planner-composition helpers live in dedicated runtime modules;
  - concrete backends no longer borrow execution helpers from other concrete backends;
  - PX4 SIH no longer stores private runtime handles in the scenario payload.
- Completed acceptance/report infrastructure extraction:
  - artifact selection, timestamp ordering, history, and retention live in `acceptance_common.py`;
  - planner, platform, PX4 failure, and quadrotor-exam acceptance keep separate contracts while sharing infrastructure;
  - report writers use atomic replacement and history writers use locked JSONL append.
- Completed wrapper/path and documentation consistency cleanup:
  - runtime wrappers locate the repository from their own path or `SIM_PLANE_HOME`;
  - algorithm subprocesses receive `SIM_PLANE_HOME`;
  - `platform-health` reports objective health and capability boundaries without a hard-coded roadmap;
  - current README and Chinese maintenance docs describe tracked baselines, scenario v1, and artifact lifecycle.
- Current validation evidence before the final closure run:
  - Python AST syntax: `111` files passed;
  - JSON syntax: `48` files passed;
  - checked-in scenario contract: `35/35` passed;
  - shell syntax and `git diff --check`: passed;
  - focused runtime tests: `40/40` passed;
  - repository reference acceptance passed for planner `4/4`, platform `21/21`, PX4 failure `1/1`, and quadrotor exam `8/8`, with reports under `/tmp/sim_plane_validation/`;
  - the sandboxed full suite ran `271` tests: `252` completed normally and `19` ended only because the sandbox denied localhost `socket()` with `PermissionError`; there were no assertion failures.
- Current frontier is final sequential closure validation in an environment that permits localhost sockets, followed by fresh lightweight runtime evidence, latest acceptance, hygiene/health, and cache/diff inspection.

### Final Structural Audit Findings - 2026-07-18

- Four independent read-only reviews were run after the first closure pass.
- The extracted PX4/ROS runtime layer had no reproducible behavior or ordering defect.
- Closure is reopened only for fresh structural defects, not for backend redesign:
  - completed artifacts can still be mutated by late daemon log threads;
  - atomic writes force mode `0644` and can expose previously private scenario/adapter data;
  - artifact allocation and hygiene pruning have an empty-directory race;
  - completed artifacts cannot be classified reliably from read-only storage because lock probing opens the lock file for append;
  - tracked baseline metadata can be absent or incomplete without failing verification;
  - baseline `source_commit` currently mislabels the freeze-time HEAD as the artifact-producing revision;
  - acceptance multi-file report publication and retention are not protected by one transaction lock;
  - the retained source quadrotor-exam report is not protected after the tracked-baseline migration;
  - latest artifact selection does not filter backend and vehicle identity;
  - waypoint aliases, adapter null/shell combinations, inherited schema versions, and safety/range bounds contain validation gaps;
  - generated algorithm workdirs and `sync_upstreams.py` still depend on caller cwd;
  - `list-adapters` is coupled to unrelated backend probes;
  - planner matrix documentation and two local-only evidence links are stale or misleading.
- No acceptance threshold, metric definition, scenario goal, backend command, topic, or timing change is authorized by these findings.
- The socket-dependent full-suite/doctor rerun remains an environment validation item; it must not hide or delay fixes to the independent defects above.

### Structural Closure Continuation - 2026-07-19

- Closed the fresh artifact lifecycle, baseline provenance/report transaction, scenario contract, cwd portability, adapter-list coupling, console coverage, and documentation consistency findings without changing runtime or acceptance contracts.
- Focused validation is green; final sequential closure now runs static/contract checks, all non-socket unit tests, fresh lightweight runtime surfaces, all latest acceptances, hygiene/health, and final residue/process/diff inspection.
- Localhost-socket tests remain classified separately because the managed sandbox denies `socket()` before product logic executes; no product patch may suppress that boundary.
- Commit and push remain explicitly deferred.

### Closure Validation Result - 2026-07-19

- Static, contract, non-socket unit, fresh lightweight, latest/reference acceptance, hygiene, process, and residue checks completed as recorded in the supervisor ledger.
- Current platform code is not promoted to commit in this round. The only environment-dependent red status is localhost socket creation inside the managed sandbox; unsandboxed verification was requested and rejected by the approval service, so it remains an explicit blocker rather than a code change.
- Preserve the current dirty worktree and valid `runs/` evidence for the next session; do not rerun the same saturation suite without a normal-socket environment or a newly bounded question.

### Normal-Host Validation Closure - 2026-07-19

- The exact full unit command completed on the normal host: `289` tests ran in `17.370s`, result `OK`.
- The sandbox-only socket blocker is retired. Structural foundation stabilization is complete; do not reopen it without fresh contradictory evidence.
- The accumulated batch remains intentionally uncommitted and unpushed pending the user's explicit next instruction.

### Operator Evidence Reconciliation - 2026-07-19

- User-provided normal-terminal evidence confirms the full suite: `289` tests, `17.370s`, `OK`.
- This closes the socket-dependent validation item and supersedes stale parallel resume notes; no further structural rerun is required without a new question.

### Release Closure - 2026-07-20

- Review the complete accumulated structural diff without changing frozen runtime or acceptance semantics.
- Include the compact `baselines/` bundles in version control so reference acceptance no longer depends on ignored local `runs/` artifacts.
- Commit and push the reviewed structural batch.
- Prove repository portability from a temporary clean checkout by running scenario-contract validation, the full unit suite, and all four reference acceptance surfaces.
- Keep broad CLI/web/docs decomposition out of this batch; assess it separately only after the portable release revision is proven.
- Pre-commit read-only review found bounded release blockers in acceptance fail-closed behavior/source binding, scenario validation, output-root containment, manual-probe lifecycle, suite log draining, process-group cleanup, managed PX4 discovery, wrapper propagation, upstream status-only behavior, and evidence wording.
- Fix only those evidenced blockers with focused tests; historical unknown source revisions remain unknown, while future artifacts gain honest Git revision/dirty-state capture.
- 2026-07-21 resume: session JSONL and worktree confirm that the first scenario/acceptance/path/manual-probe patch landed before interruption; validate it first, then continue the remaining locked items without reopening completed branches.
- 2026-07-21 reconciliation: the next resume attempt died with HTTP `503` before execution. Continue from the unrerun ROS shutdown-timeout focused tests, then finish only the remaining release blockers; treat the active external PX4/Gazebo/ROS stack as out of scope and avoid shared integration runs until it exits.
- 2026-07-21 implementation and pre-commit validation closure:
  - all bounded release blockers are fixed without changing frozen thresholds, KPI definitions, scenario targets, topics, backend commands, or timing;
  - focused tests passed at `42/42` and `64/64`, and the full suite passed `307/307`;
  - static/contract checks, fresh lightweight demo/smoke/suite/fuzz/KPI-proxy runs, all four reference and latest acceptance surfaces, artifact/manual-probe hygiene, and platform health are green apart from the expected uncommitted-worktree warning;
  - final evidence is recorded in `.supervisor/supervisor_ledger.md` under `Pre-Commit Release Validation Closure - 2026-07-21`;
  - the only remaining work is cache cleanup, final payload review, commit/push, and clean-clone proof of scenarios, full units, four reference acceptances, and Git provenance on a fresh demo artifact.
- 2026-07-22 release closure:
  - structural payload commit `18c82c12e08fbcc704ebfc48159460ac54aaffa2` is present on `origin/main`;
  - a clean remote clone passed scenario validation `35/35`, full units `307/307`, planner reference `4/4`, platform reference `21/21` with nested planner PASS, PX4 failure reference `1/1`, and quadrotor KPI/proxy reference `8/8`;
  - fresh demo artifact `runs/basic_takeoff_20260722_151854_953731` passed and recorded commit `18c82c12e08fbcc704ebfc48159460ac54aaffa2` with `dirty=false`;
  - this structural and portable-acceptance frontier is closed; later optimization must open a new bounded frontier rather than extending this release batch.
