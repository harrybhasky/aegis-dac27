# 01. Same timing as Dr. RTL at a fraction of the LLM cost

**Status: PRELIMINARY.** Two designs (soc, prim_fifo_async), one run per configuration. Needs the full multi-clock suite, ideally with
repeats, before it becomes a claim.

## Data (soc, claude-sonnet-5-5, 5x5 budget)

| soc | Aegis | Vanilla | Dr. RTL (port) |
|---|---|---|---|
| Final timing on synchronous paths | clk_w -0.04 -> +0.04, clk_r 0.19 -> 0.37 | same | same |
| Best result found in | iteration 1 | iteration 1 | iteration 1 |
| Iterations run | 3 (stopped itself) | 5 | 5 |
| LLM calls | **20** | 25 | 50 |
| Tokens in / out | **110k / 28k** | 167k / 53k | 788k / 228k |
| Cost (API-equivalent) | **$0.68** | $0.70 | $4.02 |
| Wall clock | **4.4 min** | 6.6 min | 18 min |
| Final design passes EQY | yes | **no** | yes |

Dr. RTL used ~7x the tokens and ~6x the cost of Aegis for the same timing.

## Second design: prim_fifo_async (OpenTitan)

| prim_fifo_async | Aegis | Dr. RTL (port) |
|---|---|---|
| Timing | no change (-0.11 / -0.09) | no change |
| Iterations | 4 (stopped itself) | 5 |
| LLM calls | **32** | 50 |
| Tokens in / out | **346k / 155k** | 1,278k / 392k |
| Cost | **$2.82** | $7.62 |
| Wall clock | **10.2 min** | 25.8 min |

Same outcome at ~37% of the cost (3.3x fewer tokens). Here neither improved timing (see [08](08_prim_fifo_async_locks.md)).

## Why
1. **No budget on unfixable paths.** Aegis's region selection classifies clk_x's violators as asynchronous paths with
   no CDC exception and never dispatches them. Dr. RTL's analyzer chose them as the top critical path in all 5
   iterations (see [02](02_async_path_diagnosis.md)).
2. **Smaller prompts.** Dr. RTL makes two calls per candidate (analyzer, optimizer), and every optimizer call carries
   the full 28 KB skill.md plus the whole RTL. Aegis's generator gets only the region's modules plus one chosen skill;
   the skill matcher sees only eligible skills. This gap should grow with design size (soc is small).
3. **Early stop.** Aegis stops after two iterations below epsilon; Dr. RTL's protocol always runs every iteration.

## Caveats a reviewer will raise
- Early stopping is ours; to be fair, also report **cost per iteration** (Aegis ~7 calls / ~45k tokens, Dr. RTL
  ~10 calls / ~200k tokens on soc) and **cost to reach the final result**, not only totals.
- Equal timing on soc is expected: it has one real synchronous problem and every method found it.

## Sources
`aegis_agents/flow/runs/soc/{aegis,vanilla,drrtl}.sonnet-5-5.r1/summary.json`, `llm_calls.jsonl`, `RUN_NOTES.md`.
