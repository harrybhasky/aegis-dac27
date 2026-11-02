# 04. Dr. RTL's own dual-clock FIFO has its synchronizers in the wrong clock domain

**Status: SUPPORTED** (Phase 1, deterministic; no LLM).

`benchmarks/Dr_RTL/rtl_dataset/FIFO.v0.v` has two clocks (`clk_in`, `clk_out`), but Dr. RTL's `syn.tcl` creates a
single clock. Its pointer "synchronizers" (`read_sync`, `write_sync`) and the flush synchronizer register each signal
twice in the **source** domain, not the destination, so every crossing is effectively unsynchronized.
With both clocks constrained (`drrtl_fifo_2clk`), Aegis Phase 1 reports **142 unsynchronized crossings, 0
synchronizers**, before any optimization.

## Why it matters
A benchmark used to evaluate an LLM RTL optimizer contains a real CDC bug that its single-clock flow cannot see.
This is direct evidence that single-clock tooling is blind to CDC correctness, which is Aegis's motivation.
Report it carefully and factually (a pre-existing property of the released RTL), not as a criticism of the authors.

## Sources
`aegis_agents/flow/work/drrtl_fifo_2clk/phase1/phase1_report.json`, `crossings.json`; `benchmarks/README.md`.
