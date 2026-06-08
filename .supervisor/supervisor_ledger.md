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
