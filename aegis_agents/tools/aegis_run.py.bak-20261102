#!/usr/bin/env python3
"""
AEGIS orchestrator -- the Python driver for the full closed loop (Phases 1-5.5).

  python3 tools/aegis_run.py --design soc --run-id r1 [--mode aegis|vanilla] \\
      [--model claude-sonnet-5-5 --backend claude-cli] [--iters 5] [--jobs 5] \\
      [--no-locks] [--no-cdc-check] [--zero-shot] [--scalar-score] [--no-stall-recovery] \\
      [--library fresh|shared]

Everything that decides correctness or progress is deterministic program logic here;
the LLM is called only for (a) region diagnosis, (b) skill ranking, (c) candidate RTL.
Each run lives in flow/runs/<design>/<run-id>/ (RTL versions, work, logs, LLM call log,
summary.json), so repeated runs and ablations never share state unless --library shared.

Modes
  aegis    the full pipeline described in the paper.
  vanilla  the unguarded baseline: the same model gets the RTL and the timing summary and
           returns a rewrite; no locks, no skill library, no envelope, no gating. Every
           check is still run as a measurement (lock edits, CDC regressions, SEC), and the
           best-scoring synthesizable candidate is promoted, so the comparison isolates
           the framework rather than the prompt.
Ablations (aegis mode)
  --no-locks           no lock filtering in selection/envelope; checksum gate measured only
  --no-cdc-check       Phase 4 CDC re-check measured only
  --zero-shot          no skill library: all five slots zero-shot
  --scalar-score       Dr. RTL-style global scalar score instead of the domain-aware score
  --no-stall-recovery  attempt records are not updated (no Rank-3/4 substitution, no T5 escalation)
"""
import argparse
import concurrent.futures as cf
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aegis_eval  # noqa: E402
import aegis_gen  # noqa: E402
import aegis_librarian  # noqa: E402
import aegis_llm  # noqa: E402
import aegis_verify  # noqa: E402
from aegis_common import ROOT, load_design, module_spans, module_of_line, which  # noqa: E402

PY = sys.executable
STA = which("sta", ["~/karuppu/.tools/OpenSTA/build/sta", "~/OpenSTA/build/sta"])
SCHEDULE = {  # (iteration stage, timing met) -> alpha, beta, gamma   (paper Table: adaptive schedule)
    (1, None): (0.60, 0.30, 0.10), (2, None): (0.50, 0.40, 0.10),
    (3, True): (0.35, 0.25, 0.40), (3, False): (0.55, 0.35, 0.10),
    (4, True): (0.30, 0.20, 0.50), (4, False): (0.70, 0.30, 0.00),
}


def schedule(n, met):
    if n <= 2:
        return SCHEDULE[(n, None)]
    return SCHEDULE[(3 if n == 3 else 4, bool(met))]


def sh(cmd, log=None, timeout=None, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if log:
        open(log, "a").write("$ %s\n%s%s\n" % (" ".join(cmd), r.stdout, r.stderr))
    if check and r.returncode != 0:
        raise RuntimeError("%s failed:\n%s" % (os.path.basename(cmd[1] if cmd[0] == PY else cmd[0]),
                                               (r.stderr or r.stdout)[-1500:]))
    return r


def agent_prompt(name, section=None):
    """System prompt for an LLM step = the body of the matching Claude Code agent file."""
    text = open(os.path.join(ROOT, ".claude", "agents", name + ".md")).read()
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    if section:
        i = text.find(section)
        text = text[i:] if i >= 0 else text
    return text + ("\n\n---\nORCHESTRATOR MODE: you have no tools and cannot read or write files. Everything you"
                   " need is in the user message. Reply with the single JSON object described above and nothing else.")


class Run:
    def __init__(self, a):
        self.a = a
        self.D = load_design(a.design)
        self.dir = os.path.join(ROOT, "flow", "runs", a.design, a.run_id)
        if os.path.exists(self.dir) and not a.resume:
            shutil.rmtree(self.dir)
        os.makedirs(self.dir, exist_ok=True)
        os.environ["AEGIS_LLM_LOG"] = os.path.join(self.dir, "llm_calls.jsonl")
        self.log = os.path.join(self.dir, "tools.log")
        self.phase1 = os.path.join(ROOT, "flow", "work", a.design, "phase1")
        self.margin = self.D.get("margin", 0.1)
        self.n_max = a.iters or self.D.get("n_max", 5)
        self.t0 = time.time()
        self.events = []
        # skill library
        seed = os.path.join(ROOT, "flow", "skills")
        if not os.path.exists(os.path.join(seed, "skills_index.json")):
            sh([PY, os.path.join(HERE, "aegis_skills.py"), "index", "--skill-md",
                os.path.join(ROOT, ".claude", "skill", "rtl-opt", "skill.md"), "--out", seed], self.log)
        if a.library == "shared":
            self.skills = seed
        else:
            self.skills = os.path.join(self.dir, "skills")
            os.makedirs(self.skills, exist_ok=True)
            shutil.copy(os.path.join(seed, "skills_index.json"), self.skills)
            st = os.path.join(self.skills, "library_state.json")
            if not os.path.exists(st):
                shutil.copy(os.path.join(seed, "library_state.seed.json") if os.path.exists(
                    os.path.join(seed, "library_state.seed.json")) else os.path.join(seed, "library_state.json"), st)
        self.state_path = os.path.join(self.skills, "library_state.json")
        self.attempts_path = os.path.join(self.dir, "attempts.json")
        if not os.path.exists(self.attempts_path):
            json.dump({}, open(self.attempts_path, "w"))

    # ---------------------------------------------------------------- helpers
    def files(self, ver):
        d = os.path.join(self.dir, "rtl", ver)
        return [os.path.join(d, os.path.basename(f)) for f in self.D["rtl"]]

    def llm(self, system, prompt, temperature, tag):
        if getattr(self, "llm_down", False):
            raise aegis_llm.LLMError("LLM backend marked unavailable earlier in this run")
        return aegis_llm.call(system, prompt, self.a.model, temperature, self.a.backend, self.a.effort,
                              base_url=self.a.base_url, tag=tag)

    def note(self, **kw):
        kw["t"] = round(time.time() - self.t0, 1)
        self.events.append(kw)
        print(json.dumps(kw), flush=True)

    def phase1_ensure(self):
        if os.path.exists(os.path.join(self.phase1, "phase1_report.json")) and not self.a.reingest:
            return json.load(open(os.path.join(self.phase1, "phase1_report.json")))
        cmd = [PY, os.path.join(HERE, "aegis_ingest.py"), "ingest", "--rtl"] + self.D["rtl"] + [
            "--top", self.D["top"], "--sdc", self.D["sdc"], "--contracts-tool", os.path.join(HERE, "gen_cdc_props.py"),
            "--out", self.phase1]
        if self.D.get("annotations"):
            cmd += ["--annotations", self.D["annotations"]]
        sh(cmd, self.log, timeout=7200)
        return json.load(open(os.path.join(self.phase1, "phase1_report.json")))

    def sta(self, ver):
        out = os.path.join(self.dir, "work", ver, "sta")
        mp = os.path.join(out, "metrics.json")
        if not os.path.exists(mp):
            m, err = aegis_eval.sta(self.D, self.files(ver), out, self.margin)
            if m is None:
                raise RuntimeError("STA failed on %s: %s" % (ver, err))
        return json.load(open(mp))

    # ---------------------------------------------------------------- LLM steps
    def diagnose(self, sel, rid):
        region = json.load(open(os.path.join(sel, "regions", rid + ".region.json")))
        files = {os.path.basename(p): open(p).read() for p in region["rtl_files"]}
        mods = set()
        for c in region["cone"]:
            m = module_of_line(module_spans(files.get(c["file"], "")), c["line"])
            if m:
                mods.add((c["file"], m))
        src = []
        for f, m in sorted(mods):
            s, e = next((a, b) for n, a, b in module_spans(files[f]) if n == m)
            src.append("// %s, module %s\n%s" % (f, m, "\n".join("%5d| %s" % (i, l) for i, l in
                                                               enumerate(files[f].splitlines()[s - 1:e], s))))
        prompt = "Region file contents:\n```json\n%s\n```\n\nRTL of the modules containing the cone:\n%s" % (
            json.dumps(region, indent=1), "\n\n".join(src))
        sysmsg = agent_prompt("aegis-timing-analyzer")
        d = None
        for attempt in range(2):
            r = self.llm(sysmsg, prompt + ("" if attempt == 0 else "\n\nYour previous reply was not valid. Reply with the JSON object only."),
                         0.0, "diag:" + rid)
            try:
                d = aegis_llm.extract_json(r["text"])
                break
            except aegis_llm.LLMError:
                continue
        if d is None:
            raise aegis_llm.LLMError("diagnosis for %s: no JSON" % rid)
        os.makedirs(os.path.join(sel, "diag"), exist_ok=True)
        json.dump(d, open(os.path.join(sel, "diag", rid + ".diag.json"), "w"), indent=1)

    def rank(self, rid, cands_path, region, diag, out):
        C = json.load(open(cands_path))
        if not C["eligible"] or self.a.zero_shot:
            json.dump({"region_id": rid, "ranking": [], "c5_direction": ""}, open(out, "w"))
            return
        slim = dict(C)
        slim["eligible"] = [{k: e[k] for k in ("id", "title", "pattern", "strategy", "confidence",
                                                 "matches_dominant", "sequential", "uses_late_signal")} for e in C["eligible"]]
        prompt = "candidates.json:\n%s\n\nregion:\n%s\n\ndiagnosis:\n%s" % (
            json.dumps(slim, indent=1), json.dumps({k: region[k] for k in ("region_id", "capture_clock", "endpoints",
                                                                           "cone", "locked_neighbors", "contracts")}, indent=1),
            json.dumps(diag, indent=1))
        sysmsg = agent_prompt("aegis-skill-matcher", "## Step 2")
        R = None
        for attempt in range(2):
            r = self.llm(sysmsg, prompt, 0.0, "rank:" + rid)
            try:
                R = aegis_llm.extract_json(r["text"])
                elig = {e["id"] for e in C["eligible"]}
                rk = []   # the model sometimes returns bare ids ("62" or 62) instead of {"id": .., "why": ..}
                for x in R.get("ranking") or []:
                    x = dict(x) if isinstance(x, dict) else {"id": x, "why": ""}
                    try:
                        x["id"] = int(str(x.get("id")).lstrip("#"))
                    except ValueError:
                        continue
                    if x["id"] in elig:
                        rk.append(x)
                R["ranking"] = rk
                R["region_id"] = rid
                break
            except aegis_llm.LLMError:
                continue
        json.dump(R or {"region_id": rid, "ranking": [], "c5_direction": ""}, open(out, "w"), indent=1)

    # ---------------------------------------------------------------- per-region work
    def region_round(self, n, B, sel, rid, alpha, beta, gamma, final):
        a = self.a
        rdir = os.path.join(self.dir, "work", "v%d" % n, "regions", rid)
        os.makedirs(rdir, exist_ok=True)
        region_p = os.path.join(sel, "regions", rid + ".region.json")
        diag_p = os.path.join(sel, "diag", rid + ".diag.json")
        region, diag = json.load(open(region_p)), json.load(open(diag_p))
        cands_p, rank_p, asg_p = (os.path.join(rdir, x) for x in ("candidates.json", "ranking.json", "assignment.json"))
        sh([PY, os.path.join(HERE, "aegis_skills.py"), "candidates", "--index", os.path.join(self.skills, "skills_index.json"),
            "--state", self.state_path, "--region", region_p, "--diag", diag_p, "--attempts", self.attempts_path,
            "--out", cands_p], self.log)
        self.rank(rid, cands_p, region, diag, rank_p)
        sh([PY, os.path.join(HERE, "aegis_skills.py"), "assign", "--index", os.path.join(self.skills, "skills_index.json"),
            "--candidates", cands_p, "--ranking", rank_p, "--attempts", self.attempts_path, "--out", asg_p], self.log)
        asg = json.load(open(asg_p))
        if a.zero_shot:
            for p in asg["plan"]:
                p["skill"], p["role"] = None, "zero-shot (ablation: no skill library)"
            json.dump(asg, open(asg_p, "w"), indent=1)
        env_p = os.path.join(rdir, "envelope.json")
        env_args = argparse.Namespace(region=region_p, rtl=self.files(B), top=self.D["top"],
                                      lockmap=None if a.no_locks else os.path.join(self.phase1, "lock_map.json"), out=env_p)
        env = aegis_gen.envelope(env_args)
        scopes = sorted({m["module"] for m in env["modules"]}) or [self.D["top"]]

        def one(slot):
            out = os.path.join(rdir, slot)
            g = argparse.Namespace(region=region_p, diag=diag_p, assignment=asg_p, slot=slot, envelope=env_p,
                                   out=out, rtl=self.files(B), library_state=self.state_path, temperature=None,
                                   model=a.model, backend=a.backend, base_url=a.base_url, effort=a.effort)
            meta = aegis_gen.generate(g)
            rec = {"slot": slot, "skill": meta.get("skill"), "gen_status": meta.get("status"),
                   "temperature_requested": meta.get("temperature_requested"),
                   "temperature_applied": meta.get("temperature_applied"), "latency_s": meta.get("latency_s")}
            if meta.get("status") != "ok":
                rec.update({"status": "reject", "reason": "no_code" if meta.get("status") != "llm_error" else "llm_error"})
                return rec
            cand = meta["files"]
            v = aegis_verify.run(self.D, self.files(B), cand, env, self.phase1, os.path.join(out, "verify.json"),
                                 gate_locks=not a.no_locks, gate_cdc=not a.no_cdc_check, linters=self.linters)
            rec.update({"verify": v["status"], "graded": v["graded"], "measured_violations": v["measured_violations"]})
            if v["status"] != "pass":
                st = v["stages"]
                detail = ""
                if v["reject_reason"] == "envelope":
                    detail = "; ".join(st["gate"]["envelope"][:2])
                elif v["reject_reason"] == "cdc":
                    detail = "; ".join(st["cdc"]["violations"][:2])
                elif v["reject_reason"] == "lint":
                    detail = (st["lint"].get("iverilog", {}).get("log") or "")[:200]
                rec.update({"status": "reject", "reason": v["reject_reason"], "detail": detail})
                return rec
            ev = aegis_eval.evaluate(self.D, self.files(B), cand, scopes, os.path.join(self.dir, "work", B, "sta", "metrics.json"),
                                     os.path.join(out, "eval"), alpha, beta, gamma, a.scalar_score, self.phase1)
            rec["sec"] = [(e["scope"], e["status"]) for e in ev["eqy"]]
            if not ev["sec_pass"]:
                rec.update({"status": "reject", "reason": "sec_fail",
                            "detail": "EQY %s" % ", ".join("%s:%s" % x for x in rec["sec"])})
                return rec
            if ev["score"] is None:
                rec.update({"status": "reject", "reason": "sta_error"})
                return rec
            sc = ev["score"]
            if final and sc["regressed_domains"]:
                rec.update({"status": "reject", "reason": "final_regression", "score": sc["score"]})
                return rec
            rec.update({"status": "eligible", "score": sc["score"], "wns": ev["metrics"]["wns_ns"],
                        "tns": ev["metrics"]["tns_ns"], "area": ev["metrics"]["area_um2"], "files": cand,
                        "replaced_modules": meta.get("replaced_modules")})
            return rec

        slots = ["C1", "C2", "C3", "C4", "C5"]
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            recs = list(ex.map(one, slots))
        for r in recs:
            self.note(ev="candidate", iteration=n, region=rid, **{k: r.get(k) for k in (
                "slot", "skill", "status", "reason", "score", "wns", "graded", "measured_violations")})
        elig = [r for r in recs if r["status"] == "eligible"]
        win = min(elig, key=lambda r: r["score"]) if elig else None
        return {"region_id": rid, "root_cause": diag.get("dominant_root_cause"), "candidates": recs, "winner": win,
                "scopes": scopes, "envelope_modules": env["modules"]}

    # ---------------------------------------------------------------- composition
    def compose(self, n, B, results, alpha, beta, gamma):
        wins = [r for r in results if r["winner"] and r["winner"]["score"] < 0]
        if not wins:
            return None
        best = min(wins, key=lambda r: r["winner"]["score"])
        if len(wins) == 1:
            return {"files": best["winner"]["files"], "score": best["winner"]["score"], "composed_of": [best["region_id"]]}
        # take winners whose changed modules do not overlap, best first
        used, chosen = set(), []
        for r in sorted(wins, key=lambda r: r["winner"]["score"]):
            mods = {(m["file"], m["module"]) for m in r["envelope_modules"]}
            if mods & used:
                continue
            used |= mods
            chosen.append(r)
        if len(chosen) == 1:
            return {"files": best["winner"]["files"], "score": best["winner"]["score"], "composed_of": [best["region_id"]]}
        mods = {}
        for r in chosen:
            for f in r["winner"]["files"]:
                text = open(f).read()
                for name, s, e in module_spans(text):
                    if name in (r["winner"].get("replaced_modules") or []):
                        mods[name] = "\n".join(text.splitlines()[s - 1:e])
        cdir = os.path.join(self.dir, "work", "v%d" % n, "composed")
        files, _, _ = aegis_gen.splice(self.files(B), mods, os.path.join(cdir, "rtl"))
        v = aegis_verify.run(self.D, self.files(B), files, None, self.phase1, os.path.join(cdir, "verify.json"),
                             gate_locks=not self.a.no_locks, gate_cdc=not self.a.no_cdc_check, linters=self.linters)
        ev = None
        if v["status"] == "pass":
            ev = aegis_eval.evaluate(self.D, self.files(B), files, [], os.path.join(self.dir, "work", B, "sta", "metrics.json"),
                                     os.path.join(cdir, "eval"), alpha, beta, gamma, self.a.scalar_score, self.phase1,
                                     skip_eqy=True)   # modules are disjoint and each was proven equivalent on its own
        if ev and ev["score"] and ev["score"]["score"] < best["winner"]["score"]:
            self.note(ev="composed", iteration=n, regions=[r["region_id"] for r in chosen], score=ev["score"]["score"])
            return {"files": files, "score": ev["score"]["score"], "composed_of": [r["region_id"] for r in chosen]}
        self.note(ev="composed_rejected", iteration=n, verify=v["status"],
                  score=(ev or {}).get("score", {}) and ev["score"]["score"], best_single=best["winner"]["score"])
        return {"files": best["winner"]["files"], "score": best["winner"]["score"], "composed_of": [best["region_id"]]}

    def promote(self, n, files):
        d = os.path.join(self.dir, "rtl", "v%d" % n)
        os.makedirs(d, exist_ok=True)
        for f in files:
            shutil.copy(f, os.path.join(d, os.path.basename(f)))
        return "v%d" % n

    # ---------------------------------------------------------------- loops
    def setup(self):
        rep = self.phase1_ensure()
        v0 = os.path.join(self.dir, "rtl", "v0")
        os.makedirs(v0, exist_ok=True)
        for f in self.D["rtl"]:
            shutil.copy(f, os.path.join(v0, os.path.basename(f)))
        m0 = self.sta("v0")
        base_lint = aegis_verify.lint(self.D, self.files("v0"))
        self.linters = {k: v["ok"] for k, v in base_lint.items() if isinstance(v, dict)}
        self.note(ev="baseline_lint", **self.linters)
        self.note(ev="baseline", wns=m0["wns_ns"], tns=m0["tns_ns"], area=m0["area_um2"], phase1=rep.get("crossings"))
        return m0

    def run_aegis(self):
        a = self.a
        m0 = self.setup()
        B, iters, prev_scores = "v0", [], []
        for n in range(1, self.n_max + 1):
            mB = self.sta(B)
            met = all((p["wns_ns"] is None or p["wns_ns"] >= self.margin) for p in mB["per_domain"])
            alpha, beta, gamma = schedule(n, met)
            final = n == self.n_max
            sel = os.path.join(self.dir, "work", "v%d" % n, "sel")
            cache = os.path.join(self.dir, "diag_cache")
            prep = [PY, os.path.join(HERE, "aegis_select.py"), "prepare", "--report", mB["files"]["endpoints"],
                    "--clocks", os.path.join(self.phase1, "clocks.json"), "--rtl"] + self.files(B) + [
                    "--top", self.D["top"], "--synth-json", mB["files"]["synth_json"], "--design", self.D["name"],
                    "--base-version", B, "--margin", str(self.margin), "--theta", str(self.D.get("theta", 0.5)),
                    "--phi", str(self.D.get("phi", 32)), "--smax", str(self.D.get("smax", 80)), "--cache", cache,
                    "--out", sel]
            if not a.no_locks:
                prep += ["--lockmap", os.path.join(self.phase1, "lock_map.json")]
            sh(prep, self.log)
            todo = json.load(open(os.path.join(sel, "diagnosis_todo.json")))
            with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
                list(ex.map(lambda rid: self.diagnose(sel, rid), todo))
            fin = [PY, os.path.join(HERE, "aegis_select.py"), "finalize", "--sel", sel, "--alpha", str(alpha),
                   "--beta", str(beta), "--budget", str(self.D.get("budget", 10)), "--rho", str(self.D.get("rho", 0.8)),
                   "--dispatch", str(self.D.get("dispatch", 3)), "--attempts", self.attempts_path, "--cache", cache]
            if self.D.get("weights"):
                fin += ["--weights", self.D["weights"]]
            sh(fin, self.log)
            errs_p = os.path.join(sel, "diagnosis_errors.json")
            if os.path.exists(errs_p):
                bad = list(json.load(open(errs_p)))
                with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
                    list(ex.map(lambda rid: self.diagnose(sel, rid), bad))
                os.remove(errs_p)
                sh(fin, self.log)
            S = json.load(open(os.path.join(sel, "selection.json")))
            self.note(ev="selection", iteration=n, base=B, alpha=alpha, beta=beta, gamma=gamma,
                      dispatch=S["dispatch"], blocked=S["blocked_deficit"], unreachable=S["unreachable_deficit"],
                      match_rate=S["match_rate"])
            if not S["dispatch"]:
                self.note(ev="stop", why="nothing to dispatch" if not S["area_recovery"] else "all domains meet margin")
                break
            results = [self.region_round(n, B, sel, rid, alpha, beta, gamma, final) for rid in S["dispatch"]]
            W = self.compose(n, B, results, alpha, beta, gamma)
            promoted = W is not None and W["score"] < 0
            if promoted:
                newB = self.promote(n, W["files"])
            # attempt records (per-region stall recovery)
            att = json.load(open(self.attempts_path))
            for r in results:
                won = promoted and r["region_id"] in W["composed_of"]
                if a.no_stall_recovery:
                    continue
                if won:
                    att[r["region_id"]] = {"attempts": 0, "skills_tried": [], "tabu": False}
                else:
                    rec = att.get(r["region_id"], {"attempts": 0, "skills_tried": [], "tabu": False})
                    rec["attempts"] += 1
                    asg = json.load(open(os.path.join(self.dir, "work", "v%d" % n, "regions", r["region_id"], "assignment.json")))
                    rec["skills_tried"] = sorted(set(rec["skills_tried"]) | set(asg.get("skills_used", [])))
                    rec["tabu"] = rec["attempts"] >= 2
                    att[r["region_id"]] = rec
            json.dump(att, open(self.attempts_path, "w"), indent=1)
            # Librarian
            rnd = {"design": self.D["name"], "iteration": n, "regions": [
                {"region_id": r["region_id"], "root_cause": r["root_cause"],
                 "promoted": promoted and r["region_id"] in W["composed_of"],
                 "candidates": [{k: c.get(k) for k in ("slot", "skill", "status", "reason", "score", "detail")}
                                for c in r["candidates"]]} for r in results]}
            if not a.zero_shot:
                st = json.load(open(self.state_path))
                st, changes = aegis_librarian.update(st, rnd)
                json.dump(st, open(self.state_path, "w"), indent=1)
            mN = self.sta(newB) if promoted else mB
            rec = {"iteration": n, "base": B, "promoted": promoted, "new_base": newB if promoted else B,
                   "score": W["score"] if W else None, "composed_of": W["composed_of"] if W else [],
                   "alpha": alpha, "beta": beta, "gamma": gamma, "wns": mN["wns_ns"], "tns": mN["tns_ns"],
                   "area": mN["area_um2"], "per_domain": mN["per_domain"],
                   "regions": [{"region_id": r["region_id"], "root_cause": r["root_cause"],
                                "candidates": r["candidates"]} for r in results]}
            json.dump(rec, open(os.path.join(self.dir, "work", "v%d" % n, "iteration.json"), "w"), indent=1, default=str)
            iters.append(rec)
            self.note(ev="iteration", iteration=n, promoted=promoted, score=rec["score"], wns=rec["wns"], tns=rec["tns"],
                      area=rec["area"])
            if promoted:
                B = newB
            prev_scores.append(rec["score"] if promoted else 0.0)
            if len(prev_scores) >= 2 and all(abs(s) < self.a.eps for s in prev_scores[-2:]):
                self.note(ev="stop", why="two iterations below epsilon")
                break
        return self.summary(m0, B, iters)

    def run_vanilla(self):
        a = self.a
        m0 = self.setup()
        B, iters = "v0", []
        for n in range(1, self.n_max + 1):
            mB = self.sta(B)
            mpath = os.path.join(self.dir, "work", B, "sta", "metrics.json")
            idir = os.path.join(self.dir, "work", "v%d" % n, "vanilla")

            def one(k):
                slot = "V%d" % k
                out = os.path.join(idir, slot)
                g = argparse.Namespace(rtl=self.files(B), metrics=mpath, report=mB["files"]["groups"], paths=5, slot=slot,
                                       temperature=[0.1, 0.7, 0.3, 0.8, 0.5][k - 1], out=out, model=a.model,
                                       backend=a.backend, base_url=a.base_url, effort=a.effort)
                meta = aegis_gen.vanilla(g)
                rec = {"slot": slot, "gen_status": meta.get("status")}
                if meta.get("status") != "ok":
                    rec["status"] = "no_code"
                    return rec
                cand = meta["files"]
                v = aegis_verify.run(self.D, self.files("v0"), cand, None, self.phase1, os.path.join(out, "verify.json"),
                                     gate_locks=False, gate_cdc=False, gate_envelope=False, linters=self.linters)
                rec.update({"verify": v["status"], "reject_reason": v["reject_reason"],
                            "measured_violations": v["measured_violations"],
                            "sim_mismatch": (v["stages"].get("sim") or {}).get("mismatches")})
                ev = aegis_eval.evaluate(self.D, self.files("v0"), cand, [self.D["top"]], mpath, os.path.join(out, "eval"),
                                         0.6, 0.3, 0.1, a.scalar_score, self.phase1)
                rec["sec_vs_v0"] = ev["sec_pass"]
                if ev["score"] is None:
                    rec["status"] = "sta_error"
                    return rec
                # vanilla is unguarded: cancel the SEC penalty that aegis_eval.score adds, so candidates are
                # ranked on timing/area alone (SEC is still recorded in sec_vs_v0)
                rec.update({"status": "synthesizable", "score": ev["score"]["score"] - (1e4 if ev["sec_pass"] is False else 0),
                            "wns": ev["metrics"]["wns_ns"], "tns": ev["metrics"]["tns_ns"], "area": ev["metrics"]["area_um2"],
                            "files": cand})
                return rec

            with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
                recs = list(ex.map(one, range(1, 6)))
            for r in recs:
                self.note(ev="vanilla_candidate", iteration=n, **{k: r.get(k) for k in (
                    "slot", "status", "verify", "reject_reason", "measured_violations", "sec_vs_v0", "score", "wns")})
            ok = [r for r in recs if r.get("status") == "synthesizable"]
            win = min(ok, key=lambda r: r["score"]) if ok else None
            promoted = win is not None and win["score"] < 0
            if promoted:
                B = self.promote(n, win["files"])
            mN = self.sta(B)
            rec = {"iteration": n, "promoted": promoted, "base": B, "wns": mN["wns_ns"], "tns": mN["tns_ns"],
                   "area": mN["area_um2"], "per_domain": mN["per_domain"], "candidates": recs,
                   "winner_correct": bool(win and win.get("sec_vs_v0") and not win.get("measured_violations"))}
            os.makedirs(os.path.join(self.dir, "work", "v%d" % n), exist_ok=True)
            json.dump(rec, open(os.path.join(self.dir, "work", "v%d" % n, "iteration.json"), "w"), indent=1, default=str)
            iters.append(rec)
            self.note(ev="iteration", iteration=n, promoted=promoted, wns=rec["wns"], tns=rec["tns"], area=rec["area"])
        return self.summary(m0, B, iters)

    def summary(self, m0, B, iters):
        mF = self.sta(B)
        calls = [json.loads(l) for l in open(os.environ["AEGIS_LLM_LOG"])] if os.path.exists(os.environ["AEGIS_LLM_LOG"]) else []
        ok_calls = [c for c in calls if "error" not in c]
        cands = []
        for it in iters:
            for r in it.get("regions", []):
                cands += r["candidates"]
            cands += it.get("candidates", [])
        final_check = None
        if B != "v0":   # end-to-end check of the final design against the original RTL
            v = aegis_verify.run(self.D, self.files("v0"), self.files(B), None, self.phase1,
                                 os.path.join(self.dir, "final_verify.json"), gate_locks=False, gate_cdc=False,
                                 gate_envelope=False, linters=self.linters)
            e = aegis_eval.eqy(self.files("v0"), self.files(B), self.D["top"], os.path.join(self.dir, "final_eqy"))
            final_check = {"verify": v["status"], "reject_reason": v["reject_reason"],
                           "measured_violations": v["measured_violations"], "eqy_top_vs_v0": e["status"]}
        S = {"design": self.D["name"], "run_id": self.a.run_id, "mode": self.a.mode, "model": self.a.model,
             "backend": self.a.backend, "ablations": {k: getattr(self.a, k) for k in (
                 "no_locks", "no_cdc_check", "zero_shot", "scalar_score", "no_stall_recovery")},
             "library": self.a.library, "iterations": len(iters), "final_version": B,
             "baseline": {k: m0[k] for k in ("wns_ns", "tns_ns", "area_um2", "per_domain")},
             "final": {k: mF[k] for k in ("wns_ns", "tns_ns", "area_um2", "per_domain")},
             "trajectory": [{k: it.get(k) for k in ("iteration", "promoted", "wns", "tns", "area", "score")} for it in iters],
             "candidates": {"total": len(cands),
                            "by_status": {s: sum(1 for c in cands if c.get("status") == s) for s in sorted({c.get("status") for c in cands if c.get("status")})},
                            "by_reason": {s: sum(1 for c in cands if c.get("reason") == s) for s in sorted({c.get("reason") for c in cands if c.get("reason")})},
                            "measured_lock_violations": sum(1 for c in cands if "lock_violation" in (c.get("measured_violations") or [])),
                            "measured_cdc_violations": sum(1 for c in cands if "cdc" in (c.get("measured_violations") or [])),
                            "sec_pass": sum(1 for c in cands if c.get("status") == "eligible" or c.get("sec_vs_v0"))},
             "final_check": final_check,
             "llm": {"calls": len(ok_calls), "errors": len(calls) - len(ok_calls),
                     "tokens_in": sum(c.get("tokens_in") or 0 for c in ok_calls),
                     "tokens_out": sum(c.get("tokens_out") or 0 for c in ok_calls),
                     "cost_usd": round(sum(c.get("cost_usd") or 0 for c in ok_calls), 4),
                     "temperature_applied": any(c.get("temperature_applied") for c in ok_calls)},
             "wall_clock_s": round(time.time() - self.t0, 1)}
        json.dump(S, open(os.path.join(self.dir, "summary.json"), "w"), indent=1)
        json.dump(self.events, open(os.path.join(self.dir, "events.json"), "w"), indent=1)
        print(json.dumps({k: S[k] for k in ("design", "run_id", "mode", "iterations", "baseline", "final")}, default=str)[:1500])
        return S


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mode", choices=["aegis", "vanilla"], default="aegis")
    ap.add_argument("--model", default=os.environ.get("AEGIS_MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--backend", default=os.environ.get("AEGIS_BACKEND", "claude-cli"))
    ap.add_argument("--base-url")
    ap.add_argument("--effort")
    ap.add_argument("--iters", type=int)
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--eps", type=float, default=1e-3)
    ap.add_argument("--library", choices=["fresh", "shared"], default="fresh")
    ap.add_argument("--no-locks", action="store_true")
    ap.add_argument("--no-cdc-check", action="store_true")
    ap.add_argument("--zero-shot", action="store_true")
    ap.add_argument("--scalar-score", action="store_true")
    ap.add_argument("--no-stall-recovery", action="store_true")
    ap.add_argument("--reingest", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
    if a.backend == "claude-cli":   # fail fast instead of producing a run full of empty candidates
        try:
            aegis_llm.call("Reply with OK.", "OK", a.model, 0.0, a.backend, timeout=120, retries=0, tag="preflight")
        except aegis_llm.LLMError as e:
            sys.exit("LLM backend unavailable, run not started: %s" % e)
    R = Run(a)
    R.run_vanilla() if a.mode == "vanilla" else R.run_aegis()


if __name__ == "__main__":
    main()
