#!/usr/bin/env python3
"""Shared helpers for AEGIS Phases 3-5.5 (source spans, design config, paths)."""
import json
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_MOD = re.compile(r"^\s*(?:module|macromodule)\s+([A-Za-z_][\w$]*)", re.M)


def strip_comments(text):
    """Blank out comments but keep line structure (so line numbers survive)."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if c == "\n" else " " for c in text[i:j]))
            i = j
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def module_spans(text):
    """[(name, first_line, last_line)] (1-based, inclusive) for every module in a file."""
    clean = strip_comments(text)
    spans = []
    for m in _MOD.finditer(clean):
        start = clean.count("\n", 0, m.start()) + 1
        e = re.compile(r"\bendmodule\b").search(clean, m.end())
        end = clean.count("\n", 0, e.end()) + 1 if e else clean.count("\n") + 1
        spans.append((m.group(1), start, end))
    return spans


def module_of_line(spans, line):
    for name, a, b in spans:
        if a <= line <= b:
            return name
    return None


def norm(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def load_design(design):
    """flow/designs/<design>/design.json, with paths made absolute."""
    path = os.path.join(ROOT, "flow", "designs", design, "design.json")
    d = json.load(open(path))
    fix = lambda p: p if os.path.isabs(p) else os.path.join(ROOT, p)
    d["rtl"] = [fix(p) for p in d["rtl"]]
    d["sdc"] = fix(d["sdc"])
    d["liberty"] = fix(d["liberty"])
    if d.get("annotations"):
        d["annotations"] = fix(d["annotations"])
    d["name"] = design
    return d


def yosys_json(script, quiet=True):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "n.json")
        r = subprocess.run(["yosys"] + (["-q"] if quiet else []) + ["-p", script + "; write_json " + out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("yosys failed:\n" + (r.stderr or r.stdout)[-2000:])
        return json.load(open(out))


def read_cmd(files):
    return "; ".join("read_verilog -sv %s" % os.path.abspath(f) for f in files)


def module_ports(files, top=None):
    """{module: {port: (direction, width)}} after hierarchy/proc (base module names)."""
    net = yosys_json("%s; hierarchy %s; proc" % (read_cmd(files), ("-top " + top) if top else "-auto-top"))
    out = {}
    for mn, m in net["modules"].items():
        n = mn.lstrip("\\")
        mm = re.match(r"\$paramod\$[0-9a-f]+\\(.+)$", n) or re.match(r"\$paramod\\([^\\]+)", n)
        n = mm.group(1) if mm else n
        ports = {p.lstrip("\\"): (v["direction"], len(v["bits"])) for p, v in m.get("ports", {}).items()}
        out.setdefault(n, ports)
    return out


def version_dir(design, ver):
    return os.path.join(ROOT, "flow", "rtl", design, ver)


def version_files(design, ver, base_files):
    d = version_dir(design, ver)
    return [os.path.join(d, os.path.basename(f)) for f in base_files]


def which(tool, fallbacks=()):
    from shutil import which as w
    p = w(tool)
    if p:
        return p
    for f in fallbacks:
        f = os.path.expanduser(f)
        if os.path.exists(f):
            return f
    return tool
