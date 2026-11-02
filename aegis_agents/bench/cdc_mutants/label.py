#!/usr/bin/env python3
"""
Measure which checker catches each CDC mutant. Every check runs on every mutant (nothing
short-circuits), against the original design RTL and its Phase 1 results.

  python3 bench/cdc_mutants/label.py --design async_fifo [--design ...] [--jobs 6] [--no-eqy]
      -> bench/cdc_mutants/out/<design>/<mutant>/label.json, bench/cdc_mutants/results/labels.{jsonl,md}

Checks
  lint        iverilog (+ verilator when the original lints clean)
  sim         Phase 4 differential simulation (every clock at its SDC period, LCM window, 2 seeds)
  eqy         EQY on the top module, SBY k-induction; gold = the identity mutant (the original
              written back through the same netlist round trip), so gold and gate differ only
              by the mutation (EQY's partitioned induction cannot match source RTL against an
              opt_dff netlist register-for-register)
  structural  Phase 1 re-run: new unsynchronized / insufficient-depth crossing, or a
              synchronizer / Gray / qualified crossing lost or downgraded
  contract    every contract proven on the original is still proven at the same latency
A checker "flags" a mutant when it fails; for EQY that includes "failed to prove" (partitioned
k-induction is incomplete, so an EQY flag on an equivalent mutant is inconclusive, not a counterexample). For CDC-unsafe mutants a flag is a detection; for
CDC-safe mutants a flag from a CDC checker is a false alarm.
"""
import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
import aegis_eval  # noqa: E402
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402


def label_one(design, mdir, do_eqy, verilator_ok):
    D = load_design(design)
    meta = json.load(open(os.path.join(mdir, "meta.json")))
    cand = [os.path.join(mdir, "mutant.v")]
    phase1 = os.path.join(ROOT, "flow", "work", design, "phase1")
    res = {"id": meta["id"], "design": design, "operator": meta["operator"], "ground_truth": meta["ground_truth"],
           "crossing_kind": (meta.get("crossing") or {}).get("kind"), "time_s": {}}
    t = time.time()
    lint = aegis_verify.lint(D, cand, verilator_ok, True)
    res["lint"] = lint["pass"]
    res["time_s"]["lint"] = round(time.time() - t, 1)
    t = time.time()
    try:
        s = aegis_verify.sim(D, D["rtl"], cand, json.load(open(os.path.join(phase1, "clocks.json"))))
    except Exception as e:  # noqa: BLE001 - a crash is recorded, not fatal
        s = {"pass": None, "error": str(e)[-400:]}
    res["sim"] = s.get("pass")
    res["sim_mismatches"] = s.get("mismatches")
    res["sim_error"] = s.get("error") or s.get("skipped")
    res["time_s"]["sim"] = round(time.time() - t, 1)
    t = time.time()
    c = aegis_verify.cdc(D, cand, phase1)
    v = c.get("violations", [])
    res["structural"] = not any(not x.startswith("contract ") for x in v)
    res["contract"] = not any(x.startswith("contract ") for x in v)
    res["contracts_on_original"] = len(json.load(open(os.path.join(phase1, "phase1_report.json"))).get("contracts_proven", []))
    res["cdc_violations"] = v[:6]
    # labeled with the post-2026-11-02 checker: record it under the v2 keys as well (see rescore_cdc.py)
    res["structural_v2"], res["contract_v2"], res["cdc_violations_v2"] = res["structural"], res["contract"], v[:6]
    res["contracts_on_original_v2"] = res["contracts_on_original"]
    res["time_s"]["cdc"] = round(time.time() - t, 1)
    if do_eqy:
        t = time.time()
        gold = [os.path.join(os.path.dirname(mdir), "identity", "mutant.v")]
        e = aegis_eval.eqy(gold, cand, D["top"], os.path.join(mdir, "eqy"), depth=8, timeout=1800)
        res["eqy"] = e["status"] if isinstance(e, dict) else e
        res["time_s"]["eqy"] = round(time.time() - t, 1)
        # EQY scratch is 30 MB-10 GB per mutant and only the verdict is used: keep label.json, drop the rest
        shutil.rmtree(os.path.join(mdir, "eqy"), ignore_errors=True)
    json.dump(res, open(os.path.join(mdir, "label.json"), "w"), indent=1)
    return res


def table(rows):
    ok = lambda x: "-" if x is None else ("pass" if x else "**FLAG**")
    md = ["| Design | Mutant | CDC-safe (GT) | Sim-equiv (GT) | Lint | Sim | EQY (proved?) | Structural CDC | Contract |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["design"], r["operator"], r["id"])):
        md.append("| %s | %s | %s | %s | %s | %s%s | %s | %s | %s |" % (
            r["design"], r["id"], r["ground_truth"]["cdc_safe"], r["ground_truth"]["sim_equiv"], ok(r["lint"]), ok(r["sim"]),
            (" (%d)" % r["sim_mismatches"]) if r.get("sim_mismatches") else "", r.get("eqy", "-"), ok(r["structural"]),
            ok(r["contract"]) if r["contracts_on_original"] else "n/a"))
    # detection summary per operator
    md += ["", "| Operator | n | CDC-safe | Sim flags | EQY flags | Structural flags | Contract flags | Any CDC checker |", "|---|---|---|---|---|---|---|---|"]
    ops = sorted({r["operator"] for r in rows})
    for op in ops:
        rs = [r for r in rows if r["operator"] == op]
        cnt = lambda f: sum(1 for r in rs if f(r))
        md.append("| %s | %d | %s | %d | %d | %d | %d | %d |" % (
            op, len(rs), rs[0]["ground_truth"]["cdc_safe"], cnt(lambda r: r["sim"] is False),
            cnt(lambda r: r.get("eqy") not in (None, "PASS")), cnt(lambda r: not r["structural"]),
            cnt(lambda r: r["contracts_on_original"] and not r["contract"]),
            cnt(lambda r: not r["structural"] or (r["contracts_on_original"] and not r["contract"]))))
    return "\n".join(md) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--no-eqy", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    jobs, rows = [], []
    for d in a.design:
        D = load_design(d)
        verilator_ok = aegis_verify.lint(D, D["rtl"], True, False)["pass"]
        for mid in sorted(os.listdir(os.path.join(a.out, d))):
            mdir = os.path.join(a.out, d, mid)
            if not os.path.isfile(os.path.join(mdir, "meta.json")) or (a.only and a.only not in mid):
                continue
            if os.path.exists(os.path.join(mdir, "label.json")) and not a.redo:
                rows.append(json.load(open(os.path.join(mdir, "label.json"))))
                continue
            jobs.append((d, mdir, not a.no_eqy, verilator_ok))
    with ProcessPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(label_one, *j): j for j in jobs}
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                print("FAILED", futs[f][1], repr(e)[:300], flush=True)
                continue
            rows.append(r)
            print("%-16s %-36s gt_safe=%-5s sim=%-5s eqy=%-7s struct=%-5s contract=%-5s %s" % (
                r["design"], r["id"][:36], r["ground_truth"]["cdc_safe"], r["sim"], r.get("eqy"), r["structural"],
                r["contract"], r["time_s"]), flush=True)
    res_dir = os.path.join(HERE, "results")
    os.makedirs(res_dir, exist_ok=True)
    allrows = {}
    p = os.path.join(res_dir, "labels.jsonl")
    if os.path.exists(p):
        for line in open(p):
            r = json.loads(line)
            allrows[(r["design"], r["id"])] = r
    for r in rows:
        allrows[(r["design"], r["id"])] = r
    with open(p, "w") as f:
        for r in allrows.values():
            f.write(json.dumps(r) + "\n")
    open(os.path.join(res_dir, "labels.md"), "w").write(table(list(allrows.values())))
    print(table(rows))


if __name__ == "__main__":
    main()
