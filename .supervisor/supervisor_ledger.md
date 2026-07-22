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

- Run a saturation platform audit and correction pass for `/home/coco/sim_plane`.
- Scope includes:
  - repository hygiene and ignored residue;
  - JSON/schema-style configuration validity;
  - Python syntax and unit tests;
  - CLI/frontend command alignment;
  - lightweight fresh runtime evidence;
  - suite, fuzz, exam, ingress, acceptance, flight-log, artifact-hygiene, and platform-health surfaces;
  - optional heavier backend checks only when prerequisites are ready and the run is bounded.
- Keep current validation semantics intact; do not weaken acceptance gates to manufacture a pass.
- Fix only fresh, evidence-backed defects found in this audit.
- Preserve valid `runs/` artifacts unless `artifact-hygiene` explicitly classifies them as safe to prune.
- Formal runs must be sequential when they write to or inspect `runs/`, to avoid the known incomplete-artifact false failure mode.

## Forbidden Actions

- Do not modify external business-project workspaces.
- Do not reintroduce project-specific commands or scenarios.
- Do not delete generic lab-stack support just because it was used in previous project-specific experiments.
- Do not claim a platform surface is available unless it exists in the current CLI/backend/adapter registry.

## Current Hypotheses

- The strongest current platform line is the unified runner/scenario/artifact/KPI/acceptance/dashboard flow, not any single simulator backend.
- The most valuable next work is to reduce user-facing complexity while keeping the evidence pipeline strict.
- Heavy simulator migration should not precede better user-facing workflows unless fresh evidence shows the current backends block near-term usage.
- External references support this direction:
  - PX4 MAVSDK integration testing emphasizes end-to-end SITL/CI tests and process log collection.
  - PX4 failure injection and ULog docs emphasize explicit failure surfaces and flight-log evidence.
  - ArduPilot AutoTest emphasizes named test steps, logs, local reproduction, and server/report correlation.
  - UAV benchmark projects emphasize fixed tasks, metrics, and repeatable comparisons rather than exposing every low-level command directly.

## Newly Locked This Round

- Current core architecture should not be refactored in this round.
- The optimization target is the user-facing console/evidence layer:
  - each action must say whether it is a fresh run, latest-artifact check, read-only scan, or mixed autotest;
  - each action must show what it writes under `runs/`;
  - actions that inspect `runs/` must warn against concurrent artifact-writing tasks.

## Newly Demoted This Round

- Adding another simulator backend is demoted: current complexity problem is not backend shortage.
- Rewriting acceptance semantics is demoted: current problem is user misunderstanding of evidence type, not acceptance threshold weakness.
- Full dashboard parameter editor is demoted for this round: it risks becoming a confusing CLI mirror before the workflow taxonomy is clear.
- Adding more frontend buttons is demoted for this round: the harder gap is PX4 raw log evidence, not another preset command.

## Corrective Round - User Alignment

- The user explicitly asked for three connected outcomes, not just a health closeout:
  - rebuild a system-level understanding of the whole UAV simulation platform;
  - run multiple validation rounds;
  - judge the next optimization direction from that evidence.
- The previous final answer was too compressed and did not clearly explain:
  - which part of the requested system-level understanding was rebuilt;
  - how the multi-round tests map to the platform architecture;
  - what the parallel agents did or failed to do;
  - why the recommended next optimization follows from the whole system analysis.
- Current corrective goal:
  - produce an evidence-backed platform map, usage map, validation matrix, current capability boundary, and prioritized optimization direction.
- Do not let this corrective round collapse into a narrow `platform-health` result.

## Required Closeout

- Explain the architecture and usage with current-file evidence, not memory.
- Run focused unit tests, CLI smoke, frontend coverage checks, and at least one fresh lightweight run.
- Run latest acceptance/report checks that do not require heavy simulator startup.
- Separate proven facts, inferences, and recommended next actions.
- Report PASS/FAIL and any remaining objective risk.

## Latest Evidence Snapshot

- Timestamp: `2026-06-06`
- Boundary: only `/home/coco/sim_plane` was inspected or changed; external business-project workspaces remain out of scope.
- Residual project-specific scan outside ignored `runs/` returned no active `human_follow`, `Stage1`, `Stage2`, or `follwer_ws` references.
- Static validation passed:
  - JSON syntax check for `configs/*.json` and `scenarios/*.json`
  - `python3 -m py_compile` over `sim_plane`, `scripts`, and `tests`
  - `git diff --check`
- Unit validation passed:
  - `python3 -m unittest` -> `154` tests OK
- CLI/frontend alignment passed:
  - `23` CLI subcommands
  - `16` frontend console commands
  - `7` intentionally hidden CLI commands
  - no missing or extra mappings
- Fresh runtime validation passed:
  - `python3 -m sim_plane run scenarios/basic_takeoff.json --artifact-root runs --no-hold-open --backend demo`
  - artifact: `runs/basic_takeoff_20260606_092943_510944`
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --json`
  - report: `runs/live_smoke/live_smoke_fast_20260606_092948_597930/report.json`
  - `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_degradation_suite.json --artifact-root runs --json`
  - report: `runs/suites/demo_degradation_suite_20260606_092944_030682/report.json`
  - `python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast --seed 7 --variants 6 --artifact-root runs --json`
  - report: `runs/scenario_fuzz/demo_seeded_fuzz_7_20260606_092944_053485/report.json`
  - `python3 -m sim_plane autotest-pack --profile fast --artifact-root runs --json`
  - report: `runs/autotest/sim_plane_autotest_fast_20260606_093026_205815/report.json`
  - result: `8/8` steps passed
- Latest acceptance passed:
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json`
  - report: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260606_093021_620514/report.json`
  - result: `21/21` rows passed
- Custom algorithm ingress passed:
  - `python3 -m sim_plane check-algorithm-ingress --scenario scenarios/px4_sih_quadx_external_command_template.json --artifact-root runs --json`
  - artifact: `runs/px4_sih_quadx_external_command_template_20260606_094241_725253`
  - checks: run completed, adapter present, adapter success, telemetry present, control observed, KPI present
- Hygiene/health:
  - `python3 -m sim_plane artifact-hygiene --artifact-root runs --json` -> `clean`
  - `python3 -m sim_plane platform-health --artifact-root runs --json`
  - report: `runs/platform_health/sim_plane_platform_health_20260606_094502_338730/report.json`
  - status: `warning`, with no issues; only warning is dirty git state.
- Productized console round validation:
  - `python3 -m unittest tests.test_console_commands tests.test_dashboard_replay` -> `11` tests OK.
  - `python3 -m unittest` -> `157` tests OK.
  - `git diff --check` -> passed.
  - `python3 -m py_compile sim_plane/console_commands.py` -> passed.
  - frontend console now exposes `18` whitelisted actions across `5` workflows.
  - CLI/frontend coverage is now `23` CLI commands = `18` surfaced + `5` intentionally hidden.
  - hidden commands: `flight-log-analyze`, `generate-scenario`, `planner-acceptance`, `serve`, `show-scenario`.

## Latest Inference

- The platform mainline is functionally healthy under the light-to-medium validation surface.
- The current strongest product value is the unified evidence pipeline: `CLI -> scenario -> backend/adapter -> artifact -> KPI/suite/fuzz/acceptance -> dashboard/console`.
- The current objective non-functional risk is not a failed run; it is the dirty worktree with four tracked changes that should be committed or deliberately reverted before claiming a fully clean repository state.
- After the productized console round, the immediate user-facing complexity risk is reduced but not eliminated:
  - fresh-run vs retained-artifact proof is now explicit in the UI;
  - concurrent `runs/` inspection risk is now explicit in the UI;
  - fully parameterized frontend flows for `generate-scenario` and `flight-log-analyze` are still not implemented.
- A later corrective round confirmed the user's complaint: the earlier closeout was too compressed and did not fully answer the original request to rebuild platform understanding, run multi-round tests, and judge next optimization direction.
- Corrective round used four read-only subagents for architecture, testing, frontend/CLI alignment, and optimization-direction audits; all four completed without changing files.
- Corrective round fresh evidence:
  - `python3 -m unittest` -> `154` tests OK.
  - `python3 -m sim_plane run scenarios/basic_takeoff.json --artifact-root runs --no-hold-open --backend demo` -> `runs/basic_takeoff_20260606_095911_225233`, passed.
  - `python3 -m sim_plane live-smoke --profile fast --artifact-root runs --json` -> `runs/live_smoke/live_smoke_fast_20260606_095915_844321/report.json`, passed.
  - `python3 -m sim_plane live-smoke --profile default --artifact-root runs --json` -> `runs/live_smoke/live_smoke_default_20260606_100359_889875/report.json`, `2/2` passed, including fresh `px4_sih_headless`.
  - `python3 -m sim_plane run-suite scenarios/basic_takeoff.json --suite configs/demo_degradation_suite.json --artifact-root runs --json` -> `runs/suites/demo_degradation_suite_20260606_100004_920368/report.json`, `6/6` passed.
  - `python3 -m sim_plane scenario-fuzz scenarios/basic_takeoff.json --profile demo_fast --seed 11 --variants 8 --artifact-root runs --json` -> `runs/scenario_fuzz/demo_seeded_fuzz_11_20260606_100004_947106/report.json`, `9/9` passed.
  - `python3 -m sim_plane quadrotor-exam --artifact-root runs --json` -> `runs/suites/paper_quadrotor_exam_suite_20260606_100004_930260/report.json`, `8/8` passed.
  - `python3 -m sim_plane check-algorithm-ingress --scenario scenarios/px4_sih_quadx_external_command_template.json --artifact-root runs --json` -> `runs/px4_sih_quadx_external_command_template_20260606_100042_937003`, passed.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json` -> `runs/platform_acceptance/platform_acceptance_baseline_latest_20260606_100043_625681/report.json`, `21/21` passed.
  - `python3 -m sim_plane px4-failure-acceptance --latest --artifact-root runs --json` -> `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260606_100043_261905/report.json`, `1/1` passed.
  - `python3 -m sim_plane flight-log-analyze runs/px4_sih_quadx_external_command_template_20260606_100042_937003 --report-root runs/flight_log_analysis --json` -> `runs/flight_log_analysis/artifact_px4_sih_quadx_external_command_template_20260606_100042_937003_20260606_100318_106495/report.json`, passed.
  - `python3 -m sim_plane quadrotor-exam-acceptance --latest --artifact-root runs --json` -> `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260606_100318_345655/report.json`, `8/8` passed.
  - `python3 -m sim_plane autotest-pack --profile fast --artifact-root runs --json` was first contaminated by a concurrent PX4 ingress run and failed at `artifact_hygiene`; sequential rerun passed at `runs/autotest/sim_plane_autotest_fast_20260606_100230_918824/report.json`, `8/8`.
  - Final `platform-health` -> `runs/platform_health/sim_plane_platform_health_20260606_100439_967326/report.json`, status `warning`, issues `[]`, warning only `git: status=warning`.
- Corrective round process lesson:
  - Do not run artifact-hygiene/autotest/platform-health in parallel with long-running commands that are actively writing under `runs/`, because an in-progress artifact can be correctly classified as incomplete.

## Next Best Frontier

- Deepen real PX4 evidence where it matters most:
  - make `flight-log-analyze` consume artifact-local `px4_ulog/index.json` more directly;
  - map PX4 numeric nav/arming states into clearer report labels;
  - keep dashboard/report summaries tied to real artifact-local `.ulg` status.
- Expand native failure/fault testing carefully:
  - keep demo degradation clearly separated from PX4-native failures;
  - add one PX4-supported failure surface at a time and gate it with acceptance.

## Current Round Question

- Does the current generic UAV simulation/evaluation platform still pass a saturation, fresh, end-to-end audit across structure, tests, runtime, evidence, frontend/backend alignment, and hygiene; if not, what exact project-local defects must be fixed without changing acceptance semantics?

## Saturation Audit 2026-06-08

### Locked Facts

- Start point: `main` is synced with `origin/main` after commit `ebbac14`.
- User request: run the broadest practical audit/test/correction pass and spend compute/tokens where useful.
- Boundary: only `/home/coco/sim_plane`; do not touch external workspaces.
- Valid `runs/` artifacts must be preserved.

### Current Question

- Which current project-local defects, if any, are exposed by a broad sequential audit of structure, CLI/frontend alignment, static checks, unit tests, fresh runtime surfaces, acceptance reports, artifact hygiene, and platform health?

### Forbidden This Round

- No external workspace edits.
- No acceptance-threshold weakening.
- No broad backend migration.
- No artifact inspectors while a run is actively writing.

### Interruption Resume Closure

- Fresh session/control-plane reads found unrelated latest session files from other projects; they were not used as `sim_plane` facts.
- Current `sim_plane` source of truth is this ledger, `.agent/PLANS.md`, current git diff, and fresh `runs/` evidence.
- No active `sim_plane`, PX4, ROS, Gazebo, or MAVSDK server process was found before resuming formal validation.
- Confirmed fixed defects in the current dirty worktree:
  - strict planner goal-reach verdict now handles zero-hold cases and 3-decimal report precision through `sim_plane/backends/planner_goal.py`;
  - ROS lab-stack backends now isolate default `localhost:11311` through `sim_plane/ros_master.py` while preserving explicit non-default masters;
  - strict planner scenarios now use `20 Hz` sampling and runtime goal tolerances aligned to the frozen acceptance surface.
- Recovered planner evidence:
  - `ego_planner_swarm_fast_lio_marsim` repeated `10/10` PASS after ROS master isolation;
  - latest direct planner acceptance report: `runs/acceptance/planner_acceptance_baseline_latest_20260607_174542_496071/report.json`, `4/4` passed.
- Sequential final validation after the interruption:
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane platform-acceptance --latest --artifact-root runs --json` -> passed; latest report later refreshed at `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_174339_295017/report.json`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane px4-failure-acceptance --latest --artifact-root runs --json` -> `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_174312_970303/report.json`, passed `1/1`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane quadrotor-exam-acceptance --latest --artifact-root runs --json` -> `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_174323_166482/report.json`, passed `8/8`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane autotest-pack --profile fast --artifact-root runs --json` -> `runs/autotest/sim_plane_autotest_fast_20260607_174339_301360/report.json`, passed `8/8`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane artifact-hygiene --artifact-root runs --json` -> `clean`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane manual-probe-hygiene --artifact-root runs --json` -> `clean`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m sim_plane platform-health --artifact-root runs --json` -> `runs/platform_health/sim_plane_platform_health_20260607_174408_466729/report.json`, status `warning`, `issues=[]`, only warning `git: status=warning`.
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest` -> `179` tests OK.
  - JSON syntax -> `48` files OK.
  - Python source syntax -> `92` files OK.
  - `list-backends` -> `12/12` ready.
  - `list-adapters` -> `4/4` ready.
  - `git diff --check` -> passed.
  - Repo-local residue scan outside `runs/` found no `__pycache__`, `.pyc`, or `.egg-info`.
- Current conclusion:
  - The saturation audit surface is functionally green under current evidence.
  - The only remaining warning is dirty git state from uncommitted audit fixes and ledger updates.
  - No external workspace was modified.

### Continuation Saturation Pass - No Commit Yet

- User explicitly deferred committing until later.
- Current worktree remains intentionally dirty from audit fixes and control-ledger updates.
- New round goal:
  - run another broad, sequential, no-pollution audit of the full `sim_plane` auxiliary platform;
  - exercise as many ready surfaces as practical without GUI-dependent sprawl;
  - correct only fresh, current-repo defects backed by command output or artifact evidence.
- Current round forbidden actions:
  - do not commit or push;
  - do not modify external workspaces;
  - do not weaken acceptance thresholds or semantics;
  - do not run artifact inspectors while any runtime command is actively writing under `runs/`;
  - do not delete valid historical artifacts.

## PX4 ULog Evidence Closure Result

- Implemented shared helper:
  - `sim_plane/px4_ulog.py`
  - It handles discovery, before/after snapshots, collection, manifest updates, metrics, notes, index reads, and safe failure handling.
- Wired existing PX4-family backends:
  - `sim_plane/backends/px4_sih.py`
  - `sim_plane/backends/px4_jsbsim.py`
  - `sim_plane/backends/px4_gazebo_classic.py`
- Collection is non-gating:
  - `px4_ulog/index.json` records `collected`, `missing`, `disabled`, or `failed`;
  - a collection failure is recorded as warning-style evidence and does not change the simulation verdict;

## Resume Continuation 2026-06-08

### Locked Facts

- Latest unrelated session files were found in `/home/coco/.codex/sessions`; they were not used as `sim_plane` facts.
- Relevant read-only subagent findings from `2026-06-08 05:55-06:02` were integrated.
- No active PX4/ROS/Gazebo/MAVSDK/sim_plane runtime process was found before this continuation.
- Scope remains `/home/coco/sim_plane` only.

### Fixed Without Acceptance Semantics Changes

- `sim_plane/console_commands.py` now labels `artifact-hygiene` and `manual-probe-hygiene` as `artifact_scan` instead of `latest_artifact_check`.
- `docs/算法复现手册_zh.md` now states that `--latest` commands verify existing artifacts and do not start a fresh simulation.
- `sim_plane/planner_acceptance.py` now chooses latest matching artifacts by artifact creation time from `manifest.json` when available, falling back to file/directory mtime and then directory name.
- `tests/test_planner_acceptance.py` covers the manifest-time latest-selection case.

### Validation Started

- Targeted validation passed:
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_planner_acceptance tests.test_console_commands tests.test_dashboard_replay`
  - `PYTHONDONTWRITEBYTECODE=1 python3 -B -m py_compile sim_plane/planner_acceptance.py sim_plane/console_commands.py`

### Next Actions

- Run broad validation sequentially, with no artifact inspectors while any runtime command writes `runs/`.
- Clean repo-local Python cache residue only after validation completes.

## Active Continuation Audit - 2026-06-08

### Locked Facts

- User asked for another broad saturation audit/correction pass and explicitly said not to commit yet.
- Scope remains only `/home/coco/sim_plane`.
- Fresh process check before this continuation found no active `sim_plane`, PX4, ROS, Gazebo, JSBSim, MAVSDK, or FlightGear runtime process except the check command itself.
- Current worktree is intentionally dirty from prior audit fixes and control-ledger updates.

### Current Question

- Under the current dirty-but-intentional worktree, does the platform still pass fresh runtime, acceptance, static, unit, hygiene, and health surfaces after the latest fixes?
- If not, which earliest project-local defect must be fixed without weakening acceptance semantics?

### Forbidden Actions

- Do not commit or push in this round.
- Do not edit external workspaces.
- Do not weaken acceptance thresholds or semantics.
- Do not run artifact inspectors while any runtime command is writing under `runs/`.
- Do not delete valid historical artifacts.
  - `result.json` receives `px4_ulog_collected`, `px4_ulog_count`, and `px4_ulog_total_bytes` when a backend result exists.
- Dashboard artifact summaries now include optional `px4_ulog` status and remain compatible with older artifacts that have no ULog index.
- Fresh proof:
  - `python3 -m sim_plane run scenarios/px4_sih_quadx_headless.json --artifact-root runs --no-hold-open`
  - artifact: `runs/px4_sih_quadx_headless_20260606_124503_774339`
  - status: `passed`
  - collected ULog: `runs/px4_sih_quadx_headless_20260606_124503_774339/px4_ulog/12_45_07.ulg`
  - index: `runs/px4_sih_quadx_headless_20260606_124503_774339/px4_ulog/index.json`
  - metrics: `px4_ulog_collected=true`, `px4_ulog_count=1`, `px4_ulog_total_bytes=7517823`
- Fresh ULog replay proof:
  - `python3 -m sim_plane flight-log-analyze runs/px4_sih_quadx_headless_20260606_124503_774339/px4_ulog/12_45_07.ulg --report-root runs/flight_log_analysis --json`
  - report: `runs/flight_log_analysis/ulog_12_45_07_20260606_124655_228127/report.json`
  - status: `passed`
- Validation:
  - focused test group -> `43` tests OK.
  - `python3 -m py_compile sim_plane/px4_ulog.py sim_plane/backends/px4_sih.py sim_plane/backends/px4_jsbsim.py sim_plane/backends/px4_gazebo_classic.py sim_plane/web.py sim_plane/platform_health.py` -> passed.
  - full `python3 -m unittest` -> `163` tests OK.
  - `git diff --check` -> passed.
  - `python3 -m sim_plane platform-acceptance --latest --artifact-root runs --json` -> `runs/platform_acceptance/platform_acceptance_baseline_latest_20260606_124727_417603/report.json`, `21/21` passed.
  - `python3 -m sim_plane platform-health --artifact-root runs --json` -> `runs/platform_health/sim_plane_platform_health_20260606_124840_286175/report.json`, status `warning` only because git is dirty, `issues=[]`.
- Boundary:
  - PX4-family backends attempt ULog collection by default, but actual availability remains runtime-dependent and must be read from each artifact's `px4_ulog/index.json`.
  - Artifact replay and `.ulg` replay remain distinct analysis inputs.

## Forbidden Next Round

- Do not modify external workspaces.
- Do not change acceptance thresholds.
- Do not add a new simulator backend.
- Do not turn the frontend into an unrestricted shell.
- Do not treat valid historical artifacts as garbage.
- Do not run artifact-hygiene/platform-health/autotest concurrently with a command actively writing under `runs/`.

## Comprehensive Platform Audit Result - 2026-06-07

- Boundary:
  - only `/home/coco/sim_plane` was modified;
  - no external business-project workspace was touched;
  - valid `runs/` artifacts were preserved;
  - acceptance thresholds and semantics were not weakened.
- Fresh defects fixed:
  - local dashboard tests ignored the host proxy when calling `127.0.0.1`, preventing local API checks from being polluted by `HTTP_PROXY`;
  - `list-adapters` now reuses `doctor` classification, so template adapters such as `external_command` and `ros_command` are shown as ready-with-note instead of misleading `scaffolded`;
  - MAVSDK action waits now raise labeled `AdapterError` messages instead of empty timeout strings;
  - Gazebo Classic MAVSDK action scenarios now allow `land_timeout_s=36.0`, based on fresh evidence that the previous 24s window was too tight for real land/disarm timing;
  - MAVSDK adapters now best-effort stop their local MAVSDK server;
  - `aiogrpc.WrappedIterator.__del__` is guarded only for the confirmed third-party shutdown noise `RuntimeError("cannot join current thread")`;
  - algorithm adapter collection now rejects non-dict reports with an explicit adapter failure message, preventing low-signal backend errors such as `'tuple' object has no attribute 'get'`;
  - a MAVSDK action adapter tuple-return regression was fixed and covered by tests.
- Fresh runtime evidence:
  - `basic_takeoff`: `runs/basic_takeoff_20260607_133513_329398`, passed;
  - `live-smoke --profile fast`: `runs/live_smoke/live_smoke_fast_20260607_133530_395961/report.json`, passed;
  - `live-smoke --profile default`: `runs/live_smoke/live_smoke_default_20260607_133621_223841/report.json`, passed, including fresh PX4 SIH;
  - `scenario-fuzz --seed 17 --variants 8`: `runs/scenario_fuzz/demo_seeded_fuzz_17_20260607_134044_504532/report.json`, passed;
  - `run-baseline pid_position_demo`: `runs/basic_takeoff_20260607_134121_835980`, passed;
  - `check-algorithm-ingress`: `runs/px4_sih_quadx_external_command_template_20260607_134155_460434`, passed;
  - Gazebo Classic MAVSDK action: `runs/px4_gazebo_classic_iris_mavsdk_action_20260607_135304_884798`, passed with ULog collected;
  - PX4 SIH MAVSDK failure injection: `runs/px4_sih_quadx_mavsdk_failure_motor_20260607_134908_368063`, passed with ULog collected and no aiogrpc shutdown noise;
  - JSBSim MAVSDK action: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_135738_918250`, passed with `mode_changes=6` and ULog collected.
- Fresh validation:
  - JSON syntax for `configs/*.json` and `scenarios/*.json`: `48` files OK;
  - `compileall` over `sim_plane`, `scripts`, and `tests`: passed;
  - full unit suite: `171` tests OK;
  - `git diff --check`: passed;
  - `px4-failure-acceptance --latest`: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_141916_641710/report.json`, passed `1/1`;
  - `quadrotor-exam-acceptance --latest`: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_141916_804154/report.json`, passed `8/8`;
  - `flight-log-analyze` on fresh JSBSim MAVSDK artifact: `runs/flight_log_analysis/artifact_px4_jsbsim_quadx_mavsdk_action_20260607_135738_918250_20260607_142004_531245/report.json`, passed;
  - `artifact-hygiene --artifact-root runs`: clean;
  - `manual-probe-hygiene --artifact-root runs`: clean.
- Remaining blocked evidence:
  - `planner-acceptance --latest` remains failed at `runs/acceptance/planner_acceptance_baseline_latest_20260607_141916_429525/report.json`;
  - failing surface: `ego_planner_swarm_fast_lio_marsim` headless;
  - reference artifact: `runs/ego_planner_swarm_fast_lio_marsim_20260427_195903`, `min_goal_distance_m=0.030`;
  - repeated fresh artifacts were all behavior-passed but outside the frozen regression budget:
    - `runs/ego_planner_swarm_fast_lio_marsim_20260607_140000_814304`, `min_goal_distance_m=0.062`;
    - `runs/ego_planner_swarm_fast_lio_marsim_20260607_140055_586777`, `min_goal_distance_m=0.071`;
    - `runs/ego_planner_swarm_fast_lio_marsim_20260607_140108_989459`, `min_goal_distance_m=0.065`;
    - `runs/ego_planner_swarm_fast_lio_marsim_20260607_140122_269481`, `min_goal_distance_m=0.066`;
  - the same failing artifact also records EGO-Planner-Swarm solver warnings: `Solver error. Return = -1008 ... Skip this planning.`;
  - absolute goal threshold remains satisfied (`<0.1m`) and `goal_reached=true`, but frozen latest-vs-reference regression budget `0.01m` is not satisfied.
- Consequence:
  - `platform-acceptance --latest` reports all `21/21` direct platform rows passed but overall failed because nested planner acceptance failed: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_141917_540701/report.json`;
  - `autotest-pack --profile fast` failed only at `platform_acceptance_latest`: `runs/autotest/sim_plane_autotest_fast_20260607_142010_732735/report.json`;
  - `platform-health` failed only from the same planner/platform acceptance chain and a dirty-git warning: `runs/platform_health/sim_plane_platform_health_20260607_142011_885999/report.json`.
- Current objective conclusion:
  - the generic platform core, PX4 SIH, PX4 JSBSim, PX4 Gazebo Classic, MAVSDK action, MAVSDK failure injection, ULog replay, artifact hygiene, manual probe hygiene, and unit/static layers are healthy under fresh evidence;
  - the only remaining audit blocker is a real planner regression/noise issue in the `ego_planner_swarm_fast_lio_marsim` latest-vs-reference acceptance surface, not a repository hygiene issue and not a missing run;
  - do not claim a fully green platform until this planner acceptance decision is resolved by either fixing the planner/runtime behavior or explicitly changing the frozen acceptance contract in a separate, user-approved round.

## Comprehensive Platform Audit Follow-up Resolution - 2026-06-07

- The planner acceptance blocker was resolved without changing acceptance thresholds.
- Root cause:
  - `ego_planner_swarm_fast_lio_marsim` inherited the backend default `goal_reach_tolerance_m=0.6`;
  - the planner acceptance absolute goal threshold is `0.1m` and latest-vs-reference regression budget is `0.01m`;
  - the scenario could therefore stop sampling after reaching a coarse runtime goal while still missing the finer acceptance target;
  - repeated failed artifacts showed behavior success but `min_goal_distance_m=0.062..0.071` and one run included EGO-Planner-Swarm solver warnings.
- Evidence before patch:
  - temporary `goal_reach_tolerance_m=0.1` removed warning noise but still produced `min_goal_distance_m=0.058`;
  - temporary `goal_reach_tolerance_m=0.04` produced `min_goal_distance_m=0.022`;
  - official `goal_reach_tolerance_m=0.04` with `goal_settle_hold_s=0.6` proved the distance target but produced `goal_reached=false` because the stack does not provide meaningful velocity and the strict-distance hold was too brittle.
- Patch:
  - `scenarios/ego_planner_swarm_fast_lio_marsim.json` now sets:
    - `goal_reach_tolerance_m=0.04`;
    - `goal_settle_hold_s=0.0`.
- Fresh proof after patch:
  - official scenario run: `runs/ego_planner_swarm_fast_lio_marsim_20260607_150339_456246`;
  - result: passed;
  - metrics: `goal_reached=true`, `min_goal_distance_m=0.016`, `event_levels={"info": 42}`;
  - `planner-acceptance --latest`: `runs/acceptance/planner_acceptance_baseline_latest_20260607_150421_976435/report.json`, passed `4/4`;
  - `platform-acceptance --latest`: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_150422_832468/report.json`, passed `21/21`;
  - `autotest-pack --profile fast`: `runs/autotest/sim_plane_autotest_fast_20260607_150428_694335/report.json`, passed `8/8`;
  - `platform-health`: `runs/platform_health/sim_plane_platform_health_20260607_150430_059298/report.json`, command passed with `issues=[]`; status is `warning` only because git is dirty.
- Final validation after this follow-up:
  - JSON syntax: `48` files OK;
  - `compileall`: passed;
  - full unit suite: `171` tests OK;
  - `git diff --check`: passed;
  - `artifact-hygiene`: clean with `stale_incomplete_directory_count=0`, `empty_directory_count=0`, and `attention_count=0`;
  - repo-local Python cache and egg-info residue were removed again.
- Updated conclusion:
  - the previous planner blocker is no longer active;
  - the platform audit surface is functionally green under current evidence;
  - the only remaining `platform-health` warning is expected dirty git state from uncommitted audit fixes.

## Promotion Gate

- Fresh static validation passes or every failure is patched and rechecked.
- Full unit suite passes.
- Fresh lightweight runtime, suite/fuzz/exam, ingress, acceptance, artifact-hygiene, and platform-health evidence is produced sequentially.
- Any heavier runtime probe is bounded and reported as PASS/FAIL/SKIP with a concrete reason.
- Final worktree status is explicit.

## Git Closure Result

- Implementation commit pushed to `origin/main`:
  - `124c00e Add PX4 ULog evidence and console metadata`
- Post-push health check:
  - command: `python3 -m sim_plane platform-health --artifact-root runs --json`
  - report: `runs/platform_health/sim_plane_platform_health_20260606_135621_978938/report.json`
  - status: `passed`
  - components: `8/8`
  - warnings: `0`
  - issues: `0`
- Post-push repository state:
  - local `HEAD` and `origin/main` matched at `124c00e` before this ledger-only closure update;
  - `git status --short` was clean;
  - `runs/` remained ignored and was not committed.
- Current next frontier remains bounded:
  - artifact-local ULog replay/report alignment;
  - PX4-native failure expansion only one officially supported surface at a time;
  - dashboard/report consolidation without turning the frontend into an arbitrary shell.

## Hygiene Cleanup Frontier

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

## Hygiene Cleanup Result

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

### Locked Facts

- Scope stayed limited to `/home/coco/sim_plane`; no external workspace was edited.
- Valid `runs/` artifacts were preserved.
- Current local branch is functionally green under fresh evidence, but git remains dirty because this audit batch is not committed.
- No repo-local Python cache residue remains.
- No active `/home/coco/sim_plane`, PX4, JSBSim, or MAVSDK process remained after validation.

### Defects Fixed

- `planner_goal` now rejects non-finite telemetry/config values before goal-reach evaluation.
- ROS composite backends now share one selected `ROS_MASTER_URI` across MARSIM, FAST_LIO, probe, and planner envs in the same run.
- `mavsdk_action_takeoff` now treats either local NED altitude or global-relative altitude as valid takeoff-reach evidence and records max altitude diagnostics on timeout.
- `quadrotor_exam_acceptance_matrix.json` no longer points at the missing local `20260531_183803` suite report; it points at the earliest present passed frozen suite report, `20260601_050941_402055`.

### Fresh Evidence

- Static/unit:
  - Python syntax: `92` files OK.
  - JSON syntax: `48` files OK.
  - Full unit suite: `186` tests OK.
  - Targeted new tests: `22` tests OK.
  - `git diff --check`: passed.
- Runtime:
  - JSBSim MAVSDK action fresh proof: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190013_547706`, passed.
  - JSBSim MAVSDK action repeatability: `5/5` passed, latest `runs/px4_jsbsim_quadx_mavsdk_action_20260607_190637_072036`.
- Formal reports:
  - Planner acceptance: `runs/acceptance/planner_acceptance_baseline_latest_20260607_190826_693506/report.json`, `4/4` passed.
  - PX4 failure acceptance: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_190836_653994/report.json`, `1/1` passed.
  - Quadrotor exam acceptance: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_190845_606436/report.json`, `8/8` passed.
  - Platform acceptance: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_190857_692882/report.json`, `21/21` passed.
  - Autotest fast pack: `runs/autotest/sim_plane_autotest_fast_20260607_190919_385660/report.json`, `8/8` passed.
  - Artifact replay: `runs/flight_log_analysis/artifact_px4_jsbsim_quadx_mavsdk_action_20260607_190637_072036_20260607_190930_754702/report.json`, passed.
  - ULog replay: `runs/flight_log_analysis/ulog_19_06_43_20260607_190953_595099/report.json`, passed.
  - Platform health: `runs/platform_health/sim_plane_platform_health_20260607_191018_060417/report.json`, `warning` only because git is dirty, `issues=[]`.
- Hygiene:
  - Artifact hygiene: clean, `899` complete artifacts, `0` stale/incomplete/attention.
  - Manual probe hygiene: clean, `2` retained manual probes, `0` stale.

### Current Frontier

- Current saturation audit branch is functionally closed.
- Next useful action is git review/commit/push when the user approves.

### Forbidden Next Round

- Do not rerun the same saturation audit just to accumulate more PASS counts unless new evidence appears.
- Do not change acceptance semantics or thresholds.
- Do not touch external workspaces.

## Pre-Commit Final Saturation Audit - 2026-06-08

### Locked Facts

- User requested one more complete saturation audit before committing.
- This is still scoped only to `/home/coco/sim_plane`.
- The previous functional audit was green except for dirty git state.
- Closing old subagents surfaced additional read-only evidence of user-facing drift in docs/frontend surfaces; this is fresh evidence, so this round is not a no-op rerun.

### Current Frontier

- Fix evidence-backed user-facing drift without changing acceptance semantics:
  - frontend/console coverage wording must not imply every backend/baseline parameter surface is exposed;
  - latest acceptance UI should expose row-level issues/artifacts, not only changed deltas;
  - docs that still present the platform as MVP/early blueprint must be corrected or clearly marked historical;
  - README/docs evidence wording must not call old reference artifacts "fresh" when newer reports exist.
- Then rerun a broad but non-polluting validation matrix.

### Forbidden This Round

- No commit or push.
- No edits outside `/home/coco/sim_plane`.
- No acceptance threshold or semantic weakening.
- No deletion of valid `runs/` evidence.
- No concurrent artifact inspectors while a runtime command is writing under `runs/`.

### Promotion Gate

- All changed UI/docs behavior must have direct source evidence and tests where practical.
- Static checks, full unit tests, acceptance reports, artifact/manual hygiene, and platform health must be refreshed after edits.
- Any remaining warning must be explicitly classified.

### Pre-Commit Final Saturation Audit Result - 2026-06-08

#### Locked Facts

- Scope stayed limited to `/home/coco/sim_plane`.
- No external business-project workspace was edited.
- Valid `runs/` artifacts were preserved.
- The user explicitly deferred commit/push; dirty git is expected until the user approves committing this batch.
- No active `sim_plane`, PX4, ROS, Gazebo, or MAVSDK process remained after the latest validation pass.
- Repo-local cache/build residue scan outside `runs/` was clean after cleanup: no `__pycache__`, `.pyc`, or `.egg-info` residue remained.

#### Defects Fixed In The Latest Pass

- PX4 SIH/JSBSim log classification:
  - `sim_plane/backends/px4_sih.py` now treats `Preflight Fail: height estimate not stable` as transient info-level PX4 log noise, matching the existing transient heading-estimate classification.
  - Reason: fresh JSBSim/MAVSDK evidence passed after landing/disarm/logger close/PX4 exit, and this warning appeared in shutdown-stage log noise rather than in a failed flight phase.
- Frontend/console command accuracy:
  - `run_suite_basic` now explicitly runs `configs/demo_degradation_suite.json`.
  - `scenario_fuzz_basic` now uses canonical seed `20260528`.
  - read-only console actions now say `CLI 只读，会写 console 日志` where applicable, so the UI does not imply zero filesystem writes.
  - console output detection now compares `(mtime_ns, size, type)` signatures instead of mtime alone.
- Latest/report selection and output-detection tests were expanded for planner, quadrotor exam, console command, and PX4 SIH surfaces.

#### Latest Fresh Evidence

- Targeted tests:
  - `python3 -m unittest tests.test_console_commands tests.test_planner_acceptance tests.test_quadrotor_exam_acceptance tests.test_px4_sih_backend` -> `62` tests OK.
- Full static/unit checks:
  - JSON syntax: `48` config/scenario files OK.
  - Python syntax: `96` Python files OK.
  - Full unit suite: `240` tests OK.
  - `git diff --check`: passed.
- Fresh runtime/suite/fuzz/exam evidence:
  - `basic_takeoff`: `runs/basic_takeoff_20260607_225155_170044`, passed.
  - `live-smoke --profile fast`: `runs/live_smoke/live_smoke_fast_20260607_225211_695491/report.json`, passed.
  - `live-smoke --profile default`: `runs/live_smoke/live_smoke_default_20260607_225300_785457/report.json`, passed `2/2`, including fresh `px4_sih_headless`.
  - `demo_degradation_suite`: `runs/suites/demo_degradation_suite_20260607_225307_876550/report.json`, passed.
  - `scenario-fuzz --seed 20260528`: `runs/scenario_fuzz/demo_seeded_fuzz_20260528_20260607_225322_790893/report.json`, passed.
  - `quadrotor-exam`: `runs/suites/paper_quadrotor_exam_suite_20260607_225341_991835/report.json`, passed `8/8`.
  - `run-baseline pid_position_demo`: `runs/basic_takeoff_20260607_225350_951155`, passed.
  - `check-algorithm-ingress`: `runs/px4_sih_quadx_external_command_template_20260607_225402_620359`, passed.
  - PX4 native failure run: `runs/px4_sih_quadx_mavsdk_failure_motor_20260607_225456_602956`, passed.
  - JSBSim MAVSDK action: `runs/px4_jsbsim_quadx_mavsdk_action_20260607_224522_578964`, passed.
- Latest formal reports:
  - Planner acceptance: `runs/acceptance/planner_acceptance_baseline_latest_20260607_225542_459862/report.json`, passed `4/4`.
  - PX4 failure acceptance: `runs/px4_failure_injection_acceptance/px4_failure_injection_acceptance_latest_20260607_225542_344794/report.json`, passed `1/1`.
  - Quadrotor exam acceptance: `runs/quadrotor_exam_acceptance/quadrotor_exam_acceptance_latest_20260607_225542_347975/report.json`, passed `8/8`.
  - Platform acceptance: `runs/platform_acceptance/platform_acceptance_baseline_latest_20260607_225617_503216/report.json`, passed `21/21`.
  - Autotest fast pack: `runs/autotest/sim_plane_autotest_fast_20260607_225617_514420/report.json`, passed `8/8`.
- Flight-log evidence:
  - Artifact replay: `runs/flight_log_analysis/artifact_px4_sih_quadx_external_command_template_20260607_225402_620359_20260607_225517_429261/report.json`, passed.
  - Direct ULog parse: `runs/flight_log_analysis/ulog_22_54_05_20260607_225529_969756/report.json`, passed.
- Hygiene/health:
  - Artifact hygiene: clean.
  - Manual probe hygiene: clean.
  - Platform health: `runs/platform_health/sim_plane_platform_health_20260607_225652_210555/report.json`, `warning` only because git is dirty; `issues=[]`.

#### Current Conclusion

- Under the latest saturation audit evidence, the generic `sim_plane` platform is functionally green.
- Remaining non-functional warning is dirty git only, because commit/push was intentionally deferred.
- The next useful action is either:
  - review/commit/push the accumulated platform batch when the user approves; or
  - if continuing optimization before commit, open a new bounded frontier instead of rerunning the same saturation suite without new evidence.

#### Next Improvement Candidates, Not Current Blockers

- PX4 ULog semantic enhancement:
  - map PX4 numeric nav/arming states to readable names;
  - classify ULog warning messages more precisely.
- Dashboard/report consolidation:
  - make health, suite, fuzz, acceptance, and flight-log evidence easier to browse without turning the frontend into an arbitrary shell.
- PX4-native failure expansion:
  - only add official/freshly proven failure surfaces one at a time; do not treat demo degradation as PX4 physical failure.

## Structural Foundation Stabilization - 2026-07-18

### Locked Facts

- The user explicitly paused feature expansion and requested foundation-first structural correction.
- Current scope is the generic `/home/coco/sim_plane` platform only.
- `main` and `origin/main` start aligned at `a680858`; the worktree was clean before this frontier.
- Existing behavioral and acceptance semantics are frozen unless fresh contradictory evidence and explicit user approval open a separate contract review.

### Current Question

- Can the current platform become repository-portable, contract-driven, concurrency-safe, and easier to maintain without changing its proven runtime behavior?

### Evidence-Backed Structural Defects

- Acceptance matrices reference ignored `runs/` artifacts, so a fresh clone does not carry its frozen reference evidence.
- CLI and modules derive roots from `__file__`, globally `chdir`, and depend on repository-external resources that are not packaged.
- Scenario normalization has no schema version, unknown-field rejection, or backend/adapter option validation.
- Composite backends import helpers from other concrete backends and PX4 SIH stores private runtime handles inside the scenario dictionary.
- Artifact completion is inferred from file presence; no explicit active/completed marker or cross-process lock protects inspectors from in-progress runs.
- Acceptance implementations duplicate shared reference, regression, delta, and retention logic.
- `px4_sih.py` defines `build_notes()` twice; the first definition is dead.
- Objective platform health output includes a hard-coded product roadmap that can become stale independently of health facts.

### Current Frontier

1. Version-controlled compact acceptance baselines.
2. Unified platform resource paths.
3. Versioned scenario contract and inheritance.
4. Atomic artifact lifecycle and coordination.
5. Incremental shared runtime/acceptance extraction.
6. CLI, health, wrapper-script, and documentation source-of-truth cleanup.

### Forbidden Actions

- No external workspace changes.
- No heavy backend migration or new backend.
- No acceptance weakening.
- No deletion of valid `runs/` evidence.
- No broad behavior refactor before portable baseline and scenario contracts are established.

### Promotion Gate

- Preserve current names, commands, metrics, topics, goals, and thresholds.
- Add focused static/unit evidence after each structural phase.
- Run heavy simulator acceptance only after structural phases are complete and only where needed to prove no runtime drift.

### Newly Locked This Round

- Acceptance baselines are now repository-tracked compact bundles and all four reference acceptance surfaces pass.
- Workspace/resource discovery is centralized and CLI operation no longer depends on a global `chdir`.
- Scenario contract v1 is enforced before backend startup; all checked-in scenarios load and all inherited scenarios preserve their pre-refactor effective payloads.
- `scenario_generator.py` previously emitted `launch_flightgear` and `gazebo_gui`, but those backends consume `headless`; the generator now emits the actual contract field.
- Managed artifacts now have atomic allocation/writes, a process lock, explicit `.running`/`.complete` markers, and backward-compatible legacy completion detection.
- Active artifacts are clean and unprunable during hygiene scans and are excluded from latest acceptance selection; crashed managed artifacts remain visible and unprunable for review.

### Newly Demoted This Round

- Scenario inheritance no longer carries a behavior-drift risk: all 16 converted child scenarios match their previous effective payloads after removing only the new schema/source metadata.
- The previously observed concurrent hygiene noise is no longer attributable to user timing discipline; active ownership is now machine-detectable.

### Only Question Next Round

- Does the completed structural extraction pass the full `271`-test suite in a normal localhost-socket environment and preserve fresh lightweight runtime, latest acceptance, hygiene, and health behavior?

### Forbidden Next Round

- Do not redesign backend behavior during closure validation.
- Do not change thresholds, topics, goals, timing, or scenario behavior to obtain a pass.
- Do not run artifact inspectors concurrently with commands writing under `runs/`.
- Do not patch around sandbox `socket()` denial; rerun socket-dependent tests in a normal local environment.

### Structural Extraction Closure Evidence

- Shared runtime extraction is complete and focused runtime tests pass `40/40`:
  - `sim_plane/backends/px4_common.py` owns shared PX4 process and telemetry mechanics;
  - `sim_plane/backends/ros_runtime.py` owns shared ROS environment and shutdown mechanics;
  - `ego_runtime.py`, `marsim_runtime.py`, `fast_lio_runtime.py`, and `planner_composition_runtime.py` own their respective composition mechanics;
  - concrete backend modules no longer import execution helpers from other concrete backend modules;
  - backend-specific command order, environment, readiness, timeout, topic, and verdict logic remain in their owning backend.
- Shared acceptance/report extraction is complete:
  - common artifact selection, ordering, history, and retention moved to `acceptance_common.py`;
  - each acceptance surface retains its own scenario rows, metrics, and thresholds;
  - JSON reports use atomic replacement and JSONL history uses a file lock.
- Source and contract checks are green:
  - Python AST syntax `111/111`;
  - JSON syntax `48/48`;
  - scenario contract `35/35`;
  - shell syntax and `git diff --check` passed;
  - no duplicate top-level definitions remain.
- Repository-tracked reference evidence is green:
  - planner acceptance `4/4`;
  - platform acceptance `21/21`;
  - PX4 failure acceptance `1/1`;
  - quadrotor exam acceptance `8/8`;
  - reports are retained under `/tmp/sim_plane_validation/` so this proof does not modify historical `runs/` evidence.
- The sandboxed full unit run executed `271` tests. `252` completed normally; the remaining `19` raised `PermissionError` exactly at localhost socket creation across dashboard, doctor/Gazebo probe, ROS runtime/backend, and ROS master tests. No code assertion failed.

### Newly Locked This Round

- Runtime extraction is no longer the implementation frontier; it is complete under focused and static evidence.
- Acceptance reference portability is proven from tracked baselines, independent of ignored source artifacts under `runs/`.
- The only unresolved validation fact is whether the `19` socket-dependent tests pass outside the network-isolated sandbox.

### Newly Demoted This Round

- The `19` full-suite errors are not evidence of a product defect: all stop at sandbox-denied `socket()` creation, and no assertion or backend behavior failure appears after that boundary.
- No further preventive refactor is justified before the normal-socket rerun produces contradictory evidence.

### Current Frontier

1. Rerun the complete unit suite with localhost sockets available.
2. Sequentially run a fresh demo, fast live smoke, and the smallest representative suite/fuzz checks.
3. Run latest acceptance only after runtime writers finish.
4. Run artifact hygiene and platform health last.
5. Remove repository-local cache/build residue outside `runs/`, then inspect the complete diff and worktree.

### Promotion Gate

- Full unit suite passes without socket-related skips or code changes, or any failure is classified to its earliest concrete source.
- Fresh lightweight runtime and latest acceptance remain green without changing contract semantics.
- Artifact hygiene reports no active/stale managed residue caused by this round.
- Final static checks and documentation/source consistency pass, and no external workspace was modified.

### Closure Audit Reopened By Fresh Evidence

#### Newly Locked This Round

- The extracted backend runtime modules have no reproducible command-order, environment, topic, timeout, shutdown, or verdict drift under the dedicated read-only review.
- The following are current-repo defects with direct reproductions and are independent of localhost socket denial:
  - an `ArtifactWriter` can append after `.complete`, while process log readers are daemon threads that are not joined;
  - atomic replacement forces `0644`, widening an existing private file and exposing new `scenario.json` adapter environment data on multi-user hosts;
  - allocation creates an empty artifact directory before the writer lock, while hygiene considers an empty directory prunable;
  - lifecycle inspection opens `.artifact.lock` with append access even when a completed artifact can be classified without any lock probe;
  - baseline verification treats missing metadata as success and does not require the complete artifact/report checksum set;
  - baseline metadata calls freeze-time `HEAD` the artifact `source_commit`, which is false for artifacts that predate that commit;
  - acceptance report publication is a multi-file read/write/prune sequence with no transaction lock;
  - quadrotor-exam source evidence is no longer protected from suite retention after moving the live reference to `baselines/`;
  - latest selection filters only `scenario_name`, so a newer wrong backend/vehicle artifact can hide a valid candidate;
  - waypoint aliases can pass validation but diverge between demo execution and KPI evaluation;
  - process-adapter explicit null values and `shell=true` plus list commands can pass validation and fail or misexecute later;
  - an inherited parent schema version can be overwritten by a child before validation;
  - range/safety cross-field bounds are incomplete;
  - scenario generator workdirs and upstream manifest defaults still depend on caller cwd;
  - `list-adapters` invokes unrelated backend validation and can fail before listing adapters;
  - planner evidence documentation and local-only evidence links are not aligned with repository-portable source facts.

#### Newly Demoted This Round

- The first closure PASS set is valid evidence for the paths it exercised, but it is not proof against the newly reproduced concurrency, permission, provenance, and negative-contract cases.
- Localhost socket denial is not the cause of any defect listed above and cannot be used to defer them.
- Runtime extraction itself is no longer a suspect branch unless a new targeted regression contradicts the dedicated audit.

#### Current Frontier

1. Make artifact completion immutable, join registered output threads, preserve file privacy, and close the allocation/hygiene and read-only inspection races.
2. Make tracked baseline metadata strict and truthful, lock acceptance report transactions, protect source evidence, and filter latest candidates by full identity.
3. Close scenario validation gaps without changing any checked-in effective scenario.
4. Finish cwd-independent generator/sync paths, decouple adapter listing, and correct source-of-truth documentation/console metadata.
5. Rerun focused concurrency/negative tests, all non-socket tests, fresh lightweight runtime and acceptance, then normal-socket validation when approval infrastructure permits it.

#### Forbidden Next Round

- Do not alter acceptance thresholds, regression budgets, KPI definitions, scenario targets, backend commands, topics, or timing.
- Do not turn late artifact writes into silent evidence loss without first waiting for registered producers.
- Do not claim an artifact-producing git revision when it was not recorded by the artifact.
- Do not delete or refresh source artifacts merely to make provenance fields look complete.
- Do not change external workspaces or valid historical simulation artifacts.

#### Promotion Gate

- New tests reproduce each defect before or alongside its fix.
- Checked-in scenario effective payload equivalence remains `16/16` for inherited scenarios and all `35/35` scenarios validate.
- All four tracked reference and latest acceptance surfaces remain green with unchanged gates.
- Completed artifacts are immutable, readable from read-only storage, and protected from concurrent hygiene during allocation.
- Concurrent acceptance writers cannot regress latest pointers or prune a report being published.
- Baseline provenance explicitly distinguishes unknown source revision from the commit at which the bundle was frozen.

### Structural Closure Continuation - 2026-07-19

#### Newly Locked This Round

- Artifact lifecycle, baseline/report publication, and scenario-contract defects listed above are fixed and their focused test groups pass.
- `list-adapters` now calls `collect_adapter_rows()` directly; backend registration is lazy, so an adapter-only listing no longer loads concrete backend modules or runs backend validation.
- CLI coverage has exactly two truthful states: `fixed_preset` and `hidden`; the unreachable `covered_count` field and stale hidden metadata for existing presets are removed.
- `docs/planner_validation_matrix.md` now matches every tracked planner baseline path and metric in `configs/planner_acceptance_matrix.json`.
- README and the English/Chinese probe guides now identify `runs/manual_probes/` evidence as local ignored evidence rather than repository-portable proof.
- Focused evidence after these edits: backend tests `22/22`, console/adapter-list tests `13/13`, adapter-only import isolation PASS, and `git diff --check` PASS.

#### Current Question

- Does the complete accumulated structural batch preserve all static, non-socket unit, fresh lightweight runtime, latest acceptance, hygiene, and health surfaces without changing frozen behavior or acceptance semantics?

#### Run Order

1. Static syntax, JSON, scenario-contract, shell, and source-consistency checks.
2. All unit tests that do not require localhost socket creation; socket-dependent tests remain an environment validation item.
3. Fresh `basic_takeoff`, fast/default live smoke, representative suite, and seeded fuzz, sequentially.
4. Four latest acceptance surfaces with retention disabled for this audit.
5. Artifact/manual-probe hygiene and platform health only after all writers stop.
6. Remove generated cache/build residue, inspect process state and final diff; do not commit or push.

#### Forbidden This Round

- No threshold, KPI, topic, goal, timing, backend command, or scenario-behavior changes.
- No concurrent artifact inspector while a runtime command writes under `runs/`.
- No external workspace edits, historical artifact deletion, commit, or push.

### Closure Validation Result - 2026-07-19

#### Fresh Evidence

- Static: Python AST `112/112`, JSON `140/140`, scenario contract `35/35`, shell syntax `42/42`, duplicate top-level definitions `62/62`, tracked baseline checksums `31/31`, CLI parser `23` subcommands, documentation consistency, and `git diff --check` all passed.
- Unit: full discovery found `289` tests; `271/271` non-socket tests passed. The remaining `18` exact cases all fail at sandbox-denied localhost `socket()` creation; the required unsandboxed rerun was rejected by the approval service with HTTP `503`, so no code workaround was applied.
- Fresh runtime: `basic_takeoff` passed; `live-smoke --profile fast` passed; `demo_degradation_suite` `6/6` passed; seeded fuzz `demo_seeded_fuzz_20260528` `7/7` passed.
- Cross-directory startup: from `/tmp`, `python3 -m sim_plane list-adapters` passed and resolved the platform home to `/home/coco/sim_plane`.
- Latest acceptance: planner `4/4`, platform `21/21`, PX4 failure `1/1`, and quadrotor exam `8/8` passed with unchanged contracts.
- Reference acceptance: planner `4/4`, platform `21/21`, PX4 failure `1/1`, and quadrotor exam `8/8` passed.
- Hygiene: `1251` complete artifacts, `0` active, `0` stale/incomplete, `0` attention; manual probes `2` retained and `0` stale.
- No external workspace was touched; no simulator process or `.running` marker remains; generated cache residue outside `runs/` is clean.

#### Environment-Limited Results

- `platform-health` status is `failed` only because its `doctor` component reaches the same sandbox `socket()` denial; its other `7` components and all acceptance summaries passed. This is not treated as a product fix target under the forbidden socket-workaround rule.
- `autotest-pack --profile fast` has `7/8` steps passed; its only failure is the same `doctor` exception.
- One audit `run-suite` invocation was intentionally corrected after it used the default report retention and pruned `runs/suites/demo_degradation_suite_20260607_193552_451800`; the underlying scenario artifacts remain, but the old report directory was not recoverable from the summary-only history. All subsequent report-producing commands used `--keep-last-reports 0`.

#### Final Conclusion

- The current structural correction frontier is complete under the available environment evidence.
- The only unresolved validation item is a normal-host localhost-socket rerun of the 18 isolated tests, doctor, platform-health, and the first autotest step. No acceptance or runtime contract defect was found in the available environment.

### Resume Attempt - 2026-07-19

- Rechecked the worktree, active markers, cache residue, and diff: no new runtime process, `.running` marker, cache residue, or diff-check failure was found.
- Retried the exact unsandboxed full-unit command once; the approval service again returned HTTP `503` before process creation. No files or acceptance contracts were changed in this resume attempt.
- The next valid action remains the same normal-host socket rerun; do not reopen structural patches or fabricate socket results inside the restricted sandbox.

### Resume Attempt 2 - 2026-07-19

- Current worktree checks remained clean: no active artifact, cache residue, or diff-check failure.
- A third request for the exact unsandboxed full-unit command was rejected before process creation because the approval service again returned HTTP `503`.
- No code, scenario, acceptance contract, or historical artifact was changed; the structural frontier remains complete and the normal-socket rerun is the sole external prerequisite.
- A later user-requested retry returned the same approval-service HTTP `503`; the test process again did not start.

### Normal-Host Socket Closure - 2026-07-19

- The user ran the exact required command directly on the normal host:
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest`.
- Result: `Ran 289 tests in 17.370s` and `OK`.
- The printed `baseline a_star_minimum_snap is not runnable yet: status=planned` message is expected output from the negative CLI contract test; it did not produce a test failure.
- This confirms the previous 18 errors were caused by the restricted Codex sandbox's socket policy, not by product behavior.
- The structural foundation frontier is now closed with no remaining validation blocker. No acceptance threshold, runtime contract, scenario behavior, or external workspace was changed to obtain this result.

### Resume Attempt 3 - 2026-07-19

- The approval service briefly created the unsandboxed full-unit process, but its result stream disconnected before any test summary was returned.
- Post-check found no active test/simulator process, no artifact lifecycle marker, and no report that could establish PASS or FAIL. The temporary Python cache residue was removed.
- This attempt is inconclusive, not a pass; no code or acceptance contract was changed.

### Resume Attempt 4 - 2026-07-19

- A narrower request covering only the 18 socket-dependent tests was also rejected before process creation because the approval service returned HTTP `503`.
- Final state remains clean (`.running=0`, cache residue `0`, `git diff --check` passed). Operator execution in a normal terminal is now the only remaining evidence path.

### Operator Evidence Reconciliation - 2026-07-19

- The user supplied fresh normal-terminal output for the exact command:
  `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest`.
- The authoritative result is `Ran 289 tests in 17.370s` followed by `OK`.
- This supersedes the earlier inconclusive/rejected approval attempts. The `a_star_minimum_snap ... status=planned` line is expected negative-contract output, not a failing test.
- Any later parallel resume notes that still describe the socket rerun as outstanding are stale relative to this operator evidence. The socket blocker is closed, and the structural foundation frontier is complete.
- Generated Python cache residue observed after the operator/parallel attempts was removed; no `runs/` evidence was touched.

### Release Closure Frontier - 2026-07-20

#### Locked Facts

- The accumulated structural correction batch passed the normal-host full unit suite: `289/289` tests, result `OK`.
- Static, scenario-contract, fresh lightweight runtime, latest/reference acceptance, artifact hygiene, process, and residue checks are already green as recorded above.
- Compact acceptance bundles exist locally under `baselines/`, but they are still untracked; therefore repository portability is implemented but not yet proven from version history.
- The accumulated batch remains uncommitted and unpushed.

#### Current Question

- Is the complete accumulated diff internally consistent, free of unintended behavior/acceptance changes, and ready to be frozen as one repository revision that can reproduce reference acceptance from a clean checkout?

#### Allowed Actions

1. Review the complete diff by contract area: paths/resources, scenario schema, artifact lifecycle, baseline/acceptance, backend runtime extraction, CLI/console, tests, and documentation.
2. Fix only directly evidenced release-blocking defects that preserve effective scenarios and frozen runtime/acceptance semantics.
3. Commit and push the reviewed batch, including compact `baselines/` bundles.
4. Validate a clean temporary checkout against scenario validation, unit tests, and repository reference acceptance.

#### Forbidden Actions

- Do not alter acceptance thresholds, regression budgets, KPI definitions, scenario targets, backend commands, topics, or timing.
- Do not perform broad CLI/web/documentation decomposition inside this already validated batch.
- Do not touch `/home/coco/sim_plane_ws`, unrelated projects, or valid historical `runs/` evidence.
- Do not describe local untracked baselines as clone-portable evidence before commit and clean-checkout proof.

#### Promotion Gate

- Complete diff review finds no unresolved correctness, provenance, secret, generated-file, or boundary violation.
- `baselines/` and all required source/test/docs changes are present in the committed tree.
- Clean-checkout scenario validation, full unit suite, and four reference acceptance surfaces pass without relying on ignored `runs/` artifacts.
- Remote push is confirmed, or any environment/network-only inability is reported separately from repository correctness.

### Pre-Commit Read-Only Audit Findings - 2026-07-20

#### Newly Locked Facts

- All four current reference surfaces pass and all 31 compact baseline bundles match their retained source payloads, but malformed empty acceptance matrices can currently pass with zero rows.
- Matrix `source_artifact` / `source_reference_report` values are not yet checked against the corresponding baseline metadata identity.
- Historical source artifacts do not record their producing Git revision. Their `source_commit=null` state is truthful and must not be fabricated; future artifacts need source-revision capture at creation time.
- Scenario v1 still accepts unsupported mission types, missing goal coordinates, non-string adapter environment values, and out-of-range UDP ports.
- `manual_probe_root_name` and acceptance `matrix_name` can escape their intended output roots when supplied by an external caller.
- Manual probes lack an active lifecycle lock, so concurrent hygiene can classify and prune a probe while it is still writing.
- Default PX4 discovery can select mutable checkouts outside `/home/coco/sim_plane_ws`; only explicit user paths and the managed workspace default are valid automatic inputs.
- Suite variants do not drain registered background log threads before completing their artifacts.
- Process cleanup returns early when a process-group leader has exited, even if descendants in the group remain alive.
- Wrapper and documentation review found concrete interface drift: visual wrappers without `--visualize`, showcase artifact-root propagation loss, status-only upstream sync writes, unknown upstream names silently succeeding, and demo-only surfaces described as stronger evidence than they provide.

#### Demoted Findings

- Absolute `/home/coco/...` strings inside frozen baseline payloads are historical observations, not runtime path dependencies or credentials. Preserve exact payload/checksum evidence and document the limitation rather than rewriting history.
- ROS/Gazebo free-port selection is not a release blocker because formal heavy runs remain serial; do not claim parallel heavy-backend support.
- Broad CLI/web/docs decomposition remains outside this patch batch.

#### Patch Frontier

1. Fail closed on malformed acceptance coverage and bind matrix source identities to baseline metadata.
2. Close scenario-contract and output-root traversal gaps.
3. Add manual-probe lifecycle protection, suite thread draining, descendant process-group cleanup, and managed-only PX4 fallback discovery.
4. Correct wrapper/sync/documentation contracts and record future source revisions honestly.
5. Run focused reproductions first, then the complete release validation matrix.

#### Forbidden During Fixes

- No acceptance threshold, regression budget, KPI, topic, goal, timing, or simulator command changes.
- No invented source commit for historical artifacts.
- No external workspace edits and no deletion of valid `runs/` evidence.

### Interrupted Patch Resume - 2026-07-21

#### Freshly Reconciled State

- The primary session JSONL, repository diff, supervisor ledger, and process state agree on the interruption boundary.
- The scenario/acceptance fail-closed patch, output-root containment patch, and first manual-probe lifecycle patch are present in the worktree.
- Suite thread draining, descendant process-group cleanup, managed-only PX4 discovery, wrapper/sync consistency, evidence wording, and future source-revision capture are not yet implemented.
- No simulator/ROS/PX4 process, managed `.running` marker, or partially running formal validation remains.

#### Resume Order

1. Syntax-check and focused-test the already written partial patch.
2. Correct any patch-local regression before adding more changes.
3. Implement the remaining locked findings only.
4. Run focused regression groups, then the full release validation and clean-checkout proof.

### Interrupted Patch Resume Reconciliation - 2026-07-21

#### Locked Facts

- The immediately preceding resume turn failed with HTTP `503` before any command or patch ran.
- The last successful code change in the prior interrupted turn made ROS launch shutdown share one total timeout budget and adjusted three backend test assertions; its focused test group has not run after that final adjustment.
- The worktree is still based on `a680858`; nothing from this structural batch has been staged, committed, or pushed.
- A separate project is currently using PX4, Gazebo, and ROS outside this repository. It is not `sim_plane` evidence and must not be stopped, inspected as an artifact source, or modified.

#### Current Frontier

1. Rerun the process/suite/backend focused group after the final ROS timeout edit.
2. Finish the already locked managed-PX4 discovery, upstream-sync, wrapper, documentation, and future Git-source capture fixes.
3. Review and validate the accumulated batch without changing frozen runtime or acceptance semantics.
4. Commit, push, and prove reference acceptance from a clean checkout only after all gates pass.

#### Forbidden Actions

- Do not run shared PX4/Gazebo/ROS integration commands while the unrelated external stack is active.
- Do not touch `/home/coco/sim_plane_ws`, the external project's processes, or ignored historical `runs/` evidence.
- Do not add unrelated cleanup, feature work, broad decomposition, or acceptance relaxation to this release batch.

### Pre-Commit Release Validation Closure - 2026-07-21

#### Locked Facts

- The bounded release-blocker patch is complete. It covers fail-closed acceptance and source binding, strict scenario v1 validation, output-root containment, manual-probe lifecycle protection, suite producer draining, descendant process-group cleanup, managed-only automatic PX4 discovery, upstream-sync and wrapper contracts, honest future Git provenance, and evidence wording.
- Focused regression groups passed first at `42/42` and then at `64/64` tests.
- The full normal-host unit suite passed `307/307` in `18.213s`.
- Static and contract checks passed: Python AST `115/115`, JSON `140/140`, baseline JSONL `1066/1066` lines, checked-in scenarios `35/35`, inherited effective-payload equivalence `16/16`, shell syntax, duplicate top-level definition scan `62/62`, CLI parser `23` subcommands, documentation/wrapper consistency, and `git diff --check`.
- Fresh lightweight evidence passed without using the external PX4/Gazebo/ROS stack:
  - `runs/basic_takeoff_20260721_145529_589097`;
  - `runs/live_smoke/live_smoke_fast_20260721_145545_171882/report.json`;
  - `runs/suites/demo_degradation_suite_20260721_145551_189090/report.json`, `6/6`;
  - `runs/scenario_fuzz/demo_seeded_fuzz_20260528_20260721_145600_988441/report.json`, `7/7`;
  - `runs/suites/paper_quadrotor_exam_suite_20260721_145615_098660/report.json`, `8/8`.
- All four repository-reference surfaces and all four latest surfaces passed with unchanged thresholds: planner `4/4`, platform `21/21` with required nested planner acceptance, PX4 failure `1/1`, and quadrotor KPI/proxy `8/8`.
- Hygiene is clean: `1274` complete managed artifacts, `0` active, `0` stale/incomplete, `0` attention; manual probes have `2` retained and `0` stale entries.
- Platform health report `runs/platform_health/sim_plane_platform_health_20260721_145813_181154/report.json` has `7` passed components, `1` warning, and `0` failed components. The sole warning is the intentionally uncommitted Git worktree.
- No credential, file over `1 MiB`, symlink, external-project source, or active lifecycle marker was found in the release payload. The compact `baselines/` payload is about `932K` and contains `30` artifact bundles plus `1` report bundle.
- Current source and remote remain at `a680858`; this accumulated batch is not staged, committed, or pushed yet.

#### Hypotheses

- None remain for the implementation batch. Repository portability is still an unproven release property until the exact committed revision passes from a clean clone.

#### Current Frontier

1. Remove ignored Python cache residue outside `runs/` and perform the final staged-payload review.
2. Commit and push the complete structural batch, including `baselines/` and all required source/tests/docs.
3. From a fresh `/tmp` clone of the pushed revision, prove `35/35` scenario validation, the complete unit suite, all four reference acceptance surfaces, and one fresh demo artifact whose manifest records the new commit with `dirty=false`.
4. Confirm the remote revision and close this frontier.

#### Forbidden Actions

- Do not alter runtime behavior, acceptance thresholds/budgets, KPI definitions, scenario targets, topics, commands, or timing during release closure.
- Do not include ignored `runs/`, generated cache files, credentials, or external workspace content in the commit.
- Do not start heavy/shared PX4, Gazebo, ROS, MARSIM, FAST_LIO, or planner simulations for this clean-clone proof.

#### Promotion Gate

- The complete intended payload is committed and present on `origin/main`.
- A clean clone of that exact revision passes scenario validation, the full unit suite, and all four reference acceptance surfaces without relying on local ignored `runs/` history.
- A fresh demo manifest in the clean clone records the committed revision and `dirty=false`.

### Release Publication And Clean-Clone Proof - 2026-07-22

#### Locked Facts

- The complete structural and portable-acceptance payload was committed as `18c82c12e08fbcc704ebfc48159460ac54aaffa2` and pushed to `origin/main`.
- A new clone from `git@github.com:KWM925-ui/sim_plane.git` checked out that exact revision with no tracked worktree changes.
- Clean-clone scenario loading passed `35/35` and confirmed unique scenario names.
- The clean-clone full unit command `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest` passed `307/307` in `17.303s`. The printed planned-baseline parser error is the expected negative CLI contract test, not a test failure.
- Reference acceptance from repository-tracked `baselines/` passed without local historical `runs/` input:
  - `planner-acceptance`: `4/4` rows passed;
  - `platform-acceptance`: `21/21` rows passed and required nested planner acceptance passed;
  - `px4-failure-acceptance`: `1/1` row passed;
  - `quadrotor-exam-acceptance`: `8/8` scenes passed.
- The acceptance CLI uses reference mode by default; `--latest` is the only mode switch. An attempted explicit `--reference` was rejected by argparse before validation and created no evidence.
- Fresh clean-clone demo artifact `runs/basic_takeoff_20260722_151854_953731` passed. Its manifest records `source_control.commit=18c82c12e08fbcc704ebfc48159460ac54aaffa2`, `source_control.recorded=true`, and `source_control.dirty=false`.
- Remote verification returned `18c82c12e08fbcc704ebfc48159460ac54aaffa2` for `refs/heads/main`; all `123` compact baseline files are tracked.

#### Hypotheses And Blockers

- None remain for the structural release. The only pending repository change is this control-document record; it does not alter runtime, scenario, baseline, or acceptance behavior.

#### Frontier Status

- Structural foundation stabilization and portable acceptance release are closed.
- Do not reopen this frontier without fresh contradictory evidence.
- Any future functional optimization must start as a new bounded frontier after reading this closure record.
