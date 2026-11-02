#!/usr/bin/env python3
"""
Re-score the CDC checks (structural + contract) of already-labeled mutants with the CURRENT Phase 1 and Phase 4
code, without re-running lint / simulation / EQY (those do not depend on the CDC checker).

  python3 bench/cdc_mutants/rescore_cdc.py --tag v2 [--jobs 2] [--design afifo ...]

Adds to each label.json: structural_<tag>, contract_<tag>, contracts_on_original_<tag>, cdc_violations_<tag>,
recoded_storage_<tag>. The original fields stay as they were (they record the checker at labeling time).
Written 2026-11-02 for the Phase 1 fix that binds Gray contracts to internal launch registers.
"""
import argparse
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402


def one(path, tag):
    lab = json.load(open(path))
    mdir = os.path.dirname(path)
    D = load_design(lab["design"])
    phase1 = os.path.join(ROOT, "flow", "work", lab["design"], "phase1")
    c = aegis_verify.cdc(D, [os.path.join(mdir, "mutant.v")], phase1)
    v = c.get("violations", [])
    lab["structural_" + tag] = not any(not x.startswith("contract ") for x in v)
    lab["contract_" + tag] = not any(x.startswith("contract ") for x in v)
    lab["contracts_on_original_" + tag] = len(json.load(open(os.path.join(phase1, "phase1_report.json"))).get(
        "contracts_proven", []))
    lab["cdc_violations_" + tag] = v[:6]
    lab["recoded_storage_" + tag] = len(c.get("recoded_storage", []))
    json.dump(lab, open(path, "w"), indent=1)
    return lab


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--design", action="append")
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.join(HERE, "out", "*", "*", "label.json")))
    todo = []
    for p in paths:
        lab = json.load(open(p))
        if a.design and lab["design"] not in a.design:
            continue
        if ("structural_" + a.tag) in lab and not a.redo:
            continue
        todo.append(p)
    print("%d labels to re-score" % len(todo), flush=True)
    with ProcessPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(one, p, a.tag): p for p in todo}
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", futs[f], repr(e)[:300], flush=True)
                continue
            print("%-16s %-40s gt_safe=%-5s struct %s->%s contract %s->%s" % (
                r["design"], r["id"][:40], r["ground_truth"]["cdc_safe"], r["structural"], r["structural_" + a.tag],
                r["contract"], r["contract_" + a.tag]), flush=True)


if __name__ == "__main__":
    main()
