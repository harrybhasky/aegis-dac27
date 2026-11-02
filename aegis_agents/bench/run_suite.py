#!/usr/bin/env python3
"""
Run a benchmark matrix: designs x configurations x repetitions (resumable: a run whose
summary.json exists is skipped).

  python3 bench/run_suite.py --designs soc async_fifo --configs aegis vanilla --reps 3 \\
      [--model claude-sonnet-5-5] [--parallel 2] [--iters 5]

Configurations
  aegis          full pipeline
  vanilla        unguarded baseline (same model, same budget)
  no_locks       ablation (a): locks disabled (checksum measured only)
  zero_shot      ablation (b): no skill library, five zero-shot candidates
  scalar         ablation (c): global scalar score instead of the domain-aware score
  no_stall       ablation (d): no stall recovery
  no_cdc_check   extra: Phase 4 CDC re-check measured only
  drrtl          Dr. RTL's own agents and skill.md, ported to this flow (tools/drrtl_port.py)
Run ids are <config>.<model-short>.r<k>, so cross-model runs never collide.
"""
import argparse
import concurrent.futures as cf
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# 2026-11-02: aegis runs the full iteration budget (no "two iterations below epsilon" early stop), matching
# the Dr. RTL port, which always runs n_max major iterations.
FLAGS = {"aegis": ["--eps", "0"], "vanilla": ["--mode", "vanilla"], "no_locks": ["--no-locks", "--eps", "0"],
         "zero_shot": ["--zero-shot", "--eps", "0"], "scalar": ["--scalar-score", "--eps", "0"],
         "no_stall": ["--no-stall-recovery", "--eps", "0"], "no_cdc_check": ["--no-cdc-check", "--eps", "0"],
         # 2026-11-02: both guardrails off (locks and CDC re-check measured only), same loop, skills and budget
         "no_guards": ["--no-locks", "--no-cdc-check", "--eps", "0"], "drrtl": []}


def short(model):
    return model.replace("claude-", "").replace(".", "_")


def one(job):
    design, cfg, rep, a = job
    rid = "%s.%s.r%d" % (cfg, short(a.model), rep)
    d = os.path.join(ROOT, "flow", "runs", design, rid)
    if os.path.exists(os.path.join(d, "summary.json")) and not a.force:
        return (design, rid, "skip")
    os.makedirs(d, exist_ok=True)
    tool = "drrtl_port.py" if cfg == "drrtl" else "aegis_run.py"
    cmd = [sys.executable, os.path.join(ROOT, "tools", tool), "--design", design, "--run-id", rid,
           "--model", a.model, "--backend", a.backend, "--jobs", str(a.jobs)] + FLAGS[cfg]
    if a.iters:
        cmd += ["--iters", str(a.iters)]
    t0 = time.time()
    with open(os.path.join(ROOT, "flow", "runs", design, rid + ".log"), "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    st = "ok" if r.returncode == 0 else "FAILED rc=%d" % r.returncode
    print("%-18s %-34s %s (%.0fs)" % (design, rid, st, time.time() - t0), flush=True)
    return (design, rid, st)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--designs", nargs="+", required=True)
    ap.add_argument("--configs", nargs="+", default=["aegis", "vanilla"])
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--rep-start", type=int, default=1)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--backend", default="claude-cli")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--iters", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    jobs = [(d, c, r, a) for r in range(a.rep_start, a.rep_start + a.reps) for d in a.designs for c in a.configs]
    with cf.ThreadPoolExecutor(max_workers=a.parallel) as ex:
        res = list(ex.map(one, jobs))
    bad = [r for r in res if r[2].startswith("FAILED")]
    print("done: %d runs, %d failed" % (len(res), len(bad)))


if __name__ == "__main__":
    main()
