#!/usr/bin/env python3
"""
AEGIS Phase 5 -- Metric Evaluator (deterministic).

  python3 aegis_eval.py --design soc --base-rtl <B_n files> --cand-rtl <cand files> \\
      --scope wptr_full [--scope ...] --base-metrics work/soc/v0/sta/metrics.json \\
      --out cand/<rid>/C1/eval [--alpha 0.6 --beta 0.3 --gamma 0.1] [--scalar]

  1. EQY (hard gate): gold = B_n, gate = candidate, one job per scope module
     (the modules that contain the region's edit envelope), SBY strategy with
     k-induction. PASS on every scope is required; FAIL, UNKNOWN or timeout
     disqualifies the candidate (never a soft penalty).
  2. OpenSTA on the full candidate (aegis_sta.py, same flow as the baseline).
  3. Domain-aware score (Eq. score of the paper), lower is better, relative to B_n:

       Score = sum_d w_d (alpha*Wn_d + beta*Tn_d) / sum_d w_d + gamma*f(An) + P_CDC + P_SEC
       Wn_d  = (Dmax_d(i) - Dmax_d(B)) / max(Dmax_d(B), 0.01*T_d)    worst margin deficit
       Tn_d  = (Dsum_d(i) - Dsum_d(B)) / max(Dsum_d(B), 0.01*T_d)    total margin deficit
       An    = (A(i) - A(B)) / A(B);  f(A) = A + lambda*(A-0.05)^2 for A > 0.05
       w_d   = f_d / f_max

     Deficits are measured against the closure margin m over endpoints whose
     launch/capture clocks are not asynchronous (same rule as Phase 2), so B_n scores 0.
     --scalar gives the ablation score (Dr. RTL style, design-level WNS/TNS, no w_d).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aegis_common import load_design, read_cmd, which, ROOT, run_tree  # noqa: E402

PENALTY = 1e4
STA = which("sta", ["~/karuppu/.tools/OpenSTA/build/sta", "~/OpenSTA/build/sta"])


# ----------------------------------------------------------------------------
def eqy(base, cand, scope, workdir, depth=8, timeout=1200):
    os.makedirs(workdir, exist_ok=True)
    # memories are mapped to flops on both sides: SBY cannot reason about $mem_v2 cells
    # inside a partition once gold and gate memories differ structurally
    prep = ["prep -top %s" % scope, "memory_map", "opt_clean"]
    cfg = "\n".join(["[gold]", read_cmd(base).replace("; ", "\n")] + prep + ["",
                     "[gate]", read_cmd(cand).replace("; ", "\n")] + prep + ["",
                     "[strategy sby]", "use sby", "depth %d" % depth, "engine smtbmc z3", ""])
    path = os.path.join(workdir, "%s.eqy" % scope)
    open(path, "w").write(cfg)
    run_dir = os.path.join(workdir, "eqy_" + scope)
    shutil.rmtree(run_dir, ignore_errors=True)
    try:
        r = run_tree(["eqy", "-f", "-d", run_dir, path], timeout=timeout)
        log = r.stdout + r.stderr
        status = "PASS" if r.returncode == 0 and "DONE (PASS" in log else ("FAIL" if "DONE (FAIL" in log else "ERROR")
    except subprocess.TimeoutExpired:
        log, status = "timeout after %ds" % timeout, "TIMEOUT"
    open(os.path.join(workdir, "eqy_%s.log" % scope), "w").write(log)
    failed = [l.split("partition", 1)[1].strip() for l in log.splitlines() if "Failed to prove equivalence of partition" in l]
    return {"scope": scope, "status": status, "failed_partitions": failed[:20]}


def sta(design, files, out, margin):
    r = subprocess.run([sys.executable, os.path.join(HERE, "aegis_sta.py"), "--rtl"] + files +
                       ["--top", design["top"], "--sdc", design["sdc"], "--liberty", design["liberty"],
                        "--out", out, "--margin", str(margin), "--sta", STA] +
                       (["--abc-delay-ps", str(design["abc_delay_ps"])] if design.get("abc_delay_ps") else []) +
                       (["--abc-timing"] if design.get("abc_timing", True) and design.get("abc_delay_ps") else []),
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-800:]
    return json.load(open(os.path.join(out, "metrics.json"))), None


# ----------------------------------------------------------------------------
def deficits(metrics, phase1, margin):
    """Per capture clock: worst and total deficit against the margin, async endpoints excluded."""
    from aegis_select import parse_report
    rel = json.load(open(os.path.join(phase1, "clock_relations.json")))
    rel = rel.get("relations", rel)
    eps = parse_report(open(metrics["files"]["endpoints"]).read())
    out = {}
    for e in eps:
        c, l = e.get("capture_clock"), e.get("launch_clock")
        if not c:
            continue
        r = rel.get(l, {}).get(c) if l else None
        if r == "asynchronous":
            continue
        d = max(0.0, margin - e["slack_ns"])
        o = out.setdefault(c, {"dmax": 0.0, "dsum": 0.0, "n": 0})
        o["dmax"] = max(o["dmax"], d)
        o["dsum"] += d
        o["n"] += d > 0
    for p in metrics.get("per_domain", []):
        out.setdefault(p["clock"], {"dmax": 0.0, "dsum": 0.0, "n": 0})
    return out


def score(cand_m, base_m, phase1, margin, alpha, beta, gamma, scalar=False, lam=10.0, p_cdc=False, p_sec=False):
    clocks = json.load(open(os.path.join(phase1, "clocks.json")))["clocks"]
    dc, db = deficits(cand_m, phase1, margin), deficits(base_m, phase1, margin)
    area_n = (cand_m["area_um2"] - base_m["area_um2"]) / base_m["area_um2"] if base_m.get("area_um2") else 0.0
    per = {}
    if scalar:
        wb = max([v["dmax"] for v in db.values()] or [0.0])
        wc = max([v["dmax"] for v in dc.values()] or [0.0])
        tb, tc = sum(v["dsum"] for v in db.values()), sum(v["dsum"] for v in dc.values())
        eps = 0.01 * min(v["period_ns"] for v in clocks.values() if v.get("period_ns"))
        s = 0.5 * (wc - wb) / max(wb, eps) + 0.35 * (tc - tb) / max(tb, eps) + 0.15 * area_n + (0.5 if area_n > 0.10 else 0.0)
    else:
        fmax = max(1.0 / v["period_ns"] for v in clocks.values() if v.get("period_ns"))
        num = den = 0.0
        for d in sorted(set(dc) | set(db)):
            T = clocks.get(d, {}).get("period_ns")
            if not T:
                continue
            w = (1.0 / T) / fmax
            b, c = db.get(d, {"dmax": 0.0, "dsum": 0.0}), dc.get(d, {"dmax": 0.0, "dsum": 0.0})
            eps = 0.01 * T
            wn = (c["dmax"] - b["dmax"]) / max(b["dmax"], eps)
            tn = (c["dsum"] - b["dsum"]) / max(b["dsum"], eps)
            per[d] = {"w": round(w, 4), "wns_norm": round(wn, 4), "tns_norm": round(tn, 4),
                      "dmax_base": round(b["dmax"], 4), "dmax": round(c["dmax"], 4),
                      "dsum_base": round(b["dsum"], 4), "dsum": round(c["dsum"], 4)}
            num += w * (alpha * wn + beta * tn)
            den += w
        fa = area_n if area_n <= 0.05 else area_n + lam * (area_n - 0.05) ** 2
        s = (num / den if den else 0.0) + gamma * fa
    s += (PENALTY if p_cdc else 0.0) + (PENALTY if p_sec else 0.0)
    met = all(v["dmax"] == 0 for v in dc.values())
    regress = [d for d in per if per[d]["dmax"] > per[d]["dmax_base"] + 1e-9]
    return {"score": round(s, 6), "area_norm": round(area_n, 6), "per_domain": per, "timing_met": met,
            "regressed_domains": regress, "scalar": scalar}


# ----------------------------------------------------------------------------
def evaluate(design, base, cand, scopes, base_metrics, out, alpha, beta, gamma, scalar=False, phase1=None,
             skip_eqy=False, eqy_depth=8):
    phase1 = phase1 or os.path.join(ROOT, "flow", "work", design["name"], "phase1")
    os.makedirs(out, exist_ok=True)
    res = {"eqy": [], "sec_pass": None, "metrics": None, "score": None}
    if not skip_eqy:
        for s in scopes:
            res["eqy"].append(eqy(base, cand, s, os.path.join(out, "eqy"), depth=eqy_depth,
                                  timeout=int(design.get("eqy_timeout_s", 1200))))
        res["sec_pass"] = all(e["status"] == "PASS" for e in res["eqy"])
    m, err = sta(design, cand, os.path.join(out, "sta"), design.get("margin", 0.1))
    if m is None:
        res["sta_error"] = err
    else:
        res["metrics"] = {k: m[k] for k in ("wns_ns", "tns_ns", "area_um2", "per_domain")}
        bm = json.load(open(base_metrics))
        res["score"] = score(m, bm, phase1, design.get("margin", 0.1), alpha, beta, gamma, scalar,
                             p_sec=(res["sec_pass"] is False))
    json.dump(res, open(os.path.join(out, "eval.json"), "w"), indent=1)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True)
    ap.add_argument("--base-rtl", nargs="+", required=True)
    ap.add_argument("--cand-rtl", nargs="+", required=True)
    ap.add_argument("--scope", action="append", default=[])
    ap.add_argument("--base-metrics", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--alpha", type=float, default=0.6)
    ap.add_argument("--beta", type=float, default=0.3)
    ap.add_argument("--gamma", type=float, default=0.1)
    ap.add_argument("--scalar", action="store_true")
    ap.add_argument("--skip-eqy", action="store_true")
    a = ap.parse_args()
    d = load_design(a.design)
    r = evaluate(d, a.base_rtl, a.cand_rtl, a.scope or [d["top"]], a.base_metrics, a.out, a.alpha, a.beta, a.gamma,
                 a.scalar, skip_eqy=a.skip_eqy)
    print(json.dumps({"sec_pass": r["sec_pass"], "eqy": [(e["scope"], e["status"]) for e in r["eqy"]],
                      "wns": (r["metrics"] or {}).get("wns_ns"), "score": (r["score"] or {}).get("score")}))


if __name__ == "__main__":
    main()
