# 08. prim_fifo_async: the LLM goes for the Gray logic; vanilla gains unverifiably, Aegis's lock is conservative

**Status: SUPPORTED on 1 design.** OpenTitan `prim_fifo_async`; its critical paths start at synchronizer outputs and
run through the Gray-pointer decode and full/empty compares.

| prim_fifo_async | Aegis | Vanilla | Dr. RTL (port) |
|---|---|---|---|
| clk_wr_i WNS | -0.11 -> -0.11 | -0.11 -> **+0.01** | -0.11 -> -0.11 |
| clk_rd_i WNS | -0.09 -> -0.09 | -0.09 -> **+0.02** | -0.09 -> -0.09 |
| Area | -1.4% | +9.0% | -1.2% |
| Candidates touching locked CDC logic | 10/20 (all rejected) | 23/25 (promoted) | 22/25 (21 failed SEC; 1 promoted) |
| Final design EQY vs original | PASS | FAIL (20 partitions; sim 0 mismatches) | PASS |
| Gray one-bit-per-step property | unchanged | **unverified** (hand-written Gray next-value / decode) | unchanged (provably equivalent edit) |
| Cost | $2.82 | $2.24 | $7.62 |


## What it shows
1. **The LLM targets CDC logic on its own** when the critical path runs through it: 10/20 Aegis candidates, 23/25
   vanilla, 22/25 Dr. RTL candidates edited the locked synchronizer/Gray logic.
2. **Vanilla met timing only through unverifiable CDC-critical rewrites** (new Gray next-value function, Gray-to-binary
   of synchronized pointers, Gray-domain full/empty). Claim: "unverifiable", not "broken".
3. **Dr. RTL's SEC gate stopped most of these** (23/25 failed SEC). Its one promoted lock-touching edit is
   equivalent (fan-out replication of the full/empty compare) and safe. No "SEC-pass but CDC-unsafe" case yet.
4. **Aegis is safe but conservative here:** (a) Phase 1 proved no Gray contract for this design, so the Gray logic is
   immutable; (b) the lock is a text-level fingerprint, so it rejects even equivalent restructurings (it would have
   rejected Dr. RTL's safe edit). Both are limitations to state.

## Next step this motivates
Prove the Gray contract for prim_fifo_async (fix Phase 1 or add `cdc_annotations.json`). Then Aegis can accept
rewrites like vanilla's only if they keep the Gray property, which is the paper's strongest form of the claim.

## Sources
`flow/runs/prim_fifo_async/{aegis,vanilla,drrtl}.sonnet-5-5.r1/` (summary.json, final_verify.json gate/cdc/sim,
final_eqy logs, RUN_NOTES.md).
