# Round Self-Checklist

## Boundary Checks

- Did I reopen a ruled-out chain as if it were still equal-priority?
- Did I drift from the current frontier into a larger search space?
- Did I use a later readout as if it were an earlier producer?
- Did I write a hypothesis as a fact?
- Did I leave the round without narrowing the frontier?

## Grain-Size Checks

- Did I move the frontier one level earlier or narrower?
- If not unique, did I reduce the uncertainty to at most two adjacent
  candidates?
- Did I explicitly state why the losing candidate is downstream?

## Required Ledger Delta

Before closing the round, update:

- `Locked Facts`
- `Newly Locked This Round`
- `Newly Demoted This Round`
- `Current Frontier`
- `Only Question Next Round`
- `Forbidden Next Round`
- `Promotion Gate`
