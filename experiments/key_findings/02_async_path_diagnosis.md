# 02. Aegis reports asynchronous no-exception paths as constraint bugs; the others spend effort on them

**Status: SUPPORTED on soc** (the only design so far with such paths). Check again on the rest of the suite.

soc's clk_x domain has WNS -0.38 ns, but all 8 violating endpoints (`aux_q_reg[0..7]`) are clk_w -> clk_x paths
between asynchronous clocks with no CDC exception: a deliberately unsynchronized crossing. Static timing on such a
path is meaningless; the right fix is a synchronizer or an SDC exception, not a faster rewrite.

| soc, clk_x | Aegis | Vanilla | Dr. RTL |
|---|---|---|---|
| What it did with `aux_q_reg[*]` | listed all 8 in the **constraint audit** ("violating path between asynchronous clocks: missing or violated CDC exception"); never dispatched | rewrote the crossing (moved `+1` into a clk_w register `fast_q_inc`) | analyzer picked them as the top paths in **all 5 iterations**; built a lookahead incrementer on the async path |
| clk_x WNS | -0.38 (untouched) | -0.18 ("53% gain" on an invalid path) | -0.38 (no gain after 4 iterations) |
| Told the designer the constraints are wrong? | **yes** | no | no |

## Why it matters
A single-clock (or clock-unaware) optimizer reads the worst slack in the report and optimizes it. On a multi-clock
design the worst slack is often an asynchronous path that should not be timed at all. Aegis's per-domain selection
separates synchronous deficits from constraint findings, so it optimizes what can be optimized and reports the rest.

## Sources
soc run notes in `experiments/02_multiclock/results/runs/`; `work/v1/sel/selection.json` (`constraint_audit`) of the
Aegis run; `work/v*/drrtl/m*/iter.json` of the Dr. RTL run (critical_paths).
