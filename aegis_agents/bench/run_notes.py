#!/usr/bin/env python3
"""
Write RUN_NOTES.md for finished runs: what was run, per-domain timing before/after, every iteration and
candidate, the final RTL change, and an explicit "why it improved / why not" section.

  python3 bench/run_notes.py flow/runs/<design>/<run-id> [...]          # specific runs
  python3 bench/run_notes.py --all [--copy-to <dir>] [--only-missing]    # every run with a summary.json

Everything is read from the run's own files (summary.json, events.json, work/*/iteration.json,
work/*/sel/selection.json and diag/, work/*/sta/endpoints.rpt, rtl/); nothing is recomputed or estimated.
"""
import argparse
import difflib
import glob
import json
import os
import re
import shutil
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODE_TEXT = {
    "aegis": "full AEGIS pipeline (Phase 1 locks/contracts, per-domain region selection, diagnosis, skill matching, "
             "5 candidates per region, gated verification: checksum/envelope, lint, simulation, CDC re-check, EQY)",
    "vanilla": "unguarded baseline: the model gets the whole RTL + timing summary and returns a rewrite; no locks, "
               "no skills, no gating; every check is only measured; best-scoring synthesizable candidate promoted",
    "drrtl": "Dr. RTL's own analyzer/optimizer agents + skill.md (tools/drrtl_port.py); single global score "
             "(0.5 WNS + 0.35 TNS + 0.15 area); promotion requires SEC (EQY) pass only",
}


def load(p, default=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def skill_titles():
    idx = load(os.path.join(ROOT, "flow", "skills", "skills_index.json"), []) or []
    return {e["id"]: e["title"] for e in idx}


def cross_clock_violators(rpt):
    """Violating endpoints whose launch and capture clocks differ, from an endpoints.rpt."""
    out = []
    if not rpt or not os.path.exists(rpt):
        return out
    for blk in open(rpt).read().split("Startpoint:")[1:]:
        lc = re.search(r"clocked by (\S+?)\)", blk.split("\n", 1)[0])
        ep = re.search(r"Endpoint:\s*(\S+).*?clocked by (\S+?)\)", blk)
        sl = re.search(r"(-?\d+\.\d+)\s+slack", blk)
        if lc and ep and sl and lc.group(1) != ep.group(2) and float(sl.group(1)) < 0:
            out.append((ep.group(1), lc.group(1), ep.group(2), float(sl.group(1))))
    return out


def dom_table(S):
    b = {p["clock"]: p for p in S["baseline"]["per_domain"]}
    f = {p["clock"]: p for p in S["final"]["per_domain"]}
    rows, changes = [], {}
    for c in sorted(b):
        bw, fw = b[c].get("wns_ns"), (f.get(c) or {}).get("wns_ns")
        bt, ft = b[c].get("tns_ns"), (f.get(c) or {}).get("tns_ns")
        d = None if bw is None or fw is None else round(fw - bw, 4)
        changes[c] = (bw, fw, d)
        rows.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            c, bw, fw, "%+.3f" % d if d is not None else "-", bt, ft,
            "%s -> %s" % (b[c].get("violating_endpoints"), (f.get(c) or {}).get("violating_endpoints"))))
    return rows, changes


def rtl_diff(run, final):
    if final == "v0":
        return None
    a, b = sorted(glob.glob(os.path.join(run, "rtl", "v0", "*"))), sorted(glob.glob(os.path.join(run, "rtl", final, "*")))
    out = []
    for fa in a:
        fb = os.path.join(run, "rtl", final, os.path.basename(fa))
        if os.path.exists(fb):
            out += list(difflib.unified_diff(open(fa).read().splitlines(), open(fb).read().splitlines(),
                                             "v0/" + os.path.basename(fa), final + "/" + os.path.basename(fb), lineterm="", n=2))
    return out


def candidates_of(it):
    cs = []
    for r in it.get("regions", []) or []:
        for c in r.get("candidates", []):
            cs.append(dict(c, region=r.get("region_id"), root_cause=r.get("root_cause")))
    cs += it.get("candidates", []) or []
    return cs


def notes(run):
    S = load(os.path.join(run, "summary.json"))
    if not S:
        return None
    mode = S.get("mode") or S["run_id"].split(".")[0]
    ev = load(os.path.join(run, "events.json"), []) or []
    titles = skill_titles()
    iters = []
    for n in range(1, (S.get("iterations") or 0) + 1):
        it = load(os.path.join(run, "work", "v%d" % n, "iteration.json"))
        if it:
            iters.append(it)
    L = ["# Run notes: %s / %s" % (S["design"], S["run_id"]), "",
         "Generated from this run's logs by `bench/run_notes.py`; no number here is estimated.", "",
         "## What was run", "",
         "- Design `%s`, configuration **%s**: %s." % (S["design"], mode, MODE_TEXT.get(mode, mode)),
         "- Model `%s` via `%s`; %s iteration(s); final version `%s`; wall clock %ss." % (
             S["model"], S["backend"], S["iterations"], S["final_version"], S.get("wall_clock_s")),
         "- LLM: %s calls, %s errors, %s tokens in / %s out, $%s (API-equivalent, from the CLI)." % (
             S["llm"]["calls"], S["llm"]["errors"], S["llm"]["tokens_in"], S["llm"]["tokens_out"], S["llm"]["cost_usd"]),
         "- Flow: Yosys 0.67 + Nangate45 (synthesis-only, delay-driven ABC) + OpenSTA 3.1.0; EQY for equivalence.",
         "- Ablations: %s" % (", ".join(k for k, v in (S.get("ablations") or {}).items() if v) or "none"), "",
         "## Timing per clock domain (ns)", "",
         "| Clock | WNS before | WNS after | dWNS | TNS before | TNS after | violating endpoints |",
         "|---|---|---|---|---|---|---|"]
    rows, changes = dom_table(S)
    L += rows
    L += ["", "Design: WNS %s -> %s, TNS %s -> %s, area %s -> %s um^2." % (
        S["baseline"]["wns_ns"], S["final"]["wns_ns"], S["baseline"]["tns_ns"], S["final"]["tns_ns"],
        S["baseline"]["area_um2"], S["final"]["area_um2"]), ""]
    fc, C = S.get("final_check"), S["candidates"]
    lost = sum(1 for it in iters for c in candidates_of(it) if c.get("status") == "llm_error" or c.get("gen_status") == "llm_error")
    if lost:
        L += ["**Note: %d candidate(s) were lost to LLM errors (e.g. the Claude session limit); the run used %d of %d.**" % (
            lost, C["total"] - lost, C["total"]), ""]
    L += ["## Correctness", "",
          "- Final design vs original: %s" % ("unchanged (nothing promoted)" if not fc else
                                              "verify **%s**%s, EQY top vs v0 **%s**, measured violations %s" % (
                                                  fc["verify"], " (%s)" % fc["reject_reason"] if fc.get("reject_reason") else "",
                                                  fc["eqy_top_vs_v0"], fc["measured_violations"] or "none")),
          "- Candidates: %s total; by status %s; reject reasons %s." % (C["total"], C["by_status"], C["by_reason"] or "none"),
          "- Candidates passing SEC: %s. Measured lock-tier edits: %s. Measured CDC regressions: %s." % (
              C["sec_pass"], C["measured_lock_violations"], C["measured_cdc_violations"]), ""]
    # iterations
    L += ["## Iterations", ""]
    sel_by_n = {e["iteration"]: e for e in ev if e.get("ev") == "selection"}
    for it in iters:
        n = it["iteration"]
        cs = candidates_of(it)
        L.append("### Iteration %d: %s" % (n, "promoted (WNS %s, TNS %s, area %s)" % (it.get("wns"), it.get("tns"), it.get("area"))
                                            if it.get("promoted") else "nothing promoted"))
        s = sel_by_n.get(n)
        if s:
            L.append("- Selection: alpha=%s beta=%s gamma=%s; dispatched %s; blocked %s; unreachable deficit %s." % (
                s.get("alpha"), s.get("beta"), s.get("gamma"), s.get("dispatch"), s.get("blocked") or "none", s.get("unreachable")))
        for r in it.get("regions", []) or []:
            d = load(os.path.join(run, "work", "v%d" % n, "sel", "diag", r["region_id"] + ".diag.json"), {}) or {}
            L.append("- Region `%s` (capture clock %s): root cause **%s**%s." % (
                r["region_id"], d.get("capture_clock"), r.get("root_cause") or d.get("dominant_root_cause"),
                ", late signal `%s`" % d["late_signal"] if d.get("late_signal") else ""))
        if cs:
            L += ["", "| slot | region | skill | status | reason | WNS | score | SEC vs v0 | measured violations |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for c in cs:
                sk = c.get("skill")
                L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    c.get("slot"), c.get("region", "-"), "%s %s" % (sk, titles.get(sk, "")) if sk else "zero-shot/none",
                    c.get("status"), c.get("reason") or c.get("reject_reason") or "", c.get("wns"), c.get("score"),
                    c.get("sec_vs_v0", c.get("sec")), c.get("measured_violations") or ""))
        L.append("")
    stop = [e for e in ev if e.get("ev") == "stop"]
    if stop:
        L += ["Stopped early: %s." % stop[-1].get("why"), ""]
    # constraint audit and asynchronous violators
    audit = []
    for p in sorted(glob.glob(os.path.join(run, "work", "v*", "sel", "selection.json"))):
        audit = (load(p, {}) or {}).get("constraint_audit") or audit
        break
    xb = cross_clock_violators(os.path.join(run, "work", "v0", "sta", "endpoints.rpt"))
    xf = cross_clock_violators(os.path.join(run, "work", S["final_version"], "sta", "endpoints.rpt"))
    # why
    W = []
    promoted = [it for it in iters if it.get("promoted")]
    improved = [c for c, (b, f, d) in changes.items() if d is not None and d > 1e-9]
    worse = [c for c, (b, f, d) in changes.items() if d is not None and d < -1e-9]
    still = [c for c, (b, f, d) in changes.items() if f is not None and f < 0]
    if promoted:
        for it in promoted:
            cs = [c for c in candidates_of(it) if c.get("score") is not None and c.get("status") in ("eligible", "synthesizable")]
            win = min(cs, key=lambda c: c["score"]) if cs else None
            if win:
                sk = win.get("skill")
                W.append("- Iteration %d promoted candidate %s%s%s (score %s, WNS %s)." % (
                    it["iteration"], win.get("slot"), " in region `%s`" % win["region"] if win.get("region") else "",
                    ", skill %s *%s*" % (sk, titles.get(sk, "")) if sk else "",
                    win["score"], win.get("wns")))
                if win.get("root_cause"):
                    W.append("  Diagnosed root cause: %s; the rewrite targets that cone only." % win["root_cause"])
    else:
        rs = Counter((c.get("reason") or c.get("reject_reason") or c.get("status")) for it in iters for c in candidates_of(it))
        W.append("- Nothing was promoted in any iteration. Candidate outcomes: %s." % dict(rs))
        if mode in ("aegis", "drrtl"):
            W.append("  A candidate is promoted only if it passes SEC%s and scores below the current base (score < 0)." % (
                " and every Phase 4 stage" if mode == "aegis" else ""))
    if improved:
        W.append("- Domains improved: %s." % ", ".join("%s (%+.3f ns)" % (c, changes[c][2]) for c in improved))
    if worse:
        W.append("- Domains that got worse: %s." % ", ".join("%s (%+.3f ns)" % (c, changes[c][2]) for c in worse))
    for c in still:
        xs = [x for x in xf if x[2] == c]
        if xs:
            W.append("- `%s` still violates, but its worst violators are **cross-clock paths** (e.g. `%s` launched by %s, slack %s): "
                     "asynchronous paths without a CDC exception, which a timing rewrite cannot legitimately fix; they belong "
                     "in the constraint audit%s." % (c, xs[0][0], xs[0][1], xs[0][3],
                                                 " (Aegis listed %d audit entries)" % len(audit) if audit else
                                                 "; this configuration has no constraint audit, so it treats them as ordinary paths"))
        elif mode == "aegis" and c not in improved:
            W.append("- `%s` still violates and was not improved: see the selection lines above for whether a region in this "
                     "domain was dispatched and why its candidates were rejected." % c)
    if fc and fc.get("eqy_top_vs_v0") == "FAIL":
        fv = load(os.path.join(run, "final_verify.json"), {}) or {}
        sim = (fv.get("stages") or {}).get("sim") or {}
        mism = sum(r.get("mismatches") or 0 for r in sim.get("runs", [])) if sim else None
        failed = []
        lg = os.path.join(run, "final_eqy", "eqy_%s.log" % (load(os.path.join(ROOT, "flow", "designs", S["design"], "design.json"), {}) or {}).get("top", ""))
        if os.path.exists(lg):
            failed = sorted(set(l.split("partition", 1)[1].strip() for l in open(lg) if "Failed to prove equivalence of partition" in l))
        W.append("- **The final design is not proven equivalent to the original** (EQY FAIL on partition(s) %s; differential "
                 "simulation %s). %s" % (", ".join(failed) or "?",
                                         "found %d mismatches" % mism if mism else "found no mismatch" if mism == 0 else "not run",
                 "A simulation mismatch means it is functionally wrong." if mism else
                 "With no simulation mismatch this may be an EQY proof limit (partition-local induction) rather than a real "
                 "difference; either way it fails the SEC requirement every configuration is held to."))
    rm = load(os.path.join(run, "cdc_remeasure.json"))
    if rm:
        W.append("- CDC re-measured with the corrected checker (%s): %d of %d candidates regress a crossing (was %d with the "
                 "old checker, which counted re-driven pre-existing unsafe crossings as new)%s." % (
                     rm["checker"], rm["violating"], rm["checked"], C["measured_cdc_violations"],
                     "; %d candidate(s) could not be checked (tool error)" % rm["tool_errors"] if rm.get("tool_errors") else ""))
    elif C["measured_cdc_violations"] or C["measured_lock_violations"]:
        W.append("- %d candidate(s) edited locked CDC logic and %d regressed a crossing (measured)." % (
            C["measured_lock_violations"], C["measured_cdc_violations"]))
    L += ["## Why it improved / why not", ""] + W + [""]
    if audit:
        L += ["## Constraint audit (first selection)", "", "| endpoint | launch | capture | slack | issue |", "|---|---|---|---|---|"]
        L += ["| %s | %s | %s | %s | %s |" % (a.get("endpoint"), a.get("launch_clock"), a.get("capture_clock"),
                                              a.get("slack_ns"), a.get("issue")) for a in audit[:20]]
        L.append("")
    if xb:
        L += ["Cross-clock violating endpoints at baseline: %d (after: %d)." % (len(xb), len(xf)), ""]
    D = rtl_diff(run, S["final_version"])
    L += ["## Final RTL change vs original", ""]
    if not D:
        L.append("No change (final version is v0)." if S["final_version"] == "v0" else "No textual difference found.")
    else:
        L += ["%d diff lines%s:" % (len(D), ", first 150 shown" if len(D) > 150 else ""), "", "```diff"] + D[:150] + ["```"]
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--copy-to", help="also copy each note to <dir>/<design>.<run-id>.md")
    a = ap.parse_args()
    runs = a.runs or ([os.path.dirname(p) for p in glob.glob(os.path.join(ROOT, "flow", "runs", "*", "*", "summary.json"))]
                      if a.all else [])
    for r in sorted(r.rstrip("/") for r in runs):
        if os.path.basename(r).startswith("smoke"):
            continue
        out = os.path.join(r, "RUN_NOTES.md")
        if a.only_missing and os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(os.path.join(r, "summary.json")):
            continue
        t = notes(r)
        if t is None:
            continue
        open(out, "w").write(t)
        if a.copy_to:
            os.makedirs(a.copy_to, exist_ok=True)
            shutil.copy(out, os.path.join(a.copy_to, "%s.%s.md" % (os.path.basename(os.path.dirname(r)), os.path.basename(r))))
        print("wrote", out)


if __name__ == "__main__":
    main()
