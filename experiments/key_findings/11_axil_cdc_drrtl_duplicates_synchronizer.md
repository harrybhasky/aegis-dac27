# 11. axil_cdc: Dr. RTL promotes an SEC-passing rewrite that duplicates a synchronizer stage

**Status: SUPPORTED (1 design); run in progress at time of writing; confirm it survives into the final design.**
This is the paper's core case: equivalent under SEC and simulation, unsafe in silicon, accepted by Dr. RTL.

## Original (Forencich `axil_cdc_wr`)
The write handshake flag crosses into `m_clk` through a 2-flop synchronizer
`s_flag_reg -> s_flag_sync_reg_1 -> s_flag_sync_reg_2`; one synchronized enable loads the whole transaction
(awaddr, wdata, awprot, wstrb) in the same cycle (a qualified-capture crossing).

## Dr. RTL's rewrite (iteration 1, minor m4, promoted)
To cut fan-out it created **5 copies of the second synchronizer stage**, all fed from the first stage, and gave each
its own load-enable group:

```verilog
s_flag_sync_reg_2_aa_lo <= s_flag_sync_reg_1;   // addr low half
s_flag_sync_reg_2_aa_hi <= s_flag_sync_reg_1;   // addr high half
s_flag_sync_reg_2_wd_lo <= s_flag_sync_reg_1;   // data low half
s_flag_sync_reg_2_wd_hi <= s_flag_sync_reg_1;   // data high half
s_flag_sync_reg_2_ctl   <= s_flag_sync_reg_1;   // prot / strb
...
if (ld_aa_lo) m_axil_awaddr_reg[ADDR_HALF-1:0] <= ...;
if (ld_aa_hi) m_axil_awaddr_reg[ADDR_WIDTH-1:ADDR_HALF] <= ...;
```

## Why it is a bug
`s_flag_sync_reg_1` can be metastable. Five flops sampling it can resolve to **different** values in the same cycle,
so the load groups disagree and the master side captures a **torn transaction** (e.g. new low half of the address,
old high half). This is the standard "never duplicate synchronizer flops" rule (also a Do-not-use entry in our
skill.md).

## Why only Aegis's checks see it
| Check | Result on this candidate |
|---|---|
| EQY vs original | **PASS** (copies are identical in zero-delay logic) |
| Differential simulation | **0 mismatches** |
| Dr. RTL's gate (SEC) | **accepted, promoted** |
| Aegis lock checksum | FAIL: "locked block changed" on s_flag_sync_reg_1 / s_flag_sync_reg_2 |
| Aegis CDC re-check | FAIL: synchronizer s_flag_reg -> s_flag_sync_reg_1 and 4 qualified-capture crossings downgraded |

Gain bought with it: TNS -18.73 -> -17.48 ns (WNS -0.09 unchanged).
Aegis on axil_cdc: every crossing intact (TNS -18.73 -> -18.51, EQY PASS).

## Sources
`flow/runs/axil_cdc/drrtl.sonnet-5-5.r1/work/v1/drrtl/m4/` (verify.json gate/cdc/sim, rtl/axil_cdc_wr.v vs rtl/v0).
