# 09. afifo: vanilla meets timing by cutting a 2-flop synchronizer to 1 flop

**Status: SUPPORTED (1 design, 1 run).** The first real CDC break in the experiments, and the textbook one.

## What vanilla did (ZipCPU `afifo`, final version v4)
Original: the read Gray pointer reaches the write domain through `rgray -> rgray_cross -> wr_rgray` (NFF = 2);
the full flag compares against `wr_rgray`, the settled second stage.

Vanilla: computes the full flag one cycle early from `next_wr_rgray = rgray_cross` (the **first** synchronizer
stage) and registers it; `wr_rgray` becomes unused and is removed.

```verilog
assign next_wr_rgray = rgray_cross[...];                 // first sync stage, can be metastable
wire full_if_adv  = (next_wr_rgray == wgray_p1_cmp);
wire full_if_hold = (next_wr_rgray == wgray_cmp);
...  o_wr_full <= full_nxt;
```

## Why it is a bug that functional checks miss
At cycle level `rgray_cross` equals the later `wr_rgray`, so zero-delay simulation sees **0 mismatches**. In
silicon the first stage can be metastable; feeding it into comparison logic removes the resolution time the second
flop provided. Effective synchronizer depth 2 -> 1.

| afifo | Aegis | Vanilla |
|---|---|---|
| i_rclk WNS | -0.15 -> -0.11 | -0.15 -> **+0.03** |
| i_wclk WNS | -0.11 -> -0.11 | -0.11 -> **0.00** |
| Area | +1.9% | +10.2% |
| Synchronizer depth (read pointer) | 2 (intact) | **1** |
| CDC re-check | pass | **FAIL**: "rgray -> rgray_cross disappeared", "new insufficient_depth crossing rgray -> next_wr_rgray" |
| Lock checksum | pass | FAIL: wr_rgray / rgray_cross missing, Gray next-value changed |
| Differential simulation | 0 mismatches | **0 mismatches** (bug invisible) |
| EQY vs original | PASS | FAIL (12 partitions) |

## How to state it
"Given the same model and budget, the unguarded optimizer met timing on afifo in part by consuming the first stage
of a two-flop synchronizer, a metastability hazard that differential simulation does not detect. Aegis's lock tier
and CDC re-check reject this class of rewrite."
Caveat: our EQY also failed this design, so an SEC-gated optimizer (Dr. RTL) would have rejected this exact version
in our flow; whether a stronger SEC engine would prove it equivalent is open. See the Dr. RTL afifo run.

## Sources
`flow/runs/afifo/vanilla.sonnet-5-5.r1/` (rtl/v0 vs rtl/v4 `afifo.v` lines ~92-113, final_verify.json gate/cdc/sim,
final_eqy/eqy_afifo.log); `flow/runs/afifo/aegis.sonnet-5-5.r1/`.
