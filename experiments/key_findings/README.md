# Key findings (paper points)

One file per point we may claim in the paper, each with its table, the runs it rests on, and its caveats.
Every number comes from a logged run (`aegis_agents/flow/runs/...`) or a cited source; nothing is estimated.

**Status:** `PRELIMINARY` = seen on too few designs or runs to claim yet; `SUPPORTED` = holds on all valid data so far;
`METHOD` = a methodology or validity point the paper must state.

| # | Finding | Status | Supports |
|---|---|---|---|
| [01](01_cost_efficiency.md) | Aegis reaches the same outcome as Dr. RTL at 1/6 (soc) to 1/3 (prim_fifo_async) of the LLM cost | PRELIMINARY (2 designs) | cost |
| [02](02_async_path_diagnosis.md) | Aegis reports async no-exception paths as constraint bugs; Dr. RTL and vanilla spend effort on them | SUPPORTED on soc | diagnosis |
| [03](03_vanilla_unverifiable_gains.md) | Unguarded vanilla's timing "gains" are never provably equivalent; 2 of 4 are functionally wrong | SUPPORTED (4 designs) | safety / need for gating |
| [04](04_drrtl_fifo_broken_synchronizers.md) | Dr. RTL's own dual-clock FIFO has synchronizers in the wrong clock domain | SUPPORTED | single-clock tools are CDC-blind |
| [05](05_published_numbers_not_comparable.md) | Dr. RTL's published % cannot be compared with ours: baselines differ by up to 87x | METHOD | fair comparison |
| [06](06_no_multiclock_benchmarks.md) | Existing LLM-RTL benchmarks contain almost no multi-clock designs | SUPPORTED (literature) | motivation, suite choice |
| [08](08_prim_fifo_async_locks.md) | prim_fifo_async: LLMs target the Gray logic; vanilla meets timing only via unverifiable Gray rewrites; Dr. RTL's SEC stops most; Aegis safe but conservative (no contract, text-level lock) | SUPPORTED (1 design) | safety + limitation |
| [09](09_afifo_vanilla_breaks_synchronizer.md) | afifo: vanilla meets timing by reading the first stage of a 2-flop synchronizer (depth 2 -> 1); simulation sees nothing; Aegis's lock + CDC re-check reject it | SUPPORTED (1 design) | safety, core claim |
| [10](10_aegis_conservatism_costs_timing.md) | Without proven Gray contracts, Aegis's locks reject even equivalent edits: on afifo Dr. RTL gets +0.20 ns on the read clock safely, Aegis +0.04 | SUPPORTED (2 designs), unfavourable | limitation / fix needed |
| [11](11_axil_cdc_drrtl_duplicates_synchronizer.md) | **axil_cdc: Dr. RTL promotes an SEC-passing, sim-passing rewrite that duplicates a synchronizer stage 5x (torn-transaction hazard); Aegis's lock + CDC re-check reject it** | SUPPORTED (1 design) | **core claim** |
| [12](12_lalit_report_assessment.md) | Lalit's report (interactive runs, cross-flow % vs Dr. RTL's published numbers, no logs): not usable as Aegis results; adopt his flattened re-synthesis check; he is a co-author | METHOD | method |
| [13](13_flattened_resynthesis.md) | Flattened re-synthesis: Dr. RTL's multi-clock WNS gain falls +16.7% -> +2.6%; (pre-fix) Aegis +7.6% -> +7.1% | PRELIMINARY | results |
| [14](14_metastability_injection_axil.md) | Metastability injection: axil_cdc Dr. RTL rewrite corrupts ~37% of words (10 seeds), original 0 | SUPPORTED | **core claim** |
| [07](07_validity_and_methodology.md) | Validity points: checker fix, EQY proof limit, session-limit contamination, skill leakage, protocol choices | METHOD | threats to validity |

Last updated 2026-10-18. Add a row whenever a new point appears; keep `experiments/LOG.md` as the chronological record.
