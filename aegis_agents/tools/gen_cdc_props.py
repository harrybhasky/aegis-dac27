#!/usr/bin/env python3
"""
AEGIS Phase 1 -- CDC contract generator.

Input : a crossing list produced by Phase 1 (clock periods from the SDC parse,
        crossing type / scope module / signal names from crossing detection).
Output: per crossing, a single-clock checker module, a formal wrapper that
        instantiates the scope module next to it, and a SymbiYosys job.

Every contract is a property of ONE clock domain, with the other domain's
signals left unconstrained (or constrained by an explicitly reported
assumption). That keeps the proof an ordinary single-clock problem.

Typical use
    python3 gen_cdc_props.py spec.json --out build --calibrate --run --structural

  --calibrate  prove each contract on the given (baseline) RTL first and pick
               the latency parameter LAT where a template has one. A contract
               that cannot be proven on the baseline is reported, not used:
               it is either a pre-existing CDC bug or a missing assumption.
  --run        run SymbiYosys on every generated job.
  --structural also run check_registered_launch.py on the crossing's control
               signal (value-level properties cannot see glitches).
"""
import argparse
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(HERE, "templates")

# role names each template expects, which role fixes the bus width W, whether
# the template has a latency parameter to calibrate, and which role is the
# control signal that must be launched straight from a flop.
TEMPLATES = {
    "gray_src":              {"roles": ["ptr"],                    "width": "ptr",      "lat": False, "control": "ptr"},
    "handshake_src":         {"roles": ["req", "ack_sync", "data"], "width": "data",     "lat": False, "control": "req"},
    "pulse_src":             {"roles": ["pulse_in", "tgl"],         "width": None,       "lat": True,  "control": "tgl"},
    "qualbus_src":           {"roles": ["qual", "data"],            "width": "data",     "lat": False, "control": "qual"},
    "qualified_capture_dst": {"roles": ["ev_sig", "data_dst"],      "width": "data_dst", "lat": True,  "control": None},
}
MAX_LAT = 4
SBY_DEPTH = 32


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def render(text, mapping):
    for key, val in mapping.items():
        text = text.replace("@%s@" % key, str(val))
    left = re.findall(r"@[A-Z_]+@", text)
    if left:
        raise ValueError("unfilled template fields: %s" % sorted(set(left)))
    return text


def read_template(name):
    with open(os.path.join(TEMPLATE_DIR, name)) as f:
        return f.read()


def yosys_json(rtl_files, top, params, extra_cmds=""):
    """Elaborate `top` with Yosys and return its write_json netlist."""
    chparams = " ".join("-chparam %s %s" % (k, v) for k, v in (params or {}).items())
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "net.json")
        script = "read_verilog %s; hierarchy -top %s %s; proc; %s write_json %s" % (
            " ".join(rtl_files), top, chparams, extra_cmds, out)
        res = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError("yosys failed on %s:\n%s" % (top, res.stderr or res.stdout))
        with open(out) as f:
            return json.load(f)


def module_ports(rtl_files, top, params):
    net = yosys_json(rtl_files, top, params)
    mods = net["modules"]
    # hierarchy -chparam may rename the module ($paramod...); pick the top one
    name = next((m for m, d in mods.items()
                 if d.get("attributes", {}).get("top") in ("00000000000000000000000000000001", 1, "1")), top)
    ports = mods[name]["ports"]
    return [(p, d["direction"], len(d["bits"])) for p, d in ports.items()]


_RESOLVED = {}


def expose_rtl(rtl_files, top, params, signals, outdir):
    """Internal launch register -> port (2026-11-02). The contract harness binds roles to ports of the scope
    module, so an internal Gray pointer (afifo's rgray, axis_async_fifo's wr_ptr_gray_reg) used to leave the
    crossing without a contract and its logic immutable. ONE Yosys run elaborates the scope module with its instance
    parameters, records its original port list, `expose`s the signals as outputs, keeps only them as outputs and
    lets opt_clean drop logic outside their fan-in cone (FIFO memories, data paths) -- the same logic, proc only.
    Returns (exposed netlist, original port names)."""
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "aegis_exposed.v")
    pre = os.path.join(outdir, "ports_pre.json")
    chparams = " ".join("-chparam %s %s" % (k, v) for k, v in (params or {}).items())
    sel = " ".join("%s/%s" % (top, s_) for s_ in signals)
    keep = " ".join("%s/w:%s" % (top, s_) for s_ in signals) + " %u" * (len(signals) - 1)
    script = ("read_verilog -sv %s; hierarchy -top %s %s; rename -top %s; proc; "
              "select %s; write_json -selected %s; select -clear; "
              "expose %s; delete -port %s/o:* %s %%d; opt_clean; write_verilog -noattr %s") % (
        " ".join(rtl_files), top, chparams, top, top, pre, sel, top, keep, out)
    res = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("yosys expose failed on %s:\n%s" % (top, (res.stderr or res.stdout)[-800:]))
    mods = json.load(open(pre))["modules"]
    m = mods.get(top) or next(iter(mods.values()))
    return [out], {p.lstrip("\\") for p in m["ports"]}


def resolve_rtl(cx, spec_dir, outdir):
    """(rtl files, params) the harness should use: the original RTL when every role is a port of the scope
    module, else the exposed netlist (parameters already applied). Memoized per process: the contract proof and
    the registered-launch check share one elaboration (eth_mac_1g_fifo: ~5 min each)."""
    rtl = [os.path.join(spec_dir, p) for p in cx["rtl"]]
    params = cx.get("params", {})
    sigs = sorted({cx["signals"][r] for r in TEMPLATES[cx["type"]]["roles"] if r in cx["signals"]})
    key = (tuple(rtl), cx["scope_module"], json.dumps(params, sort_keys=True), tuple(sigs))
    if key not in _RESOLVED:
        exposed, ports = expose_rtl(rtl, cx["scope_module"], params, sigs, os.path.join(outdir))
        _RESOLVED[key] = (rtl, params) if all(s_ in ports for s_ in sigs) else (exposed, {})
    return _RESOLVED[key]


def derive_windows(cx, clocks):
    """Hold window and minimum pulse gap, in SOURCE clock cycles, from SDC periods."""
    src = clocks[cx["src_clock"]]["period_ns"]
    dst = clocks[cx["dst_clock"]]["period_ns"]
    stages = int(cx.get("sync_stages", 2))
    n_hold = math.ceil((stages + 2) * dst / src)
    min_gap = math.ceil(2 * dst / src)
    return n_hold, min_gap


# --------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------
def build(cx, clocks, outdir, spec_dir, lat=None):
    """Write checker.v, formal_top.v and <id>.sby for one crossing."""
    kind = cx["type"]
    if kind not in TEMPLATES:
        raise ValueError("unknown crossing type %r" % kind)
    info = TEMPLATES[kind]
    rtl, params = resolve_rtl(cx, spec_dir, os.path.join(outdir, "_exposed"))
    ports = module_ports(rtl, cx["scope_module"], params)
    width_of = {n: w for n, _, w in ports}

    sig = cx["signals"]
    missing = [r for r in info["roles"] if r not in sig]
    if missing:
        raise ValueError("%s: missing signal roles %s" % (cx["id"], missing))
    for role in info["roles"]:
        if sig[role] not in width_of:
            raise ValueError("%s: %s=%s is not a port of %s" % (cx["id"], role, sig[role], cx["scope_module"]))

    n_hold, min_gap = derive_windows(cx, clocks)
    mod = "aegis_chk_%s_%s" % (kind, re.sub(r"\W", "_", cx["id"]))
    mapping = {
        "ID": cx["id"],
        "MOD": mod,
        "COMMON": read_template("_common.vh.tmpl").rstrip("\n"),
        "W": width_of[sig[info["width"]]] if info["width"] else 1,
        "LAT": lat if lat is not None else int(cx.get("lat", 1)),
        "N_HOLD": n_hold,
        "MIN_GAP": min_gap,
        "RATE_KIND": cx.get("rate_kind", "assume"),
        "EV_KIND": cx.get("event", "any"),
        "EV_EXPR": "(ev_sig && !past_ev)" if cx.get("event", "any") == "rise" else "(ev_sig != past_ev)",
        # cycles after reset release before checks start: 1 for a reset that drives the launch flop directly;
        # more when the reset reaches it through a reset synchronizer (spec "settle")
        "SETTLE": int(cx.get("settle", 1)),
    }
    checker = render(read_template(kind + ".v.tmpl"), mapping)

    clk, rst = cx["clock"], cx["reset"]
    inputs = [(n, w) for n, d, w in ports if d == "input"]
    outputs = [(n, w) for n, d, w in ports if d == "output"]
    rng = lambda w: ("[%d:0] " % (w - 1)) if w > 1 else ""
    pstr = ("#(" + ", ".join(".%s(%s)" % kv for kv in params.items()) + ") ") if params else ""
    top = ["// Generated by gen_cdc_props.py for crossing %s (%s)" % (cx["id"], kind),
           "module aegis_formal_top ("]
    top.append(",\n".join("  input wire %s%s" % (rng(w), n) for n, w in inputs))
    top.append(");")
    for n, w in outputs:
        top.append("  wire %s%s;" % (rng(w), n))
    top.append("  %s %sdut (%s);" % (cx["scope_module"], pstr,
                                      ", ".join(".%s(%s)" % (n, n) for n, _, _ in ports)))
    # resets: the launch flop's own reset, or (no direct reset) every reset input of the scope module;
    # checks are gated while ANY is active, and every trace starts with ALL of them active
    rsts = cx.get("resets") or [[rst, cx.get("reset_active_low", True)]]
    act = ["%s%s" % ("~" if low else "", n) for n, low in rsts]
    top.append("  wire aegis_rst_act = %s;" % " | ".join("(%s)" % x for x in act))
    top.append("  wire aegis_rst_all = %s;" % " & ".join("(%s)" % x for x in act))
    top.append("  // start every trace in reset so DUT state is defined")
    top.append("  reg aegis_init = 1'b1;")
    top.append("  always @(posedge %s) aegis_init <= 1'b0;" % clk)
    top.append("  always @(*) if (aegis_init) assume (aegis_rst_all);")
    conns = [".clk(%s)" % clk, ".rst_act(aegis_rst_act)"] + [".%s(%s)" % (r, sig[r]) for r in info["roles"]]
    top.append("  %s chk (%s);" % (mod, ", ".join(conns)))
    top.append("endmodule")

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "checker.v"), "w") as f:
        f.write(checker)
    with open(os.path.join(outdir, "formal_top.v"), "w") as f:
        f.write("\n".join(top) + "\n")
    local_rtl = []
    for p in rtl:
        dst = os.path.join(outdir, os.path.basename(p))
        shutil.copy(p, dst)
        local_rtl.append(os.path.basename(p))
    sby = "\n".join([
        "[options]", "mode prove", "depth %d" % SBY_DEPTH, "",
        "[engines]", "smtbmc z3", "",
        "[script]",
        "read -formal %s checker.v formal_top.v" % " ".join(local_rtl),
        "prep -top aegis_formal_top", "",
        "[files]", *local_rtl, "checker.v", "formal_top.v", ""])
    job = re.sub(r"\W", "_", cx["id"])
    with open(os.path.join(outdir, job + ".sby"), "w") as f:
        f.write(sby)

    obligations = []
    if kind == "pulse_src" and mapping["RATE_KIND"] == "assume":
        obligations.append("driver of %s must space pulses >= %d %s cycles (P2)"
                           % (sig["pulse_in"], min_gap, cx["src_clock"]))
    if kind == "qualified_capture_dst":
        obligations.append("%s must hold 0 while %s is in reset (A1)" % (sig["ev_sig"], cx["clock"]))
    return {"dir": outdir, "job": job, "checker_module": mod, "lat": mapping["LAT"],
            "n_hold": n_hold, "min_gap": min_gap, "obligations": obligations}


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------
def run_sby(built, engine="smtbmc z3"):
    d, job = built["dir"], built["job"]
    sby_path = os.path.join(d, job + ".sby")
    lines = open(sby_path).read().splitlines()
    i = lines.index("[engines]")
    lines[i + 1] = engine
    open(sby_path, "w").write("\n".join(lines) + "\n")
    subprocess.run(["sby", "-f", job + ".sby"], cwd=d, capture_output=True, text=True)
    status_file = os.path.join(d, job, "status")
    status = open(status_file).read().split()[0] if os.path.exists(status_file) else "ERROR"
    log = os.path.join(d, job, "logfile.txt")
    if status == "ERROR" and os.path.exists(log) and "returned FAIL" in open(log).read():
        status = "FAIL"   # engine found a counterexample; only trace replay failed
    tags = []
    if os.path.exists(log):
        checker_lines = open(os.path.join(d, "checker.v")).read().splitlines()
        for line in open(log):
            if "Assert failed in" not in line:
                continue
            m = re.search(r"checker\.v:(\d+)", line)
            if m:
                src = checker_lines[int(m.group(1)) - 1]
                t = re.search(r"\[(\w+)\]", src)
                if t and t.group(1) not in tags:
                    tags.append(t.group(1))
    trace = None
    for root, _, files in os.walk(os.path.join(d, job)):
        for fn in files:
            if fn.endswith(".vcd"):
                trace = os.path.join(root, fn)
    return {"status": status, "failed": tags, "trace": trace, "engine": engine}


def prove(built):
    """k-induction first (fast, labelled counterexamples). If it is stuck
    (UNKNOWN: base case passes but induction does not close, typically
    because the rewrite relies on an internal invariant), fall back to IC3/PDR,
    which infers inductive invariants itself. Anything short of PASS rejects."""
    # 2026-11-02: PDR first. Both engines give unbounded proofs; PDR closes the Gray-pointer contracts of
    # internal-register scopes in seconds (axis_async_fifo: 5 s) where k-induction was still stuck after
    # minutes. k-induction then runs only when PDR does not pass, to label the failing property.
    r0 = run_sby(built, engine="abc pdr")
    if r0["status"] == "PASS":
        r0["note"] = "PDR PASS"
        return r0
    r = run_sby(built)
    if r["status"] != "UNKNOWN":
        r["note"] = "PDR %s; k-induction %s" % (r0["status"], r["status"])
        return r
    r["note"] = "PDR %s; k-induction stuck on %s" % (r0["status"], ",".join(r["failed"]) or "?")
    return r


def calibrate(cx, clocks, outdir, spec_dir):
    """Prove on the baseline; for latency templates pick the smallest LAT that passes."""
    if not TEMPLATES[cx["type"]]["lat"]:
        b = build(cx, clocks, outdir, spec_dir)
        return b, prove(b)
    last = None
    for lat in range(1, MAX_LAT + 1):
        b = build(cx, clocks, outdir, spec_dir, lat=lat)
        r = prove(b)
        last = (b, r)
        if r["status"] == "PASS":
            return last
    return last


def structural(cx, spec_dir):
    role = TEMPLATES[cx["type"]]["control"]
    if role is None:
        return None
    sys.path.insert(0, HERE)
    from check_registered_launch import check_registered_launch
    # reuses the elaboration of build() when it ran in this process (memoized); exposed files live in a
    # persistent per-crossing directory so the memoized path stays valid
    rtl, params = resolve_rtl(cx, spec_dir, os.path.join(spec_dir, "_exposed_" + re.sub(r"\W", "_", cx["id"])))
    return check_registered_launch(rtl, cx["scope_module"], params, cx["signals"][role], cx["clock"])


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out", default="build")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--structural", action="store_true")
    a = ap.parse_args()

    spec_dir = os.path.dirname(os.path.abspath(a.spec))
    spec = json.load(open(a.spec))
    report = []
    for cx in spec["crossings"]:
        outdir = os.path.join(a.out, re.sub(r"\W", "_", cx["id"]))
        if a.calibrate:
            b, r = calibrate(cx, spec["clocks"], outdir, spec_dir)
        else:
            b = build(cx, spec["clocks"], outdir, spec_dir)
            r = prove(b) if a.run else None
        s = structural(cx, spec_dir) if a.structural else None
        entry = {"id": cx["id"], "type": cx["type"], **b, "proof": r, "structural": s}
        if a.calibrate and r and r["status"] != "PASS":
            entry["baseline_violation"] = ("contract fails on the unmodified design: pre-existing CDC "
                                           "bug or missing assumption -- review before locking")
        report.append(entry)
        line = "%-22s %-22s LAT=%s" % (cx["id"], cx["type"], b["lat"])
        if r:
            line += "  proof=%s%s" % (r["status"], (" " + ",".join(r["failed"])) if r["failed"] else "")
        if s:
            line += "  launch=%s" % ("OK" if s["ok"] else "FAIL")
        print(line)
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
