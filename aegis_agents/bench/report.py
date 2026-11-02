#!/usr/bin/env python3
"""
Aggregate flow/runs/*/*/summary.json into the paper's tables (mean +- std over repetitions).

  python3 bench/report.py [--out bench/results]

Writes results/runs.csv (one row per run) and results/report.md with
  T1  per design and configuration: WNS/TNS/area change vs the synthesis-only baseline,
      SEC (EQY) pass rate of candidates, lock / CDC violations measured, LLM tokens and cost;
  T2  per-domain worst deficit before/after (multi-clock designs);
  T3  rejection reasons per configuration (where the guardrails fire).
Numbers are computed only from run logs; a configuration with no completed run is omitted.
"""
import argparse
import csv
import glob
import json
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def ms(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return "-"
    m = sum(xs) / len(xs)
    if len(xs) == 1:
        return "%.2f" % m
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return "%.2f ± %.2f" % (m, s)


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return 100.0 * (a - b) / abs(b)


def load():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "flow", "runs", "*", "*", "summary.json"))):
        S = json.load(open(p))
        cfg = S["run_id"].split(".")[0]
        if S["run_id"].startswith("smoke"):
            continue
        b, f = S["baseline"], S["final"]
        c = S["candidates"]
        tot = max(c["total"], 1)
        rows.append({"design": S["design"], "config": cfg, "model": S["model"], "run_id": S["run_id"],
                     "iterations": S["iterations"], "wns_base": b["wns_ns"], "wns_final": f["wns_ns"],
                     "tns_base": b["tns_ns"], "tns_final": f["tns_ns"], "area_base": b["area_um2"],
                     "area_final": f["area_um2"],
                     "dwns_pct": pct(f["wns_ns"], b["wns_ns"]) if b["wns_ns"] and b["wns_ns"] < 0 else None,
                     "dtns_pct": pct(f["tns_ns"], b["tns_ns"]) if b["tns_ns"] and b["tns_ns"] < 0 else None,
                     "darea_pct": pct(f["area_um2"], b["area_um2"]),
                     "candidates": c["total"], "sec_pass_rate": 100.0 * c["sec_pass"] / tot,
                     "lock_violations": c["measured_lock_violations"], "cdc_violations": c["measured_cdc_violations"],
                     "reasons": c["by_reason"], "final_check": S.get("final_check"),
                     "tokens": S["llm"]["tokens_in"] + S["llm"]["tokens_out"], "cost_usd": S["llm"]["cost_usd"],
                     "wall_s": S["wall_clock_s"], "per_domain_base": b["per_domain"], "per_domain_final": f["per_domain"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    a = ap.parse_args()
    rows = load()
    os.makedirs(a.out, exist_ok=True)
    keys = ["design", "config", "model", "run_id", "iterations", "wns_base", "wns_final", "dwns_pct", "tns_base",
            "tns_final", "dtns_pct", "area_base", "area_final", "darea_pct", "candidates", "sec_pass_rate",
            "lock_violations", "cdc_violations", "tokens", "cost_usd", "wall_s"]
    with open(os.path.join(a.out, "runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    g = defaultdict(list)
    for r in rows:
        g[(r["design"], r["config"], r["model"])].append(r)
    md = ["# AEGIS benchmark report", "", "Generated from %d run summaries. Changes are relative to the synthesis-only "
          "baseline (Yosys + delay-driven ABC, Nangate45, OpenSTA); negative WNS/TNS %% = less negative slack." % len(rows), "",
          "## T1. Results per design and configuration", "",
          "| Design | Config | Model | Runs | ΔWNS % | ΔTNS % | ΔArea % | SEC pass % | Lock viol. | CDC viol. | Tokens (k) | Wall (min) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (d, c, m), rs in sorted(g.items()):
        md.append("| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            d, c, m.replace("claude-", ""), len(rs), ms([-x if x is not None else None for x in (r["dwns_pct"] for r in rs)]),
            ms([-x if x is not None else None for x in (r["dtns_pct"] for r in rs)]), ms([r["darea_pct"] for r in rs]),
            ms([r["sec_pass_rate"] for r in rs]), ms([r["lock_violations"] for r in rs]),
            ms([r["cdc_violations"] for r in rs]), ms([r["tokens"] / 1000 for r in rs]), ms([r["wall_s"] / 60 for r in rs])))
    md += ["", "ΔWNS/ΔTNS are reported as improvement (positive = better).", "",
           "## T2. Per-domain WNS before / after (first run of each configuration)", "",
           "| Design | Config | Domain | WNS base (ns) | WNS final (ns) | TNS base | TNS final |", "|---|---|---|---|---|---|---|"]
    for (d, c, m), rs in sorted(g.items()):
        r = rs[0]
        fin = {p["clock"]: p for p in r["per_domain_final"]}
        for p in r["per_domain_base"]:
            q = fin.get(p["clock"], {})
            md.append("| %s | %s | %s | %s | %s | %s | %s |" % (d, c, p["clock"], p["wns_ns"], q.get("wns_ns"),
                                                                 p["tns_ns"], q.get("tns_ns")))
    md += ["", "## T3. Candidate rejection reasons (summed over runs)", "", "| Config | Model | Candidates | Reasons |", "|---|---|---|---|"]
    agg = defaultdict(lambda: defaultdict(int))
    tot = defaultdict(int)
    for r in rows:
        k = (r["config"], r["model"])
        tot[k] += r["candidates"]
        for why, n in r["reasons"].items():
            agg[k][why] += n
    for k in sorted(agg):
        md.append("| %s | %s | %d | %s |" % (k[0], k[1].replace("claude-", ""), tot[k],
                                             ", ".join("%s: %d" % x for x in sorted(agg[k].items(), key=lambda x: -x[1]))))
    md += ["", "## T4. End-to-end check of each final design against the original RTL", "",
           "| Design | Run | Phase 4 vs v0 | Measured violations | EQY (top) vs v0 |", "|---|---|---|---|---|"]
    for r in rows:
        fc = r["final_check"]
        if fc:
            md.append("| %s | %s | %s | %s | %s |" % (r["design"], r["run_id"], fc["verify"],
                                                     ",".join(fc["measured_violations"]) or "none", fc["eqy_top_vs_v0"]))
    open(os.path.join(a.out, "report.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
