# Child Execution Protocol

Follow this protocol every round until the ledger explicitly changes it.

## Round Start

1. Read `supervisor_ledger.md`.
2. Restate only:
   - locked facts
   - current frontier
   - forbidden actions
   - required output shape

## During The Round

1. Solve only the ledger's current question.
2. Prefer direct discriminating reads over broad exploration.
3. Do not re-prove already locked exclusions.
4. Do not drift into system-overview mode.
5. Classify new evidence as:
   - strengthens current frontier
   - contradicts ledger

## Output Contract

Use the exact section headers requested by the current round.
For critical technical points, prefer:

- `log field -> variable -> function -> code location -> branch meaning`

## Progress Standard

A round counts as real progress only if:

- the frontier shrinks
- or one branch is demoted
- or one producer, writer, branch, or hunk is uniquely locked

These do not count:

- broad summaries
- rephrasing prior conclusions
- same-granularity restatements

## Run/Patch Gate

No formal run and no new patch unless both:

- the phase allows it
- and the ledger explicitly allows it

## Round End

Before closing the round:

1. run the checklist mentally
2. update the ledger
3. only then emit the final structured answer
