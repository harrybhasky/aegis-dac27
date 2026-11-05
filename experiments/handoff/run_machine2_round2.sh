#!/usr/bin/env bash
# Machine 2, ROUND 2 (2026-11-05). Machine 1 (the author's laptop) overheats and now runs nothing heavy, so machine 2
# runs every remaining benchmark run, in this priority order (most important for the paper first):
#  1. Exp 02 multi-clock: axis_async_fifo / aegis           (1 run; its first try was invalidated by a network outage)
#  2. Exp 01 single-clock expansion: drrtl_spi drrtl_pcie drrtl_dsp drrtl_router x aegis, drrtl   (8 runs)
#  3. Exp 04 RTL-OPT (standard 2026 benchmark, arXiv 2601.01765): 6 designs x aegis, drrtl         (12 runs)
#  4. Exp 02 multi-clock: eth_mac_1g_fifo x aegis, drrtl    (2 runs, the largest design: ~1 day each)
# Same settings as round 1: one run at a time, 2 candidates at once, nice 19. Resumable (finished runs are skipped).
# After each step the finished runs are packed and pushed (branch results-machine2-r2).
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
export MAX_PASSES=200 PARALLEL=1 JOBS=2
python3 "$HERE/handoff/check_env.py" || { echo "environment check failed: not running"; exit 1; }
step() { echo "### $1 $(date '+%F %T')"
  DESIGNS="$2" CONFIGS="$3" REPS=1 OUT="$4" nice -n 19 bash "$HERE/run_matrix.sh"
  bash "$HERE/handoff/pack_results.sh" || echo "pack/push failed (will retry after the next step)"; }
step "1 axis_async_fifo aegis" "axis_async_fifo" "aegis" "$HERE/02_multiclock/results"
step "2 Exp 01 expansion" "drrtl_spi drrtl_pcie drrtl_dsp drrtl_router" "aegis drrtl" "$HERE/01_drrtl_suite/results"
step "3 RTL-OPT" "rtlopt_fsm rtlopt_fsm_encode rtlopt_gray rtlopt_mac rtlopt_mul rtlopt_ticket_machine" "aegis drrtl" "$HERE/04_rtlopt/results"
step "4 eth_mac_1g_fifo" "eth_mac_1g_fifo" "aegis drrtl" "$HERE/02_multiclock/results"
echo "### machine 2 round 2 done $(date '+%F %T')"
