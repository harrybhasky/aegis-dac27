# 13. Flattened re-synthesis: most of Dr. RTL's multi-clock WNS gain relies on module boundaries

**Status: PRELIMINARY (2026-11-02).** The Aegis rows below are the PRE-FIX Aegis runs (archived when queue_v2 starts);
re-check with the re-runs. Dr. RTL and vanilla rows are final.

Method: `bench/final_remeasure.py` re-synthesizes the original and the final design of every run with
`aegis_sta.py --flatten` (same ABC script, SDC, library; hierarchical SDC pins rewritten to the driver pin of the
flattened net), and reports the worst-domain WNS change. Idea from Lalit's report (key_findings/12).

| Multi-clock, 6 designs | Avg worst-WNS gain (hierarchical) | Avg worst-WNS gain (flattened) |
|---|---|---|
| Aegis (pre-fix) | +7.6 % | +7.1 % |
| Dr. RTL (reproduced) | +16.7 % | +2.6 % |
| Vanilla (3 designs, all EQY-fail) | +87.2 % | +72.1 % |

Per design (flattened WNS, original -> final): async_fifo Aegis -0.19 -> -0.16, Dr. RTL -0.19 -> -0.20;
axis_async_fifo Dr. RTL -0.16 -> -0.18 (hierarchical -0.24 -> -0.11); afifo Dr. RTL -0.15 -> -0.10 (survives),
Aegis -0.15 -> -0.11; soc all -0.38 -> -0.38 except vanilla -0.18; axil_cdc unchanged for both.

Caveat: flattening changes the baseline too (async_fifo -0.16 -> -0.19, axis_async_fifo -0.24 -> -0.16), so the
flattened column is a robustness check, not the primary metric. Source: flow/runs/*/*/final_remeasure.json.
