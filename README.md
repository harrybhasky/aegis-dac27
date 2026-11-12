# Aegis — DAC 2027 benchmark (private, double-blind: do not share)

**For the person on machine 2:** open this folder in Claude Code and say:
*"Read CLAUDE.md, inspect the current machine-2 status, and execute the current handoff. Run the environment check
first, do not run benchmarks if it fails, and log every start, completion, retry, and abnormal event."*
Everything Claude needs (methodology, exact tool versions, setup, which runs to do, rules, logging, and how to send
results back) is in [CLAUDE.md](CLAUDE.md).

Quick manual version:
1. Install the tools in CLAUDE.md §4, then `python3 experiments/handoff/check_env.py` → must print `ENVIRONMENT MATCHES`.
2. Read the **Current machine-2 handoff** section at the top of `CLAUDE.md`; it supersedes older round notes.
3. Every few hours and at the end: `bash experiments/handoff/pack_results.sh` (pushes results on the designated results branch).
