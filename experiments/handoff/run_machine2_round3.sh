#!/usr/bin/env bash
# Machine 2, ROUND 3 (2026-11-05): the remaining 10 of Dr. RTL's 20 designs (so the single-clock comparison covers
# Dr. RTL's FULL suite), x {aegis, drrtl}, smallest first. 20 runs, ~1-3 h each.
# Start it any time: it WAITS until round 2 has finished its RTL-OPT step, then stops round 2 BEFORE eth_mac_1g_fifo,
# runs these 20 runs, and then runs eth_mac_1g_fifo itself (round 2's step 4). Same settings as rounds 1-2.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"; LOG="$HERE/handoff/machine2_r2.out"
export MAX_PASSES=200 PARALLEL=1 JOBS=2
echo "### round 3 waiting for round 2 step 3 to finish $(date '+%F %T')"
until grep -q "### 4 eth_mac_1g_fifo\|### machine 2 round 2 done" "$LOG" 2>/dev/null || ! pgrep -f run_machine2_round2.sh >/dev/null; do sleep 120; done
pkill -f run_machine2_round2.sh; pkill -f run_matrix.sh; pkill -f bench/run_suite.py; pkill -f tools/aegis_run.py
pkill -f tools/drrtl_port.py; sleep 5; pkill -x yosys; pkill -f "yosys-smtbmc|bin/eqy|bin/sby"; sleep 2
# a partial eth_mac run dir (if round 2 had started it) is wiped automatically when the run restarts
step() { echo "### $1 $(date '+%F %T')"
  DESIGNS="$2" CONFIGS="$3" REPS=1 OUT="$4" nice -n 19 bash "$HERE/run_matrix.sh"
  bash "$HERE/handoff/pack_results.sh" || echo "pack/push failed (will retry after the next step)"; }
for d in drrtl_cpu_pipe drrtl_tv80 drrtl_arm_cpu2 drrtl_datapath drrtl_vending_machine drrtl_lstm drrtl_arm_cpu1 \
         drrtl_aes drrtl_cpu_fsm drrtl_fifo; do
  step "R3 Exp 01 full suite: $d" "$d" "aegis drrtl" "$HERE/01_drrtl_suite/results"
done
step "R3 eth_mac_1g_fifo" "eth_mac_1g_fifo" "aegis drrtl" "$HERE/02_multiclock/results"
echo "### machine 2 round 3 done $(date '+%F %T')"
