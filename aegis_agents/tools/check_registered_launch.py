#!/usr/bin/env python3
"""
Structural CDC rule R4 ("registered launch"): every bit of a signal that
crosses into another clock domain must be driven DIRECTLY by a flip-flop
clocked by the source clock -- no gates between that flop and the first
synchronizer stage. Combinational launch glitches, and the far domain can
sample the glitch. No value-level property can see this, because cycle
values are unchanged.

Usage
    python3 check_registered_launch.py --rtl a.v b.v --top mod --signal wptr --clock wclk
"""
import argparse
import json
import os
import subprocess
import tempfile

FLOP_TYPES = {"$dff", "$adff", "$sdff", "$dffe", "$adffe", "$sdffe", "$sdffce",
              "$aldff", "$aldffe", "$dffsr", "$dffsre"}


def check_registered_launch(rtl_files, top, params, signal, clock):
    chparams = " ".join("-chparam %s %s" % (k, v) for k, v in (params or {}).items())
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "net.json")
        # proc + opt_clean only: no opt_merge/opt_dff, so we judge the RTL's
        # own structure rather than what later optimisation might do to it.
        script = "read_verilog %s; hierarchy -top %s %s; proc; opt_clean; write_json %s" % (
            " ".join(rtl_files), top, chparams, out)
        res = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr or res.stdout)
        net = json.load(open(out))

    mod = next(m for m in net["modules"].values()
               if m.get("attributes", {}).get("top") in ("00000000000000000000000000000001", 1, "1"))
    clk_bits = mod["ports"][clock]["bits"]
    driver = {}
    for name, cell in mod["cells"].items():
        for port, direction in cell.get("port_directions", {}).items():
            if direction == "output":
                for bit in cell["connections"][port]:
                    driver[bit] = (name, cell["type"], port, cell)

    problems = []
    for i, bit in enumerate(mod["ports"][signal]["bits"]):
        if isinstance(bit, str):
            problems.append("%s[%d] is a constant" % (signal, i))
            continue
        if bit not in driver:
            problems.append("%s[%d] has no cell driver (wired straight from an input?)" % (signal, i))
            continue
        name, ctype, port, cell = driver[bit]
        if ctype not in FLOP_TYPES or port != "Q":
            problems.append("%s[%d] driven by %s (%s), not a flop" % (signal, i, ctype, name.split("$")[-1]))
        elif cell["connections"].get("CLK") != clk_bits:
            problems.append("%s[%d] driven by a flop on another clock" % (signal, i))
    return {"rule": "R4 registered launch", "signal": signal, "ok": not problems,
            "problems": problems[:4] + (["... %d more" % (len(problems) - 4)] if len(problems) > 4 else [])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl", nargs="+", required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--signal", required=True)
    ap.add_argument("--clock", required=True)
    a = ap.parse_args()
    print(json.dumps(check_registered_launch(a.rtl, a.top, {}, a.signal, a.clock), indent=2))
