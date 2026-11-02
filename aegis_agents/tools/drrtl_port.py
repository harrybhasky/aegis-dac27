#!/usr/bin/env python3
"""
Dr. RTL baseline, ported to the AEGIS measurement flow.

  python3 tools/drrtl_port.py --design drrtl_uart --run-id drrtl.sonnet-5-5.r1 [--iters 5] [--model ...]

Reproduces the loop in Dr. RTL's released repo (benchmarks/Dr_RTL/CLAUDE.md and .claude/agents/):
  for each major version: 5 independent minors, each = rtl-timing-analyzer -> rtl-optimizer -> evaluate;
  the best SEC-pass minor (lowest score) is promoted. The analyzer and optimizer system prompts are
  Dr. RTL's own agent files, verbatim, and the optimizer gets Dr. RTL's released skill.md.
What changes, and only because the original tools are unavailable:
  Design Compiler -> Yosys + OpenSTA (same synthesis-only flow as every other configuration),
  Jasper SEC     -> EQY against the original RTL,
  file I/O       -> the orchestrator passes files in the prompt and parses the reply (as aegis_run.py does).
Score = Dr. RTL's formula: 0.5 WNS_norm + 0.35 TNS_norm + 0.15 Area_norm + 0.5 if Area_norm > 0.10
(aegis_eval.score with scalar=True), relative to the current major version.
Not reproduced: the cross-design skill extractor (the released skill.md, learned by Dr. RTL on these same
designs, is used as a fixed library) and the per-minor "orchestrator defined" diversity choice, which is
fixed here to the five-row table below so runs are repeatable.
Each lint/sim check is run as a measurement only, as in vanilla mode.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aegis_eval  # noqa: E402
import aegis_gen  # noqa: E402
import aegis_llm  # noqa: E402
import aegis_run  # noqa: E402
import aegis_verify  # noqa: E402
from aegis_common import ROOT  # noqa: E402

DRRTL = os.path.join(os.path.dirname(ROOT), "benchmarks", "Dr_RTL", ".claude")
DIVERSITY = [  # minor index -> (path_selection, optimization_focus)
    ("top-K by slack", "combinational"),
    ("endpoint clustering", "mixed"),
    ("high fanout", "combinational"),
    ("path range: the K paths after the top K", "sequential"),
    ("module-focused", "mixed"),
]
TOOLS_NOTE = ("\n\n---\nORCHESTRATOR MODE: you have no tools and cannot read or write files. Every input file is"
              " given in the user message. ")


def agent_body(name):
    t = open(os.path.join(DRRTL, "agents", name + ".md")).read()
    return t.split("---", 2)[2] if t.startswith("---") else t


def paths_json(report, limit=60):
    """Dr. RTL's timing_word.json equivalent: one entry per violating endpoint, worst first."""
    out = []
    for blk in open(report).read().split("Startpoint:")[1:]:
        sp = blk.split("\n", 1)[0].strip()
        ep = re.search(r"Endpoint:\s*(.*)", blk)
        sl = re.search(r"(-?\d+\.\d+)\s+slack", blk)
        cells = re.findall(r"^\s+-?\d+\.\d+\s+-?\d+\.\d+ [\^v] (\S+) \((\w+)\)", blk, re.M)
        out.append({"slack": float(sl.group(1)) if sl else None, "startpoint": sp,
                    "endpoint": ep.group(1).strip() if ep else None,
                    "cells": ["%s (%s)" % c for c in cells]})
    out.sort(key=lambda p: p["slack"] if p["slack"] is not None else 0.0)
    return {"total_paths": len(out), "paths": out[:limit]}


class DrRTLRun(aegis_run.Run):
    def minor(self, n, k, B, mpath, timing):
        a = self.a
        tgt = "v%d.%d" % (n - 1, k)
        out = os.path.join(self.dir, "work", "v%d" % n, "drrtl", "m%d" % k)
        os.makedirs(out, exist_ok=True)
        src = "\n\n".join("// file %s\n%s" % (os.path.basename(p), open(p).read()) for p in self.files(B))
        ps, focus = DIVERSITY[k - 1]
        rec = {"slot": "m%d" % k, "target_version": tgt, "path_selection": ps, "optimization_focus": focus}
        # ANALYZE
        sysA = agent_body("rtl-timing-analyzer") + TOOLS_NOTE + "Reply with the iter.json object only."
        pA = "\n".join(["Design: %s   Base version: %s   Target version: %s" % (self.D["name"], B, tgt),
                        "Diversity strategy (orchestrator): %s" % json.dumps(
                            {"minor_index": k, "path_selection": ps, "optimization_focus": focus}),
                        "", "Timing report (timing_word.json):", json.dumps(timing, indent=1), "", "RTL source:", src])
        try:
            it = None
            for attempt in range(2):
                r = self.llm(sysA, pA + ("" if attempt == 0 else "\n\nReply with the JSON object only."), None,
                             "drrtl-analyze:%s" % tgt)
                try:
                    it = aegis_llm.extract_json(r["text"])
                    break
                except aegis_llm.LLMError:
                    continue
            if it is None:
                rec["status"] = "no_analysis"
                return rec
            json.dump(it, open(os.path.join(out, "iter.json"), "w"), indent=1)
            # OPTIMIZE
            sysO = (agent_body("rtl-optimizer") + "\n\n# RTL Optimization skills (skill.md)\n\n" +
                    open(os.path.join(DRRTL, "skill", "rtl-opt", "skill.md")).read() + TOOLS_NOTE +
                    "Reply with (1) the iter.json update in one ```json fenced block, then (2) the full optimized RTL"
                    " file in one ```verilog fenced block.")
            pO = "\n".join(["Target version: %s" % tgt, "", "iter.json:", json.dumps(it, indent=1), "",
                            "RTL source (%s):" % B, src])
            r = self.llm(sysO, pO, None, "drrtl-optimize:%s" % tgt)
        except aegis_llm.LLMError as e:
            rec.update({"status": "llm_error", "error": str(e)[:300]})
            return rec
        open(os.path.join(out, "reply.txt"), "w").write(r["text"])
        m = re.search(r"```json\s*(\{.*?\})\s*```", r["text"], re.S)
        if m:
            open(os.path.join(out, "iter_update.json"), "w").write(m.group(1))
        # drop the json block first: its closing fence would otherwise be read as an opening one
        mods = aegis_gen.parse_modules(re.sub(r"```json\s*\{.*?\}\s*```", "", r["text"], flags=re.S))
        if not mods:
            rec["status"] = "no_code"
            return rec
        cand, _, unknown = aegis_gen.splice(self.files(B), mods, os.path.join(out, "rtl"))
        if unknown:
            rec["unknown_modules"] = unknown
        # EVALUATE: synthesis + STA, SEC (EQY) against the original RTL; other checks measured only
        v = aegis_verify.run(self.D, self.files("v0"), cand, None, self.phase1, os.path.join(out, "verify.json"),
                             gate_locks=False, gate_cdc=False, gate_envelope=False, linters=self.linters)
        rec.update({"verify": v["status"], "reject_reason": v["reject_reason"],
                    "measured_violations": v["measured_violations"]})
        ev = aegis_eval.evaluate(self.D, self.files("v0"), cand, [self.D["top"]], mpath, os.path.join(out, "eval"),
                                 0.5, 0.35, 0.15, True, self.phase1)
        rec["sec_vs_v0"] = ev["sec_pass"]
        if ev["score"] is None:
            rec["status"] = "sta_error"
            return rec
        rec.update({"status": "eligible" if ev["sec_pass"] else "sec_fail", "reason": None if ev["sec_pass"] else "sec_fail",
                    "score": ev["score"]["score"], "wns": ev["metrics"]["wns_ns"], "tns": ev["metrics"]["tns_ns"],
                    "area": ev["metrics"]["area_um2"], "files": cand})
        return rec

    def run_drrtl(self):
        m0 = self.setup()
        B, iters = "v0", []
        for n in range(1, self.n_max + 1):
            mB = self.sta(B)
            mpath = os.path.join(self.dir, "work", B, "sta", "metrics.json")
            timing = paths_json(mB["files"]["endpoints"])
            with cf.ThreadPoolExecutor(max_workers=self.a.jobs) as ex:
                recs = list(ex.map(lambda k: self.minor(n, k, B, mpath, timing), range(1, 6)))
            for r in recs:
                self.note(ev="drrtl_minor", iteration=n, **{k: r.get(k) for k in (
                    "slot", "status", "verify", "reject_reason", "measured_violations", "sec_vs_v0", "score", "wns")})
            ok = [r for r in recs if r.get("status") == "eligible"]
            win = min(ok, key=lambda r: r["score"]) if ok else None
            promoted = win is not None and win["score"] < 0
            if promoted:
                B = self.promote(n, win["files"])
            mN = self.sta(B)
            rec = {"iteration": n, "promoted": promoted, "base": B, "wns": mN["wns_ns"], "tns": mN["tns_ns"],
                   "area": mN["area_um2"], "per_domain": mN["per_domain"], "score": win["score"] if promoted else None,
                   "candidates": recs}
            os.makedirs(os.path.join(self.dir, "work", "v%d" % n), exist_ok=True)
            json.dump(rec, open(os.path.join(self.dir, "work", "v%d" % n, "iteration.json"), "w"), indent=1, default=str)
            iters.append(rec)
            self.note(ev="iteration", iteration=n, promoted=promoted, wns=rec["wns"], tns=rec["tns"], area=rec["area"])
        return self.summary(m0, B, iters)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", default=os.environ.get("AEGIS_MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--backend", default=os.environ.get("AEGIS_BACKEND", "claude-cli"))
    ap.add_argument("--base-url")
    ap.add_argument("--effort")
    ap.add_argument("--iters", type=int)
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--reingest", action="store_true")
    a = ap.parse_args()
    a.mode, a.library, a.zero_shot = "drrtl", "fresh", False
    a.no_locks = a.no_cdc_check = a.scalar_score = a.no_stall_recovery = False
    a.scalar_score = True
    os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
    if a.backend == "claude-cli":
        try:
            aegis_llm.call("Reply with OK.", "OK", a.model, 0.0, a.backend, timeout=120, retries=0, tag="preflight")
        except aegis_llm.LLMError as e:
            sys.exit("LLM backend unavailable, run not started: %s" % e)
    DrRTLRun(a).run_drrtl()


if __name__ == "__main__":
    main()
