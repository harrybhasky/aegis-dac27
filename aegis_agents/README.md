# AEGIS: agents and tools for Phases 1–2

Claude Code agents and the deterministic tools they run, from RTL/SDC ingestion through skill selection. `CLAUDE.md` is the orchestrator.

| Step | Agent | Tool | Model's job |
|---|---|---|---|
| Phase 1: parse SDC/RTL, crossings, lock tiers, checksums, contracts | `aegis-ingest` | `tools/aegis_ingest.py` (+ `gen_cdc_props.py`) | run, check, report |
| Baseline synthesis + OpenSTA | `aegis-sta-runner` | `tools/aegis_sta.py` | run only |
| Region selection (prepare / finalize) | `aegis-region-selector` | `tools/aegis_select.py` | run, check, report |
| Root cause and amenability per region | `aegis-timing-analyzer` | none | diagnose |
| Skill choice per region | `aegis-skill-matcher` | `tools/aegis_skills.py` | rank eligible skills |
| Checksum gate for candidates | (orchestrator) | `tools/aegis_ingest.py verify` | none |

## Requirements

- Yosys (tested 0.33) and SymbiYosys at the matching tag, Z3; `yosys-abc` for the PDR fallback.
- OpenSTA (tested 3.1.0, built from source with CUDD and GTest available).
- A liberty file. The example uses Nangate45 from OpenROAD-flow-scripts:
  `curl -o pdk/nangate45.lib https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/master/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib`

## Example

`flow/designs/soc/` is a small multi-clock SoC (async FIFO with Gray pointers, req/ack handshake, pulse synchronizer, clock divider, a third clock without exceptions, and one unsynchronized crossing) with tight clocks so it violates timing. Phase 1 on it finds 3 synchronizers, 2 Gray buses (both contracts proven automatically), 1 qualified capture, 2 unsynchronized crossings, and 8 constraint-audit entries.

## What the tools assume

- **Lock granularity.** Locks are per source line. Registers assigned on the same line as a locked register are locked with it.
- **Contracts.** Gray pointers are detected and calibrated automatically. Handshake, pulse and qualifier crossings need entries in `cdc_annotations.json` (same format as `gen_cdc_props.py` specs); without one, their launch and capture registers stay immutable. Contracts use the scope module's default parameters.
- **Clocks.** Clocks must come from ports or flop outputs named in the SDC. Gated or muxed clocks are not traced; their flops are reported as unclocked.
- **Memories.** FIFO memories are treated as storage. Memory bits that synthesis turns into flops map back to the memory's write port.
- **Area recovery.** Selecting area-recovery targets is not implemented; finalize only reports when every domain meets the margin.
- **Generation onward.** Phase 3 onward (generation, verification, scoring, Librarian) is not part of this package.
