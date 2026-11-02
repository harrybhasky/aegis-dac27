#!/usr/bin/env python3
"""
AEGIS baseline synthesis and static timing analysis (deterministic).

  python3 aegis_sta.py --rtl a.v b.v --top TOP --sdc design.sdc --liberty lib.lib \
      --out work/<design>/<version>/sta [--margin 0.1] [--abc-delay-ps 0]

Steps
  1. Yosys: read RTL, synthesize with hierarchy preserved and FSM re-encoding
     disabled (so RTL register names survive), map flops and logic to the liberty.
  2. Rename every mapped flop to <register>_reg[<bit>] so SDC objects such as
     [get_pins u_div/div_q_reg/Q] and STA endpoint names match the RTL.
  3. OpenSTA: link, read SDC, write
       endpoints.rpt   worst setup path per endpoint with slack below the margin
       groups.rpt      worst setup path per clock (path group), for per-domain WNS
  4. metrics.json: per-domain WNS/TNS/violating endpoints, design WNS/TNS,
     cell area, and every SDC object OpenSTA could not match.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, log, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    open(log, "w").write(r.stdout + r.stderr)
    if r.returncode != 0:
        sys.exit("command failed (%s), see %s:\n%s" % (cmd[0], log, (r.stderr or r.stdout)[-1500:]))
    return r.stdout


def rename_flops(js_in, js_out):
    """Give mapped flops DC-style names derived from the register they hold."""
    net = json.load(open(js_in))
    renamed = 0
    for mname, m in net["modules"].items():
        bitname = {}
        for wn, w in m.get("netnames", {}).items():
            if w.get("hide_name"):
                continue
            n = wn.lstrip("\\")
            for i, b in enumerate(w["bits"]):
                if isinstance(b, str):
                    continue
                idx = int(w.get("offset", 0)) + i
                cand = n if len(w["bits"]) == 1 else "%s[%d]" % (n, idx)
                port = n in [p.lstrip("\\") for p in m.get("ports", {})]
                prev = bitname.get(b)
                # prefer internal register names over port aliases, then shorter names
                if prev is None or (prev[1] and not port) or (prev[1] == port and len(cand) < len(prev[0])):
                    bitname[b] = (cand, port)
        # a new cell name must not equal an existing cell OR wire name (Yosys read_json asserts on either;
        # seen with --flatten on axil_cdc, 2026-11-02). Runs that did not hit a collision are unaffected.
        used = set(m["cells"]) | {wn.lstrip("\\") for wn in m.get("netnames", {})}
        new_cells = {}
        for cn, c in m["cells"].items():
            q = c.get("connections", {}).get("Q") or c.get("connections", {}).get("QN")
            conns = c.get("connections", {})
            is_ff = ("CK" in conns or "CLK" in conns) and q
            if is_ff and not isinstance(q[0], str) and q[0] in bitname:
                reg = bitname[q[0]][0]
                m_ = re.match(r"^(.*?)(\[\d+\])?$", reg)
                name = "%s_reg%s" % (m_.group(1), m_.group(2) or "")
                if name in used or name in new_cells:
                    name = name + "_dup%d" % renamed
                new_cells[name] = c
                renamed += 1
            else:
                new_cells[cn] = c
        m["cells"] = new_cells
    json.dump(net, open(js_out, "w"))
    return renamed


def parse_groups(text):
    """Worst slack per capture clock from a -group_path_count 1 report."""
    out = {}
    for block in re.split(r"(?m)^\s*Startpoint:", text)[1:]:
        g = re.search(r"Path Group:\s*(\S+)", block)
        s = re.search(r"(?m)^\s*(-?\d+(?:\.\d+)?)\s+slack\b", block)
        if g and s:
            out[g.group(1)] = min(float(s.group(1)), out.get(g.group(1), 1e9))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rtl", nargs="+", required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--sdc", required=True)
    ap.add_argument("--liberty", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--margin", type=float, default=0.1)
    ap.add_argument("--abc-delay-ps", type=int, default=0)
    ap.add_argument("--abc-timing", action="store_true",
                    help="timing-driven ABC script: delay-targeted mapping plus buffering and gate up/down-sizing")
    ap.add_argument("--sta", default="sta")
    ap.add_argument("--flatten", action="store_true",
                    help="flatten the hierarchy before synthesis (robustness check: gains that rely on module "
                         "boundaries disappear; off for all optimization runs)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lib = os.path.abspath(a.liberty)
    o = lambda f: os.path.join(os.path.abspath(a.out), f)

    # 1. synthesis
    reads = "; ".join("read_verilog -sv %s" % os.path.abspath(f) for f in a.rtl)
    abc = "abc -liberty %s%s" % (lib, (" -D %d" % a.abc_delay_ps) if a.abc_delay_ps else "")
    if a.abc_timing and a.abc_delay_ps:
        abc += (" -script +strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf,{D};&put;"
                "buffer,-p;upsize,{D};dnsize,{D};stime,-p")
    script = "; ".join([
        reads, "hierarchy -check -top %s" % a.top,
        "synth -top %s -nofsm%s -run begin:fine" % (a.top, " -flatten" if a.flatten else ""),  # hierarchy kept unless --flatten
        "synth -top %s -nofsm -run fine:check" % a.top,
        "dfflibmap -liberty %s" % lib, abc,
        "hilomap -hicell LOGIC1_X1 Z -locell LOGIC0_X1 Z", "setundef -zero", "opt_clean",
        "tee -o %s stat -liberty %s -top %s" % (o("area.txt"), lib, a.top),
        "write_json %s" % o("synth_raw.json")])
    run(["yosys", "-q", "-p", script], o("yosys.log"))
    n = rename_flops(o("synth_raw.json"), o("synth.json"))
    run(["yosys", "-q", "-p", "read_json %s; hierarchy -top %s; write_verilog -noattr -noexpr %s"
         % (o("synth.json"), a.top, o("netlist.v"))], o("yosys_write.log"))
    # OpenSTA's Verilog reader rejects `signed` on declarations; it carries no meaning in a gate netlist
    nl = open(o("netlist.v")).read()
    open(o("netlist.v"), "w").write(re.sub(r"\b(input|output|inout|wire|reg)\s+signed\b", r"\1", nl))

    # 2. static timing analysis
    tcl = "\n".join([
        "read_liberty %s" % lib,
        "read_verilog %s" % o("netlist.v"),
        "link_design %s" % a.top,
        "read_sdc %s" % os.path.abspath(a.sdc),
        "set ::env(AEGIS_MARGIN) %s" % a.margin,
        "set ::env(AEGIS_STA_RPT) %s" % o("endpoints.rpt"),
        "source %s" % os.path.join(HERE, "sta_endpoints.tcl"),
        "report_checks -path_delay max -format full -group_path_count 1 > %s" % o("groups.rpt"),
        "report_checks -unconstrained -path_delay max -format end -group_path_count 5 > %s" % o("unconstrained.rpt"),
        "exit"])
    open(o("sta.tcl"), "w").write(tcl)
    sta_log = run([a.sta, "-no_splash", "-exit", o("sta.tcl")], o("sta.log"))

    # 3. metrics
    sys.path.insert(0, HERE)
    from aegis_select import parse_report
    endpoints = parse_report(open(o("endpoints.rpt")).read())
    worst = parse_groups(open(o("groups.rpt")).read())
    clocks = sorted(set(worst) | {e["capture_clock"] for e in endpoints if e["capture_clock"]})
    per = []
    for c in clocks:
        neg = [e["slack_ns"] for e in endpoints if e["capture_clock"] == c and e["slack_ns"] < 0]
        per.append({"clock": c, "wns_ns": worst.get(c), "tns_ns": round(sum(neg), 4),
                    "violating_endpoints": len(neg),
                    "below_margin_endpoints": sum(1 for e in endpoints if e["capture_clock"] == c)})
    area_txt = open(o("area.txt")).read()
    am = re.findall(r"Chip area for (?:top )?module '?\\?%s'?:\s*([\d.]+)" % re.escape(a.top), area_txt) or \
         re.findall(r"Chip area[^:]*:\s*([\d.]+)", area_txt)
    unmatched = sorted(set(re.findall(r"(?m)^Warning:.*(?:not found|no matches|could not find).*$", sta_log + open(o("sta.log")).read())))
    metrics = {
        "top": a.top, "margin_ns": a.margin,
        "wns_ns": min([p["wns_ns"] for p in per if p["wns_ns"] is not None], default=None),
        "tns_ns": round(sum(p["tns_ns"] for p in per), 4),
        "area_um2": float(am[-1]) if am else None,
        "per_domain": per, "flops_renamed": n,
        "sdc_unmatched": unmatched,
        "files": {k: o(v) for k, v in [("netlist", "netlist.v"), ("synth_json", "synth.json"),
                                        ("endpoints", "endpoints.rpt"), ("groups", "groups.rpt"),
                                        ("sta_log", "sta.log"), ("area", "area.txt")]},
    }
    json.dump(metrics, open(o("metrics.json"), "w"), indent=1)
    print(json.dumps({k: metrics[k] for k in ("wns_ns", "tns_ns", "area_um2", "per_domain", "sdc_unmatched")}))


if __name__ == "__main__":
    main()
