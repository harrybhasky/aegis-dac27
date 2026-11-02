# 05. Dr. RTL's published percentages cannot be compared with ours

**Status: METHOD.** The paper must not put our % next to Dr. RTL's published %.

Dr. RTL measured with Synopsys Design Compiler; we measure with Yosys + ABC + OpenSTA on the same Nangate45 library
and 0.1 ns clock. The starting points differ greatly, so percentage gains are not comparable:

| Design | Dr. RTL baseline WNS (DC, paper Table) | Our baseline WNS (Yosys, synthesis-only) | Ratio |
|---|---|---|---|
| vending_machine | -0.27 | -23.50 | 87x |
| cpu_fsm | -0.82 | -7.80 | 9.5x |
| arm_cpu2 | -1.01 | -2.08 | 2.1x |
| cpu_pipe | -0.38 | -1.64 | 4.3x |
| tv80 | -1.31 | -2.17 | 1.7x |
| uart | -0.38 | -0.65 | 1.7x |
| ticket_machine | -0.23 | -0.26 | 1.1x |
| LSTM | -6.51 | -6.05 | 0.9x |

A weak starting point makes a large % easy (e.g. a friend's run reported -98% on cpu_fsm against Dr. RTL's -26%).
Our own numbers also did not reproduce that run (controller: -46% there vs -5% here), so it cannot be used either.

## What we do instead
Compare all configurations (Aegis, vanilla, Dr. RTL ported to our flow) against the **same** synthesis-only baseline
in one flow. Dr. RTL's published numbers may be quoted only as a labelled side note.

## Sources
Dr. RTL paper (`Reading/2604.14989v1.pdf`, results table); `aegis_agents/bench/results/baseline.md`.
