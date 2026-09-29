#!/usr/bin/env bash
# E10B supervisor: keeps the canonical run alive until 100/100.
# - checks every 10 min; resumes `py -m src.experiments.run_e10b` if no python procs
# - stall detection: if log untouched >30 min while CSV < 100, kill and resume
# - on completion: runs final stats once
LOG=results/tables/e10b_run.log
CSV=results/tables/e10b_nulls.csv
cd "$(dirname "$0")/.." || exit 1
echo "[supervisor] started $(date)" >> "$LOG"
while true; do
  N=$(($(wc -l < "$CSV") - 1))
  if [ "$N" -ge 100 ]; then
    echo "[supervisor] COMPLETE 100/100 $(date)" >> "$LOG"
    py -m src.experiments.run_e10b stats >> "$LOG" 2>&1
    break
  fi
  PROC=$(tasklist 2>/dev/null | grep -ci python || true)
  FRESH=$(find "$LOG" -mmin -30 2>/dev/null | wc -l)
  if [ "$PROC" -eq 0 ] || [ "$FRESH" -eq 0 ]; then
    echo "[supervisor] dead/stalled at N=$N (procs=$PROC fresh=$FRESH) - resuming $(date)" >> "$LOG"
    if [ "$PROC" -gt 0 ]; then taskkill //F //IM python.exe >/dev/null 2>&1; sleep 10; fi
    nohup py -m src.experiments.run_e10b >> "$LOG" 2>&1 &
    sleep 120
  fi
  sleep 600
done
echo "[supervisor] exiting $(date)" >> "$LOG"
