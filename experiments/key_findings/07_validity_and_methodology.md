# 07. Validity and methodology points the paper must state

**Status: METHOD.** Each item is something a reviewer could otherwise use against us.

| Item | What happened / what we do | Where |
|---|---|---|
| CDC checker false positive (fixed 2026-10-18) | Re-driving an already-unsafe crossing from a renamed register was counted as a new crossing; an unsynchronized -> insufficient-depth change counted as a regression. Fixed; guardrail suite results identical before/after; affected runs re-measured (`cdc_remeasure.json`). | `tools/aegis_verify.py:cdc`, LOG.md |
| EQY proof limit | EQY proves per partition; a correct retiming that adds a register with an invariant (e.g. `fast_q_inc == fast_q + 1`) can fail. Report "not proven equivalent" and give simulation results alongside. Aegis is held to the same bar. | finding 03 |
| Session-limit contamination | Runs that lose candidates to the Claude session limit still finish and understate that config. `bench/validate_runs.py` flags them (llm_error candidates) and archives them for re-run; 3 Exp 01 runs were invalidated. | `flow/runs_archive/invalid/` |
| Dr. RTL skill-library leakage (favours Dr. RTL) | Dr. RTL's released skill.md was learned on the same 20 designs; the port uses it as a fixed library. On Exp 01 this advantages Dr. RTL. | `tools/drrtl_port.py` docstring |
| Dr. RTL budget | Port runs 5 majors x 5 minors (Dr. RTL: 10 x 5) to match the Aegis budget. | drrtl_port.py |
| Dr. RTL port is a port | Prompts and skill.md verbatim; DC -> Yosys+OpenSTA, Jasper -> EQY; orchestrator passes files in prompts; per-minor diversity fixed to a 5-row table. | drrtl_port.py |
| Vanilla is iterative, equal budget | 5 iterations x 5 candidates with timing feedback (isolates the framework). Single-shot and best-of-5 are reported from iteration 1 of the same runs (no extra runs). | aegis_run.py `run_vanilla` |
| Vanilla prompt gets 1 worst path | Code passes `groups.rpt` with one path per group; the paper draft says "five worst paths". Fix the text (or the code before final runs). | aegis_gen.py `vanilla` |
| Temperature | Opus/Sonnet 5.5 via CLI reject temperature; stratified temperatures are requested but not applied, in all configs. | llm_calls.jsonl `temperature_applied` |
| Phase 1 coverage | Gray contracts auto-proven only on async_fifo (and soc); on other FIFOs Gray/synchronizer registers are locked as immutable instead. cc_cdc_fifo_gray shows 9 "unsynchronized" crossings, likely PULP sync cells not recognized: to check. | phase1_report.json |
| CDC checker: memory coding style (open) | If a rewrite recodes a FIFO memory so Yosys infers registers instead of a memory, Phase 1 stops treating it as storage and the CDC check reports new unsynchronized crossings (mem[i] -> read data). afifo / aegis v3 C5 was rejected this way although EQY PASS and the pointer protocol is unchanged. Affects Aegis only (it gates on CDC); count safe rejections per design. | LOG.md 2026-10-19 |
| Lock is text-level (conservative) | The checksum fingerprints the source of locked cones, so it rejects provably equivalent restructurings too (prim_fifo_async: Dr. RTL's safe fan-out replication would be rejected). State as a limitation; contracts/EQY-based locks would relax it. | finding 08 |
| soc is ours | Constructed example; reported separately from headline averages. | finding 06 |
| Single runs | So far 1 run per config; repeats needed for mean +/- std. | |
