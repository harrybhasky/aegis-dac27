# 10. Without proven contracts, Aegis's locks cost timing that Dr. RTL gets safely

**Status: SUPPORTED on 2 designs (afifo, prim_fifo_async).** Unfavourable to Aegis; must be addressed or stated.

| | afifo: Aegis | afifo: Dr. RTL | afifo: vanilla | prim: Aegis | prim: Dr. RTL | prim: vanilla |
|---|---|---|---|---|---|---|
| Read-domain WNS | -0.15 -> -0.11 | -0.15 -> **+0.05** | -0.15 -> +0.03 | -0.09 -> -0.09 | -0.09 -> -0.09 | -0.09 -> +0.02 |
| Write-domain WNS | -0.11 -> -0.11 | -0.11 -> -0.10 | -0.11 -> 0.00 | -0.11 -> -0.11 | -0.11 -> -0.11 | -0.11 -> +0.01 |
| Final EQY | PASS | PASS | FAIL | PASS | PASS | FAIL |
| CDC actually safe? | yes | **yes** | **no** (sync 2 -> 1, finding 09) | yes | yes | unverified |
| Gray contracts proven by Phase 1 | 0 | | | 0 | | |
| Aegis candidates rejected by lock / CDC false positive | 9 / 1 | | | 10 / 0 | | |

## Why
1. Phase 1 auto-proves Gray contracts only on async_fifo (and soc); on afifo and prim_fifo_async the Gray logic is
   therefore **immutable**, not contract-bound.
2. The lock is a text-level fingerprint of the locked cones, so it rejects equivalent restructurings that Dr. RTL's
   SEC gate accepts (and that are CDC-safe because the Gray registers' values are unchanged and still registered).
3. The CDC re-check's memory-coding false positive (finding 07) rejected one more safe candidate on afifo.

## Fix options (proposed, not done)
- Prove Gray contracts on afifo / prim_fifo_async (fix Phase 1's detection or add `cdc_annotations.json`).
- Accept an edit to locked logic when it is EQY-equivalent on the enclosing module and the CDC re-check passes
  (structural launch/sync intact), instead of rejecting any text change.
- Recognise per-word register arrays as FIFO storage in Phase 1.
Any of these changes Aegis's behaviour, so the finished Aegis runs would be re-run for consistency.

## Update 2026-11-02: second design (axis_async_fifo)
Dr. RTL (reproduced) final v1: worst-domain WNS -0.24 -> -0.11 ns, TNS -25.86 -> -26.32, area -3.1%, EQY PASS vs v0.
Automatic re-check flags it (lock_violation + cdc), manual audit says **CDC-safe**: the rewrite (a) recodes the FIFO
memory write as a per-entry generate block and the read as an even/odd mux, (b) rewrites `full_wr` into an equivalent
balanced compare. Pointers, Gray logic and synchronizers are untouched. All 32 CDC flags are `u.mem[i] ->
u.m_axis_pipe_reg[0]` (memory-recoding false positive, finding 07); the lock flag is the text-level checksum on full_wr.
Aegis on the same design promoted nothing. Source: flow/runs/axis_async_fifo/drrtl.sonnet-5-5.r1/{final_verify.json, rtl/v0 vs rtl/v1}.
Fixing the memory-coding false positive (recognise per-entry register arrays written under a pointer decode as storage)
is now the single most valuable Aegis fix; it would change Aegis behaviour, so finished Aegis runs would need re-running.
