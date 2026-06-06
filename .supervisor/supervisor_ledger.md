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

- Use the landed PX4 raw flight-log collection surface to tighten artifact-local ULog replay and reporting.
- Keep automatic PX4 `.ulg` discovery, collection, artifact indexing, and dashboard summarization as a completed platform surface.
- Keep current validation semantics intact; do not weaken acceptance gates or add unrelated heavy backends.
- Keep generic custom-algorithm ingress central:
  - `external_command` for PX4-side host processes.
  - `ros_command` for ROS planner/perception processes.
  - `mavsdk_action_takeoff` and `mavsdk_failure_injection` for MAVSDK/PX4 surfaces.
- Keep frontend/backend command descriptions aligned with the actual CLI.

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

- Answered: existing PX4 backends now automatically attempt to collect and index PX4 `.ulg` logs into each run artifact without changing acceptance semantics or adding backend sprawl.

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

## Promotion Gate

- Metadata/unit tests prove every console action has workflow/evidence/concurrency fields.
- Dashboard static guard passes.
- Focused dashboard/console tests pass.
- Full unit suite passes or any failure is explicitly unrelated and artifact-backed.

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
