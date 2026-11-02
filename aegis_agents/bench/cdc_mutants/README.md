# CDC mutation benchmark

Clock-domain-crossing faults injected into real multi-clock designs. Each mutant comes with
ground-truth labels and a measurement of which checker catches it. The central question is
which CDC-breaking rewrites pass functional simulation, and which guardrail catches them.

No LLM is involved anywhere in generation or labeling.

## Pipeline

```
python3 bench/cdc_mutants/gen_mutants.py --design <d> [--design ...]   # out/<d>/<mutant>/{mutant.v, meta.json}
python3 bench/cdc_mutants/label.py      --design <d> [--jobs 6]       # out/<d>/<mutant>/label.json
                                                                      # results/labels.{jsonl,md}
```

Prerequisite: Phase 1 output (`flow/work/<d>/phase1/`) exists for the design, which
`tools/aegis_ingest.py` produces. The mutation sites are the crossings Phase 1 classified as
`synchronizer`, `gray_candidate` or `qualified_capture`.

## How mutants are made

Mutation is applied to the hierarchical Yosys netlist (`read; hierarchy; proc; opt_dff`), not to
source text. Every operator therefore applies to any design without per-design patterns. Two
fix-ups keep the netlist comparable to the original:

- Parameterized modules are renamed back to their base names.
- A module with several instances is cloned before editing, so only the targeted instance changes.

Each mutant is written out as one Verilog file.

| Operator | What changes | CDC-safe | Sim-equivalent |
|---|---|---|---|
| `sync_bypass` | Synchronizer stage 2 samples the crossing source directly (depth n → n−1) | no | latency-dependent |
| `sync_remove` | Consumers of the synchronizer output read the unsynchronized source | no | latency-dependent |
| `binary_cross` | Gray crossing re-encoded: gray→binary before stage 1, binary→gray after the last stage | no | **yes** |
| `qual_bypass` | Qualified capture register's enable tied active | no | latency-dependent |
| `extra_stage` | One more synchronizer flop | yes | latency-dependent |
| `post_invert` | Bit 0 of the synchronizer output inverted (functional bug) | yes | no |
| `identity` | Netlist round trip only | yes | yes |
| `free_dblinv` | Double inversion on combinational logic outside every CDC module | yes | yes |

The `binary_cross` class is the motivating case. It is cycle-for-cycle equivalent in
zero-delay RTL simulation. In silicon, however, multiple binary bits change at once and pass
through combinational XOR logic into the synchronizer. Any functional check passes it, so only
a CDC-aware check can reject it.

Related prior work: the CDC mutation taxonomy of Synopsys patent US9990453B2 (chain bypass,
glitch insertion, stuck handshake, …) is a method with no dataset. Timing-logic metamorphosis
(arXiv:2507.16808) applies *semantics- and CDC-preserving* clock-domain transformations to stress
optimizers. This benchmark is the complement: rewrites that are functionally plausible but
CDC-unsafe.

## Checkers measured (`label.py`)

| Column | Check |
|---|---|
| Sim | Phase 4 differential simulation: every clock at its SDC period, LCM window, 2 seeds |
| EQY | Partitioned SBY k-induction (depth 8). Gold is the `identity` netlist, so gold and gate differ only by the mutation. A flag means "not proven" (inconclusive), not a counterexample. |
| Structural | Phase 1 re-run: new unsynchronized or insufficient-depth crossing, or a protected crossing lost or downgraded |
| Contract | Every SBY contract proven on the original is still proven at the same latency (only for designs with calibrated contracts) |

Aegis's source-line lock checksum gate is not measured here. Mutants are netlists, so the
gate would reject every one of them trivially. The hand-written source-level mutants in
`bench/guardrail_tests.py` cover the lock gate.

## Status / known limitations

- Glitch-insertion, handshake (stuck ack) and reset-synchronizer operators are not
  implemented yet. Covering them needs designs with req/ack and reset-sync crossings (see
  `benchmarks/README.md`).
- `sim_equiv = None` operators change latency. Whether random-stimulus simulation sees the
  change depends on the protocol and the stimulus.
