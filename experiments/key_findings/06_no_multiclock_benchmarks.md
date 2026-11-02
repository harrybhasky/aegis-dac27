# 06. Existing LLM-RTL benchmarks contain almost no multi-clock designs

**Status: SUPPORTED** (literature; details and citations in `paper/related_work_notes.md`).

- RTLLM v2.0: 2 of 50 designs are multi-clock; VerilogEval / RTL-OPT (36 designs) / Dr. RTL (20) / RTLRewriter:
  single-clock tasks.
- Some bug/assertion benchmarks filter clocks out explicitly (AssertLLM2: "Clock and reset signals are explicitly
  filtered" from mutation targets).
- No released benchmark of CDC-breaking but functionally equivalent rewrites of real multi-clock RTL was found.

## Consequence for the paper
There is no standard CDC suite to adopt, so we justify ours by provenance: Cummings' SNUG 2002 Gray FIFO
(`async_fifo`), Forencich's open-source IP (`axis_async_fifo`, `axil_cdc`, `eth_mac_1g_fifo`), OpenTitan
(`prim_fifo_async`), PULP common_cells (`cc_cdc_fifo_gray`), ZipCPU `afifo`, Dr. RTL's own FIFO with both clocks.
Our own `soc` is reported separately, not in headline averages.
