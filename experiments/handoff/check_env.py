#!/usr/bin/env python3
"""Environment check for the second machine. MUST pass before any benchmark run.

Re-synthesizes and times the ORIGINAL RTL of the 10 designs this machine will run, with exactly the function the
benchmark uses (aegis_eval.sta), and compares WNS / TNS / area / per-clock WNS with reference_baselines.json,
produced on the first machine. Any difference means the EDA tools differ (Yosys/ABC/OpenSTA/liberty), and results
would not be comparable with the first machine's runs -- do NOT start benchmarks then.

  python3 experiments/handoff/check_env.py
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "aegis_agents"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]

import aegis_eval  # noqa: E402  (resolves OpenSTA exactly as the benchmark does: `sta` on PATH or known build dirs)
ok = True
for tool, args in [("yosys", ["-V"]), (aegis_eval.STA, ["-version"]), ("sby", ["--help"]), ("eqy", ["--help"]),
                   ("yosys-smtbmc", ["--help"]), ("yosys-abc", ["-h"]), ("z3", ["--version"]), ("iverilog", ["-V"]),
                   ("vvp", ["-V"]), ("verilator", ["--version"]), ("claude", ["--version"])]:
    p = shutil.which(tool) or (tool if os.path.isfile(tool) else None)
    if not p:
        print("MISSING  %s" % tool); ok = False; continue
    try:
        out = subprocess.run([tool] + args, capture_output=True, text=True, timeout=30)
        first = (out.stdout or out.stderr).strip().splitlines()[:1]
    except Exception as e:  # noqa: BLE001
        first = [repr(e)]
    print("found    %-13s %s  %s" % (tool, p, first[0][:90] if first else ""))
if not ok:
    sys.exit("install the missing tools first (see CLAUDE.md, section 'Environment')")

from aegis_common import load_design  # noqa: E402
ref = json.load(open(os.path.join(HERE, "reference_baselines.json")))
with tempfile.TemporaryDirectory() as td:
    for d, r in ref.items():
        D = load_design(d)
        m, err = aegis_eval.sta(D, list(D["rtl"]), os.path.join(td, d), D.get("margin", 0.1))
        if m is None:
            print("FAIL     %-22s synthesis/STA error: %s" % (d, (err or "")[-300:])); ok = False; continue
        got = {"wns_ns": m["wns_ns"], "tns_ns": m["tns_ns"], "area_um2": m["area_um2"],
               "per_domain": [{"clock": x["clock"], "wns_ns": x["wns_ns"], "tns_ns": x["tns_ns"]} for x in m["per_domain"]]}
        same = got == r
        ok &= same
        print("%-8s %-22s wns %s/%s tns %s/%s area %s/%s" % ("OK" if same else "MISMATCH", d, got["wns_ns"], r["wns_ns"],
              got["tns_ns"], r["tns_ns"], got["area_um2"], r["area_um2"]))
print("\nENVIRONMENT %s" % ("MATCHES the reference machine: you may run the benchmarks" if ok else
                            "DOES NOT MATCH: do not run benchmarks; report the mismatches above"))
sys.exit(0 if ok else 1)
