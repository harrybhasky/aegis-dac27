# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

AEGIS: guardrailed LLM optimization of multi-clock RTL for timing closure.
- Synthesis with Yosys, static timing with OpenSTA, formal checks with SymbiYosys and EQY.
- Clock-domain crossings are protected by three lock tiers (immutable, contract-bound, free).
- Optimization targets are chosen per clock domain, as *regions* of overlapping logic cones.

Deterministic steps are Python tools in `tools/`. Agents in `.claude/agents/` either run a tool and report (`aegis-ingest`, `aegis-sta-runner`, `aegis-region-selector`) or make a judgment the tools cannot (`aegis-timing-analyzer`, `aegis-skill-matcher`). No agent computes a number, edits a lock, or touches the SDC.

This file covers the whole loop: Phase 1, baseline STA, region selection, diagnosis, skill selection, generation (Phase 3), verification (Phase 4), evaluation (Phase 5) and the Librarian (Phase 5.5).

The same loop is implemented deterministically by `tools/aegis_run.py` (the Python orchestrator used for all reported experiments); it calls the LLM only for diagnosis, skill ranking and generation, with the agent files below as system prompts. Run it with `python3 tools/aegis_run.py --design <d> --run-id <id> [--mode vanilla] [ablation flags]`. Follow this file only when driving the loop from Claude Code instead.

## Layout

```
.claude/agents/            agent definitions
.claude/skill/rtl-opt/     skill.md (the skill library)
tools/                     aegis_ingest.py, aegis_sta.py, aegis_select.py, aegis_skills.py,
                           gen_cdc_props.py (+ templates/), check_registered_launch.py, sta_endpoints.tcl,
                           aegis_gen.py (Phase 3), aegis_verify.py (Phase 4), aegis_eval.py (Phase 5),
                           aegis_librarian.py (Phase 5.5), aegis_run.py (orchestrator), aegis_llm.py, aegis_common.py
bench/                     setup_designs.py, run_baseline.py, run_suite.py, report.py, results/
flow/designs/<design>/     design.json, rtl/, <design>.sdc, optional cdc_annotations.json
flow/rtl/<design>/<ver>/   RTL of each version (v0 = original)
flow/work/<design>/        phase1/, <ver>/sta/, <target>/sel/, <target>/skills/, attempts.json, diag_cache/
flow/skills/               skills_index.json, library_state.json (owned by the Librarian)
flow/log/                  <design>.<target>.iter.json
```

`design.json`:
```json
{"top": "soc", "rtl": ["flow/designs/soc/rtl/soc.v"], "sdc": "flow/designs/soc/soc.sdc",
 "liberty": "pdk/nangate45.lib", "annotations": null, "weights": null,
 "margin": 0.1, "budget": 10, "rho": 0.8, "dispatch": 3,
 "theta": 0.5, "phi": 32, "smax": 80, "n_max": 5}
```

## Once per design

1. Copy the RTL to `flow/rtl/<design>/v0/`.
2. **INGEST**: @agent-aegis-ingest with `design`, `config`, `out_dir = flow/work/<design>/phase1`.
   - `status: blocked` → stop and show `needs_human`. Do not optimize until the SDC parses cleanly.
   - `status: ok` → show `needs_human` to the user (pre-existing CDC issues, constraint audit) and continue.
3. If `flow/skills/skills_index.json` is missing:
   `python3 tools/aegis_skills.py index --skill-md .claude/skill/rtl-opt/skill.md --out flow/skills`
4. Create `flow/work/<design>/attempts.json` as `{}`.

## Optimization loop

The baseline $B_1$ is `v0`. For iteration $n = 1 \ldots n_{max}$, with target version `v<n>`:

### Steps per iteration

1. **STA**: @agent-aegis-sta-runner on $B_n$ (skip if `flow/work/<design>/<B_n>/sta/metrics.json` exists).
2. **SELECT (prepare)**: @agent-aegis-region-selector with `mode: prepare`, using $B_n$'s `endpoints.rpt`, Phase 1 `clocks.json` and `lock_map.json`, and `margin`, `theta`, `phi`, `smax` from `design.json`.
3. **ANALYZE**: @agent-aegis-timing-analyzer once per region in `sel/diagnosis_todo.json`. These calls are independent; run them in parallel.
4. **SELECT (finalize)**: @agent-aegis-region-selector with `mode: finalize`, $\alpha$/$\beta$ from the schedule below, and `budget`, `rho`, `dispatch`, `weights` from `design.json`.
   - If it reports `rediagnose`, re-run the analyzer once on those regions, then finalize again.
   - If `area_recovery` is true, every domain meets the margin: report it and stop (area-recovery targets are not implemented in these tools).
   - If `dispatch` is empty, there is nothing left to optimize: stop.
5. **MATCH SKILLS**: @agent-aegis-skill-matcher once per region in `selection.json["dispatch"]`, in parallel.
6. **RECORD**: write `flow/log/<design>.v<n>.iter.json` from `sel/selection.json` (per-domain deficits, quotas, constraint audit, unmapped and no-logic endpoints, match rate, blocked and unreachable deficit, regions with diagnoses) and each region's `skills/<region_id>.assignment.json` under `regions[i].optimization.plan`. Leave `result` and `evaluation` null.
7. **GENERATE** (Phase 3): for each dispatched region, compute the edit envelope once, then run @agent-aegis-generator for C1..C5 in parallel (`out_dir = flow/work/<design>/v<n>/cand/<region_id>/<slot>`).
8. **VERIFY** (Phase 4): @agent-aegis-verifier on every candidate with `status: ok`, in parallel. The checksum and envelope gate runs first, before any lint or simulation.
9. **EVALUATE** (Phase 5): @agent-aegis-evaluator on every candidate that passed, with `scopes` = the envelope's modules and $\alpha,\beta,\gamma$ from the schedule. The region winner $W^{(r)}_n$ is the lowest score among candidates with `sec_pass: true`; in the final iteration a candidate that worsens any domain's worst deficit is rejected.
10. **COMPOSE**: apply the winners of disjoint modules together to $B_n$, re-verify (gate, lint, sim, CDC), re-time; keep the composition only if it beats the best single winner.

### After verification and scoring

11. **UPDATE ATTEMPTS** in `flow/work/<design>/attempts.json`, for each dispatched region:
   - promoted → `{"attempts": 0, "skills_tried": [], "tabu": false}`
   - not promoted → `attempts += 1`, append the assignment's `skills_used` to `skills_tried`, and set `tabu: true` when `attempts` reaches 2.
12. **LIBRARIAN** (Phase 5.5): write `flow/work/<design>/v<n>/round.json` (every candidate's slot, skill, status, reject reason, score) and run @agent-aegis-librarian.
13. **PROMOTE**: $B_{n+1}$ = the iteration winner if its score is strictly better than $B_n$'s (score < 0, since $B_n$ scores 0); otherwise $B_{n+1} = B_n$. Copy the winner's RTL to `flow/rtl/<design>/v<n>/`.

### Stop when
- $n = n_{max}$, or
- step 4 dispatches nothing (queue empty or all regions tabu), or
- two consecutive iterations improve the score by less than $\varepsilon$.

## Adaptive schedule ($\alpha$, $\beta$ for region scoring)

"All domains meet $m$" means every domain's WNS is at least the margin in $B_n$'s `metrics.json`.

| Iteration | Condition | $\alpha$ | $\beta$ |
|---|---|---|---|
| 1 | | 0.60 | 0.30 |
| 2 | | 0.50 | 0.40 |
| 3 | all domains meet $m$ | 0.35 | 0.25 |
| 3 | some domain below $m$ | 0.55 | 0.35 |
| 4–5 | all domains meet $m$ | 0.30 | 0.20 |
| 4–5 | some domain below $m$ | 0.70 | 0.30 |

## Rules

- Never edit RTL in `flow/rtl/<design>/v0/`, the SDC, `design.json`, or anything under `flow/work/<design>/phase1/`.
- Never change lock tiers, contracts, or checksums by hand. To change them, re-run Phase 1 on a new original design.
- Never dispatch regions other than `selection.json["dispatch"]`, and never skip the checksum gate.
- Never promote a candidate that did not pass every Phase 4 stage and EQY on every scope.
- Never compute deficits, priorities, quotas, or skill eligibility yourself; read them from the tools' outputs.
- Agent outputs are JSON. If an agent returns `status: error`, stop the iteration and report it.
