#!/usr/bin/env python3
"""
AEGIS skill selection (deterministic parts).

  index       skill.md -> skills_index.json (+ library_state.json if missing)
  candidates  region + diagnosis + library state -> eligible skills for ranking
  assign      eligible skills + LLM ranking + attempt record -> C1..C5 assignment

  python3 aegis_skills.py index --skill-md .claude/skill/rtl-opt/skill.md --out skills/
  python3 aegis_skills.py candidates --index skills/skills_index.json --state skills/library_state.json \
      --region sel/regions/<rid>.region.json --diag sel/diag/<rid>.diag.json \
      [--attempts attempts.json] --out skills_sel/<rid>.candidates.json
  python3 aegis_skills.py assign --candidates skills_sel/<rid>.candidates.json \
      --ranking skills_sel/<rid>.ranking.json [--attempts attempts.json] \
      --out skills_sel/<rid>.assignment.json

Rank exclusion: skills already tried on this region (attempt record) are
removed before ranking, so a redispatched region gets the next-ranked skills
(the paper's Rank-3/Rank-4 substitution) and C5's temperature rises by 0.1.
"""
import argparse
import json
import os
import re
import sys

LCD, WF, ARITH, CTL, RECON = ("long_combinational_depth", "wide_fanin_fanout", "complex_arithmetic",
                              "control_data_coupling", "reconvergent_fanout")
# root causes each entry addresses (eligibility only; the ranking agent judges fit)
ROOT_CAUSES = {
    1: [LCD, CTL, WF], 2: [LCD, CTL], 3: [LCD, CTL, WF], 4: [LCD, CTL], 5: [ARITH, RECON], 6: [ARITH, RECON, WF],
    7: [WF], 8: [WF], 9: [ARITH], 10: [ARITH], 11: [ARITH, LCD], 13: [CTL, LCD], 14: [CTL, ARITH],
    15: [ARITH, CTL], 16: [LCD, CTL], 17: [LCD, CTL], 18: [LCD, WF], 19: [LCD, WF, CTL], 20: [ARITH, LCD],
    21: [LCD, WF], 22: [LCD, ARITH], 23: [ARITH], 24: [CTL, ARITH, RECON], 25: [CTL, LCD], 26: [CTL, LCD],
    27: [LCD, ARITH], 28: [ARITH], 29: [ARITH, CTL], 30: [CTL, ARITH], 31: [ARITH], 32: [WF, CTL], 33: [LCD],
    48: [CTL, LCD, ARITH], 49: [CTL, LCD], 50: [CTL, RECON, LCD, ARITH], 51: [LCD, ARITH], 52: [ARITH, CTL],
    61: [ARITH, LCD], 62: [ARITH, CTL], 63: [ARITH, LCD], 64: [LCD, ARITH],
}
SEQUENTIAL = {7, 48, 49, 51, 61}           # move or add registers (no latency change)
LATE_SIGNAL = {14, 50, 52}                 # most useful when one input arrives late
NEEDS_CONTRACT_BOUND = {61, 62}            # only for logic that launches a Gray crossing
START_CONF = {"High-confidence": 0.8, "Medium-confidence": 0.5, "CDC contract-bound logic": 0.5,
              "Low-confidence": 0.3}
# Do-not-use entries quoted to the generator as explicit warnings
ALWAYS_WARN = [12, 53, 55, 56, 57]
WARN_IF_TAG = {"contract-bound": [65, 54], "lock-adjacent": [54, 60], "latency-sensitive": [34, 37]}


# ----------------------------------------------------------------------------
def index(a):
    text = open(a.skill_md).read()
    entries, section = [], None
    for part in re.split(r"(?m)^(## .*|### \d+\..*)$", text):
        if part.startswith("## "):
            section = part[3:].strip()
            continue
        m = re.match(r"^### (\d+)\.\s*`?<(.*?)>`?\s*$", part.strip()) if part.startswith("### ") else None
        if m:
            entries.append({"id": int(m.group(1)), "section": section, "title": m.group(2).strip(), "body": ""})
            continue
        if entries and not part.startswith("#"):
            entries[-1]["body"] += part
    out = []
    for e in entries:
        b = e.pop("body")
        field = lambda name: (re.search(r"- \*\*%s\*\*:\s*(.*?)(?=\n- \*\*|\Z)" % name, b, re.S) or [None, ""])[1].strip()
        ex = re.search(r"```verilog\n(.*?)```", b, re.S)
        e.update({"pattern": field("Pattern"), "strategy": field("Strategy"), "aegis_notes": field("AEGIS notes"),
                  "verified": field("Verified"), "example": ex.group(1).strip() if ex else "",
                  "root_causes": ROOT_CAUSES.get(e["id"], []),
                  "do_not_use": e["section"] == "Do not use",
                  "sequential": e["id"] in SEQUENTIAL, "late_signal": e["id"] in LATE_SIGNAL,
                  "needs_contract_bound": e["id"] in NEEDS_CONTRACT_BOUND})
        out.append(e)
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, "skills_index.json"), "w"), indent=1)
    st = os.path.join(a.out, "library_state.json")
    if not os.path.exists(st):
        json.dump({"confidence": {str(e["id"]): START_CONF.get(e["section"], 0.0) for e in out if not e["do_not_use"]},
                   "anti_patterns": {}, "history": []}, open(st, "w"), indent=1)
    usable = [e for e in out if not e["do_not_use"]]
    missing = [e["id"] for e in usable if not e["root_causes"]]
    print("entries=%d usable=%d do_not_use=%d%s" % (len(out), len(usable), len(out) - len(usable),
          ("  WARNING: no root-cause mapping for %s" % missing) if missing else ""))


# ----------------------------------------------------------------------------
def candidates(a):
    idx = json.load(open(a.index))
    state = json.load(open(a.state))
    region = json.load(open(a.region))
    diag = json.load(open(a.diag))
    rid = region["region_id"]
    rec = (json.load(open(a.attempts)).get(rid, {}) if a.attempts and os.path.exists(a.attempts) else {})
    tried = set(rec.get("skills_tried", []))
    tags = {t for e in region["endpoints"] for t in e.get("tags", [])}
    amen = [e for e in diag["endpoints"] if e["amenability"] in ("combinational", "sequential-safe")]
    causes = [diag.get("dominant_root_cause")] + sorted({e["root_cause"] for e in amen} - {diag.get("dominant_root_cause")})
    causes = [c for c in causes if c]
    any_seq = any(e["amenability"] == "sequential-safe" for e in amen)
    anti = set()
    for c in causes:
        anti |= set(state.get("anti_patterns", {}).get(c, []))
    elig, excluded = [], []
    for e in idx:
        why_not = None
        if e["do_not_use"]:
            continue
        if not set(e["root_causes"]) & set(causes):
            continue
        if e["id"] in anti:
            why_not = "anti-pattern for this root cause"
        elif e["id"] in tried:
            why_not = "already tried on this region"
        elif e["needs_contract_bound"] and "contract-bound" not in tags:
            why_not = "applies only to logic launching a Gray crossing"
        if why_not:
            excluded.append({"id": e["id"], "reason": why_not})
            continue
        elig.append({"id": e["id"], "section": e["section"], "title": e["title"], "pattern": e["pattern"],
                     "strategy": e["strategy"], "aegis_notes": e["aegis_notes"],
                     "confidence": state.get("confidence", {}).get(str(e["id"]), 0.0),
                     "matches_dominant": diag.get("dominant_root_cause") in e["root_causes"],
                     "sequential": e["sequential"], "uses_late_signal": e["late_signal"]})
    elig.sort(key=lambda x: (not x["matches_dominant"], -x["confidence"], x["id"]))
    warn_ids = list(ALWAYS_WARN)
    for t, ids in WARN_IF_TAG.items():
        if t in tags:
            warn_ids += ids
    warns = [{"id": e["id"], "title": e["title"], "strategy": e["strategy"]} for e in idx if e["id"] in set(warn_ids)]
    out = {"region_id": rid, "dominant_root_cause": diag.get("dominant_root_cause"), "root_causes": causes,
           "late_signal": diag.get("late_signal"), "tags": sorted(tags), "has_sequential_safe": any_seq,
           "attempts": rec.get("attempts", 0), "eligible": elig, "excluded": excluded, "warnings": warns}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print("region=%s eligible=%d excluded=%d dominant=%s" % (rid, len(elig), len(excluded), out["dominant_root_cause"]))


# ----------------------------------------------------------------------------
def assign(a):
    C = json.load(open(a.candidates))
    R = json.load(open(a.ranking))
    idx = {e["id"]: e for e in json.load(open(a.index))} if a.index else {}
    rid = C["region_id"]
    rec = (json.load(open(a.attempts)).get(rid, {}) if a.attempts and os.path.exists(a.attempts) else {})
    eligible = {e["id"]: e for e in C["eligible"]}
    errors = []
    if R.get("region_id") != rid:
        errors.append("ranking is for a different region")
    ranked = []
    for r in R.get("ranking", []):
        sid = r.get("id")
        if sid not in eligible:
            errors.append("skill %s is not eligible for this region" % sid)
        elif sid not in [x["id"] for x in ranked]:
            ranked.append({"id": sid, "why": r.get("why", "")})
    if errors:
        json.dump({"region_id": rid, "errors": errors}, open(a.out, "w"), indent=1)
        sys.exit("invalid ranking: " + "; ".join(errors))
    # fall back to the deterministic order for anything the agent did not rank
    for e in C["eligible"]:
        if e["id"] not in [x["id"] for x in ranked]:
            ranked.append({"id": e["id"], "why": "(not ranked by agent; deterministic order)"})
    attempts = rec.get("attempts", 0)
    t5 = min(0.5 + 0.1 * attempts, 1.0)

    def skill(i):
        if i >= len(ranked):
            return None
        e = eligible[ranked[i]["id"]]
        full = idx.get(e["id"], {})
        return {"id": e["id"], "title": e["title"], "strategy": e["strategy"], "aegis_notes": e["aegis_notes"],
                "example": full.get("example", ""), "why": ranked[i]["why"]}
    s1, s2 = skill(0), skill(1) or skill(0)
    plan = [
        {"slot": "C1", "skill": s1, "temperature": 0.1, "role": "strict application of the primary skill"},
        {"slot": "C2", "skill": s1, "temperature": 0.7, "role": "structural variation of the primary skill"},
        {"slot": "C3", "skill": s2, "temperature": 0.3, "role": "alternate skill"},
        {"slot": "C4", "skill": s2, "temperature": 0.8, "role": "exploratory variant of the alternate skill"},
        {"slot": "C5", "skill": None, "temperature": t5,
         "role": "zero-shot structural rewrite that preserves cycle latency (retiming, resource sharing, restructuring); no pipelining",
         "direction": R.get("c5_direction", "")},
    ]
    if s1 is None:
        for p in plan[:4]:
            p["skill"], p["role"] = None, "zero-shot (no eligible skill)"
    out = {"region_id": rid, "attempt": attempts, "skills_used": sorted({p["skill"]["id"] for p in plan if p["skill"]}),
           "plan": plan, "warnings": C["warnings"], "tags": C["tags"], "late_signal": C["late_signal"]}
    json.dump(out, open(a.out, "w"), indent=1)
    print("region=%s C1/C2=%s C3/C4=%s T5=%.1f" % (rid, s1 and s1["id"], s2 and s2["id"], t5))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("--skill-md", required=True)
    i.add_argument("--out", required=True)
    c = sub.add_parser("candidates")
    for k in ("--index", "--state", "--region", "--diag", "--out"):
        c.add_argument(k, required=True)
    c.add_argument("--attempts")
    s = sub.add_parser("assign")
    for k in ("--candidates", "--ranking", "--out"):
        s.add_argument(k, required=True)
    s.add_argument("--index")
    s.add_argument("--attempts")
    a = ap.parse_args()
    {"index": index, "candidates": candidates, "assign": assign}[a.cmd](a)


if __name__ == "__main__":
    main()
