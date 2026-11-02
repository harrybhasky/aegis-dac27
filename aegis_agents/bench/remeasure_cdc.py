#!/usr/bin/env python3
"""
Re-run the Phase 4 CDC check (measurement only) on every candidate of a finished run, with the current checker.
Writes <run>/cdc_remeasure.json; summary.json is left untouched as the original record.

  python3 bench/remeasure_cdc.py flow/runs/<design>/<run-id>
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402

run = sys.argv[1].rstrip("/")
S = json.load(open(os.path.join(run, "summary.json")))
D = load_design(S["design"])
p1 = os.path.join(ROOT, "flow", "work", S["design"], "phase1")
dirs = sorted(set(os.path.dirname(f) for f in glob.glob(os.path.join(run, "work", "v*", "*", "*", "rtl", "*")) +
                  glob.glob(os.path.join(run, "work", "v*", "regions", "*", "*", "rtl", "*"))))
res = {}
for d in dirs:
    files = sorted(glob.glob(os.path.join(d, "*")))
    r = aegis_verify.cdc(D, files, p1)
    res[os.path.relpath(d, run)] = {"pass": r["pass"], "violations": r["violations"], "resourced_unsafe": r.get("resourced_unsafe", [])}
def tool_error(v):
    return any(x.startswith("Phase 1 re-run failed") for x in v["violations"])


out = {"checker": "aegis_verify.cdc with re-sourced-crossing fix (2026-10-18)", "checked": len(res),
       "violating": sum(1 for v in res.values() if not v["pass"] and not tool_error(v)),
       "tool_errors": sum(1 for v in res.values() if tool_error(v)), "candidates": res}
json.dump(out, open(os.path.join(run, "cdc_remeasure.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in ("checked", "violating", "tool_errors")}))
