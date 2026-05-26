# Platform Blueprint

## 1. Goal

Build a UAV algorithm simulation platform that is:

- strong in capability,
- broad enough for algorithm work,
- feasible on the current machine,
- simple to install and use,
- simple to integrate with custom code,
- and light enough that the default path is not painful.

This means the platform should not start from a "max fidelity at all times" mindset. It should start from a "light by default, richer only when needed" architecture.

## 2. Product Positioning

This repository should become a practical middle layer between:

- low-level flight-stack simulation,
- algorithm development code,
- scenario definition,
- evaluation and replay,
- and optional user-facing visualization.

It should not initially try to replace every upstream simulator feature. It should orchestrate them cleanly and hide complexity behind a stable local interface.

## 3. Design Principles

### 3.1 Light First

- The default path should boot quickly and run headless.
- GUI and 3D rendering should be optional, not mandatory.
- Middleware should be optional unless it materially improves the first-use experience.

### 3.2 Strong Core, Not Heavy Core

- Keep the flight-stack contract realistic by using PX4-based backends.
- Keep algorithm integration simple by using a small adapter API.
- Keep scenario and evaluation logic local to this repo instead of scattering it across simulator-specific scripts.

### 3.3 Dual-Layer Validation

- Fast loop for algorithm iteration.
- Richer loop for scene, sensor, and integration checks.

If one backend tries to serve both goals, it usually becomes slow, fragile, and hard to maintain.

### 3.4 One Stable Entry Surface

Users should not need to remember backend-specific startup commands. The platform should eventually present one consistent local surface such as:

- `sim-plane up`
- `sim-plane run scenario/basic_takeoff`
- `sim-plane eval scenario/mission_01`

The specific command names can change later, but the principle should stay.

## 4. Requirement Supplement

These are the requirements that are worth adding even if the user did not explicitly list them yet.

### 4.1 Functional Requirements

- Single-vehicle simulation must be available first.
- Quadrotor is the current product mainline; fixed-wing remains an architectural compatibility option only if that scope is explicitly reopened.
- The platform must expose telemetry, state, and control channels to custom algorithms.
- The platform must support named scenarios with reproducible initial conditions.
- The platform must record run artifacts, including backend type, scenario, logs, and evaluation summary.
- The platform must support headless execution for batch tests.
- The platform should support optional GUI monitoring.
- The platform should allow fault or disturbance injection later, such as wind, GPS degradation, or sensor dropout.
- The platform should support replay or deterministic re-run where upstream backend behavior allows it.

### 4.2 Integration Requirements

- User algorithms should plug in through a narrow adapter instead of binding directly to every simulator detail.
- `MAVSDK` should be the first adapter target because it is simpler than a ROS-first path for command/control integration.
- ROS should be optional and isolated behind an adapter boundary if later required for perception or high-rate integration.
- Scenario configuration should live in simple local files such as YAML or TOML rather than hidden shell fragments.

### 4.3 Usability Requirements

- One-command start for the normal path.
- Sensible defaults for backend, vehicle, log path, and scenario path.
- Clear error messages when a backend is unavailable on the current host.
- A fast smoke-test scenario for sanity checking the install.
- Minimal manual wiring for ports, parameters, and environment variables.

### 4.4 Evaluation Requirements

- Basic metrics should exist from the start: startup success, arm success, takeoff success, mode switch success, trajectory tracking error, and end-state verdict.
- Scenario verdicts should be machine-readable.
- Regressions should be easy to compare between runs.
- The platform should later support KPI plugins instead of hardcoding every metric in the runner.

### 4.5 Non-Functional Requirements

- The default path should stay usable on the current Ubuntu 20.04 host with 14 GiB RAM.
- Optional richer paths may require more resources, but they must not block the MVP.
- Cold start should be short enough for iterative development.
- Dependency sprawl should stay limited.
- The core should remain debuggable from logs and CLI output alone.

## 5. Recommended Architecture

## 5.1 Layers

### Layer A: Orchestrator

Owns startup, shutdown, configuration loading, scenario selection, artifact paths, and evaluation dispatch.

Recommended implementation:

- Python-based CLI
- lightweight config files
- no mandatory web service in phase 1

### Layer B: Backend Adapter

Wrap each simulator backend behind one local interface:

- start
- stop
- reset
- load vehicle
- load scenario
- expose connection info
- collect artifacts

Backends should be swappable without rewriting algorithm code.

### Layer C: Algorithm Adapter

Defines how local user code talks to the simulated vehicle.

Recommended first adapter:

- `MAVSDK`

Optional later adapters:

- `ROS`
- direct MAVLink
- custom perception bridges

### Layer D: Scenario System

A scenario should define:

- backend
- vehicle type
- map or world
- initial pose
- environment modifiers
- mission or target
- evaluation profile

This should be local schema, not simulator-specific shell commands.

### Layer E: Evaluation

Consumes telemetry and logs, then emits:

- pass/fail
- metric summary
- artifact index
- notable warnings

### Layer F: Visualization

Optional, not required for every run:

- QGroundControl
- backend-native UI
- later a light local dashboard

## 5.2 Default Backend Stack

### Primary Default: PX4 SIH

Why:

- official PX4 docs describe SIH as lightweight, headless, and zero-dependency,
- it avoids external simulator processes,
- it is the fastest path to a usable closed loop,
- it supports both quad and airplane examples in current PX4 docs.

Best use:

- controller logic,
- offboard control flow,
- mission logic,
- telemetry pipeline,
- regression smoke tests,
- CI-friendly validation later.

Limitations:

- not the right default for rich 3D sensing,
- not the right default for obstacle-rich perception testing.

### Secondary Dynamics Backend: PX4 + JSBSim

Why:

- it gives richer flight-dynamics behavior than the simplest loop,
- it gives the current quadrotor mainline a FlightGear-backed viewer route without making a heavy scene simulator mandatory.

Best use:

- flight-dynamics-sensitive testing,
- scenario replay where a full 3D world is not yet needed.

### Transitional Rich Backend on Current Host: PX4 + Gazebo Classic

Why:

- current host is Ubuntu 20.04,
- official Gazebo Harmonic binary support is for Ubuntu 22.04 and 24.04,
- PX4 docs still document Gazebo Classic usage and headless mode,
- Gazebo Classic supports more vehicle types and richer scene interaction than SIH.

Best use:

- camera and object-rich scenarios,
- visualization-heavy debugging,
- more realistic scene interaction before an OS upgrade.

Important caveat:

- Gazebo Classic is already end-of-life, so it should be treated as a bridge, not the forever core.

## 5.3 Integration Stack

### Algorithm API First Choice: MAVSDK

Why:

- PX4 docs explicitly say MAVSDK is easier to learn than ROS 2 and has a more stable API,
- it is a better fit for low-bandwidth command/control and telemetry integration,
- it keeps the phase 1 user experience simple.

### ROS Policy

ROS should not be the mandatory core in phase 1.

Reasons:

- ROS 1 Noetic reached end-of-life on `2025-05-31`,
- forcing ROS into the core path would add install and maintenance weight on Ubuntu 20.04,
- many control and mission workflows can start cleanly with MAVSDK first.

ROS can still be added later for:

- perception pipelines,
- high-rate sensor processing,
- richer robotics ecosystem reuse.

## 6. What Not To Choose As The Default

### Not Default: AirSim

Why not:

- Microsoft states no further updates will be made to the original AirSim and points users toward Project AirSim,
- Unreal-based workflows are heavier than needed for this repo's first goal,
- it is a poor fit for "simple install, simple use, light enough to run now" as the default baseline.

### Not Default: Gazebo Harmonic on This Host

Why not:

- official binary support targets Ubuntu 22.04 and 24.04,
- current host is Ubuntu 20.04,
- forcing an unsupported default would immediately reduce feasibility.

### Not Default: Mandatory QGroundControl

Why not:

- current QGroundControl `master` and `v5.0` docs list Ubuntu 22.04 and 24.04 as supported versions,
- older QGroundControl `v4.4.3` docs still documented Ubuntu 20.04 and later, which means compatibility on this host is possible but not the best default assumption for a new platform,
- the platform still needs a usable control surface even if QGC is absent.

QGC should be optional because it is still useful when available.

### Not Default: ROS-First Core

Why not:

- higher install and maintenance cost,
- weaker fit for the user's "simple access and implementation" requirement,
- unnecessary for the first useful closed-loop platform.

## 7. Suggested Repo Shape

Once implementation starts, a good local structure would be:

```text
sim_plane/
  AGENTS.md
  README.md
  .agent/
    PLANS.md
  docs/
    platform_blueprint.md
  sim_plane/
    cli/
    backends/
    adapters/
    scenarios/
    evaluators/
    artifacts/
  configs/
  scenarios/
  scripts/
  tests/
```

The exact paths can change, but the responsibility split should stay similar.

## 8. Suggested Phased Roadmap

### Phase 0: Repo Bootstrap

- lock architecture,
- lock backend selection policy,
- define scenario and artifact concepts.

### Phase 1: Lightweight MVP

- integrate `PX4 SIH`,
- add one local CLI entry,
- add `MAVSDK` adapter,
- add one smoke scenario,
- store artifacts and a verdict.

Success condition:

- one command can launch the backend, connect an algorithm adapter, execute a small control task, and write a result.

### Phase 2: Airplane and Better Dynamics

- add `JSBSim`,
- support airplane scenario selection,
- add evaluation for tracking and mode transitions.

### Phase 3: Rich Scene Backend

- add `Gazebo Classic` as optional on the current host,
- support headless and UI modes,
- add scene-aware sensor validation if required.

### Phase 4: Upgrade Path

- when the user is ready, consider Ubuntu 22.04 or 24.04,
- then promote modern Gazebo from optional to preferred rich-scene backend,
- optionally add a ROS 2 adapter if a clear requirement exists.

## 9. MVP Acceptance Criteria

The first meaningful version should satisfy all of the following:

- installs on the current machine without an OS upgrade,
- starts with one documented command,
- supports at least one vehicle end-to-end,
- exposes telemetry and control hooks for custom code,
- runs headless,
- saves artifacts,
- emits a machine-readable run verdict,
- and does not require ROS as a core dependency.

## 10. Next Bounded Action

The next best move is not to add a heavy simulator first. It is to implement a thin local runner around:

- `PX4 SIH`
- `MAVSDK`
- one simple scenario schema
- one evaluation output schema

That creates a real working backbone while keeping the platform light enough for the current machine.

## 11. External References

- PX4 simulation overview: `https://docs.px4.io/main/en/simulation/`
- PX4 SIH: `https://docs.px4.io/main/en/sim_sih/`
- PX4 JSBSim: `https://docs.px4.io/main/en/sim_jsbsim/`
- PX4 Gazebo Classic: `https://docs.px4.io/main/en/sim_gazebo_classic/`
- PX4 MAVSDK guidance: `https://docs.px4.io/main/en/robotics/mavsdk`
- Gazebo Harmonic install targets: `https://gazebosim.org/docs/harmonic/install_ubuntu/`
- Gazebo Classic EOL note: `https://classic.gazebosim.org/distributions`
- QGroundControl current install guide: `https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html`
- QGroundControl 4.4 install guide: `https://docs.qgroundcontrol.com/v4.4.3/en/qgc-user-guide/getting_started/download_and_install.html`
- ROS Noetic EOL notice: `https://ros.org/blog/noetic-eol/`
- AirSim repository notice: `https://github.com/microsoft/AirSim`
