#!/usr/bin/env python3
"""
AEGIS Phase 2 region selection -- deterministic part.

Two subcommands, with LLM diagnosis in between (aegis-timing-analyzer):

  prepare   STA report + clocks + RTL (+ lock map)  ->  regions + analyzer inputs
  finalize  regions + diagnoses (+ weights, attempt records)  ->  ranked queue + dispatch

Every number in the selection (deficits, weights, overlaps, scores, quotas)
is computed here, never by an LLM, so the same inputs always give the same
selection.

prepare
  python3 aegis_select.py prepare --report sta.rpt --clocks clocks.json \
      --rtl a.v b.v --top TOP [--synth-json synth.json] [--lockmap lock_map.json] \
      [--design NAME --base-version v2.0] [--margin 0.1] [--theta 0.5] \
      [--phi 32] [--smax 80] [--cache diag_cache] --out sel/

finalize
  python3 aegis_select.py finalize --sel sel/ [--weights weights.json] \
      [--attempts attempts.json] [--alpha 0.6 --beta 0.3] [--budget 10] \
      [--rho 0.8] [--dispatch 3] [--cache diag_cache]
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict

FLOP_TYPES = {"$dff", "$adff", "$sdff", "$dffe", "$adffe", "$sdffe", "$sdffce",
              "$aldff", "$aldffe", "$dffsr", "$dffsre", "$dlatch", "$adlatch"}
PIN_NAMES = {"D", "Q", "CK", "CLK", "C", "QN", "SE", "SI", "RN", "SN", "E", "EN"}


# ----------------------------------------------------------------------------
# 1. STA report parsing (OpenSTA / PrimeTime-style "full" path reports)
# ----------------------------------------------------------------------------
def parse_report(text):
    """Return the worst path per endpoint. Each path: startpoint, endpoint,
    launch/capture clocks, slack, launch/capture edge times, required time R."""
    paths = []
    for block in re.split(r"(?m)^\s*Startpoint:", text)[1:]:
        block = "Startpoint:" + block
        sp = re.search(r"Startpoint:\s*(\S+)\s*\((.*?)\)", block)
        ep = re.search(r"Endpoint:\s*(\S+)\s*\((.*?)\)", block)
        sl = re.search(r"(?m)^\s*(-?\d+(?:\.\d+)?)\s+slack\b", block)
        if not (sp and ep and sl):
            continue
        clk_of = lambda desc: (re.search(r"clocked by\s+(\S+?)\)?$", desc) or [None, None])[1]
        edges = re.findall(r"(?m)^\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+clock\s+(\S+)\s+\((rise|fall) edge\)", block)
        launch_t = float(edges[0][1]) if len(edges) >= 1 else None
        capture_t = float(edges[1][1]) if len(edges) >= 2 else None
        cap_clk = clk_of(ep.group(2)) or (edges[1][2] if len(edges) >= 2 else None)
        lau_clk = clk_of(sp.group(2)) or (edges[0][2] if edges else None)
        paths.append({
            "startpoint": sp.group(1), "endpoint": ep.group(1),
            "launch_clock": lau_clk, "capture_clock": cap_clk,
            "slack_ns": float(sl.group(1)),
            "launch_edge_ns": launch_t, "capture_edge_ns": capture_t,
        })
    worst = {}
    for p in paths:
        key = strip_pin(p["endpoint"])
        if key not in worst or p["slack_ns"] < worst[key]["slack_ns"]:
            worst[key] = p
    return list(worst.values())


def strip_pin(name):
    parts = re.split(r"[/]", name)
    if len(parts) > 1 and parts[-1] in PIN_NAMES:
        parts = parts[:-1]
    return "/".join(parts)


# ----------------------------------------------------------------------------
# 2. Clock relations
# ----------------------------------------------------------------------------
def clock_relation(clocks, a, b):
    """identical | related | asynchronous, from clocks.json:
       {"clocks": {name: {"period_ns": x, "master": name|null}},
        "synchronous_groups": [[name, ...], ...]}"""
    if a is None or b is None or a == b:
        return "identical"
    C = clocks["clocks"]

    def root(c):
        seen = set()
        while c in C and C[c].get("master") and c not in seen:
            seen.add(c)
            c = C[c]["master"]
        return c
    if root(a) == root(b):
        return "related"
    for g in clocks.get("synchronous_groups", []):
        if a in g and b in g:
            return "related"
    return "asynchronous"


# ----------------------------------------------------------------------------
# 3. Netlists and cones
# ----------------------------------------------------------------------------
def yosys_json(script):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "n.json")
        r = subprocess.run(["yosys", "-q", "-p", script + "; write_json " + out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("yosys failed:\n" + (r.stderr or r.stdout))
        return json.load(open(out))


def top_module(net):
    for name, m in net["modules"].items():
        if m.get("attributes", {}).get("top") in (1, "1", "00000000000000000000000000000001"):
            return m
    return next(iter(net["modules"].values()))


class Netlist:
    """Pre-synthesis RTL netlist (Yosys after proc + flatten) with source lines."""

    def __init__(self, rtl_files, top):
        fe = "; ".join(("read_verilog -sv " + f) for f in rtl_files)
        self.m = top_module(yosys_json("%s; hierarchy -top %s; proc; flatten; opt_clean" % (fe, top)))
        self.driver, self.readers = {}, defaultdict(int)
        for cname, c in self.m["cells"].items():
            for port, d in c.get("port_directions", {}).items():
                for bit in c["connections"].get(port, []):
                    if isinstance(bit, str):
                        continue
                    if d == "output":
                        self.driver[bit] = cname
                    else:
                        self.readers[bit] += 1
        self.names = {}
        for wname, w in self.m["netnames"].items():
            if w.get("hide_name"):
                continue
            self.names[wname.lstrip("\\")] = w

    def src_lines(self, cname):
        src = self.m["cells"][cname].get("attributes", {}).get("src", "")
        out = set()
        for piece in src.split("|")[-1:]:     # own statement only; flatten prepends the instance line
            mm = re.match(r"(.+?):(\d+)", piece)
            if mm:
                out.add("%s:%s" % (os.path.basename(mm.group(1)), mm.group(2)))
        return out

    def lookup(self, base, idx):
        cands = [n for n in self.names if n == base or n.endswith("." + base)]
        if not cands:
            return None, None
        name = min(cands, key=len)
        w = self.names[name]
        bits = w["bits"]
        off = int(w.get("offset", 0))
        i = 0 if idx is None else (idx - off if not w.get("upto") else len(bits) - 1 - (idx - off))
        if not 0 <= i < len(bits):
            return None, None
        return name, bits[i]

    def lookup_mem(self, base):
        """Memory endpoints (synthesized to flops, e.g. u_mem/mem[2]_reg[0]) map to the
        write ports of the RTL memory: returns the $memwr cells for that memory."""
        b = re.sub(r"\[\d+\]$", "", base)
        out = []
        for cn, c in self.m["cells"].items():
            if c["type"].startswith("$memwr"):
                mid = str(c.get("parameters", {}).get("MEMID", "")).lstrip("\\")
                if mid == b or mid.endswith("." + b):
                    out.append(cn)
        return out

    def mem_cone(self, cells, phi=None):
        bits, ep = [], set()
        for cn in cells:
            ep |= self.src_lines(cn)
            c = self.m["cells"][cn]
            for p, d in c.get("port_directions", {}).items():
                if d == "input" and p != "CLK":
                    bits += [x for x in c["connections"].get(p, []) if not isinstance(x, str)]
        stmts = set()
        for b in bits:
            s_, _ = self.cone(b, phi)
            stmts |= s_
            drv = self.driver.get(b)
        return stmts | ep, ep

    def cone(self, bit, phi=None):
        """Source statements in the combinational fan-in of `bit`, stopping at
        flops and primary inputs. With phi set, do not traverse through nets
        read by more than phi cells (shared control nets)."""
        start = bit
        drv = self.driver.get(bit)
        stmts, ep_stmt = set(), set()
        if drv is not None and self.m["cells"][drv]["type"] in FLOP_TYPES:
            ep_stmt = self.src_lines(drv)
            start_bits = [b for b in self.m["cells"][drv]["connections"].get("D", []) if not isinstance(b, str)]
        else:
            start_bits = [start]
        seen, stack = set(), list(start_bits)
        while stack:
            b = stack.pop()
            if b in seen:
                continue
            seen.add(b)
            if phi is not None and b not in start_bits and self.readers[b] > phi:
                continue
            c = self.driver.get(b)
            if c is None or self.m["cells"][c]["type"] in FLOP_TYPES:
                continue
            stmts |= self.src_lines(c)
            cell = self.m["cells"][c]
            for port, d in cell.get("port_directions", {}).items():
                if d == "input":
                    stack.extend(x for x in cell["connections"].get(port, []) if not isinstance(x, str))
        return stmts, ep_stmt


def normalize(name):
    """STA instance or net name -> (hierarchical base, bit index)."""
    n = strip_pin(name).lstrip("\\").replace("/", ".")
    n = re.sub(r"\$.*$", "", n)                       # Yosys cell suffixes like $_DFF_P_
    m = re.match(r"^(.*?)(?:_reg)?(?:\[(\d+)\])?(?:_reg)?$", n)
    base, idx = m.group(1), m.group(2)
    base = re.sub(r"\\", "", base).strip()
    return base, (int(idx) if idx is not None else None)


def synth_q_names(synth_json):
    """Instance name -> name of the net on its Q pin, from a synthesized netlist
    JSON, for flows where flop instance names do not carry the register name."""
    if not synth_json:
        return {}
    m = top_module(json.load(open(synth_json)))
    bit2name = {}
    for wname, w in m["netnames"].items():
        if w.get("hide_name"):
            continue
        for i, b in enumerate(w["bits"]):
            if not isinstance(b, str):
                idx = int(w.get("offset", 0)) + i
                bit2name[b] = "%s[%d]" % (wname.lstrip("\\"), idx) if len(w["bits"]) > 1 else wname.lstrip("\\")
    out = {}
    for cname, c in m["cells"].items():
        q = c.get("connections", {}).get("Q")
        if q and not isinstance(q[0], str) and q[0] in bit2name:
            out[cname.lstrip("\\")] = bit2name[q[0]]
    return out


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def read_lines(rtl_files):
    text = {}
    for f in rtl_files:
        for i, line in enumerate(open(f).read().splitlines(), 1):
            text["%s:%d" % (os.path.basename(f), i)] = line.strip()
    return text


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:10]


class UF:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


# ----------------------------------------------------------------------------
# prepare
# ----------------------------------------------------------------------------
def prepare(a):
    clocks = json.load(open(a.clocks))
    lockmap = json.load(open(a.lockmap)) if a.lockmap else {"immutable": [], "contract": {}, "contracts": {}}
    L = set(lockmap.get("immutable", []))
    K = dict(lockmap.get("contract", {}))
    paths = parse_report(open(a.report).read())
    net = Netlist(a.rtl, a.top)
    qnames = synth_q_names(a.synth_json)
    srctext = read_lines(a.rtl)
    os.makedirs(os.path.join(a.out, "regions"), exist_ok=True)

    audit, unmapped, kept, no_logic = [], [], [], []
    blocked = defaultdict(float)
    for p in paths:
        if p["slack_ns"] >= a.margin:
            continue
        period = clocks["clocks"].get(p["capture_clock"], {}).get("period_ns")
        R = None
        if p["launch_edge_ns"] is not None and p["capture_edge_ns"] is not None:
            R = p["capture_edge_ns"] - p["launch_edge_ns"]
        if not R or R <= 0:
            R = period
        if not R:
            unmapped.append({**p, "reason": "no required time and no clock period"})
            continue
        p["required_ns"] = R
        p["deficit"] = max(0.0, a.margin - p["slack_ns"]) / R
        rel = clock_relation(clocks, p["launch_clock"], p["capture_clock"])
        p["relation"] = rel
        if rel == "asynchronous":
            audit.append({"endpoint": p["endpoint"], "launch_clock": p["launch_clock"],
                          "capture_clock": p["capture_clock"], "slack_ns": p["slack_ns"],
                          "issue": "violating path between asynchronous clocks: missing or violated CDC exception"})
            continue
        ep_inst = strip_pin(p["endpoint"])
        key = qnames.get(ep_inst, ep_inst)
        base, idx = normalize(key)
        wname, bit = net.lookup(base, idx)
        if bit is None:
            mem = net.lookup_mem(base)
            if not mem:
                unmapped.append({**p, "reason": "endpoint not found in RTL netlist (%s)" % key})
                continue
            wname = re.sub(r"\[\d+\]$", "", base) + "[mem]"
            cone, ep_stmt = net.mem_cone(mem)
            cone_red, _ = net.mem_cone(mem, phi=a.phi)
        else:
            cone, ep_stmt = net.cone(bit)
            cone_red, _ = net.cone(bit, phi=a.phi)
        tags = []
        if rel == "related":
            tags.append("latency-sensitive")
        if not cone:
            no_logic.append({**p, "reason": "register-to-register path with no logic in the RTL cone (not an RTL logic problem)"})
            continue
        if cone <= L:
            blocked[lockmap.get("category", {}).get(sorted(cone & L)[0], "immutable")] += p["deficit"]
            continue
        removed = sorted(cone & L)
        if removed:
            tags.append("lock-adjacent")
            cone, cone_red = cone - L, cone_red - L
        crossings = sorted({K[s] for s in cone if s in K})
        if crossings:
            tags.append("contract-bound")
        kept.append({**p, "rtl_register": wname, "bit_index": idx, "cone": sorted(cone), "locked_removed": removed,
                     "cone_reduced": sorted(cone_red or cone), "endpoint_stmt": sorted(ep_stmt),
                     "tags": tags, "crossings": crossings})

    # cluster per capture domain
    regions = []
    by_dom = defaultdict(list)
    for e in kept:
        by_dom[e["capture_clock"]].append(e)
    for dom, eps in sorted(by_dom.items()):
        ids = list(range(len(eps)))
        uf = UF(ids)
        members = {i: {i} for i in ids}
        cone_of = {i: set(eps[i]["cone"]) for i in ids}
        pairs = []
        for i in ids:
            for j in ids:
                if j <= i:
                    continue
                ci, cj = set(eps[i]["cone_reduced"]), set(eps[j]["cone_reduced"])
                ov = len(ci & cj) / max(1, min(len(ci), len(cj)))
                if ov >= a.theta:
                    pairs.append((-ov, i, j))
        for _, i, j in sorted(pairs):
            ri, rj = uf.find(i), uf.find(j)
            if ri == rj:
                continue
            merged = cone_of[ri] | cone_of[rj]
            if len(merged) > a.smax:
                continue
            uf.union(ri, rj)
            r = uf.find(ri)
            members[r] = members.pop(ri, set()) | members.pop(rj, set()) | {ri, rj}
            cone_of[r] = merged
        groups = defaultdict(list)
        for i in ids:
            groups[uf.find(i)].append(eps[i])
        for g in groups.values():
            g.sort(key=lambda e: -e["deficit"])
            regs = sorted(e["rtl_register"] + ("" if e["bit_index"] is None else "[%d]" % e["bit_index"]) for e in g)
            rid = "r_" + h(dom + "|" + "|".join(regs))
            cone = sorted(set().union(*[set(e["cone"]) for e in g]))
            regions.append({
                "region_id": rid, "capture_clock": dom,
                "period_ns": clocks["clocks"].get(dom, {}).get("period_ns"),
                "endpoints": g, "cone": cone,
                "crossings": sorted(set().union(*[set(e["crossings"]) for e in g])),
                "cone_hash": h("\n".join(srctext.get(s, s) for s in cone)),
            })

    # analyzer inputs, diagnosis cache
    todo = []
    cache = a.cache
    os.makedirs(os.path.join(a.out, "diag"), exist_ok=True)
    for r in regions:
        region_json = {
            "design": a.design, "base_version": a.base_version, "region_id": r["region_id"],
            "capture_clock": r["capture_clock"], "period_ns": r["period_ns"], "margin_ns": a.margin,
            "endpoints": [{k: e[k] for k in ("endpoint", "startpoint", "launch_clock", "slack_ns",
                                             "required_ns", "deficit", "relation", "tags")} for e in (r["endpoints"] if len(r["endpoints"]) <= REP_MAX else rep_endpoints(r["endpoints"]))],
            "cone": [{"file": s.split(":")[0], "line": int(s.split(":")[1]), "text": srctext.get(s, ""),
                      "tier": "contract" if s in K else "free"} for s in r["cone"]],
            "rtl_files": [os.path.abspath(f) for f in a.rtl],
            "context": [],
            "locked_neighbors": [{"file": s.split(":")[0], "line": int(s.split(":")[1]), "text": srctext.get(s, "")}
                                 for s in sorted(set().union(*[set(e["locked_removed"]) for e in r["endpoints"]]))],
            "contracts": [lockmap.get("contracts", {}).get(c, {"crossing": c}) for c in r["crossings"]],
            "attempt_record": None,
            "root_cause_keys": ["long_combinational_depth", "wide_fanin_fanout", "complex_arithmetic",
                                "control_data_coupling", "reconvergent_fanout"],
        }
        json.dump(region_json, open(os.path.join(a.out, "regions", r["region_id"] + ".region.json"), "w"), indent=1)
        ck = os.path.join(cache, "%s.%s.diag.json" % (r["region_id"], r["cone_hash"])) if cache else None
        dst = os.path.join(a.out, "diag", r["region_id"] + ".diag.json")
        if ck and os.path.exists(ck):
            open(dst, "w").write(open(ck).read())
        else:
            todo.append(r["region_id"])

    state = {"margin_ns": a.margin, "design": a.design, "base_version": a.base_version,
             "params": {"theta": a.theta, "phi": a.phi, "smax": a.smax},
             "regions": regions, "constraint_audit": audit, "unmapped_endpoints": unmapped, "no_logic_endpoints": no_logic,
             "match_rate": (len(kept) + len(no_logic) + 0.0) / max(1, len(kept) + len(no_logic) + len(unmapped)),
             "blocked_deficit": dict(blocked)}
    json.dump(state, open(os.path.join(a.out, "regions.json"), "w"), indent=1)
    json.dump(todo, open(os.path.join(a.out, "diagnosis_todo.json"), "w"), indent=1)
    print("paths<margin=%d async=%d unmapped=%d no_logic=%d kept=%d regions=%d needs_diagnosis=%d"
          % (len([p for p in paths if p["slack_ns"] < a.margin]), len(audit), len(unmapped), len(no_logic),
             len(kept), len(regions), len(todo)))


# 2026-11-04: a region with more than REP_MAX endpoints (only drrtl_fifo_2clk: its 128x32 FIFO memory synthesized to
# 2494 flops sharing one cone; every other region in every run so far has <= 665) is shown to the analyzer as one
# endpoint per register (its worst bit); the diagnosis of a register applies to all its bits. Regions at or below
# REP_MAX are unchanged, so completed runs are unaffected.
REP_MAX = 1000


def rep_key(e):
    return re.sub(r"\[\d+\]$", "", e["endpoint"])


def rep_endpoints(eps):
    seen, out = set(), []
    for e in eps:  # eps are sorted by deficit, so the first of each register is its worst bit
        if rep_key(e) not in seen:
            seen.add(rep_key(e)); out.append(e)
    return out


def expand_diag(r, d):
    if len(r["endpoints"]) <= REP_MAX:
        return d
    by = {rep_key({"endpoint": e.get("endpoint", "")}): e for e in d.get("endpoints", [])}
    d = dict(d)
    d["endpoints"] = [dict(by[rep_key(e)], endpoint=e["endpoint"]) for e in r["endpoints"] if rep_key(e) in by]
    return d


# ----------------------------------------------------------------------------
# finalize
# ----------------------------------------------------------------------------
AMENABLE = {"combinational", "sequential-safe"}


def check_diag(r, d):
    errs = []
    want = [e["endpoint"] for e in r["endpoints"]]
    got = [e.get("endpoint") for e in d.get("endpoints", [])]
    if want != got:
        errs.append("endpoint list differs from input")
    for e in d.get("endpoints", []):
        if e.get("amenability") not in AMENABLE | {"sequential-unsafe", "out-of-scope"}:
            errs.append("bad amenability for %s" % e.get("endpoint"))
    return errs


def finalize(a):
    S = json.load(open(os.path.join(a.sel, "regions.json")))
    weights = json.load(open(a.weights)) if a.weights else {}
    attempts = json.load(open(a.attempts)) if a.attempts and os.path.exists(a.attempts) else {}
    regions = S["regions"]

    # attach diagnoses
    problems = {}
    for r in regions:
        p = os.path.join(a.sel, "diag", r["region_id"] + ".diag.json")
        if not os.path.exists(p):
            problems[r["region_id"]] = ["missing diagnosis"]
            r["diagnosis"] = None
            continue
        d = expand_diag(r, json.load(open(p)))
        errs = check_diag(r, d)
        if errs:
            problems[r["region_id"]] = errs
            r["diagnosis"] = None
            continue
        r["diagnosis"] = d
        if a.cache:
            os.makedirs(a.cache, exist_ok=True)
            json.dump(d, open(os.path.join(a.cache, "%s.%s.diag.json" % (r["region_id"], r["cone_hash"])), "w"), indent=1)
    if problems:
        json.dump(problems, open(os.path.join(a.sel, "diagnosis_errors.json"), "w"), indent=1)
        print("diagnosis problems in %d regions (see diagnosis_errors.json); they are excluded" % len(problems))

    # per-domain deficits over all surviving endpoints
    dom = defaultdict(lambda: {"max": 0.0, "sum": 0.0})
    for r in regions:
        for e in r["endpoints"]:
            D = dom[r["capture_clock"]]
            D["max"] = max(D["max"], e["deficit"])
            D["sum"] += e["deficit"]
    unreachable = 0.0
    for r in regions:
        r["eligible"] = False
        r["priority"] = 0.0
        r["amenable_sum"] = 0.0
        if r["diagnosis"] is None:
            continue
        lab = {e["endpoint"]: e["amenability"] for e in r["diagnosis"]["endpoints"]}
        am = [e for e in r["endpoints"] if lab.get(e["endpoint"]) in AMENABLE]
        unreachable += sum(e["deficit"] for e in r["endpoints"] if lab.get(e["endpoint"]) not in AMENABLE)
        if not am:
            continue
        D = dom[r["capture_clock"]]
        dmax = max(e["deficit"] for e in am)
        dsum = sum(e["deficit"] for e in am)
        r["amenable_sum"] = dsum
        r["priority"] = (a.alpha * dmax / D["max"] if D["max"] else 0) + (a.beta * dsum / D["sum"] if D["sum"] else 0)
        rec = attempts.get(r["region_id"], {})
        r["tabu"] = bool(rec.get("tabu"))
        r["eligible"] = r["priority"] > 0 and not r["tabu"]

    # quotas
    w = lambda d: float(weights.get(d, 1.0))
    viol = sorted([d for d in dom if dom[d]["sum"] > 0], key=lambda d: (-w(d) * dom[d]["sum"], d))
    avail = {d: sum(1 for r in regions if r["capture_clock"] == d and r["eligible"]) for d in viol}
    quota = {d: 0 for d in viol}
    B, nv = a.budget, len(viol)
    if nv > B:
        for d in viol[:B]:
            quota[d] = 1
    elif nv:
        tot = sum(w(d) * dom[d]["sum"] for d in viol)
        raw = {d: (B - nv) * w(d) * dom[d]["sum"] / tot for d in viol}
        for d in viol:
            quota[d] = 1 + int(math.floor(raw[d]))
        left = B - sum(quota.values())
        for d in sorted(viol, key=lambda d: (-(raw[d] - math.floor(raw[d])), d))[:left]:
            quota[d] += 1
    spare = 0
    for d in viol:
        if quota[d] > avail[d]:
            spare += quota[d] - avail[d]
            quota[d] = avail[d]
    while spare:
        open_doms = [d for d in viol if quota[d] < avail[d]]
        if not open_doms:
            break
        quota[open_doms[0]] += 1
        spare -= 1

    # greedy pick per domain, then merge
    picked = {}
    for d in viol:
        cand = sorted([r for r in regions if r["capture_clock"] == d and r["eligible"]],
                      key=lambda r: (-r["priority"], r["region_id"]))
        sel, cov = [], 0.0
        for r in cand:
            if len(sel) >= quota[d] or (dom[d]["sum"] and cov >= a.rho * dom[d]["sum"]):
                break
            sel.append(r)
            cov += r["amenable_sum"]
        picked[d] = sel
    queue = []
    heads = {d: list(v) for d, v in picked.items() if v}
    while heads:
        d = max(heads, key=lambda d: (w(d) * heads[d][0]["amenable_sum"], d))
        queue.append(heads[d].pop(0))
        if not heads[d]:
            del heads[d]

    # dispatch R pairwise-disjoint regions, preferring different files
    dispatch, used_stmts, used_files = [], set(), set()
    for pass_ in (0, 1):
        for r in queue:
            if len(dispatch) >= a.dispatch or r in dispatch:
                continue
            cone = set(r["cone"])
            files = {s.split(":")[0] for s in cone}
            if cone & used_stmts:
                continue
            if pass_ == 0 and files & used_files:
                continue
            dispatch.append(r)
            used_stmts |= cone
            used_files |= files

    timing_met = all(dom[d]["sum"] == 0 for d in dom)
    out = {
        "design": S["design"], "base_version": S["base_version"], "margin_ns": S["margin_ns"],
        "alpha": a.alpha, "beta": a.beta, "budget": B, "rho": a.rho,
        "per_domain": [{"clock": d, "weight": w(d), "deficit_max": round(dom[d]["max"], 6),
                        "deficit_sum": round(dom[d]["sum"], 6), "quota": quota.get(d, 0),
                        "regions_available": avail.get(d, 0)} for d in sorted(dom)],
        "constraint_audit": S["constraint_audit"], "unmapped_endpoints": S["unmapped_endpoints"],
        "no_logic_endpoints": S.get("no_logic_endpoints", []),
        "match_rate": S["match_rate"], "blocked_deficit": S["blocked_deficit"],
        "unreachable_deficit": round(unreachable, 6),
        "area_recovery": timing_met,
        "queue": [{"region_id": r["region_id"], "capture_clock": r["capture_clock"],
                   "priority": round(r["priority"], 6), "amenable_deficit": round(r["amenable_sum"], 6)} for r in queue],
        "dispatch": [r["region_id"] for r in dispatch],
        "regions": [{"region_id": r["region_id"], "capture_clock": r["capture_clock"],
                     "priority": round(r["priority"], 6), "eligible": r["eligible"],
                     "tabu": r.get("tabu", False), "dispatched": r in dispatch,
                     "tags": sorted(set(t for e in r["endpoints"] for t in e["tags"])),
                     "crossings": r["crossings"], "endpoints": [e["endpoint"] for e in r["endpoints"]],
                     "cone": r["cone"], "diagnosis": r["diagnosis"],
                     "optimization": None, "result": None} for r in regions],
    }
    json.dump(out, open(os.path.join(a.sel, "selection.json"), "w"), indent=1)
    print("domains=%d violating=%d queue=%d dispatch=%s area_recovery=%s"
          % (len(dom), len(viol), len(queue), out["dispatch"], timing_met))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--report", required=True)
    p.add_argument("--clocks", required=True)
    p.add_argument("--rtl", nargs="+", required=True)
    p.add_argument("--top", required=True)
    p.add_argument("--synth-json")
    p.add_argument("--lockmap")
    p.add_argument("--design", default="design")
    p.add_argument("--base-version", default="v0")
    p.add_argument("--margin", type=float, default=0.1)
    p.add_argument("--theta", type=float, default=0.5)
    p.add_argument("--phi", type=int, default=32)
    p.add_argument("--smax", type=int, default=80)
    p.add_argument("--cache")
    p.add_argument("--out", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("--sel", required=True)
    f.add_argument("--weights")
    f.add_argument("--attempts")
    f.add_argument("--alpha", type=float, default=0.6)
    f.add_argument("--beta", type=float, default=0.3)
    f.add_argument("--budget", type=int, default=10)
    f.add_argument("--rho", type=float, default=0.8)
    f.add_argument("--dispatch", type=int, default=3)
    f.add_argument("--cache")
    a = ap.parse_args()
    prepare(a) if a.cmd == "prepare" else finalize(a)


if __name__ == "__main__":
    main()
