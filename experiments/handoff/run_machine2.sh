#!/usr/bin/env bash
# Machine 2 queue (2026-11-02). Runs ONLY these; machine 1 runs everything else (multi-clock Exp 02).
#  Exp 01 (single-clock, 6 smallest Dr. RTL designs): aegis on all 6, drrtl on 5 (drrtl_uart/drrtl is done on machine 1)
#  Exp 03 (ablation): no_guards (Aegis with locks + CDC re-check measured only) on afifo, axil_cdc, async_fifo, soc
# Low load: one run at a time, 2 candidates at once, nice 19. Resumable: re-running skips finished runs; after a
# Claude usage-limit failure it waits 20 min and retries.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
export MAX_PASSES=200 PARALLEL=1 JOBS=2
python3 "$HERE/handoff/check_env.py" || { echo "environment check failed: not running"; exit 1; }
echo "### Exp 01 aegis $(date '+%F %T')"
DESIGNS="$(tr '\n' ' ' < "$HERE/01_drrtl_suite/designs_subset6.txt")" CONFIGS="aegis" REPS=1 OUT="$HERE/01_drrtl_suite/results" nice -n 19 bash "$HERE/run_matrix.sh"
echo "### Exp 01 drrtl $(date '+%F %T')"
DESIGNS="drrtl_ticket_machine drrtl_controller drrtl_communication drrtl_simple_spi drrtl_i2c" CONFIGS="drrtl" REPS=1 OUT="$HERE/01_drrtl_suite/results" nice -n 19 bash "$HERE/run_matrix.sh"
echo "### Exp 03 no_guards $(date '+%F %T')"
DESIGNS="afifo axil_cdc async_fifo soc" CONFIGS="no_guards" REPS=1 OUT="$HERE/03_ablation" nice -n 19 bash "$HERE/run_matrix.sh"
(cd "$HERE/../aegis_agents" && python3 bench/validate_runs.py --archive)
echo "### machine 2 queue done $(date '+%F %T')"
