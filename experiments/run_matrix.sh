#!/usr/bin/env bash
# Generic resumable driver: DESIGNS x CONFIGS x REPS, retrying after Claude usage-limit failures.
# usage: DESIGNS="a b" CONFIGS="x y" REPS=1 OUT=dir bash run_matrix.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; AEGIS="$HERE/../aegis_agents"; OUT="${OUT:-$HERE/results_matrix}"
export PATH="$HOME/.local/bin:$PATH"; MAX_PASSES="${MAX_PASSES:-200}"; REPS="${REPS:-1}"
mkdir -p "$OUT"; cd "$AEGIS"
for pass in $(seq 1 "$MAX_PASSES"); do
  echo "=== pass $pass $(date '+%F %T')"
  python3 bench/run_suite.py --designs $DESIGNS --configs $CONFIGS --reps "$REPS" \
      --parallel "${PARALLEL:-1}" --jobs "${JOBS:-2}" 2>&1 | tee -a "$OUT/run.log"
  missing=0
  for d in $DESIGNS; do for c in $CONFIGS; do for r in $(seq 1 "$REPS"); do
    [ -f "flow/runs/$d/$c.sonnet-5-5.r$r/summary.json" ] || missing=$((missing+1)); done; done; done
  echo "=== pass $pass: $missing runs missing"
  [ "$missing" -eq 0 ] && break
  if grep -qsi "session limit\|usage limit\|hour limit\|weekly limit\|hit your .*limit\|LLM backend unavailable" $(for d in $DESIGNS; do echo flow/runs/$d/*.log; done); then
    echo "=== usage limit hit; sleeping 20 min"; sleep 1200
  else
    echo "=== remaining failures are not usage-limit failures; stopping for a human to look"; break
  fi
done
echo "=== finished $(date '+%F %T')"
