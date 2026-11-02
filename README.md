# Aegis — DAC 2027 benchmark (private, double-blind: do not share)

**For the person on machine 2:** open this folder in Claude Code and say
*"Read CLAUDE.md and do the machine 2 task."* Everything Claude needs (methodology, exact tool versions, setup,
which runs to do, rules, how to send results back) is in [CLAUDE.md](CLAUDE.md).

Quick manual version:
1. Install the tools in CLAUDE.md §4, then `python3 experiments/handoff/check_env.py` → must print `ENVIRONMENT MATCHES`.
2. `cd experiments && nohup caffeinate -i bash handoff/run_machine2.sh >> handoff/machine2.out 2>&1 &`
3. Every few hours and at the end: `bash experiments/handoff/pack_results.sh` (pushes results on branch `results-machine2`).
