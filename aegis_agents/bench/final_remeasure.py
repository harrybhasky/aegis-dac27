#!/usr/bin/env python3
"""
Final re-measurement of finished runs with ONE checker and ONE flow, whatever the configuration (2026-11-02).

For every run flow/runs/<design>/<config>.sonnet-5-5.r1 with a summary.json:
  * CDC re-check (aegis_verify.cdc) and lock checksums of the FINAL design against the current Phase 1 of the
    original design -- measurement only, so all configurations are judged by the same, final checker;
  * flattened re-synthesis + STA of the original and the final design (aegis_sta.py --flatten): gains that rely
    only on module boundaries disappear (the robustness check of key_findings/12).
Writes <run>/final_remeasure.json; summary.json is never modified.

  python3 bench/final_remeasure.py [--design d ...] [--config c ...] [--redo] [--no-flat]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
import aegis_eval  # noqa: E402
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402

CHECKER = "aegis_verify.cdc + lock checksums, Phase 1 of 2026-11-02 (internal-register Gray contracts, recoded storage)"


def flat_sdc(sdc, out):
    """Hierarchical pin references (a/b/x_reg/Q) do not exist after flattening: the flop is renamed and only its
    output net keeps the hierarchical name (a.b.x). Point them at the driver pin of that net instead."""
    t = open(sdc).read()
    t2 = re.sub(r"\[get_pins\s+\{?((?:[\w\[\]]+/)+)(\w+?)_reg/Q\}?\]",
                lambda m: '[get_pins -of_objects [get_nets {%s%s}] -filter "direction == output"]' % (
                    m.group(1).replace("/", "."), m.group(2)), t)
    if t2 == t:
        return sdc
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, "flat.sdc")
    open(p, "w").write(t2)
    return p


def flat_sta(D, files, out):
    """aegis_sta.py with --flatten and the same options aegis_eval.sta uses."""
    if os.path.exists(os.path.join(out, "metrics.json")):
        return json.load(open(os.path.join(out, "metrics.json")))
    cmd = [sys.executable, os.path.join(ROOT, "tools", "aegis_sta.py"), "--rtl"] + files + [
        "--top", D["top"], "--sdc", flat_sdc(D["sdc"], out), "--liberty", D["liberty"], "--out", out,
        "--margin", str(D.get("margin", 0.1)), "--sta", aegis_eval.STA, "--flatten"]
    if D.get("abc_delay_ps"):
        cmd += ["--abc-delay-ps", str(D["abc_delay_ps"])]
        if D.get("abc_timing", True):
            cmd += ["--abc-timing"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-600:]}
    return json.load(open(os.path.join(out, "metrics.json")))


def worst(m):
    return min(x["wns_ns"] for x in m["per_domain"]) if m and m.get("per_domain") else None


def one(run, flat=True):
    S = json.load(open(os.path.join(run, "summary.json")))
    D = load_design(S["design"])
    p1 = os.path.join(ROOT, "flow", "work", S["design"], "phase1")
    fv = S["final_version"]
    final = sorted(glob.glob(os.path.join(run, "rtl", fv, "*.v"))) if fv != "v0" else list(D["rtl"])
    res = {"checker": CHECKER, "final_version": fv}
    if fv == "v0":
        res.update(cdc_pass=True, cdc_violations=[], lock_pass=True, note="nothing promoted")
    else:
        c = aegis_verify.cdc(D, final, p1)
        g = aegis_verify.gate(D, D["rtl"], final, None, os.path.join(p1, "checksums.json"))
        res.update(cdc_pass=c["pass"], cdc_violations=c["violations"][:20], recoded_storage=len(c.get("recoded_storage", [])),
                   resourced_unsafe=c.get("resourced_unsafe", []), lock_pass=bool(g["checksum"].get("pass")),
                   lock_failures=g["checksum"].get("failures", [])[:10])
    if flat:
        base = flat_sta(D, list(D["rtl"]), os.path.join(ROOT, "flow", "work", S["design"], "flat_v0_sta"))
        fin = base if fv == "v0" else flat_sta(D, final, os.path.join(run, "final_flat_sta"))
        res["flat"] = {"base_wns": worst(base), "final_wns": worst(fin),
                       "base_tns": base.get("tns_ns"), "final_tns": fin.get("tns_ns"),
                       "base_area": base.get("area_um2"), "final_area": fin.get("area_um2"),
                       "error": base.get("error") or fin.get("error")}
    json.dump(res, open(os.path.join(run, "final_remeasure.json"), "w"), indent=1)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append")
    ap.add_argument("--config", action="append")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--no-flat", action="store_true")
    a = ap.parse_args()
    for s in sorted(glob.glob(os.path.join(ROOT, "flow", "runs", "*", "*.sonnet-5-5.r1", "summary.json"))):
        run = os.path.dirname(s)
        d, cfg = run.split(os.sep)[-2], os.path.basename(run).split(".")[0]
        if (a.design and d not in a.design) or (a.config and cfg not in a.config):
            continue
        if os.path.exists(os.path.join(run, "final_remeasure.json")) and not a.redo:
            continue
        try:
            r = one(run, flat=not a.no_flat)
        except Exception as e:  # noqa: BLE001 - recorded, next run continues
            print("FAILED %s/%s: %r" % (d, cfg, e)[:300], flush=True)
            continue
        f = r.get("flat", {})
        print("%-22s %-8s cdc=%-5s lock=%-5s flatWNS %s -> %s %s" % (
            d, cfg, r["cdc_pass"], r["lock_pass"], f.get("base_wns"), f.get("final_wns"), f.get("error") or ""), flush=True)


if __name__ == "__main__":
    main()
