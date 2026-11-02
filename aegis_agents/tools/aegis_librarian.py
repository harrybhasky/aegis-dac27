#!/usr/bin/env python3
"""
AEGIS Phase 5.5 -- The Librarian (deterministic skill-library update).

  python3 aegis_librarian.py update --state flow/skills/library_state.json --round round.json

round.json (written by the orchestrator, one entry per dispatched region):
  {"design": "soc", "iteration": 1, "regions": [
     {"region_id": "r_..", "root_cause": "complex_arithmetic", "promoted": true,
      "candidates": [{"slot": "C1", "skill": 62, "status": "eligible"|"reject", "reason": null|"lint"|...,
                      "score": -0.12 | null}, ...]}]}

Update rule (group-relative, per region):
  Delta_k = Score_k - Score(B_n) = Score_k  (scores are relative to B_n, so Score(B_n) = 0)
  For eligible candidates: advantage A_k = (mean(Delta) - Delta_k) / (std(Delta) + eps)
  (positive = better than the candidate group; scores are lower-is-better).
    improved (Delta_k < 0) and A_k >= 0  -> conf += delta * (1 + [region winner])
    not improved and A_k < 0             -> conf -= delta / 2
  Rejected by a correctness check (lock, envelope, ports, lint, sim mismatch, CDC, SEC):
    conf -= delta;  failure count (root cause, skill) += 1;
    two correctness failures with no success for that root cause -> anti-pattern for it.
  Failure reasons are kept per root cause (last 20) and quoted in the next prompts.
  Zero-shot candidates (C5) carry no skill and only contribute failure notes.
"""
import argparse
import json
import math
import time

DELTA = 0.05
CORRECTNESS = {"lock_violation", "envelope", "ports", "lint", "sim_mismatch", "cdc", "sec_fail"}


def update(state, rnd, delta=DELTA):
    conf = state.setdefault("confidence", {})
    anti = state.setdefault("anti_patterns", {})
    fails = state.setdefault("failure_counts", {})
    wins = state.setdefault("success_counts", {})
    notes = state.setdefault("failure_notes", {})
    changes = []
    for reg in rnd["regions"]:
        rc = reg.get("root_cause") or "unknown"
        cands = reg["candidates"]
        elig = [c for c in cands if c["status"] == "eligible" and c.get("score") is not None]
        ds = [c["score"] for c in elig]
        mu = sum(ds) / len(ds) if ds else 0.0
        sd = math.sqrt(sum((x - mu) ** 2 for x in ds) / len(ds)) if len(ds) > 1 else 0.0
        best = min(elig, key=lambda c: c["score"]) if elig else None
        for c in cands:
            sid = c.get("skill")
            key = str(sid) if sid is not None else None
            if c["status"] != "eligible":
                why = c.get("reason") or "rejected"
                notes.setdefault(rc, []).append("%s (%s): rejected by %s%s" % (
                    ("skill #%s" % sid) if sid else "zero-shot", c["slot"], why,
                    (" -- " + c["detail"][:160]) if c.get("detail") else ""))
                notes[rc] = notes[rc][-20:]
                if key and why in CORRECTNESS:
                    conf[key] = round(max(0.0, conf.get(key, 0.5) - delta), 4)
                    fk = "%s|%s" % (rc, key)
                    fails[fk] = fails.get(fk, 0) + 1
                    if fails[fk] >= 2 and wins.get(fk, 0) == 0 and sid not in anti.get(rc, []):
                        anti.setdefault(rc, []).append(sid)
                        changes.append({"skill": sid, "root_cause": rc, "change": "anti_pattern"})
                    changes.append({"skill": sid, "slot": c["slot"], "change": -delta, "why": why})
                continue
            if not key:
                continue
            adv = (mu - c["score"]) / (sd + 1e-9) if sd > 0 else 0.0
            if c["score"] < 0 and adv >= 0:
                inc = delta * (2 if (best is c and reg.get("promoted")) else 1)
                conf[key] = round(min(1.0, conf.get(key, 0.5) + inc), 4)
                fk = "%s|%s" % (rc, key)
                wins[fk] = wins.get(fk, 0) + 1
                changes.append({"skill": sid, "slot": c["slot"], "change": inc, "advantage": round(adv, 3)})
            elif c["score"] >= 0 and adv < 0:
                conf[key] = round(max(0.0, conf.get(key, 0.5) - delta / 2), 4)
                changes.append({"skill": sid, "slot": c["slot"], "change": -delta / 2, "advantage": round(adv, 3)})
    state.setdefault("history", []).append({"design": rnd.get("design"), "iteration": rnd.get("iteration"),
                                            "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "changes": changes})
    return state, changes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update")
    u.add_argument("--state", required=True)
    u.add_argument("--round", required=True)
    a = ap.parse_args()
    st = json.load(open(a.state))
    st, ch = update(st, json.load(open(a.round)))
    json.dump(st, open(a.state, "w"), indent=1)
    print(json.dumps({"changes": len(ch), "anti_patterns": st["anti_patterns"]}))


if __name__ == "__main__":
    main()
