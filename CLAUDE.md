# ROUND 3 (2026-11-05, after round 2 was started) -- READ THIS FIRST

The paper now covers Dr. RTL's FULL 20-design suite, so 10 more designs (20 runs) are added and run BEFORE
eth_mac_1g_fifo. Do NOT stop round 2. Just pull and start the round-3 script; it waits by itself until round 2 has
finished its RTL-OPT step, then takes over (stops round 2 before eth_mac, runs the 20 runs, then eth_mac):
```
git pull origin main          # only adds Phase 1 data for 10 designs + handoff/run_machine2_round3.sh; no code change
cd experiments && nohup caffeinate -i bash handoff/run_machine2_round3.sh >> handoff/machine2_r3.out 2>&1 &
```
If `git pull` complains because round 2 packed results on branch results-machine2-r2, run
`git stash; git checkout main; git pull origin main` first (your runs in aegis_agents/flow/runs are untracked and
safe). Results are packed and pushed to results-machine2-r2 after every design. Report progress to the user after
each design. All rules of rounds 1-2 still apply.

---------------------------------------------------------------------------------------------------------------

# ROUND 2 (2026-11-05) -- READ THIS FIRST

Round 1 (Exp 01 subset + Exp 03 ablation, 15 runs) is done and imported on machine 1. Thank you!
Machine 1 overheats, so this machine now runs ALL remaining benchmark runs (21 runs, a few days).

1. Stop anything still running from round 1: `pkill -f run_machine2.sh; pkill -f run_matrix.sh` (it should be done).
2. Get the round-2 code (two small fixes + Phase 1 data for 12 more designs). Your finished runs in
   `aegis_agents/flow/runs/` are untracked and are NOT touched by this:
   ```
   git fetch origin && git checkout main && git pull origin main
   ```
   What changed: `tools/aegis_select.py` (a region with >1000 timing endpoints, e.g. a FIFO memory synthesized to
   flops, is shown to the analyzer as one endpoint per register; regions <=1000 are unchanged, so round-1 runs are
   unaffected), `run_matrix.sh` (also retries when the Claude CLI is briefly unreachable),
   `handoff/pack_results.sh` (pushes to the NEW branch `results-machine2-r2`), `handoff/reference_baselines.json`
   (+ axis_async_fifo), `handoff/run_machine2_round2.sh` (new queue), and `flow/work/<d>/phase1/` for axis_async_fifo,
   eth_mac_1g_fifo, drrtl_spi, drrtl_pcie, drrtl_dsp, drrtl_router and the 6 rtlopt_* designs.
3. Same environment as round 1 (section "Environment" below; nothing new to install). The queue first runs
   `handoff/check_env.py`; it must print `ENVIRONMENT MATCHES` (11 designs now).
4. Start the queue (keep the laptop on the charger, awake, online):
   ```
   cd experiments && nohup caffeinate -i bash handoff/run_machine2_round2.sh >> handoff/machine2_r2.out 2>&1 &
   ```
   Order (most important first): axis_async_fifo/aegis -> drrtl_spi/pcie/dsp/router x {aegis, drrtl} ->
   RTL-OPT 6 designs x {aegis, drrtl} -> eth_mac_1g_fifo x {aegis, drrtl} (largest, ~1 day each, EQY limit 2700 s).
5. It packs and pushes after every step automatically. You can also push any time: `bash experiments/handoff/pack_results.sh`.
6. All rules below still apply: no code edits, never type numbers, invalid runs are archived and re-run automatically,
   low load. Additionally, kill orphaned EDA processes if you see any running for hours with parent PID 1:
   `for p in $(pgrep -P 1 -f "yosys|yosys-smtbmc|bin/eqy|bin/sby|z3"); do kill $p; done`
   (machine 1 found yosys / yosys-smtbmc processes left behind by timed-out EQY calls, running 9-21 h).
7. Report to the user in plain words after each step: which runs finished, anything abnormal
   (write abnormal events to `experiments/handoff/MACHINE2_NOTES.md`).

---------------------------------------------------------------------------------------------------------------

# CLAUDE.md — Aegis DAC 2027 benchmark, machine 2 handoff

You are helping run the second half of the benchmark for the paper **"Aegis: Clock-Domain-Aware Guardrails for
Agentic LLM Timing Optimization of Multi-Clock RTL"** (DAC 2027; manuscript deadline **Nov 18, 2026, 5 PM PT**).
Machine 1 (the first author's laptop) runs the multi-clock comparison. **This machine (machine 2) runs only the
jobs listed under "Your task".** Read this file completely before doing anything.

This repository is **private and the paper is under double-blind review**: never make it public, never post its
contents, names or results anywhere.

---------------------------------------------------------------------------------------------------------------
## 1. Your task (and only this)

1. Set up the environment (Section 4) and pass the environment check:
   `python3 experiments/handoff/check_env.py` must end with `ENVIRONMENT MATCHES`. If it does not, **stop and report
   the mismatching lines to the user**; do not run anything (results would not be comparable with machine 1).
2. Make sure `claude` (Claude Code CLI) is logged in on this machine (`claude -p "say ok"` must answer).
3. Start the queue in the background and keep the laptop awake:
   ```
   cd experiments && nohup caffeinate -i bash handoff/run_machine2.sh >> handoff/machine2.out 2>&1 &
   ```
   (Linux: drop `caffeinate -i`.) It runs, one at a time:
   - **Exp 01** single-clock subset (the 6 smallest Dr. RTL designs by baseline area): `aegis` on all 6, `drrtl` on
     5 (drrtl_uart/drrtl is already done on machine 1). 11 runs.
   - **Exp 03** ablation: `no_guards` (Aegis with locks and CDC re-check turned into measurements only) on afifo,
     axil_cdc, async_fifo, soc. 4 runs.
   Each run takes ~20 min to a few hours. When the Claude usage limit is hit, the driver sleeps 20 min and retries.
4. Every few hours, and at the end, send results back: `bash experiments/handoff/pack_results.sh`
   (packs each finished run without proof scratch, commits on branch `results-machine2`, pushes).
5. Report progress to the user in plain words: which runs finished, which are left, anything abnormal.

Do **not** run anything else (no Exp 02 multi-clock runs, no repeats, no other configs): machine 1 runs those, and
duplicate runs waste the usage budget.

---------------------------------------------------------------------------------------------------------------
## 2. Rules (they keep the two machines' results comparable and the paper honest)

- **Do not edit any code, design, SDC, liberty, Phase 1 file or skill file.** Both machines must run the identical
  commit. If you find a bug, stop the queue and tell the user what you found (file, line, evidence); machine 1 will
  decide and push a fix. A run made with modified code cannot be mixed with the others.
- **Never invent, estimate or retype numbers.** Every result comes from `flow/runs/<design>/<run>/summary.json`,
  produced by the tools. Do not edit any run directory.
- Runs that lose LLM candidates to the usage limit are invalid; `bench/validate_runs.py --archive` moves them to
  `flow/runs_archive/invalid/` and the driver re-runs them. That is expected; do not "rescue" a partial run.
- Keep load low (the drivers already use one run at a time, 2 candidates, nice 19). Do not raise parallelism.
- Do not delete `flow/runs` or `flow/work` contents. Do not push anything except via `pack_results.sh`.
- Log anything unusual (crashes, repeated failures, tool errors) in `experiments/handoff/MACHINE2_NOTES.md` with the
  date, what happened and the exact error text, and tell the user.

---------------------------------------------------------------------------------------------------------------
## 3. Methodology (what the benchmark measures and why)

**Research question.** LLM agents that optimize RTL timing accept a rewrite when sequential equivalence checking
(SEC) and simulation pass. On multi-clock designs that gate is unsound: SEC and zero-delay simulation model clean
0/1 values, so a rewrite that breaks a clock-domain crossing (CDC) — e.g. copying a synchronizer stage — passes both.
Aegis adds CDC guardrails to the agent loop. The benchmark compares, in ONE open-source flow:
- **aegis** — the full method: Phase 1 recovers clocks from the SDC and classifies every crossing on the elaborated
  netlist (synchronizer / Gray / qualified / insufficient depth / unsynchronized); locks what verification cannot
  check (immutable tier, SHA-256 checksums that survive code motion); proves CDC *contracts* (e.g. Gray pointer
  steps by one bit) with SymbiYosys so contract-bound logic stays editable; selects optimization regions per clock
  domain; generates 5 candidates per region from a skill library; verifies each (checksum + envelope gate, lint,
  LCM multi-clock differential simulation, CDC re-check = Phase 1 re-run + contract re-proof), evaluates survivors
  (EQY on touched modules, Yosys+ABC synthesis, OpenSTA) and scores per clock domain; promotes a winner only if the
  score improves. 5 iterations (no early stop).
- **drrtl** — a faithful reproduction of Dr. RTL (arXiv 2604.14989): its released agent prompts and skill library
  (`benchmarks/Dr_RTL/.claude/`), its loop (5 parallel minors per major version) and its 0.5/0.35/0.15
  WNS/TNS/area score, with Design Compiler → Yosys+OpenSTA and Jasper SEC → EQY vs the original. 5 iterations.
- **vanilla** — model gets RTL + timing report, no guardrails (not run on this machine).
- **no_guards** (ablation) — Aegis with locks and CDC re-check measured but not enforced; same loop, skills, budget.
  Shows what the guardrails prevent and what they cost.

**Protocol (identical on both machines).** Claude Sonnet 5.5 (`claude-sonnet-5-5`) through the `claude -p` CLI
(no API key; the CLI rejects a temperature, so candidates differ by slot role/skill only). One run per design and
configuration, run id `<config>.sonnet-5-5.r1`. 5 iterations × 5 candidates. Nangate45 library, Yosys 0.67 with a
timing-driven ABC script, OpenSTA, synthesis-only baseline. Single-clock designs use Dr. RTL's 0.1 ns clock;
multi-clock designs use per-domain periods at 75 % of the raw critical path. EQY timeout 1200 s per check (per
design `eqy_timeout_s` in design.json may raise it). Final designs are re-checked against the ORIGINAL RTL (EQY on
top + CDC re-check), whatever the configuration.

**Metrics reported.** Worst-domain WNS, TNS, area (relative change vs the synthesis-only baseline); EQY pass of the
final design vs the original; CDC verdict of the final design (re-measured by one checker for all configs); LLM
tokens and calls; and a flattened re-synthesis check (gains that rely only on module boundaries vanish). Dr. RTL's
*published* percentages are never compared with ours (different tools and baselines).

**Validity rules.** Numbers only from logged runs; usage-limit-damaged runs are discarded and re-run; no
cherry-picking (designs and subsets fixed before results: Exp 01 subset = 6 smallest by baseline area); every
decision is logged in `experiments/LOG.md` (read it for the full history and reasoning, and `experiments/key_findings/`
for the results so far).

---------------------------------------------------------------------------------------------------------------
## 4. Environment (exact versions; results depend on them)

Machine 1: macOS 15.5, Apple Silicon (arm64), Python 3.14.3. Required tools and the versions used on machine 1:

| Tool | Version on machine 1 | How to get it |
|---|---|---|
| Yosys (+ yosys-abc, yosys-smtbmc) | **0.67+post, git sha1 b8e7da6f40ae8f552c116bf6c359b07c6533e159** | macOS: `brew install yosys` only if it gives this exact version; otherwise build from source: `git clone https://github.com/YosysHQ/yosys && cd yosys && git checkout b8e7da6f40ae8f552c116bf6c359b07c6533e159 && git submodule update --init && make -j4 && sudo make install` |
| OpenSTA | **3.1.0, commit 6541058** (2026-09-10) | `git clone https://github.com/The-OpenROAD-Project/OpenSTA ~/OpenSTA && cd ~/OpenSTA && git checkout 6541058 && mkdir build && cd build && cmake .. && make -j4` (needs cmake, tcl, swig, bison, flex, eigen, cudd per OpenSTA README). The tools find it as `sta` on PATH or at `~/OpenSTA/build/sta`. |
| SymbiYosys (sby) | the release matching Yosys 0.67 | `git clone https://github.com/YosysHQ/sby && cd sby && git tag` → check out the tag for Yosys 0.67, then `make install PREFIX=~/.local` (or use the sby shipped with the same Yosys package/OSS CAD Suite build) |
| EQY | the release matching Yosys 0.67 | `git clone https://github.com/YosysHQ/eqy && cd eqy && git tag` → check out the tag for Yosys 0.67, then `make install PREFIX=~/.local` |
| Z3 | 5.1.0 | `brew install z3` / distro package |
| Icarus Verilog (iverilog, vvp) | 12.0 | `brew install icarus-verilog` / `apt install iverilog` |
| Verilator | 5.044 | `brew install verilator` (lint only; minor version differences are harmless) |
| Python | 3.14.3 (3.10+ works; standard library only) | |
| Claude Code CLI | 2.1.316 | `npm i -g @anthropic-ai/claude-code`, then `claude` once to log in |

Cell library: `aegis_agents/pdk/nangate45.lib` (in the repo). `~/.local/bin` must be on PATH (the tools add it).
**The environment check (`experiments/handoff/check_env.py`) is the acceptance test**: it re-synthesizes and times
the 10 designs this machine runs and must reproduce machine 1's numbers exactly. Yosys/ABC version differences change
synthesis results, so a mismatch means stop and report, not "close enough".

---------------------------------------------------------------------------------------------------------------
## 5. Repository map

```
aegis_agents/tools/        the pipeline (aegis_run.py = orchestrator; drrtl_port.py = Dr. RTL reproduction;
                           aegis_ingest.py = Phase 1; gen_cdc_props.py = CDC contracts; aegis_verify.py = Phase 4;
                           aegis_eval.py = EQY + synthesis/STA + score; aegis_sta.py = Yosys/OpenSTA wrapper)
aegis_agents/bench/        run_suite.py (one run per design/config), validate_runs.py, report.py, final_remeasure.py,
                           candidate_audit.py, cdc_mutants/ (CDC mutation benchmark scripts)
aegis_agents/flow/designs/ every design: design.json, rtl/, SDC
aegis_agents/flow/work/<d>/phase1/   Phase 1 results (locks, contracts) for the designs this machine runs -- do not
                           regenerate or edit; they are identical to machine 1's
aegis_agents/flow/runs/    created by the runs: flow/runs/<design>/<config>.sonnet-5-5.r1/{summary.json, rtl/, work/, ...}
aegis_agents/CLAUDE.md     describes driving the loop by hand from Claude Code -- NOT used here; always use the scripts
benchmarks/Dr_RTL/.claude/ Dr. RTL's released prompts and skill library (used verbatim by drrtl_port.py)
experiments/run_matrix.sh  resumable driver (usage-limit retry)
experiments/handoff/       check_env.py, run_machine2.sh, pack_results.sh, reference_baselines.json
experiments/LOG.md, key_findings/   full decision log and findings so far (context; read-only)
paper/dac27/               the paper (LaTeX; tables are generated from runs by gen_tables.py on machine 1)
```

## 6. Monitoring
- Queue output: `experiments/handoff/machine2.out`; per-run log: `aegis_agents/flow/runs/<d>/<run>.log`.
- A run is finished when `flow/runs/<d>/<run>/summary.json` exists. Quick view:
  `cd aegis_agents && python3 bench/report.py --out /tmp/report && cat /tmp/report/*.md`
- "usage limit hit; sleeping 20 min" is normal. "remaining failures are not usage-limit failures; stopping for a
  human to look" is not: read the failed run's `.log`, write it into MACHINE2_NOTES.md, tell the user.
