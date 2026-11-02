#!/usr/bin/env python3
"""refs.bib = paper/related_work.bib (verified entries; internal `note` fields dropped, arXiv ids made visible
to IEEEtran.bst) + extras.bib (tools and benchmark sources)."""
import os, re
H = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(H, "..", "related_work.bib")).read()
out = []
for e in re.split(r"\n(?=@)", src):
    if not e.startswith("@"):
        continue
    e = re.sub(r"\n\s*note\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\},?", "", e)
    m = re.search(r"eprint\s*=\s*\{([^}]*)\}", e)
    if m and not re.search(r"\b(booktitle|journal|howpublished)\s*=", e):
        e = re.sub(r"\}\s*$", ",\n  howpublished  = {arXiv:%s}\n}" % m.group(1), e.rstrip())
    out.append(e.rstrip())
out.append(open(os.path.join(H, "extras.bib")).read())
open(os.path.join(H, "refs.bib"), "w").write(re.sub(r",(\s*),", r",\1", "\n\n".join(out)) + "\n")
