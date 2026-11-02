#!/usr/bin/env python3
"""
AEGIS Phase 1 -- Ingestion and the Shield (deterministic).

  ingest   SDC + RTL  ->  clocks.json, clock_relations.json, constraint_audit.json,
                          sdc_exceptions.json, crossings.json, lock_map.json,
                          checksums.json, contracts/ (calibrated), phase1_report.json
  verify   checksums.json + candidate RTL  ->  pass/fail per locked entry

ingest
  python3 aegis_ingest.py ingest --rtl a.v b.v --top TOP --sdc design.sdc \
      [--annotations cdc_annotations.json] [--contracts-tool tools/gen_cdc_props.py] \
      --out work/<design>/phase1

verify
  python3 aegis_ingest.py verify --checksums work/<design>/phase1/checksums.json \
      --rtl cand1.v cand2.v --top TOP

Lock tiers produced:
  immutable       synchronizer flops (whole always block), ASYNC_REG/keep flops,
                  clock-divider flops, `parameter` declarations, and the launch and
                  capture registers of every crossing that is not contract-bound
  contract-bound  fan-in logic of crossings whose contract proves on this design
                  (Gray pointers detected automatically, other types via annotations);
                  their launch registers must stay registers (rule R4, Phase 4)
  free            everything else
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

STATE_CELLS = {"$dff", "$adff", "$sdff", "$dffe", "$adffe", "$sdffe", "$sdffce",
               "$aldff", "$aldffe", "$dffsr", "$dffsre"}
MEM_CELLS = {"$memwr", "$memwr_v2", "$memrd", "$memrd_v2", "$meminit", "$meminit_v2", "$mem", "$mem_v2"}
FF_INPUTS_SKIP = {"CLK", "ARST", "SRST", "CLR", "SET", "AD", "ALOAD"}


# ============================================================================
# SDC (Tcl subset)
# ============================================================================
def tcl_words(s):
    """Split a Tcl command into words, keeping [...] and {...} groups intact."""
    words, cur, depth = [], "", 0
    for ch in s:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                words.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        words.append(cur)
    return words


def obj(word):
    """'[get_ports clk]' -> ('ports', ['clk']); '{a b}' -> ('names', ['a','b'])."""
    w = word.strip()
    m = re.match(r"^\[\s*(get_\w+|all_clocks|all_inputs|all_outputs)\s*(.*?)\s*\]$", w, re.S)
    if m:
        kind = m.group(1).replace("get_", "")
        rest = m.group(2).strip().strip("{}").split()
        rest = [x for x in rest if not x.startswith("-")]
        return kind, rest
    return "names", w.strip("{}").split()


def parse_sdc(path):
    text = open(path).read().replace("\\\n", " ")
    variables = {}
    clocks, gens, groups, exceptions, other = {}, [], [], [], []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.strip().startswith("#") else ""
        if not line:
            continue
        line = re.sub(r"\$\{?(\w+)\}?", lambda m: variables.get(m.group(1), m.group(0)), line)
        w = tcl_words(line)
        cmd, args = w[0], w[1:]

        def opt(name, default=None):
            return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default
        if cmd == "set" and len(args) >= 2:
            variables[args[0]] = args[1].strip("{}\"")
        elif cmd == "create_clock":
            target = obj(args[-1]) if args and args[-1].startswith("[") else ("names", [])
            name = opt("-name") or (target[1][0] if target[1] else None)
            clocks[name] = {"period_ns": float(opt("-period")), "master": None,
                            "source_kind": target[0], "source": target[1][0] if target[1] else None}
        elif cmd == "create_generated_clock":
            target = obj(args[-1])
            gens.append({"name": opt("-name") or target[1][0], "source": obj(opt("-source", "{}")),
                         "master_clock": opt("-master_clock"),
                         "divide_by": float(opt("-divide_by", 1)), "multiply_by": float(opt("-multiply_by", 1)),
                         "target_kind": target[0], "target": target[1][0] if target[1] else None})
        elif cmd == "set_clock_groups":
            kind = next((a[1:] for a in args if a in ("-asynchronous", "-logically_exclusive", "-physically_exclusive")), "asynchronous")
            gs = [obj(args[i + 1])[1] for i, a in enumerate(args) if a == "-group"]
            groups.append({"kind": kind, "groups": gs})
        elif cmd in ("set_false_path", "set_max_delay", "set_min_delay", "set_multicycle_path"):
            e = {"cmd": cmd, "raw": line, "datapath_only": "-datapath_only" in args}
            for k in ("-from", "-to", "-through"):
                if opt(k):
                    e[k[1:]] = obj(opt(k))
            exceptions.append(e)
        else:
            other.append(line)
    # resolve generated clocks
    for g in gens:
        master = g["master_clock"]
        if not master:
            src = g["source"][1][0] if g["source"][1] else None
            master = next((n for n, c in clocks.items() if c["source"] == src), None)
        mp = clocks.get(master, {}).get("period_ns")
        clocks[g["name"]] = {"period_ns": (mp * g["divide_by"] / g["multiply_by"]) if mp else None,
                             "master": master, "source_kind": g["target_kind"], "source": g["target"],
                             "divide_by": g["divide_by"], "multiply_by": g["multiply_by"]}
    return clocks, groups, exceptions, other


def root_of(clocks, c):
    seen = set()
    while clocks.get(c, {}).get("master") and c not in seen:
        seen.add(c)
        c = clocks[c]["master"]
    return c


def relation(clocks, a, b):
    if a == b:
        return "identical"
    return "related" if root_of(clocks, a) == root_of(clocks, b) else "asynchronous"


def covered(groups, exceptions, a, b):
    """How an asynchronous ordered pair (a -> b) is constrained, if at all."""
    for g in groups:
        if g["kind"] in ("asynchronous", "logically_exclusive", "physically_exclusive"):
            ga = [i for i, grp in enumerate(g["groups"]) if a in grp]
            gb = [i for i, grp in enumerate(g["groups"]) if b in grp]
            if ga and gb and ga[0] != gb[0]:
                return "clock_groups"
            if ga and not gb and len(g["groups"]) == 1:
                return "clock_groups"
    for e in exceptions:
        fr, to = e.get("from", ("", [])), e.get("to", ("", []))
        if fr[0] == "clocks" and to[0] == "clocks" and a in fr[1] and b in to[1]:
            if e["cmd"] == "set_false_path":
                return "false_path"
            if e["cmd"] == "set_max_delay" and e["datapath_only"]:
                return "max_delay_datapath_only"
    return None


# ============================================================================
# netlists
# ============================================================================
def yosys_json(script):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "n.json")
        r = subprocess.run(["yosys", "-q", "-p", script + "; write_json " + out], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("yosys failed:\n" + (r.stderr or r.stdout))
        return json.load(open(out))


def is_top(m):
    return m.get("attributes", {}).get("top") in (1, "1", "00000000000000000000000000000001")


class Flat:
    def __init__(self, rtl, top):
        fe = "; ".join("read_verilog -sv " + f for f in rtl)
        # opt_dff folds synchronous resets and enables into the flop cell (SRST/EN pins), so a
        # reset-only mux in front of a synchronizer stage does not hide a direct Q->D chain
        net = yosys_json("%s; hierarchy -top %s; proc; flatten; opt_clean; opt_dff; opt_clean" % (fe, top))
        self.m = next(m for m in net["modules"].values() if is_top(m))
        self.cells = self.m["cells"]
        self.driver, self.readers = {}, defaultdict(int)
        for cn, c in self.cells.items():
            for p, d in c.get("port_directions", {}).items():
                for b in c["connections"].get(p, []):
                    if isinstance(b, str):
                        continue
                    if d == "output":
                        self.driver[b] = (cn, p)
                    else:
                        self.readers[b] += 1
        self.bitname = {}
        self.names = {}
        for wn, w in self.m["netnames"].items():
            if w.get("hide_name"):
                continue
            n = wn.lstrip("\\")
            self.names[n] = w
            for i, b in enumerate(w["bits"]):
                if not isinstance(b, str):
                    self.bitname.setdefault(b, []).append((n, int(w.get("offset", 0)) + i, len(w["bits"])))
        self.ports = {p.lstrip("\\"): d for p, d in self.m["ports"].items()}

    def ffs(self):
        return [cn for cn, c in self.cells.items() if c["type"] in STATE_CELLS]

    def q_bits(self, cn):
        return [b for b in self.cells[cn]["connections"].get("Q", []) if not isinstance(b, str)]

    def reg_name(self, cn):
        """Name of the register in the module that declares the flop (a Q net has
        aliases in every module it passes through)."""
        qs = self.q_bits(cn)
        if not qs or qs[0] not in self.bitname:
            return cn
        m = re.match(r"^\$flatten\\?(.*)\.\$", cn.lstrip("\\"))
        prefix = (m.group(1) + ".") if m else ""
        names = [n for n, _, _ in self.bitname[qs[0]]]
        own = [n for n in names if prefix and n.startswith(prefix) and "." not in n[len(prefix):]]
        if own:
            return own[0]
        if not prefix:
            top_level = [n for n in names if "." not in n]
            if top_level:
                return top_level[0]
        return min(names, key=len)

    def src_range(self, cn):
        """Own source range (file basename, first line, last line) of a cell."""
        src = self.cells[cn].get("attributes", {}).get("src", "")
        piece = src.split("|")[-1] if src else ""
        m = re.match(r"(.+?):(\d+)\.\d+-(\d+)\.\d+", piece) or re.match(r"(.+?):(\d+)", piece)
        if not m:
            return None
        f, l1 = os.path.basename(m.group(1)), int(m.group(2))
        l2 = int(m.group(3)) if m.lastindex and m.lastindex >= 3 else l1
        return f, l1, l2

    def fanin(self, start_bits):
        """Sources of the combinational fan-in: (ff_cell or None, bit), plus the cone's cells."""
        seen, stack, sources, cone = set(), list(start_bits), [], set()
        while stack:
            b = stack.pop()
            if b in seen or isinstance(b, str):
                continue
            seen.add(b)
            d = self.driver.get(b)
            if d is None:
                sources.append((None, b))
                continue
            cn, port = d
            t = self.cells[cn]["type"]
            if t in STATE_CELLS:
                sources.append((cn, b))
                continue
            if t in MEM_CELLS:
                sources.append(("mem:" + cn, b))
                continue
            cone.add(cn)
            for p, dirn in self.cells[cn].get("port_directions", {}).items():
                if dirn == "input":
                    stack.extend(self.cells[cn]["connections"].get(p, []))
        return sources, cone

    def ff_data_bits(self, cn):
        c = self.cells[cn]
        out = []
        for p, d in c.get("port_directions", {}).items():
            if d == "input" and p not in FF_INPUTS_SKIP:
                out += [b for b in c["connections"].get(p, []) if not isinstance(b, str)]
        return out


def lookup_net(flat, name):
    """SDC/STA object name -> bit (pin names like u_div/div_q_reg/Q, port names, nets)."""
    n = name.lstrip("\\")
    n = re.sub(r"/(Q|QN|Z|Y|O|D|CK|CLK)$", "", n).replace("/", ".")
    n = re.sub(r"_reg(\[\d+\])?$", r"\1", n)
    idx = None
    m = re.match(r"^(.*)\[(\d+)\]$", n)
    if m:
        n, idx = m.group(1), int(m.group(2))
    cands = [k for k in flat.names if k == n or k.endswith("." + n)]
    if not cands:
        return None
    w = flat.names[min(cands, key=len)]
    i = 0 if idx is None else idx - int(w.get("offset", 0))
    return w["bits"][i] if 0 <= i < len(w["bits"]) else None


def norm_text(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def file_lines(rtl):
    lines = {}
    for f in rtl:
        lines[os.path.basename(f)] = open(f).read().splitlines()
    return lines


def block_text(lines, f, l1, l2):
    return "\n".join(lines[f][l1 - 1:l2])


# ============================================================================
# ingest
# ============================================================================
def ingest(a):
    os.makedirs(a.out, exist_ok=True)
    clocks, groups, exceptions, other = parse_sdc(a.sdc)
    flat = Flat(a.rtl, a.top)
    lines = file_lines(a.rtl)
    report = {"warnings": [], "issues": []}

    # ---- clock relations and constraint audit ------------------------------
    names = sorted(clocks)
    rel = {x: {y: relation(clocks, x, y) for y in names} for x in names}
    audit = []
    for x in names:
        for y in names:
            if x != y and rel[x][y] == "asynchronous":
                how = covered(groups, exceptions, x, y)
                if how is None:
                    audit.append({"from": x, "to": y, "issue": "asynchronous clock pair has no clock group, false path, or -datapath_only bound"})
    for c, v in clocks.items():
        if v["period_ns"] is None:
            report["issues"].append("clock %s: period could not be resolved" % c)

    # ---- clock nets and flop domains ---------------------------------------
    clk_of_bit = {}
    for c, v in clocks.items():
        b = lookup_net(flat, v["source"]) if v.get("source") else None
        if b is None:
            report["issues"].append("clock %s: source object %s not found in RTL" % (c, v.get("source")))
        else:
            clk_of_bit[b] = c
    dom, unclocked = {}, []
    for cn in flat.ffs():
        cb = flat.cells[cn]["connections"].get("CLK", [None])[0]
        if cb in clk_of_bit:
            dom[cn] = clk_of_bit[cb]
        else:
            unclocked.append(flat.reg_name(cn))
    if unclocked:
        report["issues"].append("flops with no SDC clock (gated or muxed clocks are not traced): %s" % sorted(set(unclocked))[:10])
    div_ffs = [cn for cn in flat.ffs() if any(b in clk_of_bit for b in flat.q_bits(cn))]

    # ---- crossings ----------------------------------------------------------
    q_owner = {}
    for cn in flat.ffs():
        for b in flat.q_bits(cn):
            q_owner[b] = cn
    edges = []    # (src_ff, dst_ff, direct)
    srcbits = defaultdict(set)
    for dst in flat.ffs():
        if dst not in dom:
            continue
        dbits = flat.ff_data_bits(dst)
        sources, _ = flat.fanin(dbits)
        direct_srcs = {q_owner.get(b) for b in flat.cells[dst]["connections"].get("D", []) if not isinstance(b, str)}
        for src, b in sources:
            if not src or src.startswith("mem:") or src not in dom:
                continue
            if rel.get(dom[src], {}).get(dom[dst]) == "asynchronous":
                edges.append((src, dst, src in direct_srcs and len(direct_srcs) == 1))
                srcbits[(src, dst)].add(b)
    edges = sorted(set(edges))

    def next_stage(ff):
        """Next synchronizer stage: a flop in the same domain whose D is exactly this
        flop's Q, with every Q bit read only by that flop (multi-bit flops are one cell)."""
        qs = flat.q_bits(ff)
        if not qs or any(flat.readers[b] != 1 for b in qs):
            return None
        for cn in flat.ffs():
            if dom.get(cn) == dom.get(ff) and flat.cells[cn]["connections"].get("D") == qs:
                return cn
        return None

    sync_ffs = set()
    sync_outputs = set()      # Q bits of the last stage of each synchronizer chain
    crossings = defaultdict(lambda: {"bits": 0, "stages": [], "direct": True, "dst_ffs": [], "src_ffs": []})
    for src, dst, direct in edges:
        key = (flat.reg_name(src), flat.reg_name(dst))
        X = crossings[key]
        X["bits"] += len(srcbits[(src, dst)]) or 1
        X["src_clock"], X["dst_clock"] = dom[src], dom[dst]
        X["direct"] = X["direct"] and direct
        X["src_ffs"].append(src)
        X["dst_ffs"].append(dst)
        chain = [dst]
        if direct:
            while len(chain) < 4:
                nxt = next_stage(chain[-1])
                if not nxt:
                    break
                chain.append(nxt)
        X["stages"].append(len(chain) if direct else 0)
        if direct and len(chain) >= 2:
            sync_ffs.update(chain)
            sync_outputs.update(flat.q_bits(chain[-1]))
            for c in chain[1:]:
                sync_outputs.update(flat.q_bits(c))

    # classify
    out_crossings = []
    for (sreg, dreg), X in sorted(crossings.items()):
        depth = min(X["stages"]) if X["stages"] else 0
        cid = "x_" + hashlib.sha1(("%s->%s" % (sreg, dreg)).encode()).hexdigest()[:8]
        rec = {"id": cid, "src_reg": sreg, "dst_reg": dreg, "src_clock": X["src_clock"], "dst_clock": X["dst_clock"],
               "width": X["bits"], "sync_depth": depth}
        # qualified capture: the destination's data or enable fan-in includes a synchronizer
        # output (with opt_dff the enable is a separate EN pin, so check before the depth rule)
        qualified = False
        if not (X["direct"] and depth >= 2):
            for dst in X["dst_ffs"]:
                srcs, _ = flat.fanin(flat.ff_data_bits(dst))
                if any(b in sync_outputs or (s and s in sync_ffs) for s, b in srcs):
                    qualified = True
        if X["direct"] and depth >= 2:
            rec["kind"] = "gray_candidate" if X["bits"] > 1 else "synchronizer"
        elif qualified:
            rec["kind"] = "qualified_capture"
        elif X["direct"] and depth == 1:
            rec["kind"] = "insufficient_depth"
            report["issues"].append("R2: %s -> %s has a single-flop synchronizer" % (sreg, dreg))
        else:
            rec["kind"] = "unsynchronized"
            report["issues"].append("R1: %s (%s) -> %s (%s) crosses asynchronous clocks with no synchronizer or qualifier"
                                    % (sreg, X["src_clock"], dreg, X["dst_clock"]))
        rec["_src_ffs"], rec["_dst_ffs"] = sorted(set(X["src_ffs"])), sorted(set(X["dst_ffs"]))
        out_crossings.append(rec)

    # gray buses must be bounded, not false-pathed
    for x in out_crossings:
        if x["kind"] == "gray_candidate":
            how = covered(groups, exceptions, x["src_clock"], x["dst_clock"])
            if how in ("clock_groups", "false_path"):
                audit.append({"from": x["src_clock"], "to": x["dst_clock"], "crossing": x["id"],
                              "issue": "multi-bit Gray bus %s -> %s is covered by %s; use set_max_delay -datapath_only so bit skew stays bounded"
                                       % (x["src_reg"], x["dst_reg"], how)})

    # ---- lock map -----------------------------------------------------------
    immutable, category, entries = {}, {}, []

    def lock_lines(f, l1, l2, cat):
        for l in range(l1, l2 + 1):
            key = "%s:%d" % (f, l)
            immutable[key] = True
            category.setdefault(key, cat)

    def lock_ff_block(cn, cat, whole):
        r = flat.src_range(cn)
        if not r:
            report["warnings"].append("no source location for %s" % flat.reg_name(cn))
            return
        f, l1, l2 = r
        reg = flat.reg_name(cn).split(".")[-1]
        text = block_text(lines, f, l1, l2)
        if whole:
            lock_lines(f, l1, l2, cat)
            frag = norm_text(text)
        else:
            assign = re.compile(r"\b%s\s*(\[[^\]]*\])?\s*<=" % re.escape(reg))
            hit = [l1 + i for i, t in enumerate(text.splitlines()) if assign.search(t)]
            for l in hit:
                lock_lines(f, l, l, cat)
            frag = " ".join(sorted(norm_text(m.group(0)) for m in
                                   re.finditer(r"\b%s\s*(\[[^\]]*\])?\s*<=[^;]*;" % re.escape(reg), text)))
        entries.append({"reg": flat.reg_name(cn), "category": cat, "scope": "block" if whole else "assignments",
                        "file": f, "lines": [l1, l2], "sha256": hashlib.sha256(frag.encode()).hexdigest()})

    for cn in sorted(sync_ffs):
        lock_ff_block(cn, "synchronizer", whole=True)
    for cn in flat.ffs():
        qs = flat.q_bits(cn)
        attrs = flat.names.get(flat.reg_name(cn), {}).get("attributes", {})
        if any(k.lower() in ("async_reg", "keep", "dont_touch") for k in attrs) and cn not in sync_ffs:
            lock_ff_block(cn, "synchronizer", whole=True)
    for cn in div_ffs:
        lock_ff_block(cn, "clock_generation", whole=True)
    for f, ls in lines.items():
        for i, t in enumerate(ls, 1):
            if re.search(r"\bparameter\b", t) and not re.search(r"\blocalparam\b", t):
                lock_lines(f, i, i, "capacity")
                entries.append({"reg": "param@%s:%d" % (f, i), "category": "capacity", "scope": "line", "file": f,
                                "lines": [i, i], "sha256": hashlib.sha256(norm_text(t).encode()).hexdigest()})

    # ---- contracts: calibrate Gray candidates (+ annotated crossings) -------
    contract_lines, contracts = {}, {}
    specs = []
    hier = yosys_json("%s; hierarchy -top %s; proc" % ("; ".join("read_verilog -sv " + f for f in a.rtl), a.top))
    hmods = hier["modules"]

    def base_mod(name):
        n = name.lstrip("\\")
        m = re.match(r"\$paramod\$[0-9a-f]+\\(.+)$", n) or re.match(r"\$paramod\\([^\\]+)", n)
        return m.group(1) if m else n

    def find_scope(flat_reg):
        """flat register name 'u_a.u_b.reg' -> (module, port, clock port, reset port, active_low)."""
        parts = flat_reg.split(".")
        mod = next(k for k, v in hmods.items() if is_top(v))
        for inst in parts[:-1]:
            cell = hmods[mod]["cells"].get(inst) or hmods[mod]["cells"].get("\\" + inst)
            if not cell:
                return None
            mod = cell["type"]
        M = hmods.get(mod)
        reg = parts[-1]
        if not M or reg not in [p.lstrip("\\") for p in M["ports"]]:
            return None
        rbits = M["ports"].get(reg, M["ports"].get("\\" + reg))["bits"]
        for cn, c in M["cells"].items():
            if c["type"] in STATE_CELLS and c["connections"].get("Q", [None])[0] in rbits:
                portbit = {tuple(v["bits"]): p.lstrip("\\") for p, v in M["ports"].items()}
                clkp = next((p for bits, p in portbit.items() if c["connections"]["CLK"][0] in bits), None)
                arst = c["connections"].get("ARST")
                rstp = next((p for bits, p in portbit.items() if arst and arst[0] in bits), None) if arst else None
                pol = str(c["parameters"].get("ARST_POLARITY", "1")).strip("'")
                active_low = pol.endswith("0") if pol else True
                return {"module": base_mod(mod), "port": reg, "clock": clkp, "reset": rstp, "active_low": active_low,
                        "params": {}}
        return None

    for x in out_crossings:
        if x["kind"] != "gray_candidate":
            continue
        sc = find_scope(x["src_reg"])
        if not sc or not sc["reset"]:
            x["contract"] = "no_scope"
            report["warnings"].append("Gray candidate %s: launch register is not a port of a module with a reset; left immutable" % x["src_reg"])
            continue
        specs.append({"id": x["id"], "type": "gray_src", "rtl": [os.path.abspath(f) for f in a.rtl],
                      "scope_module": sc["module"], "clock": sc["clock"], "reset": sc["reset"],
                      "reset_active_low": sc["active_low"], "src_clock": x["src_clock"], "dst_clock": x["dst_clock"],
                      "sync_stages": x["sync_depth"], "signals": {"ptr": sc["port"]}, "params": sc["params"],
                      "_crossing": x})
    if a.annotations:
        for s in json.load(open(a.annotations)):
            s = dict(s)
            s["rtl"] = [os.path.abspath(p) for p in s.get("rtl", a.rtl)]
            s["_crossing"] = None
            specs.append(s)

    passed = {}
    if specs and a.contracts_tool:
        cdir = os.path.join(a.out, "contracts")
        os.makedirs(cdir, exist_ok=True)
        spec_file = os.path.join(cdir, "spec.json")
        clean = [{k: v for k, v in s.items() if not k.startswith("_")} for s in specs]
        clk_json = {c: {"period_ns": v["period_ns"]} for c, v in clocks.items()}
        json.dump({"clocks": clk_json, "crossings": clean}, open(spec_file, "w"), indent=1)
        r = subprocess.run([sys.executable, a.contracts_tool, spec_file, "--out", os.path.join(cdir, "build"),
                            "--calibrate", "--structural"], capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            report["issues"].append("contract calibration failed to run: " + (r.stderr or r.stdout)[-500:])
        else:
            for e in json.load(open(os.path.join(cdir, "build", "report.json"))):
                ok = e.get("proof", {}).get("status") == "PASS" and (not e.get("structural") or e["structural"]["ok"])
                passed[e["id"]] = ok
                if not ok:
                    report["issues"].append("contract %s (%s) does not hold on the unmodified design: pre-existing CDC issue or missing assumption; its logic stays immutable"
                                            % (e["id"], e["type"]))
    elif specs:
        report["warnings"].append("no --contracts-tool given: Gray candidates and annotated crossings stay immutable")

    for s in specs:
        x = s["_crossing"]
        if not passed.get(s["id"]):
            if x:
                x["contract"] = x.get("contract", "failed" if s["id"] in passed else "not_run")
            continue
        props = {"gray_src": ["G1", "G2"], "handshake_src": ["H1", "H2", "H3"], "pulse_src": ["P1", "P2"],
                 "qualbus_src": ["Q1", "Q2"], "qualified_capture_dst": ["D1"]}.get(s["type"], [])
        contracts[s["id"]] = {"crossing": s["id"], "type": s["type"], "scope_module": s["scope_module"],
                              "signals": s["signals"], "properties": props}
        if x:
            x["contract"] = "proven"
        # contract-bound statements: fan-in logic of the flops driving the contract's outputs
        targets = []
        for role, sig in s["signals"].items():
            for cn in flat.ffs():
                rn = flat.reg_name(cn)
                if rn == sig or rn.endswith("." + sig):
                    targets.append(cn)
        for cn in targets:
            _, cone = flat.fanin(flat.ff_data_bits(cn))
            for c in cone:
                r = flat.src_range(c)
                if r:
                    for l in range(r[1], r[2] + 1):
                        contract_lines.setdefault("%s:%d" % (r[0], l), s["id"])
            r = flat.src_range(cn)
            if r:
                for l in range(r[1], r[2] + 1):
                    contract_lines.setdefault("%s:%d" % (r[0], l), s["id"])

    # launch and capture registers of crossings that are not contract-bound stay immutable
    for x in out_crossings:
        if x.get("contract") == "proven":
            continue
        if x["kind"] in ("synchronizer", "gray_candidate", "qualified_capture"):
            for cn in x["_src_ffs"]:
                lock_ff_block(cn, "crossing_launch", whole=False)
        if x["kind"] == "gray_candidate":
            # no proven contract: nothing downstream can check that the pointer still steps
            # in Gray code, so the logic computing its next value is immutable as well
            for cn in x["_src_ffs"]:
                _, cone = flat.fanin(flat.ff_data_bits(cn))
                for c in cone:
                    r = flat.src_range(c)
                    if not r:
                        continue
                    f, l1, l2 = r
                    for l in range(l1, l2 + 1):
                        key = "%s:%d" % (f, l)
                        if key in immutable:
                            continue
                        lock_lines(f, l, l, "crossing_launch_cone")
                        t = lines.get(f, [""] * l)[l - 1] if f in lines and l - 1 < len(lines[f]) else ""
                        if norm_text(t):
                            entries.append({"reg": "cone@%s:%d" % (f, l), "category": "crossing_launch_cone",
                                            "scope": "line", "file": f, "lines": [l, l],
                                            "sha256": hashlib.sha256(norm_text(t).encode()).hexdigest()})
        if x["kind"] == "qualified_capture":
            for cn in x["_dst_ffs"]:
                lock_ff_block(cn, "crossing_capture", whole=False)

    contract_lines = {k: v for k, v in contract_lines.items() if k not in immutable}

    # ---- write --------------------------------------------------------------
    sdc_hash = hashlib.sha256(open(a.sdc, "rb").read()).hexdigest()
    for x in out_crossings:
        x.pop("_src_ffs", None)
        x.pop("_dst_ffs", None)
    clocks_out = {"clocks": {c: {"period_ns": v["period_ns"], "master": v.get("master"), "root": root_of(clocks, c),
                                 "source": v.get("source")} for c, v in clocks.items()},
                  "synchronous_groups": []}
    w = lambda name, obj_: json.dump(obj_, open(os.path.join(a.out, name), "w"), indent=1)
    w("clocks.json", clocks_out)
    w("clock_relations.json", rel)
    w("constraint_audit.json", audit)
    w("sdc_exceptions.json", {"clock_groups": groups, "exceptions": exceptions, "other": other})
    w("crossings.json", out_crossings)
    w("lock_map.json", {"immutable": sorted(immutable), "category": category,
                        "contract": contract_lines, "contracts": contracts})
    w("checksums.json", {"sdc": {"file": os.path.basename(a.sdc), "sha256": sdc_hash},
                         "rtl_top": a.top, "entries": entries})
    summary = {
        "clocks": len(clocks), "asynchronous_pairs": sum(1 for x in names for y in names if rel[x][y] == "asynchronous"),
        "constraint_audit": len(audit), "flops": len(flat.ffs()), "unclocked_flops": len(set(unclocked)),
        "crossings": {k: sum(1 for x in out_crossings if x["kind"] == k) for k in
                      ("synchronizer", "gray_candidate", "qualified_capture", "insufficient_depth", "unsynchronized")},
        "contracts_proven": sorted(contracts), "immutable_lines": len(immutable),
        "contract_lines": len(contract_lines), "checksum_entries": len(entries), **report}
    w("phase1_report.json", summary)
    print(json.dumps({k: summary[k] for k in ("clocks", "constraint_audit", "crossings", "contracts_proven",
                                              "immutable_lines", "contract_lines")}))


# ============================================================================
# verify (Phase 3/4 checksum gate)
# ============================================================================
def verify(a):
    C = json.load(open(a.checksums))
    flat = Flat(a.rtl, a.top or C["rtl_top"])
    lines = file_lines(a.rtl)
    by_reg = defaultdict(list)
    for cn in flat.ffs():
        by_reg[flat.reg_name(cn)].append(cn)
    fails = []
    for e in C["entries"]:
        if e["category"] == "capacity":
            texts = [norm_text(t) for f in lines for t in lines[f] if re.search(r"\bparameter\b", t)]
            if not any(hashlib.sha256(t.encode()).hexdigest() == e["sha256"] for t in texts):
                fails.append({"entry": e["reg"], "why": "parameter declaration changed or removed"})
            continue
        if e["category"] == "crossing_launch_cone":
            # line-level lock, matched by text anywhere in the candidate (robust to moved code)
            if not any(hashlib.sha256(norm_text(t).encode()).hexdigest() == e["sha256"] for f in lines for t in lines[f]):
                fails.append({"entry": e["reg"], "why": "locked Gray next-value logic changed or removed"})
            continue
        cns = by_reg.get(e["reg"])
        if not cns:
            fails.append({"entry": e["reg"], "why": "locked register missing"})
            continue
        r = flat.src_range(cns[0])
        if not r:
            fails.append({"entry": e["reg"], "why": "no source location"})
            continue
        f, l1, l2 = r
        text = block_text(lines, f, l1, l2)
        if e["scope"] == "block":
            frag = norm_text(text)
        else:
            reg = e["reg"].split(".")[-1]
            frag = " ".join(sorted(norm_text(m.group(0)) for m in
                                   re.finditer(r"\b%s\s*(\[[^\]]*\])?\s*<=[^;]*;" % re.escape(reg), text)))
        if hashlib.sha256(frag.encode()).hexdigest() != e["sha256"]:
            fails.append({"entry": e["reg"], "why": "locked %s changed" % e["scope"]})
    if a.sdc:
        if hashlib.sha256(open(a.sdc, "rb").read()).hexdigest() != C["sdc"]["sha256"]:
            fails.append({"entry": "sdc", "why": "SDC file changed"})
    print(json.dumps({"pass": not fails, "failures": fails}, indent=1))
    sys.exit(0 if not fails else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("--rtl", nargs="+", required=True)
    i.add_argument("--top", required=True)
    i.add_argument("--sdc", required=True)
    i.add_argument("--annotations")
    i.add_argument("--contracts-tool")
    i.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--checksums", required=True)
    v.add_argument("--rtl", nargs="+", required=True)
    v.add_argument("--top")
    v.add_argument("--sdc")
    a = ap.parse_args()
    ingest(a) if a.cmd == "ingest" else verify(a)


if __name__ == "__main__":
    main()
