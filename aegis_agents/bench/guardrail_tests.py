#!/usr/bin/env python3
"""
Guardrail test suite: hand-written candidate rewrites with a known ground truth, each run
through Phase 4 (gate, lint, LCM simulation, CDC re-check) and Phase 5 EQY, with every check
evaluated as a measurement (nothing short-circuits), so the table shows which layer catches
which class of error. No LLM is involved.

  python3 bench/guardrail_tests.py    ->  bench/results/guardrail_tests.{json,md}

Ground-truth classes
  equivalent            functionally equivalent rewrite of free logic           (should pass)
  functional_bug        changes behavior                                         (sim/EQY should fail)
  sync_edit             edits a synchronizer chain (removes a stage)             (lock must fail)
  gray_binary           launches a binary instead of a Gray pointer              (sim/EQY or CDC)
  comb_launch           functionally EQUIVALENT, but the Gray pointer is launched
                        from combinational logic (glitch-prone across the crossing)  (only CDC/R4 can fail)
  reconverge            functionally EQUIVALENT, but a crossing bus is re-captured without
                        a synchronizer                                           (only CDC can fail)
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ["PATH"]
import aegis_eval  # noqa: E402
import aegis_verify  # noqa: E402
from aegis_common import load_design  # noqa: E402


def soc_cases(src):
    L = "wire        wfull_next = (wgray_next == {~wq2_rptr[AW:AW-1], wq2_rptr[AW-2:0]});"
    yield "equivalent", "wfull compare as XOR-reduce", {"soc.v": src.replace(
        L, "wire [AW:0] tgt = {~wq2_rptr[AW:AW-1], wq2_rptr[AW-2:0]};\n  wire        wfull_next = ~|(wgray_next ^ tgt);")}, "wptr_full"
    yield "functional_bug", "full flag compares against un-inverted MSBs", {"soc.v": src.replace(
        L, "wire        wfull_next = (wgray_next == {wq2_rptr[AW:AW-1], wq2_rptr[AW-2:0]});")}, "wptr_full"
    yield "sync_edit", "second synchronizer stage samples d directly", {"soc.v": src.replace(
        "else        begin s1 <= d;         s2 <= s1;         end", "else        begin s1 <= d;         s2 <= d;          end")}, "sync2"
    yield "gray_binary", "write pointer launched in binary", {"soc.v": src.replace("wptr <= wgray_next;", "wptr <= wbin_next;")}, "wptr_full"
    s2 = src.replace("output reg [AW:0] wptr, output reg wfull", "output [AW:0] wptr, output reg wfull")
    s2 = s2.replace("if (!wrst_n) begin wbin <= 0; wptr <= 0; wfull <= 1'b0; end", "if (!wrst_n) begin wbin <= 0; wfull <= 1'b0; end")
    s2 = s2.replace("else begin wbin <= wbin_next; wptr <= wgray_next; wfull <= wfull_next; end",
                    "else begin wbin <= wbin_next; wfull <= wfull_next; end\n  assign wptr = (wbin >> 1) ^ wbin;")
    yield "comb_launch", "Gray pointer driven combinationally from the binary register", {"soc.v": s2}, "wptr_full"


def fifo_cases(files):
    w = files["wptr_full.v"]
    yield "equivalent", "full compare as XOR-reduce", {"wptr_full.v": w.replace(
        "assign wfull_val = (wgraynext == {~wq2_rptr[ADDRSIZE:ADDRSIZE-1],wq2_rptr[ADDRSIZE-2:0]});",
        "wire [ADDRSIZE:0] wfull_tgt = {~wq2_rptr[ADDRSIZE:ADDRSIZE-1],wq2_rptr[ADDRSIZE-2:0]};\n     assign wfull_val = ~|(wgraynext ^ wfull_tgt);")}, "wptr_full"
    yield "functional_bug", "binary increment ignores full", {"wptr_full.v": w.replace(
        "assign wbinnext  = wbin + ((winc & ~wfull) ? 1 : 0);", "assign wbinnext  = wbin + (winc ? 1 : 0);")}, "wptr_full"
    s = files["sync_r2w.v"]
    yield "sync_edit", "read-pointer synchronizer reduced to one stage", {"sync_r2w.v": s.replace(
        "{wq2_rptr,wq1_rptr} <= {wq1_rptr,rptr};", "{wq2_rptr,wq1_rptr} <= {rptr,rptr};")}, "sync_r2w"
    yield "gray_binary", "write pointer launched in binary", {"wptr_full.v": w.replace(
        "{wbin, wptr} <= {wbinnext, wgraynext};", "{wbin, wptr} <= {wbinnext, wbinnext};")}, "wptr_full"


def run_case(D, base_files, design, cls, desc, edits, scope):
    with tempfile.TemporaryDirectory() as td:
        cand = []
        for f in base_files:
            b = os.path.basename(f)
            p = os.path.join(td, b)
            open(p, "w").write(edits.get(b, open(f).read()))
            cand.append(p)
        changed = [b for b in edits if edits[b] != open(next(f for f in base_files if os.path.basename(f) == b)).read()]
        assert changed, "mutation did not apply: %s %s" % (design, desc)
        phase1 = os.path.join(ROOT, "flow", "work", design, "phase1")
        v = aegis_verify.run(D, base_files, cand, None, phase1, None, gate_locks=False, gate_cdc=False, gate_envelope=False)
        st = v["stages"]
        ev = aegis_eval.evaluate(D, base_files, cand, [scope], os.path.join(ROOT, "flow", "work", design, "baseline_synth", "metrics.json"),
                                 os.path.join(td, "eval"), 0.6, 0.3, 0.1, skip_eqy=False)
        sim = st.get("sim") or {}
        return {"design": design, "class": cls, "mutation": desc,
                "lock": st["gate"]["checksum"]["pass"], "lint": (st.get("lint") or {}).get("pass"),
                "sim": sim.get("pass"), "sim_mismatches": sim.get("mismatches"),
                "eqy": [e["status"] for e in ev["eqy"]][0] if ev["eqy"] else None,
                "cdc": (st.get("cdc") or {}).get("pass"), "cdc_violations": (st.get("cdc") or {}).get("violations", [])[:3]}


def main():
    rows = []
    D = load_design("soc")
    src = open(D["rtl"][0]).read()
    for cls, desc, edits, scope in soc_cases(src):
        rows.append(run_case(D, D["rtl"], "soc", cls, desc, edits, scope))
        print(json.dumps(rows[-1]), flush=True)
    D = load_design("async_fifo")
    files = {os.path.basename(f): open(f).read() for f in D["rtl"]}
    for cls, desc, edits, scope in fifo_cases(files):
        rows.append(run_case(D, D["rtl"], "async_fifo", cls, desc, edits, scope))
        print(json.dumps(rows[-1]), flush=True)
    out = os.path.join(HERE, "results")
    os.makedirs(out, exist_ok=True)
    json.dump(rows, open(os.path.join(out, "guardrail_tests.json"), "w"), indent=1)
    ok = lambda x: "-" if x is None else ("pass" if x else "**FAIL**")
    md = ["| Design | Class | Mutation | Lock checksum | Lint | LCM sim | EQY | CDC re-check |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append("| %s | %s | %s | %s | %s | %s%s | %s | %s |" % (
            r["design"], r["class"], r["mutation"], ok(r["lock"]), ok(r["lint"]), ok(r["sim"]),
            (" (%d)" % r["sim_mismatches"]) if r["sim_mismatches"] else "", r["eqy"], ok(r["cdc"])))
    open(os.path.join(out, "guardrail_tests.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
