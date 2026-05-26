# Supervisor State Machine

This state machine prevents a long-running task from sliding back into a
generic workflow.

## Global Invariants

- Fresh evidence only.
- No broad reset or revert.
- Facts, hypotheses, and inferences remain separated.
- Do not reopen ruled-out branches unless fresh evidence contradicts the
  ledger.

## Phases

### `S0: Startup Compliance`
Goal:
- establish repo or task state
- complete must-read items
- build first truth ledger
Promotion rule:
- first bounded frontier exists

### `S1: Earliest-Split Locking`
Goal:
- reduce broad subsystem suspicion to one bounded chain
Promotion rule:
- frontier narrowed to one local chain

### `S2: Producer-Chain Locking`
Goal:
- identify the earliest producer or writer layer inside the winning chain
Promotion rule:
- one chain wins, or only two adjacent candidates remain

### `S3: Writer/Branch/Hunk Locking`
Goal:
- lock the specific writer, branch, or hunk
Promotion rule:
- unique writer or branch locked, or two adjacent candidates remain

### `S4: Patch Candidate Formation`
Goal:
- form exactly one minimal patch candidate and one impact table
Promotion rule:
- candidate plus confirmation and falsification plan exist

### `S5: Low-Pollution Validation`
Goal:
- run one clean validation round after hygiene
Promotion rule:
- candidate confirmed or falsified cleanly

### `S6: Repeatability`
Goal:
- prove repeatability before widening
Promotion rule:
- repeated clean evidence exists

### `S7: Widening`
Goal:
- broader scenes or broader workload after baseline is stable
Promotion rule:
- no longer a one-case success

### `S8: Acceptance Packaging`
Goal:
- build the formal evidence package
Promotion rule:
- all blocking acceptance items are satisfied

## Current Phase

Current phase: `S8`

## Phase-Specific Allowed Actions

Allowed:
- read code
- read docs and upstream READMEs
- read logs
- patch project-local backend, runtime, and control-doc code for the current widening target
- run one bounded validation round and targeted tests for the current widening target
- update the ledger

Forbidden:
- broad multi-repo bring-up in parallel
- system-wide package churn without a locked blocker
- reopening the retired shutdown branch without fresh contradictory evidence
- widening the search space without narrowing the current frontier first
