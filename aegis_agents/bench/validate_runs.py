#!/usr/bin/env python3
"""
Flag finished runs whose candidates were lost to LLM failures (e.g. the Claude session limit), which makes their
numbers understate that configuration. A finished run (summary.json present) is INVALID if more than
max(2, 10%) of its candidates failed with an LLM error, or the run log shows an LLM failure; with fewer losses it is
DEGRADED (kept, and the loss is stated in its RUN_NOTES).

  python3 bench/validate_runs.py                  # report
  python3 bench/validate_runs.py --archive        # move invalid runs to flow/runs_archive/invalid/<stamp>/
                                                  # so the resumable drivers re-run them
"""
import argparse
import glob
import json
import os
import re
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAT = re.compile(r"session limit|usage limit|LLM call failed|LLMError")


def check(run):
    bad_meta = bad_it = 0
    for m in glob.glob(os.path.join(run, "work", "v*", "**", "meta.json"), recursive=True):
        try:
            if json.load(open(m)).get("status") == "llm_error":
                bad_meta += 1
        except ValueError:
            pass
    for p in glob.glob(os.path.join(run, "work", "v*", "iteration.json")):
        it = json.load(open(p))
        cs = list(it.get("candidates") or []) + [c for r in it.get("regions") or [] for c in r.get("candidates", [])]
        bad_it += sum(1 for c in cs if c.get("status") == "llm_error" or c.get("gen_status") == "llm_error")
    log = run + ".log"
    hits = sum(1 for l in open(log, errors="replace") if PAT.search(l)) if os.path.exists(log) else 0
    return max(bad_meta, bad_it), hits   # the same lost candidate can appear in both places


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", action="store_true")
    a = ap.parse_args()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for s in sorted(glob.glob(os.path.join(ROOT, "flow", "runs", "*", "*", "summary.json"))):
        run = os.path.dirname(s)
        if os.path.basename(run).startswith("smoke"):
            continue
        bad, hits = check(run)
        total = (json.load(open(s)).get("candidates") or {}).get("total") or 25
        if bad and bad <= max(2, total // 10) and not hits:
            print("DEGRADED %s: %d of %d candidates lost to LLM errors (kept; noted in RUN_NOTES)" % (
                os.path.relpath(run, os.path.join(ROOT, "flow", "runs")), bad, total))
            continue
        if bad or hits:
            rel = os.path.relpath(run, os.path.join(ROOT, "flow", "runs"))
            print("INVALID %s: %d llm_error candidates, %d LLM-failure log lines" % (rel, bad, hits))
            if a.archive:
                dst = os.path.join(ROOT, "flow", "runs_archive", "invalid", stamp, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(run, dst)
                if os.path.exists(run + ".log"):
                    shutil.copy(run + ".log", dst + ".log")   # the log stays so the driver sees the limit and retries


if __name__ == "__main__":
    main()
