# 12. Lalit's experiment report (lalit_experiments.pdf, 2026-10-20): what can and cannot be used

**Status: METHOD.** Assessed 2026-11-02. Source: `~/code/Projects/AI_RTL_Ver/lalit_experiments.pdf` (13 pages,
authors K Hari Bhaskaran, V Lalit Kishore). No run folders or logs came with it.

## Headline claims in the report
- Dr. RTL 20-design suite: AEGIS WNS -45.8 %, TNS -38.1 %, area -7.7 % (avg) "against 21.3/16.9/5.8 % published for
  Dr. RTL"; 24.2/17.1/7.0 % when original and final are re-synthesized with the hierarchy flattened.
- RTLRewriter-Bench short cases: fewest cells or tied best on 12/14.
- Multi-clock: toy SoC (2 rounds), OpenCores eth_top (1 round on 1 of 3 violating regions), a Groq-API pilot.

## Why the numbers cannot go into our paper as Aegis results
1. **Different system / protocol.** Candidates were written by an interactive Claude Code session ("Claude-native"),
   up to 10 rounds, stop after 2 without promotion; agents screened drafts with tools/Python outside the 5-candidate
   budget on some designs; a compliance rule added mid-run replaced promoted versions; Librarian notes from earlier
   designs were given to later ones (no held-out split). Our results come from the automated `aegis_run.py` loop,
   5 iterations, identical for every design.
2. **Cross-flow comparison.** The 45.8 % is set against Dr. RTL's *published* Design Compiler numbers (finding 05).
   Baselines differ widely (cpu_fsm WNS -37.80 in his flow vs -0.82 in Dr. RTL's paper and -7.80 in ours;
   communication -1.92 vs -0.40 vs -0.43). A reviewer will reject this comparison.
3. **Hierarchy dependence.** Nearly half of the gain disappears when the hierarchy is flattened (45.8 -> 24.2 % WNS).
4. **No logs.** Our rule: every number must come from a logged run we can re-measure.
5. **Single-clock.** It does not test the paper's claim (CDC safety on multi-clock designs).
6. **Not reproduced.** Our own run gave controller -5 % WNS where his gave -46 % (finding 05).

## What we use
- **Co-author:** V Lalit Kishore is an author of this work -> added to the abstract-registration package.
- **Flattened re-synthesis check** (his Sec. IX-B): our flow also keeps hierarchy (`aegis_sta.py`: `synth -run
  begin:fine` without flatten), so the same objection applies to us. Plan: re-synthesize every original and final
  design flattened and report the flattened WNS change next to the main numbers (no LLM cost).
- **Verification lessons** (his Sec. IX-D, X-A): EQY's partitioning can fail to prove a correct Gray full-flag
  restructuring. Now that Gray logic is contract-bound and editable, such candidates may be rejected as EQY
  TIMEOUT/FAIL: conservative, not unsafe; watch for it in the re-runs. His miter's vacuity issue (reset-value initial
  links) does not apply to our EQY setup (no initial-state assumptions).
- Optional, only with his logs and if time permits: RTLRewriter-Bench short cases run through *our* pipeline.
