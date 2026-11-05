#!/usr/bin/env bash
# 2026-11-05: RTL-OPT (round 2, step 3) now runs on machine 1. This waits until round 2 reaches step 3 and stops just
# that step; round 2 then moves on to step 4, where round 3 takes over (remaining Dr. RTL designs, then eth_mac).
LOG="$(cd "$(dirname "$0")" && pwd)/machine2_r2.out"
until grep -q "### 3 RTL-OPT" "$LOG" 2>/dev/null; do sleep 60; done
sleep 5; pkill -f "run_matrix.sh"; pkill -f "bench/run_suite.py"; pkill -f "tools/aegis_run.py"; pkill -f "tools/drrtl_port.py"
sleep 3; pkill -x yosys; pkill -f "yosys-smtbmc|bin/eqy|bin/sby"
echo "skipped RTL-OPT step $(date '+%F %T')"
