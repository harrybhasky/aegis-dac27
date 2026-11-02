#!/usr/bin/env python3
"""Generate every results table and inline number of the DAC'27 paper from the logged runs.

  python3 paper/dac27/gen_tables.py        # writes paper/dac27/tables/*.tex and numbers.tex

Sources (nothing is typed in by hand except MANUAL_AUDIT, which cites the key-findings file it comes from):
  aegis_agents/flow/runs/<design>/<config>.sonnet-5-5.r1/summary.json   (benchmark runs)
  aegis_agents/flow/work/<design>/phase1/phase1_report.json             (crossing classification)
  aegis_agents/flow/work/<design>/baseline_synth/                        (baseline when no run exists yet)
  aegis_agents/bench/cdc_mutants/out/<design>/<mutant>/label.json       (CDC mutation benchmark)
Runs archived as invalid (flow/runs_archive/) are never read.
"""
import glob, json, os, statistics

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AEGIS = os.path.join(ROOT, "aegis_agents")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables")
EXP02 = os.path.join(ROOT, "experiments", "02_multiclock", "designs.txt")
EXP01 = os.path.join(ROOT, "experiments", "01_drrtl_suite", "designs_subset6.txt")  # 6 smallest by baseline area (2026-11-02)
RID = "%s.sonnet-5-5.r1"

# Manual CDC audit of final designs whose automatic CDC re-check result needs a human reading
# (each entry cites the key-findings file with the evidence).
MANUAL_AUDIT = {
    ("afifo", "drrtl"): ("safe", "memory recoded as registers; re-check false positive (key_findings/10)"),
    ("axil_cdc", "drrtl"): ("unsafe", "2nd synchronizer stage duplicated 5x (key_findings/11)"),
    ("afifo", "vanilla"): ("unsafe", "synchronizer depth 2 -> 1 (key_findings/09)"),
    ("axis_async_fifo", "drrtl"): ("safe", "memory recoded as per-entry regs + equivalent full_wr; all 32 flags are mem[i] (key_findings/10)"),
}


def designs(path):
    return [l.strip() for l in open(path) if l.strip()]


def run(d, c):
    p = os.path.join(AEGIS, "flow", "runs", d, RID % c, "summary.json")
    return json.load(open(p)) if os.path.exists(p) else None


def phase1(d):
    p = os.path.join(AEGIS, "flow", "work", d, "phase1", "phase1_report.json")
    return json.load(open(p)) if os.path.exists(p) else None


def baseline(d):
    for c in ("aegis", "drrtl", "vanilla"):
        r = run(d, c)
        if r:
            return r["baseline"]
    p = os.path.join(AEGIS, "flow", "work", d, "baseline_synth", "metrics.json")
    if os.path.exists(p):
        m = json.load(open(p))
        return {"wns_ns": m.get("wns_ns"), "tns_ns": m.get("tns_ns"), "area_um2": m.get("area_um2")}
    return None


def tex(s):
    return str(s).replace("_", r"\_")


def f2(x):
    return "--" if x is None else ("%.2f" % x).replace("-", "$-$")


def pct(new, old):
    return None if old in (None, 0) or new is None else 100.0 * (new - old) / abs(old)


def eqy(r):
    fc = r.get("final_check") or {}
    if r["final_version"] == "v0":
        return "n/c"  # nothing promoted: the final design is the original
    return {"PASS": r"\cmark", "FAIL": r"\xmark"}.get(fc.get("eqy_top_vs_v0"), "?")


def remeasure(d, c):
    p = os.path.join(AEGIS, "flow", "runs", d, RID % c, "final_remeasure.json")
    return json.load(open(p)) if os.path.exists(p) else None


def cdc_status(d, c, r):
    """manual audit first; else the final re-measurement (one checker for every configuration, bench/
    final_remeasure.py); else the check recorded by the run itself"""
    fr = remeasure(d, c)
    if (d, c) in MANUAL_AUDIT:
        if fr and fr["cdc_pass"] and MANUAL_AUDIT[(d, c)][0] == "unsafe":
            print("NOTE: %s/%s audited unsafe but the final CDC re-check passes it" % (d, c))
        return MANUAL_AUDIT[(d, c)][0]
    if r["final_version"] == "v0":
        return "n/c"
    if fr:
        return "safe" if fr["cdc_pass"] else "flag"
    viol = (r.get("final_check") or {}).get("measured_violations") or []
    return "flag" if "cdc" in viol else "safe"


def flat_gain(d, c):
    fr = remeasure(d, c)
    f = (fr or {}).get("flat") or {}
    return None if f.get("error") or f.get("base_wns") is None else gain(f["final_wns"], f["base_wns"])


CDC_SYM = {"safe": r"\cmark", "unsafe": r"\xmark", "flag": r"\textbf{?}", "n/c": "n/c"}

nums = {}


def num(name, val):
    nums[name] = val


# ---------------------------------------------------------------- T1: multi-clock suite (Phase 1)
def t_suite():
    rows = []
    for d in designs(EXP02):
        p, b = phase1(d), baseline(d)
        if not p:
            continue
        x = p["crossings"]
        clocks = p["clocks"] if isinstance(p["clocks"], int) else len(p["clocks"])
        rows.append(r"\texttt{%s} & %d & %d & %d & %d & %d & %d & %d & %s & %s & %s \\" % (
            tex(d), clocks, p["flops"], x["synchronizer"], x["gray_candidate"], x["qualified_capture"],
            x["insufficient_depth"] + x["unsynchronized"], len(p["contracts_proven"]),
            f2(b and b["wns_ns"]), f2(b and b["tns_ns"]), "--" if not b else "{:,.0f}".format(b["area_um2"])))
    open(os.path.join(OUT, "suite.tex"), "w").write("\n".join(rows) + "\n")
    num("NMcDesigns", len(rows))
    P = [phase1(d) for d in designs(EXP02) if phase1(d)]
    num("NMcGrayDesigns", sum(1 for p in P if p["crossings"]["gray_candidate"] > 0))
    num("NMcContractDesigns", sum(1 for p in P if p["crossings"]["gray_candidate"] > 0 and p["contracts_proven"]))


# ---------------------------------------------------------------- T2: multi-clock results
def gain(new, old):
    """improvement in % (positive = closer to zero / better), Dr. RTL's convention with the sign flipped"""
    return None if old in (None, 0) or new is None else 100.0 * (new - old) / abs(old)


def t_multiclock():
    rows, done, tot = [], 0, 0
    tok = {"aegis": [], "drrtl": []}
    agg = {"aegis": [], "drrtl": [], "vanilla": []}
    for d in designs(EXP02):
        first = True
        for c in ("aegis", "drrtl", "vanilla"):
            r = run(d, c)
            if c == "vanilla" and not r:
                continue  # vanilla was dropped from Exp 02 after the first five designs
            tot += c != "vanilla"
            name = r"\texttt{%s}" % tex(d) if first else ""
            first = False
            cfg = {"aegis": r"\textsc{Aegis}", "drrtl": "Dr.\\,RTL", "vanilla": "Vanilla"}[c]
            if not r:
                rows.append(r"%s & %s & \multicolumn{8}{c}{\emph{run pending}} \\" % (name, cfg))
                continue
            done += c != "vanilla"
            b, f = r["baseline"], r["final"]
            worst = lambda m: min(x["wns_ns"] for x in m["per_domain"])
            llm = r.get("llm", {})
            ktok = (llm.get("tokens_in", 0) + llm.get("tokens_out", 0)) / 1000.0
            if c in tok:
                tok[c].append((d, ktok))
            gw, gt = gain(worst(f), worst(b)), gain(f["tns_ns"], b["tns_ns"])
            ga = -pct(f["area_um2"], b["area_um2"])
            ok = eqy(r) in (r"\cmark", "n/c") and cdc_status(d, c, r) in ("safe", "n/c")
            fg = flat_gain(d, c)
            agg[c].append({"w": gw, "t": gt, "a": ga, "ok": ok, "eqy": eqy(r), "cdc": cdc_status(d, c, r), "tok": ktok,
                           "flat": fg})
            pc = lambda v: ("(%+.0f\\%%)" % v).replace("-", "$-$")
            rows.append(r"%s & %s & %s$\to$%s %s & %s$\to$%s %s & %s & %s & %s & %s & %.0f & %d \\" % (
                name, cfg, f2(worst(b)), f2(worst(f)), pc(gw), f2(b["tns_ns"]), f2(f["tns_ns"]), pc(gt),
                "--" if fg is None else ("%+.0f" % fg).replace("-", "$-$"),
                ("%+.1f" % pct(f["area_um2"], b["area_um2"])).replace("-", "$-$"),
                eqy(r), CDC_SYM[cdc_status(d, c, r)], ktok, llm.get("calls", 0)))
        rows.append(r"\midrule")
    if rows and rows[-1] == r"\midrule":
        rows.pop()
    # average rows (Dr. RTL's Table 2 reports the plain average; we add the average over shippable final
    # designs, where a final design that fails EQY or is CDC-unsafe counts as 0% gain: it cannot be used)
    rows.append(r"\midrule")
    m = lambda v: ("%+.1f" % statistics.mean(v)).replace("-", "$-$") if v else "--"
    for c in ("aegis", "drrtl", "vanilla"):
        A = agg[c]
        if not A:
            continue
        cfg = {"aegis": r"\textsc{Aegis}", "drrtl": "Dr.\\,RTL", "vanilla": "Vanilla"}[c]
        z = lambda k: [x[k] if x["ok"] else 0.0 for x in A]
        fl = [x["flat"] for x in A if x["flat"] is not None]
        rows.append(r"\multicolumn{2}{@{}l}{Avg.\ %s (%d)} & %s\%% & %s\%% & %s & %s & %d/%d & %d/%d & %.0f & \\" % (
            cfg, len(A), m([x["w"] for x in A]), m([x["t"] for x in A]), m(fl) if len(fl) == len(A) else "--",
            m([-x["a"] for x in A]),
            sum(x["eqy"] == r"\cmark" for x in A), sum(x["eqy"] != "n/c" for x in A),
            sum(x["cdc"] in ("safe", "n/c") for x in A), len(A), statistics.mean([x["tok"] for x in A])))
        rows.append(r"\multicolumn{2}{@{}l}{\quad shippable only} & %s\%% & %s\%% & & %s & & & & \\" % (
            m(z("w")), m(z("t")), m([-v for v in z("a")])))
        num("AvgW" + c.capitalize(), m([x["w"] for x in A]))
        num("AvgT" + c.capitalize(), m([x["t"] for x in A]))
        num("ShipW" + c.capitalize(), m(z("w")))
        num("ShipT" + c.capitalize(), m(z("t")))
    open(os.path.join(OUT, "multiclock.tex"), "w").write("\n".join(rows) + "\n")
    num("NMcRunsDone", done)
    num("NMcRunsTotal", tot)
    both = [d for d, _ in tok["aegis"] if d in dict(tok["drrtl"])]
    if both:
        ratio = statistics.median(dict(tok["drrtl"])[d] / dict(tok["aegis"])[d] for d in both)
        num("TokRatioMedian", "%.1f" % ratio)
        num("NTokPairs", len(both))


# ---------------------------------------------------------------- T3: single-clock suite (Exp 01)
def t_singleclock():
    rows = []
    for c in ("aegis", "drrtl", "vanilla"):
        rs = [(d, run(d, c)) for d in designs(EXP01)]
        rs = [(d, r) for d, r in rs if r]
        n = len(rs)
        prom = [(d, r) for d, r in rs if r["final_version"] != "v0"]
        ok = [(d, r) for d, r in prom if (r.get("final_check") or {}).get("eqy_top_vs_v0") == "PASS"]
        gains = [pct(min(x["wns_ns"] for x in r["final"]["per_domain"]),
                     min(x["wns_ns"] for x in r["baseline"]["per_domain"])) for _, r in ok]
        tns = [pct(r["final"]["tns_ns"], r["baseline"]["tns_ns"]) for _, r in ok]
        cfg = {"aegis": r"\textsc{Aegis}", "drrtl": "Dr.\\,RTL", "vanilla": "Vanilla"}[c]
        med = lambda v: ("%.1f" % statistics.median(v)) if v else "--"
        rows.append(r"%s & %d/%d & %d & %d & %s & %s \\" % (cfg, n, len(designs(EXP01)), len(prom), len(ok), med(gains), med(tns)))
        num("NScDone" + c.capitalize(), n)
    open(os.path.join(OUT, "singleclock.tex"), "w").write("\n".join(rows) + "\n")
    num("NScDesigns", len(designs(EXP01)))


# ---------------------------------------------------------------- T4: CDC mutation benchmark
def t_mutants():
    labs = [json.load(open(p)) for p in glob.glob(os.path.join(AEGIS, "bench", "cdc_mutants", "out", "*", "*", "label.json"))]
    # CDC checker version: the re-scored fields (bench/cdc_mutants/rescore_cdc.py --tag v2, the checker after the
    # 2026-11-02 Phase 1 fix) are used only when EVERY label has them, so one table never mixes two checkers
    if labs and all("structural_v2" in l for l in labs):
        for l in labs:
            l["structural_v1"], l["contract_v1"] = l["structural"], l["contract"]
            l["structural"], l["contract"] = l["structural_v2"], l["contract_v2"]
        num("MutChecker", "v2")
    else:
        num("MutChecker", "v1")
    # Calibration rule: a design whose own identity (netlist round-trip) control is flagged by the structural
    # check is excluded; on such designs Phase 1 does not recognise the synchronizer cells (PULP common_cells).
    bad = {l["design"] for l in labs if l["operator"] == "identity" and l["structural"] is False}
    use = [l for l in labs if l["design"] not in bad]
    U = [l for l in use if l["ground_truth"]["cdc_safe"] is False]
    S = [l for l in use if l["ground_truth"]["cdc_safe"] is True]
    sim_pass = lambda l: l["sim"] is True
    eqy_pass = lambda l: l["eqy"] == "PASS"
    struct = lambda l: l["structural"] is False
    contract = lambda l: l["contract"] is False
    checks = [
        ("Differential simulation (LCM, 2 seeds)", lambda l: not sim_pass(l)),
        ("EQY ($k$-induction, gold = identity)", lambda l: not eqy_pass(l)),
        ("Simulation $\\lor$ EQY (functional gates)", lambda l: not (sim_pass(l) and eqy_pass(l))),
        ("Contract re-proof only", contract),
        ("Structural re-classification only", struct),
        ("\\textsc{Aegis} CDC re-check (structural $\\lor$ contract)", lambda l: struct(l) or contract(l)),
    ]
    rows = []
    for i, (name, flags) in enumerate(checks):
        fa = "n/a" if i < 3 else "%d/%d" % (sum(map(flags, S)), len(S))  # functional gates rightly reject safe-but-
        rows.append(r"%s & %d/%d & %s \\" % (name, sum(map(flags, U)), len(U), fa))  # non-equivalent mutants
    open(os.path.join(OUT, "mutants.tex"), "w").write("\n".join(rows) + "\n")
    num("NMutLabeled", len(labs))
    num("NMutUsed", len(use))
    num("NMutDesigns", len({l["design"] for l in use}))
    num("NMutExclDesigns", len(bad))
    num("NMutUnsafe", len(U))
    num("NMutSafe", len(S))
    num("NMutUnsafeSimPass", sum(map(sim_pass, U)))
    num("NMutUnsafeEqyPass", sum(map(eqy_pass, U)))
    num("NMutUnsafeStructMiss", sum(1 for l in U if not struct(l)))
    num("NMutUnsafeCaught", sum(1 for l in U if struct(l) or contract(l)))
    num("NMutSafeFalseAlarm", sum(1 for l in S if struct(l) or contract(l)))
    bc = [l for l in U if l["operator"] == "binary_cross"]
    num("NMutUnsafeBothPass", sum(1 for l in U if sim_pass(l) and eqy_pass(l)))
    num("NMutBinaryCross", len(bc))
    num("NMutBinaryCrossEqyPass", sum(map(eqy_pass, bc)))
    num("NMutBinaryCrossSimPass", sum(map(sim_pass, bc)))
    # unsafe mutants the contract re-proof flags only under the post-fix checker (v2) and not under v1
    num("NMutContractNew", sum(1 for l in U if "contract_v1" in l and l["contract_v1"] and not l["contract"]))


# ---------------------------------------------------------------- Exp 05: metastability injection (axil_cdc)
def t_meta():
    p = os.path.join(ROOT, "experiments", "05_metastability", "results.txt")
    if not os.path.exists(p):
        return
    import re
    R = {}
    for l in open(p):
        m = re.match(r"(\w+) (NO_META|META) seed=\d+ RESULT sent=(\d+) .* torn=(\d+)", l)
        if m:
            R.setdefault((m.group(1), m.group(2)), []).append((int(m.group(3)), int(m.group(4))))
    if ("drrtl", "META") not in R:
        return
    num("MetaSeeds", len(R[("drrtl", "META")]))
    num("MetaWrites", R[("drrtl", "META")][0][0])
    num("MetaWords", 2 * R[("drrtl", "META")][0][0])
    num("MetaOrigTorn", max(t for _, t in R[("orig", "META")]))
    num("MetaNoInjTorn", max(t for k in (("orig", "NO_META"), ("drrtl", "NO_META")) for _, t in R[k]))
    num("MetaDrMin", "{:,}".format(min(t for _, t in R[("drrtl", "META")])))
    num("MetaDrMax", "{:,}".format(max(t for _, t in R[("drrtl", "META")])))
    num("MetaDrPct", "%.0f" % (100.0 * statistics.mean(t for _, t in R[("drrtl", "META")]) / (2 * R[("drrtl", "META")][0][0])))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    t_suite(); t_multiclock(); t_singleclock(); t_mutants(); t_meta()
    with open(os.path.join(OUT, "numbers.tex"), "w") as f:
        f.write("% generated by gen_tables.py -- do not edit\n")
        for k, v in sorted(nums.items()):
            f.write("\\newcommand{\\%s}{%s}\n" % (k, v))
    print(json.dumps(nums, indent=1))
