#!/usr/bin/env python3
"""
AEGIS Phase 3 -- Execution Engine (candidate generation).

  envelope  region + lock map  ->  edit envelope E(r) = (C(r) U A(r) U D_new) \\ L
  generate  region + diagnosis + assignment slot  ->  one candidate (C1..C5)
  vanilla   whole design + timing summary  ->  one unguarded candidate (baseline mode)

  python3 aegis_gen.py envelope --region sel/regions/<rid>.region.json --rtl a.v b.v --top TOP \\
      --lockmap phase1/lock_map.json --out cand/<rid>/envelope.json
  python3 aegis_gen.py generate --region ... --diag ... --assignment ... --slot C1 \\
      --envelope cand/<rid>/envelope.json --rtl a.v b.v --out cand/<rid>/C1 \\
      [--library-state flow/skills/library_state.json] [--model M --backend claude-cli]

The LLM sees the modules that contain the region with every line tagged
E (editable), L (locked, immutable) or . (context), and returns complete
rewritten modules. Splicing is deterministic: only modules the LLM returns
are replaced, byte-for-byte elsewhere. Whether the candidate respects the
envelope is NOT trusted to the LLM: Phase 4 (aegis_verify.py gate) re-checks it.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aegis_llm  # noqa: E402
from aegis_common import module_spans, module_of_line, norm  # noqa: E402

SYSTEM = """You are the RTL Optimizer in the AEGIS framework. You rewrite synthesizable Verilog/SystemVerilog to reduce the delay of specific failing timing endpoints in a multi-clock design.

Rules you must follow exactly:
1. Change only lines tagged E. Lines tagged L are clock-domain-crossing or clock-generation logic and are immutable; lines tagged . are context and must stay as they are.
2. You may add new wire/reg/logic declarations and new continuous assignments or always blocks that drive NEW signals, inside the shown modules.
3. Never change module names, parameters, port lists, port widths or directions. Never add or remove modules.
4. Preserve cycle-accurate behavior at every module port and every existing register: same values on the same clock edge, including during and after reset. No pipelining, no added or removed latency, no changed reset values.
5. Keep the code synthesizable (no initial blocks, delays, or simulation-only constructs).
6. Return every module you changed IN FULL, each in its own ```verilog fenced block, and nothing else except at most three sentences explaining the change. Do not return modules you did not change."""

SLOT_INTRO = {
    "C1": "Apply the PRIMARY skill below as directly and conservatively as possible.",
    "C2": "Apply the PRIMARY skill below, but explore a structurally different variant of it than the most obvious one.",
    "C3": "Apply the ALTERNATE skill below conservatively.",
    "C4": "Apply the ALTERNATE skill below, exploring a bolder structural variant.",
    "C5": "Propose a structurally distinct, latency-preserving implementation of the editable logic (restructuring, resource sharing, retiming of registers within the editable lines). Do not pipeline.",
}


# ----------------------------------------------------------------------------
def endpoint_blocks(region, rtl, top, immutable):
    """A(r): source ranges of the always blocks that assign the region's endpoint registers."""
    from aegis_ingest import Flat, lookup_net
    flat = Flat(rtl, top)
    owner = {}
    for cn in flat.ffs():
        for b in flat.q_bits(cn):
            owner[b] = cn
    out = set()
    for e in region["endpoints"]:
        b = lookup_net(flat, e["endpoint"])
        cn = owner.get(b)
        r = flat.src_range(cn) if cn else None
        if r:
            f, l1, l2 = r
            for l in range(l1, l2 + 1):
                if "%s:%d" % (f, l) not in immutable:
                    out.add((f, l))
    return out


def envelope(a):
    region = json.load(open(a.region))
    lm = json.load(open(a.lockmap)) if a.lockmap else {"immutable": {}}
    immutable = set(lm.get("immutable", {}))
    cone = {(c["file"], c["line"]) for c in region["cone"]}
    blocks = endpoint_blocks(region, a.rtl, a.top, immutable) if a.top else set()
    lines = {}
    for f, l in cone | blocks:
        if "%s:%d" % (f, l) in immutable:
            continue
        lines.setdefault(f, set()).add(l)
    texts = {os.path.basename(p): open(p).read() for p in a.rtl}
    modules = set()
    for f, ls in lines.items():
        spans = module_spans(texts.get(f, ""))
        for l in ls:
            m = module_of_line(spans, l)
            if m:
                modules.add((f, m))
    out = {"region_id": region["region_id"], "files": {f: sorted(ls) for f, ls in lines.items()},
           "modules": sorted([{"file": f, "module": m} for f, m in modules], key=lambda x: (x["file"], x["module"])),
           "contract_lines": sorted("%s:%d" % (c["file"], c["line"]) for c in region["cone"] if c.get("tier") == "contract"),
           "immutable_in_modules": []}
    for f, m in modules:
        spans = module_spans(texts[f])
        a_, b_ = next((s, e) for n, s, e in spans if n == m)
        out["immutable_in_modules"] += ["%s:%d" % (f, l) for l in range(a_, b_ + 1) if "%s:%d" % (f, l) in immutable]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({"region_id": out["region_id"], "editable_lines": sum(len(v) for v in out["files"].values()),
                      "modules": [m["module"] for m in out["modules"]]}))
    return out


# ----------------------------------------------------------------------------
def tagged_source(rtl, env):
    """Modules containing the envelope, every line tagged E / L / ."""
    texts = {os.path.basename(p): open(p).read() for p in rtl}
    imm = set(env["immutable_in_modules"])
    parts = []
    for m in env["modules"]:
        f = m["file"]
        src = texts[f].splitlines()
        spans = module_spans(texts[f])
        s, e = next((a, b) for n, a, b in spans if n == m["module"])
        edit = set(env["files"].get(f, []))
        body = []
        for l in range(s, e + 1):
            tag = "E" if l in edit else ("L" if "%s:%d" % (f, l) in imm else ".")
            body.append("%s %5d| %s" % (tag, l, src[l - 1]))
        parts.append("// file %s, module %s (lines %d-%d)\n%s" % (f, m["module"], s, e, "\n".join(body)))
    return "\n\n".join(parts)


def failure_notes(state, causes, limit=6):
    notes = []
    for c in causes:
        notes += state.get("failure_notes", {}).get(c, [])[-limit:]
    return notes[-limit:]


def build_prompt(region, diag, plan, env, rtl, state):
    eps = []
    dmap = {d["endpoint"]: d for d in diag.get("endpoints", [])}
    for e in region["endpoints"]:
        d = dmap.get(e["endpoint"], {})
        eps.append("- %s  (start %s, slack %.3f ns, %s; root cause %s; %s)" % (
            e["endpoint"], e["startpoint"], e["slack_ns"], ", ".join(e.get("tags", [])) or "no tags",
            d.get("root_cause"), d.get("amenability")))
    p = ["Design region %s, capture clock %s (period %.3f ns, closure margin %.3f ns)." % (
        region["region_id"], region["capture_clock"], region["period_ns"], region["margin_ns"]),
        "", "Failing endpoints:", "\n".join(eps),
        "", "Dominant root cause: %s. Late-arriving signal: %s." % (diag.get("dominant_root_cause"), diag.get("late_signal")),
        "", "Task (%s): %s" % (plan["slot"], SLOT_INTRO[plan["slot"]])]
    sk = plan.get("skill")
    if sk:
        p += ["", "Skill #%d: %s" % (sk["id"], sk["title"]), "Strategy: %s" % sk["strategy"]]
        if sk.get("aegis_notes"):
            p.append("AEGIS notes: %s" % sk["aegis_notes"])
        if sk.get("why"):
            p.append("Why it fits here: %s" % sk["why"])
        if sk.get("example"):
            p += ["Example:", "```verilog", sk["example"], "```"]
    elif plan.get("direction"):
        p += ["", "Direction: %s" % plan["direction"]]
    if region.get("contracts"):
        p += ["", "CDC contracts that must still hold after your rewrite (logic feeding a crossing): %s" %
              json.dumps(region["contracts"]),
              "The value sequence on every crossing signal must stay identical; a Gray pointer must still change by at most one bit per clock."]
    warns = plan.get("_warnings") or []
    if warns:
        p += ["", "Do NOT do any of the following (they failed before or break CDC/latency):"]
        p += ["- #%d %s" % (w["id"], w["title"]) for w in warns]
    notes = failure_notes(state or {}, [diag.get("dominant_root_cause")] if diag.get("dominant_root_cause") else [])
    if notes:
        p += ["", "Recent failures of other rewrites for this root cause (avoid repeating them):"] + ["- " + n for n in notes]
    p += ["", "Source (E = editable, L = locked, . = context; line numbers are for reference only, do not include them):",
          "", tagged_source(rtl, env)]
    return "\n".join(p)


_FENCE = re.compile(r"```(?:verilog|systemverilog|sv|v)?\s*\n(.*?)```", re.S)


def parse_modules(reply):
    """{module_name: module_text} from fenced blocks in the reply."""
    mods = {}
    for block in _FENCE.findall(reply):
        block = re.sub(r"(?m)^[EL.] {1,6}\d+\| ", "", block)   # tolerate echoed line tags
        for name, s, e in module_spans(block):
            lines = block.splitlines()
            mods[name] = "\n".join(lines[s - 1:e])
    return mods


def splice(rtl, mods, outdir):
    """Write copies of rtl into outdir with the returned modules replaced."""
    os.makedirs(outdir, exist_ok=True)
    replaced, unknown = [], set(mods)
    files = []
    for p in rtl:
        text = open(p).read()
        lines = text.splitlines()
        spans = module_spans(text)
        for name, s, e in sorted(spans, key=lambda x: -x[1]):
            if name in mods:
                lines[s - 1:e] = mods[name].splitlines()
                replaced.append(name)
                unknown.discard(name)
        dst = os.path.join(outdir, os.path.basename(p))
        open(dst, "w").write("\n".join(lines) + ("\n" if text.endswith("\n") else ""))
        files.append(dst)
    return files, replaced, sorted(unknown)


def llm_args(ap):
    ap.add_argument("--model", default=os.environ.get("AEGIS_MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--backend", default=os.environ.get("AEGIS_BACKEND", "claude-cli"))
    ap.add_argument("--base-url")
    ap.add_argument("--effort")


def generate(a):
    region = json.load(open(a.region))
    diag = json.load(open(a.diag))
    asg = json.load(open(a.assignment))
    env = json.load(open(a.envelope))
    state = json.load(open(a.library_state)) if a.library_state and os.path.exists(a.library_state) else {}
    plan = dict(next(p for p in asg["plan"] if p["slot"] == a.slot))
    plan["_warnings"] = asg.get("warnings", [])
    if a.temperature is not None:
        plan["temperature"] = a.temperature
    prompt = build_prompt(region, diag, plan, env, a.rtl, state)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "prompt.txt"), "w").write(prompt)
    meta = {"region_id": region["region_id"], "slot": a.slot, "skill": (plan.get("skill") or {}).get("id"),
            "temperature_requested": plan["temperature"], "model": a.model, "backend": a.backend}
    try:
        r = aegis_llm.call(SYSTEM, prompt, a.model, plan["temperature"], a.backend, a.effort,
                           base_url=a.base_url, tag="gen:%s:%s" % (region["region_id"], a.slot))
    except aegis_llm.LLMError as e:
        meta.update({"status": "llm_error", "error": str(e)[:500]})
        json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
        print(json.dumps(meta))
        return meta
    open(os.path.join(a.out, "reply.txt"), "w").write(r["text"])
    mods = parse_modules(r["text"])
    meta.update({k: r[k] for k in ("temperature_applied", "tokens_in", "tokens_out", "cost_usd", "latency_s")})
    if not mods:
        meta.update({"status": "no_code"})
    else:
        files, replaced, unknown = splice(a.rtl, mods, os.path.join(a.out, "rtl"))
        meta.update({"status": "ok" if not unknown else "unknown_module", "replaced_modules": replaced,
                     "unknown_modules": unknown, "files": files})
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(json.dumps({k: meta.get(k) for k in ("region_id", "slot", "status", "skill", "replaced_modules", "latency_s")}))
    return meta


# ----------------------------------------------------------------------------
VANILLA_SYSTEM = """You are an expert RTL designer. Rewrite the given Verilog to improve timing (worst negative slack) after synthesis, keeping the design functionally equivalent. Return every module you changed IN FULL, each in its own ```verilog fenced block. Do not change module names or port lists."""


def vanilla(a):
    """Unguarded baseline: whole RTL + timing summary, no locks, no skills, no envelope."""
    metrics = json.load(open(a.metrics))
    paths = open(a.report).read().split("Startpoint:")[1:a.paths + 1] if a.report else []
    src = "\n\n".join("// file %s\n%s" % (os.path.basename(p), open(p).read()) for p in a.rtl)
    prompt = "\n".join([
        "Synthesized timing (OpenSTA, per clock): %s" % json.dumps(metrics.get("per_domain")),
        "Design WNS %.3f ns, TNS %.3f ns." % (metrics.get("wns_ns") or 0, metrics.get("tns_ns") or 0),
        "", "Worst paths:", "\n".join("Startpoint:" + p[:1500] for p in paths),
        "", "RTL:", src])
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "prompt.txt"), "w").write(prompt)
    meta = {"slot": a.slot, "mode": "vanilla", "model": a.model, "backend": a.backend,
            "temperature_requested": a.temperature}
    try:
        r = aegis_llm.call(VANILLA_SYSTEM, prompt, a.model, a.temperature, a.backend, a.effort,
                           base_url=a.base_url, tag="vanilla:%s" % a.slot)
    except aegis_llm.LLMError as e:
        meta.update({"status": "llm_error", "error": str(e)[:500]})
        json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
        return meta
    open(os.path.join(a.out, "reply.txt"), "w").write(r["text"])
    mods = parse_modules(r["text"])
    meta.update({k: r[k] for k in ("temperature_applied", "tokens_in", "tokens_out", "cost_usd", "latency_s")})
    if mods:
        files, replaced, unknown = splice(a.rtl, mods, os.path.join(a.out, "rtl"))
        meta.update({"status": "ok" if not unknown else "unknown_module", "replaced_modules": replaced,
                     "unknown_modules": unknown, "files": files})
    else:
        meta["status"] = "no_code"
    json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print(json.dumps({k: meta.get(k) for k in ("slot", "status", "replaced_modules", "latency_s")}))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("envelope")
    e.add_argument("--region", required=True)
    e.add_argument("--rtl", nargs="+", required=True)
    e.add_argument("--top")
    e.add_argument("--lockmap")
    e.add_argument("--out", required=True)
    g = sub.add_parser("generate")
    for k in ("--region", "--diag", "--assignment", "--slot", "--envelope", "--out"):
        g.add_argument(k, required=True)
    g.add_argument("--rtl", nargs="+", required=True)
    g.add_argument("--library-state")
    g.add_argument("--temperature", type=float)
    llm_args(g)
    v = sub.add_parser("vanilla")
    v.add_argument("--rtl", nargs="+", required=True)
    v.add_argument("--metrics", required=True)
    v.add_argument("--report")
    v.add_argument("--paths", type=int, default=5)
    v.add_argument("--slot", default="V1")
    v.add_argument("--temperature", type=float, default=0.5)
    v.add_argument("--out", required=True)
    llm_args(v)
    a = ap.parse_args()
    {"envelope": envelope, "generate": generate, "vanilla": vanilla}[a.cmd](a)


if __name__ == "__main__":
    main()
