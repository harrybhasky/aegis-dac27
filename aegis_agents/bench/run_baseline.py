#!/usr/bin/env python3
"""
No-LLM baseline for every design in flow/designs/: Phase 1 (shield) and two synthesis
flows, written to bench/results/baseline.json and baseline.md.

  raw        Yosys synth + ABC area-oriented mapping (no delay target)
  synth      Yosys synth + timing-driven ABC (abc -D = fastest clock period, delay mapping,
             buffering, gate up/down-sizing);
             the "synthesis-only" column: what the tool achieves with no LLM involved.
             All Aegis / vanilla runs are measured with this same flow.

  python3 bench/run_baseline.py [--designs a b ...] [--jobs 4]
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from aegis_common import load_design, which  # noqa: E402

STA = which("sta", ["~/karuppu/.tools/OpenSTA/build/sta"])
OUT = os.path.join(HERE, "results")


def sta(D, out, delay):
    cmd = [sys.executable, os.path.join(ROOT, "tools", "aegis_sta.py"), "--rtl"] + D["rtl"] + [
        "--top", D["top"], "--sdc", D["sdc"], "--liberty", D["liberty"], "--out", out,
        "--margin", str(D.get("margin", 0.1)), "--sta", STA]
    if delay:
        cmd += ["--abc-delay-ps", str(delay), "--abc-timing"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-600:]}
    m = json.load(open(os.path.join(out, "metrics.json")))
    cells = None
    try:
        txt = open(os.path.join(out, "area.txt")).read()
        import re
        c = re.findall(r"Number of cells:\s+(\d+)", txt) or re.findall(r"^\s+(\d+)\s+[\d.]+\s+cells", txt, re.M)
        cells = int(c[-1]) if c else None
    except OSError:
        pass
    return {"wns_ns": m["wns_ns"], "tns_ns": m["tns_ns"], "area_um2": m["area_um2"], "cells": cells,
            "per_domain": m["per_domain"], "time_s": round(time.time() - t0, 1)}


def one(name):
    D = load_design(name)
    work = os.path.join(ROOT, "flow", "work", name)
    res = {"design": name, "top": D["top"], "suite": D.get("suite", "cdc")}
    t0 = time.time()
    cmd = [sys.executable, os.path.join(ROOT, "tools", "aegis_ingest.py"), "ingest", "--rtl"] + D["rtl"] + [
        "--top", D["top"], "--sdc", D["sdc"], "--contracts-tool", os.path.join(ROOT, "tools", "gen_cdc_props.py"),
        "--out", os.path.join(work, "phase1")]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if r.returncode == 0:
        p = json.load(open(os.path.join(work, "phase1", "phase1_report.json")))
        res["phase1"] = {k: p.get(k) for k in ("clocks", "asynchronous_pairs", "constraint_audit", "flops",
                                                "unclocked_flops", "crossings", "contracts_proven", "immutable_lines",
                                                "contract_lines", "checksum_entries")}
        res["phase1"]["issues"] = len(p.get("issues", []))
        res["phase1"]["time_s"] = round(time.time() - t0, 1)
    else:
        res["phase1"] = {"error": (r.stderr or r.stdout)[-600:]}
    res["raw"] = sta(D, os.path.join(work, "baseline_raw"), None)
    res["synth"] = sta(D, os.path.join(work, "baseline_synth"), D.get("abc_delay_ps"))
    print(json.dumps({"design": name, "phase1": (res["phase1"] or {}).get("crossings"),
                      "raw_wns": res["raw"].get("wns_ns"), "synth_wns": res["synth"].get("wns_ns")}), flush=True)
    return res


def table(rows):
    h = ["| Design | Suite | Clocks | Flops | Sync | Gray | Qual | 1-flop | Unsync | Contracts | Locked lines | "
         "WNS raw | WNS synth | TNS synth | Area synth (um2) |", "|" + "---|" * 15]
    for r in rows:
        p = r.get("phase1", {})
        x = p.get("crossings") or {}
        f = lambda v: "-" if v is None else ("%.3f" % v if isinstance(v, float) else str(v))
        h.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["design"], r["suite"], f(p.get("clocks")), f(p.get("flops")), f(x.get("synchronizer")),
            f(x.get("gray_candidate")), f(x.get("qualified_capture")), f(x.get("insufficient_depth")),
            f(x.get("unsynchronized")), len(p.get("contracts_proven") or []), f(p.get("immutable_lines")),
            f(r["raw"].get("wns_ns")), f(r["synth"].get("wns_ns")), f(r["synth"].get("tns_ns")),
            f(r["synth"].get("area_um2"))))
    return "\n".join(h) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", nargs="*")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    names = a.designs or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "flow", "designs", "*", "design.json")))
    os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = list(ex.map(one, names))
    os.makedirs(OUT, exist_ok=True)
    old = {}
    if os.path.exists(os.path.join(OUT, "baseline.json")):
        old = {r["design"]: r for r in json.load(open(os.path.join(OUT, "baseline.json")))}
    for r in rows:
        old[r["design"]] = r
    rows = [old[k] for k in sorted(old, key=lambda n: (old[n]["suite"] != "cdc", n))]
    json.dump(rows, open(os.path.join(OUT, "baseline.json"), "w"), indent=1)
    open(os.path.join(OUT, "baseline.md"), "w").write(table(rows))
    print(table(rows))


if __name__ == "__main__":
    main()
