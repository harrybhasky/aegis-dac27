#!/usr/bin/env python3
"""
Candidate-level CDC audit (2026-11-02): how many LLM-generated candidates that the FUNCTIONAL gates accept
(simulation and EQY) are flagged by the CDC re-check? Evidence from real LLM rewrites, not injected mutants.

For every candidate of every finished run (Dr. RTL minors work/v*/drrtl/m*, vanilla work/v*/vanilla/V*, Aegis and
ablation region candidates work/v*/regions/*/C*):
  sim  = verify.json stages.sim.pass (None if not run)
  eqy  = eval/eval.json sec_pass (None if not evaluated; for Aegis the scope is the edited modules, for Dr. RTL
         and vanilla the top module)
  cdc  = aegis_verify.cdc on the candidate vs the ORIGINAL design's Phase 1, with the current checker
         (cached in <cand>/cdc_audit.json)
Writes bench/results/candidate_audit.{json,md}.

  python3 bench/candidate_audit.py [--design d ...] [--config c ...] [--redo]
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402

PATTERNS = ["work/v*/drrtl/m*", "work/v*/vanilla/V*", "work/v*/regions/*/C*"]
CHECKER = "aegis_verify.cdc, Phase 1 of 2026-11-02"


def load(p):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return None


def audit_candidate(D, cdir, p1, redo):
    cache = os.path.join(cdir, "cdc_audit.json")
    if os.path.exists(cache) and not redo:
        c = load(cache)
        if c and c.get("checker") == CHECKER:
            return c
    files = sorted(glob.glob(os.path.join(cdir, "rtl", "*.v")) + glob.glob(os.path.join(cdir, "rtl", "*.sv")))
    if not files:
        return None
    r = aegis_verify.cdc(D, files, p1)
    c = {"checker": CHECKER, "pass": r["pass"], "violations": r["violations"][:10],
         "recoded_storage": len(r.get("recoded_storage", []))}
    json.dump(c, open(cache, "w"), indent=1)
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append")
    ap.add_argument("--config", action="append")
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    rows = []
    for s in sorted(glob.glob(os.path.join(ROOT, "flow", "runs", "*", "*.sonnet-5-5.r*", "summary.json"))):
        run = os.path.dirname(s)
        d, rid = run.split(os.sep)[-2], os.path.basename(run)
        cfg = rid.split(".")[0]
        if (a.design and d not in a.design) or (a.config and cfg not in a.config):
            continue
        D = load_design(d)
        p1 = os.path.join(ROOT, "flow", "work", d, "phase1")
        for pat in PATTERNS:
            for cdir in sorted(glob.glob(os.path.join(run, pat))):
                if not os.path.isdir(os.path.join(cdir, "rtl")):
                    continue
                v = load(os.path.join(cdir, "verify.json")) or {}
                e = load(os.path.join(cdir, "eval", "eval.json")) or {}
                sim = ((v.get("stages") or {}).get("sim") or {}).get("pass")
                try:
                    c = audit_candidate(D, cdir, p1, a.redo)
                except Exception as ex:  # noqa: BLE001 - recorded, audit continues
                    c = {"pass": None, "violations": ["audit error: %r" % ex][:1]}
                if c is None:
                    continue
                rows.append({"design": d, "run": rid, "config": cfg, "cand": os.path.relpath(cdir, run),
                             "sim": sim, "eqy": e.get("sec_pass"), "cdc": c["pass"], "cdc_violations": c["violations"],
                             "reject_reason": v.get("reject_reason")})
                print("%-18s %-24s %-28s sim=%-5s eqy=%-5s cdc=%s" % (d, rid, rows[-1]["cand"], sim, e.get("sec_pass"),
                                                                      c["pass"]), flush=True)
    out = os.path.join(HERE, "results")
    os.makedirs(out, exist_ok=True)
    json.dump(rows, open(os.path.join(out, "candidate_audit.json"), "w"), indent=1)
    md = ["| Config | Candidates | CDC-flagged | Sim+EQY accepted | ...of which CDC-flagged |", "|---|---|---|---|---|"]
    for cfg in sorted({r["config"] for r in rows}):
        R = [r for r in rows if r["config"] == cfg]
        acc = [r for r in R if r["sim"] is not False and r["eqy"] is True]
        md.append("| %s | %d | %d | %d | %d |" % (cfg, len(R), sum(r["cdc"] is False for r in R), len(acc),
                                                sum(r["cdc"] is False for r in acc)))
    md += ["", "Accepted by simulation and EQY but flagged by the CDC re-check:", ""]
    for r in rows:
        if r["sim"] is not False and r["eqy"] is True and r["cdc"] is False:
            md.append("- %s %s %s: %s" % (r["design"], r["run"], r["cand"], "; ".join(r["cdc_violations"][:3])))
    open(os.path.join(out, "candidate_audit.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md[:2 + len({r['config'] for r in rows})]))


if __name__ == "__main__":
    main()
