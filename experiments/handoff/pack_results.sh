#!/usr/bin/env bash
# Pack every FINISHED run of machine 2 (summary.json present, validated) without proof scratch / netlists, one
# .tgz per run in experiments/handoff/results/, then commit and push them on branch results-machine2-r2.
# Safe to run repeatedly (e.g. after each finished run); existing archives are refreshed.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"; A="$HERE/../../aegis_agents"; OUT="$HERE/results"; mkdir -p "$OUT"
EVENT="$HERE/log_event.sh"
log() { bash "$EVENT" "$1" "${2-}" || true; }
log "Packing finished machine-2 results"
(cd "$A" && python3 bench/validate_runs.py --archive) || true
n=0
for s in "$A"/flow/runs/*/*.sonnet-5-5.r1/summary.json; do
  [ -f "$s" ] || continue
  run="$(dirname "$s")"; d="$(basename "$(dirname "$run")")"; rid="$(basename "$run")"
  tar -C "$A/flow/runs/$d" --exclude='*/eqy/*' --exclude='*/eqy_*' --exclude='*/final_eqy/*' --exclude='netlist.v' \
      --exclude='synth.json' --exclude='synth_raw.json' -czf "$OUT/${d}__${rid}.tgz" "$rid" "$rid.log" 2>/dev/null || \
  tar -C "$A/flow/runs/$d" --exclude='*/eqy/*' --exclude='*/eqy_*' --exclude='*/final_eqy/*' --exclude='netlist.v' \
      --exclude='synth.json' --exclude='synth_raw.json' -czf "$OUT/${d}__${rid}.tgz" "$rid"
  n=$((n+1))
done
echo "packed $n runs into $OUT"; du -sh "$OUT"
log "Packed $n finished run(s)"
cd "$HERE/../.."
git checkout -B results-machine2-r2 >/dev/null 2>&1 || true
git add experiments/handoff/results experiments/handoff/MACHINE2_NOTES.md experiments/01_drrtl_suite/results experiments/03_ablation 2>/dev/null || true
git commit -m "machine 2 results: $n runs ($(date '+%F %T'))" || echo "nothing new to commit"
git push -u origin results-machine2-r2 && log "Pushed results to results-machine2-r2" || {
  log "ABNORMAL: result push failed" "git push -u origin results-machine2-r2"
  exit 1
}
