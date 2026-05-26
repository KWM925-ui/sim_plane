# sim_plane Supervisor Pack

Purpose: externalize the rolling supervisor state that should not live
only inside one chat thread.

Project:

- `sim_plane`

Workspace:

- `/home/coco/sim_plane`

Primary child session:

- `(not set yet)`

Objective:

- Keep `sim_plane` on a light-core path while proving real PX4 SIH usability first, then expanding one lab stack at a time under `/home/coco/sim_plane_ws`.

Read order at the start of every supervised round:

1. `supervisor_ledger.md`
2. `state_machine.md`
3. `child_execution_protocol.md`
4. `round_self_checklist.md`

If the round touches the human-follow simulation branch, also read:

5. `human_follow_collab_ledger.md`

Use rules:

- Treat `supervisor_ledger.md` as the live source of truth.
- Treat `human_follow_collab_ledger.md` as the cross-session source of truth for the human-follow simulation branch.
- Do not work from memory when the pack exists.
- Do not reopen branches already demoted by the ledger unless fresh
  evidence contradicts the ledger.
- Do not run formal validations or write new patches until the ledger
  explicitly allows them.
