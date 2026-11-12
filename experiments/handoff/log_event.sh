#!/usr/bin/env bash
# Append one factual, timestamped machine-2 event to the durable handoff log.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/MACHINE2_NOTES.md"
mkdir -p "$HERE"
if [ ! -f "$LOG" ]; then
  printf '# Machine 2 notes\n\n' > "$LOG"
fi
{
  printf '\n## %s\n\n' "$(date '+%Y-%m-%d %H:%M:%S %z')"
  printf '%s\n' "${1:?event is required}"
  if [ "$#" -ge 2 ] && [ -n "$2" ]; then
    printf '\n```\n%s\n```\n' "$2"
  fi
} >> "$LOG"
