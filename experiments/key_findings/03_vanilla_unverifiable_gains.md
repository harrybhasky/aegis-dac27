# 03. Unguarded vanilla's timing "gains" are never provably equivalent

**Status: SUPPORTED** on all 4 valid vanilla runs so far (3 single-clock Dr. RTL designs + soc).

| Design | Apparent WNS gain | Candidates passing EQY | Final design EQY vs original | Differential simulation | Verdict |
|---|---|---|---|---|---|
| ticket_machine | -0.26 -> -0.08 (+69%) | 0 / 25 | FAIL (5 partitions) | **2 mismatches** | functionally wrong |
| controller | -0.39 -> -0.33 (+15%) | 0 / 25 | FAIL (4 partitions) | **19 mismatches** | functionally wrong |
| uart | -0.65 -> -0.33 (+49%) | 0 / 25 | FAIL (3 partitions) | 0 mismatches | not proven equivalent |
| soc | -0.38 -> -0.18 (+53%) | 0 / 25 | FAIL (1 partition, `soc.aux_q`) | 0 mismatches | not proven; gain is on an async path ([02](02_async_path_diagnosis.md)) |

For comparison, Aegis's final designs on ticket_machine, controller and soc all pass EQY.

## Wording for the paper
Say "not proven equivalent" in general and "functionally wrong" only where simulation found a mismatch. Where
simulation is clean, the EQY failure may be a proof limit (partition-local induction cannot use invariants such as
`fast_q_inc == fast_q + 1`); it still fails the SEC requirement every configuration is held to.

## Sources
`final_verify.json` (sim) and `final_eqy/eqy_<top>.log` (failed partitions) in each vanilla run.
