#!/usr/bin/env python3
"""
CDC mutant generator: injects clock-domain-crossing faults (and benign controls) into a
design's elaborated netlist, at the crossings Phase 1 found, and writes each mutant as
a self-contained Verilog file with its ground-truth labels. No LLM is involved.

  python3 bench/cdc_mutants/gen_mutants.py --design async_fifo [--design ...] [--out bench/cdc_mutants/out]

Mutation happens on the hierarchical Yosys netlist (read; hierarchy; proc; opt_dff), so every
operator applies to any design whose crossings Phase 1 has classified; no source pattern
matching. Parameterized modules are renamed back to their base names, and a module that is
instantiated more than once is cloned before it is edited, so only the targeted instance changes.

Operators (one mutant per operator x applicable crossing):
  sync_bypass     a synchronizer chain loses its first stage (depth n -> n-1)        unsafe
  sync_remove     consumers of the synchronizer output read the unsynchronized input    unsafe
  binary_cross    a Gray crossing carries binary: gray->binary before the first stage,  unsafe
                  binary->gray after the last (functionally equivalent in zero-delay
                  simulation; multi-bit binary + combinational logic on the crossing)
  sync_wrong_clock  the synchronizer flops are clocked by the SOURCE clock (the bug found in    unsafe
                  Dr. RTL's two-clock FIFO); only where the source clock reaches the module
  qual_bypass     a qualified capture register loads every cycle (enable/hold removed)  unsafe
  extra_stage     one more synchronizer stage (latency +1, CDC-safe)                    safe
  post_invert     the synchronizer output is inverted after the last stage              safe (functional bug only)
Per design:
  identity        the netlist written back unchanged                                   safe, equivalent
  free_dblinv     a double inversion inserted on a combinational net of non-CDC logic   safe, equivalent

Ground truth per mutant: cdc_safe (by construction) and sim_equiv: True = cycle-accurate
equivalent to the original by construction, False = functionally different by construction,
None = latency change whose visibility at the outputs depends on the protocol. label.py measures which checker catches what.
"""
import argparse
import copy
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from aegis_common import load_design, read_cmd  # noqa: E402

FF_TYPES = {"$dff", "$adff", "$dffe", "$adffe", "$sdff", "$sdffe", "$sdffce", "$dffsr", "$dffsre", "$aldff", "$aldffe"}
GT = {  # operator: (cdc_safe, sim_equiv, description)
    "sync_bypass": (False, None, "synchronizer chain loses its first stage"),
    "sync_remove": (False, None, "synchronizer output consumers read the unsynchronized source"),
    "binary_cross": (False, True, "Gray crossing re-encoded to binary across the synchronizer"),
    "qual_bypass": (False, None, "qualified capture register loads every cycle"),
    "sync_wrong_clock": (False, None, "synchronizer stages clocked by the source domain (pattern of Dr. RTL's FIFO)"),
    "extra_stage": (True, None, "extra synchronizer stage"),
    "post_invert": (True, False, "synchronizer output inverted (functional bug, CDC-safe)"),
    "identity": (True, True, "netlist round trip, no change"),
    "free_dblinv": (True, True, "double inversion on non-CDC combinational logic"),
}


def yosys(script, timeout=3600):
    r = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("yosys failed: " + (r.stderr or r.stdout)[-1500:])


def elaborate(D, cache):
    if os.path.exists(cache):
        return json.load(open(cache))
    yosys("%s; hierarchy -top %s; proc; opt_clean; opt_dff; opt_clean; write_json %s" % (read_cmd(D["rtl"]), D["top"], cache))
    return json.load(open(cache))


def base_name(n):
    m = re.match(r"\$paramod\$[0-9a-f]+\\(.+)$", n) or re.match(r"\$paramod\\([^\\]+)", n)
    return m.group(1) if m else n


def normalize_names(net):
    """$paramod...\\foo -> foo (foo__p1, foo__p2 when one base has several specializations)."""
    ren, used = {}, set(n for n in net["modules"] if not n.startswith("$paramod"))
    for n in sorted(net["modules"]):
        if n.startswith("$paramod"):
            b = base_name(n)
            k, cand = 0, b
            while cand in used:
                k += 1
                cand = "%s__p%d" % (b, k)
            used.add(cand)
            ren[n] = cand
    net["modules"] = {ren.get(n, n): m for n, m in net["modules"].items()}
    for m in net["modules"].values():
        for c in m["cells"].values():
            c["type"] = ren.get(c["type"], c["type"])
    return net


class Mod:
    """Bit-level view of one module (rebuilt after every edit)."""

    def __init__(self, m):
        self.m = m
        self.driver, self.readers = {}, {}
        for cn, c in m["cells"].items():
            for p, d in c.get("port_directions", {}).items():
                for i, b in enumerate(c["connections"].get(p, [])):
                    if isinstance(b, str):
                        continue
                    if d == "output":
                        self.driver[b] = (cn, p, i)
                    else:
                        self.readers.setdefault(b, []).append((cn, p, i))
        self.outports = {b for p in m["ports"].values() if p["direction"] == "output" for b in p["bits"]}
        self.top = max([b for c in m["cells"].values() for bs in c["connections"].values() for b in bs if not isinstance(b, str)] +
                       [b for w in m["netnames"].values() for b in w["bits"] if not isinstance(b, str)] + [1])

    def fresh(self, n):
        out = list(range(self.top + 1, self.top + 1 + n))
        self.top += n
        return out

    def wire(self, name):
        w = self.m["netnames"].get(name)
        return None if w is None else w["bits"]

    def ff_of(self, b):
        d = self.driver.get(b)
        if d and self.m["cells"][d[0]]["type"] in FF_TYPES and d[1] == "Q":
            return d
        return None


def add_cell(m, name, typ, params, conns, dirs):
    m["cells"][name] = {"hide_name": 1, "type": typ, "parameters": params, "attributes": {},
                        "port_directions": dirs, "connections": conns}


def binp(v, w=32):
    return format(v, "0%db" % w)


def gate1(M, typ, a, b=None, y=None):
    y = y if y is not None else M.fresh(1)[0]
    name = "$mut$%s$%d" % (typ.strip("$"), y)
    if b is None:
        add_cell(M.m, name, typ, {"A_SIGNED": binp(0), "A_WIDTH": binp(1), "Y_WIDTH": binp(1)},
                 {"A": [a], "Y": [y]}, {"A": "input", "Y": "output"})
    else:
        add_cell(M.m, name, typ, {"A_SIGNED": binp(0), "B_SIGNED": binp(0), "A_WIDTH": binp(1), "B_WIDTH": binp(1),
                                  "Y_WIDTH": binp(1)}, {"A": [a], "B": [b], "Y": [y]},
                 {"A": "input", "B": "input", "Y": "output"})
    return y


def redrive(M, old_bits):
    """Detach old_bits from their drivers (driver output moves to fresh bits); returns the fresh bits.
    The caller must drive old_bits again (e.g. with gate1(..., y=old))."""
    new = M.fresh(len(old_bits))
    for o, n in zip(old_bits, new):
        cn, p, i = M.driver[o]
        M.m["cells"][cn]["connections"][p][i] = n
    return new


# ----------------------------------------------------------------------------
def instance_path(net, top, path):
    """'u.rx_fifo.fifo_inst.x_reg' -> ([(module, cell)...], module, wire); greedy over instance names."""
    toks, mod, chain, i = path.split("."), top, [], 0
    while i < len(toks):
        cells = net["modules"][mod]["cells"]
        hit = None
        for j in range(len(toks), i, -1):          # longest instance name first (names may contain dots)
            nm = ".".join(toks[i:j])
            if nm in cells and cells[nm]["type"] in net["modules"]:
                hit = (nm, j)
                break
        if hit is None or hit[1] == len(toks):
            break
        chain.append((mod, hit[0]))
        mod, i = cells[hit[0]]["type"], hit[1]
    return chain, mod, ".".join(toks[i:])


def descend(net, mod, wire, chain):
    """A port-level alias of a register (e.g. a top output driven by a submodule's flop):
    follow the driving instance down until the bits are flop outputs. Returns (chain, mod, bits)."""
    M = Mod(net["modules"][mod])
    bits = M.wire(wire)
    for _ in range(8):
        if bits is None or all(M.ff_of(b) for b in bits):
            return chain, mod, bits
        ds = {M.driver.get(b, (None, None, None))[:2] for b in bits}
        if len(ds) != 1:
            return chain, mod, None
        cn, port = ds.pop()
        if cn is None or M.m["cells"][cn]["type"] not in net["modules"]:
            return chain, mod, None
        idx = [M.driver[b][2] for b in bits]
        chain = chain + [(mod, cn)]
        mod = M.m["cells"][cn]["type"]
        M = Mod(net["modules"][mod])
        pb = M.m["ports"][port]["bits"]
        bits = [pb[i] for i in idx]
    return chain, mod, None


def uniquify(net, top, chain, tag):
    """Clone every module along the instance chain that has more than one instance."""
    def count(mt):
        return sum(1 for m in net["modules"].values() for c in m["cells"].values() if c["type"] == mt)
    for parent, cell in chain:
        mt = net["modules"][parent]["cells"][cell]["type"]
        if count(mt) > 1:
            nn = "%s__%s" % (mt, tag)
            net["modules"][nn] = copy.deepcopy(net["modules"][mt])
            net["modules"][nn]["attributes"].pop("top", None)
            net["modules"][parent]["cells"][cell]["type"] = nn
    # the module that holds the target after cloning
    mod = top
    for _, cell in chain:
        mod = net["modules"][mod]["cells"][cell]["type"]
    return mod


def chain_stages(M, s1_bits):
    """Synchronizer stages starting at the bits of the first destination register:
    [[stage1 bits], [stage2 bits], ...] following direct Q->D links in the same domain."""
    stages = [s1_bits]
    while True:
        nxt = []
        for b in stages[-1]:
            rs = [r for r in M.readers.get(b, []) if M.m["cells"][r[0]]["type"] in FF_TYPES and r[1] == "D"]
            if len(rs) != 1:
                return stages
            cn, _, i = rs[0]
            nxt.append(M.m["cells"][cn]["connections"]["Q"][i])
        if any(isinstance(b, str) for b in nxt) or len(stages) > 6:
            return stages
        stages.append(nxt)


def d_of(M, q_bits):
    out = []
    for b in q_bits:
        cn, _, i = M.ff_of(b)
        out.append(M.m["cells"][cn]["connections"]["D"][i])
    return out


def set_d(M, q_bits, d_bits):
    for b, d in zip(q_bits, d_bits):
        cn, _, i = M.ff_of(b)
        M.m["cells"][cn]["connections"]["D"][i] = d


# ----------------------------------------------------------------------------
def op_sync_bypass(M, st, x):
    if len(st) < 2:
        return None
    set_d(M, st[1], d_of(M, st[0]))
    return "stage %d of the synchronizer now samples the crossing source directly" % 2


def op_sync_remove(M, st, x):
    if len(st) < 2:
        return None
    src = d_of(M, st[0])
    last = st[-1]
    redrive(M, last)
    for o, s in zip(last, src):
        gate1(M, "$pos", s, y=o)
    return "the synchronizer output is replaced by the unsynchronized source"


def op_binary_cross(M, st, x):
    if x["kind"] != "gray_candidate" or len(st[0]) < 2:
        return None
    g = d_of(M, st[0])          # Gray source bits (LSB first)
    n = len(g)
    b = [None] * n              # gray -> binary: b[n-1] = g[n-1], b[i] = b[i+1] ^ g[i]
    b[n - 1] = gate1(M, "$pos", g[n - 1])
    for i in range(n - 2, -1, -1):
        b[i] = gate1(M, "$xor", b[i + 1], g[i])
    set_d(M, st[0], b)
    last = st[-1]
    q = redrive(M, last)        # binary -> Gray after the last stage
    for i in range(n):
        if i == n - 1:
            gate1(M, "$pos", q[i], y=last[i])
        else:
            gate1(M, "$xor", q[i], q[i + 1], y=last[i])
    return "Gray pointer converted to binary before the synchronizer and back to Gray after it"


def op_sync_wrong_clock(M, st, x):
    if x["kind"] not in ("synchronizer", "gray_candidate") or not M.src_clk:
        return None
    for stage in st:
        for b in stage:
            cn, _, _ = M.ff_of(b)
            c = M.m["cells"][cn]
            c["connections"]["CLK"] = [M.src_clk[0]]
            c["parameters"]["CLK_POLARITY"] = M.src_clk[1]
    return "synchronizer flops clocked by the source clock"


def op_qual_bypass(M, st, x):
    if x["kind"] != "qualified_capture":
        return None
    changed = False
    for b in st[0]:
        cn, _, i = M.ff_of(b)
        c = M.m["cells"][cn]
        if "EN" in c["connections"]:
            pol = c["parameters"].get("EN_POLARITY", "1")
            c["connections"]["EN"] = ["1" if int(pol, 2) else "0"]
            changed = True
    return "capture register enable tied active (loads every cycle)" if changed else None


def op_extra_stage(M, st, x):
    if x["kind"] not in ("synchronizer", "gray_candidate"):
        return None
    last = st[-1]
    cn, _, _ = M.ff_of(last[0])
    proto = M.m["cells"][cn]
    q = redrive(M, last)
    w = len(last)
    c = copy.deepcopy(proto)
    c["parameters"]["WIDTH"] = binp(w)
    for k in ("ARST_VALUE", "SRST_VALUE"):
        if k in c["parameters"]:
            v = c["parameters"][k]
            c["parameters"][k] = (v * w)[:w] if len(set(v)) == 1 else v[-1] * w
    c["connections"]["D"], c["connections"]["Q"] = q, last
    c["attributes"] = {}
    M.m["cells"]["$mut$extra_stage$%d" % last[0]] = c
    return "one extra flop appended to the synchronizer chain"


def op_post_invert(M, st, x):
    if x["kind"] not in ("synchronizer", "gray_candidate"):
        return None
    last = st[-1][:1]
    q = redrive(M, last)
    gate1(M, "$not", q[0], y=last[0])
    return "bit 0 of the synchronizer output inverted"


OPS = {"sync_bypass": op_sync_bypass, "sync_remove": op_sync_remove, "sync_wrong_clock": op_sync_wrong_clock, "binary_cross": op_binary_cross,
       "qual_bypass": op_qual_bypass, "extra_stage": op_extra_stage, "post_invert": op_post_invert}


def op_free_dblinv(net, top, cdc_mods, rng):
    """Double inversion on one combinational output bit in a module with no crossing endpoint."""
    cands = []
    for mn, m in net["modules"].items():
        if mn in cdc_mods:
            continue
        for cn, c in m["cells"].items():
            if c["type"] in ("$and", "$or", "$xor", "$add", "$sub", "$mux", "$eq", "$ne", "$lt", "$not", "$reduce_or", "$reduce_and"):
                ys = [b for b in c["connections"].get("Y", []) if not isinstance(b, str)]
                if ys:
                    cands.append((mn, cn, ys[0]))
    if not cands:
        return None
    mn, cn, y = rng.choice(sorted(cands))
    M = Mod(net["modules"][mn])
    q = redrive(M, [y])
    gate1(M, "$not", gate1(M, "$not", q[0]), y=y)
    return "double inversion on an output bit of %s in module %s" % (cn, mn)


# ----------------------------------------------------------------------------
def write_mutant(net, top, out_dir, meta):
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(net, f)
        tmp = f.name
    try:
        yosys("read_json %s; hierarchy -top %s; write_verilog -noattr %s" % (tmp, top, os.path.join(out_dir, "mutant.v")))
    finally:
        os.unlink(tmp)
    meta["sha1"] = hashlib.sha1(open(os.path.join(out_dir, "mutant.v"), "rb").read()).hexdigest()
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"), indent=1)


def generate(design, out_root, seed=1, only_ops=None):
    D = load_design(design)
    phase1 = os.path.join(ROOT, "flow", "work", design, "phase1")
    xs = json.load(open(os.path.join(phase1, "crossings.json")))
    os.makedirs(os.path.join(out_root, design), exist_ok=True)
    base = normalize_names(elaborate(D, os.path.join(out_root, design, "elab.json")))
    top = D["top"]
    rng = random.Random(seed)
    made, skipped = [], []

    def emit(mid, op, net, detail, x=None):
        cdc_safe, sim_equiv, desc = GT[op]
        meta = {"id": mid, "design": design, "top": top, "operator": op, "description": desc, "detail": detail,
                "crossing": x, "ground_truth": {"cdc_safe": cdc_safe, "sim_equiv": sim_equiv}}
        write_mutant(net, top, os.path.join(out_root, design, mid), meta)
        made.append(meta)

    if not only_ops or "identity" in only_ops:
        emit("identity", "identity", copy.deepcopy(base), "unchanged")
    cdc_mods = set()
    for x in xs:
        if x["kind"] == "unsynchronized":
            continue
        for op, fn in OPS.items():
            if only_ops and op not in only_ops:
                continue
            net = copy.deepcopy(base)
            chain, mod0, wire = instance_path(net, top, x["dst_reg"])
            chain, mod0, bits = descend(net, mod0, wire, chain)
            if bits is None:
                skipped.append({"crossing": x["id"], "op": op, "why": "destination %s is not a flop wire in %s" % (wire, mod0)})
                break
            cdc_mods.add(mod0)
            mod = uniquify(net, top, chain, x["id"][2:])
            M = Mod(net["modules"][mod])
            M.src_clk = None
            schain, smod, swire = instance_path(net, top, x["src_reg"])
            if [c for _, c in schain] == [c for _, c in chain] and M.wire(swire):
                sb = M.wire(swire)
                if M.ff_of(sb[0]):
                    sc = M.m["cells"][M.ff_of(sb[0])[0]]
                    M.src_clk = (sc["connections"]["CLK"][0], sc["parameters"].get("CLK_POLARITY", "1"))
            st = chain_stages(M, bits)
            try:
                detail = fn(M, st, x)
            except (KeyError, TypeError, IndexError) as e:
                skipped.append({"crossing": x["id"], "op": op, "why": "operator error: %r" % e})
                continue
            if detail is None:
                continue
            emit("%s__%s" % (op, x["id"]), op, net, "%s (%s -> %s, depth %d)" % (detail, x["src_reg"], x["dst_reg"], len(st)), x)
    for k in range(2 if not only_ops or "free_dblinv" in only_ops else 0):
        net = copy.deepcopy(base)
        detail = op_free_dblinv(net, top, cdc_mods | {top}, rng)
        if detail:
            emit("free_dblinv_%d" % k, "free_dblinv", net, detail)
    if not only_ops:
        json.dump({"design": design, "mutants": len(made), "skipped": skipped}, open(os.path.join(out_root, design, "index.json"), "w"), indent=1)
    return made, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", action="append", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--op", action="append", help="generate only these operators (others are left untouched)")
    a = ap.parse_args()
    for d in a.design:
        made, skipped = generate(d, a.out, a.seed, a.op)
        by = {}
        for m in made:
            by[m["operator"]] = by.get(m["operator"], 0) + 1
        print("%-18s %3d mutants %s  skipped=%d" % (d, len(made), by, len(skipped)))
        for s in skipped:
            print("   skip", s)


if __name__ == "__main__":
    main()
