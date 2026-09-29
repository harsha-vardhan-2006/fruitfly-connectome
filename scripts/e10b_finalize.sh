#!/usr/bin/env bash
# E10B finalizer: triggered automatically when the run reaches 100/100.
# Executes the FINAL_REPORT §7 finish-line procedure in order:
#   1. wait until all 100 nulls are in the CSV
#   2. run `stats` HERE (do not trust a pre-existing e10b_results.json,
#      which may be the stale 16-null artifact) and verify n==100
#   3. regenerate all figures (Fig6 upgrades to 100-null file)
#   4. full test suite
#   5. freeze copies into results/final/ + results/e10b/
#   6. write results/final/FINALIZE_DONE.stamp with timestamps
LOG=results/tables/e10b_run.log
cd "$(dirname "$0")/.." || exit 1

echo "[finalizer] re-armed (v2, race-hardened) $(date)" >> "$LOG"

# 1. Wait until every null is merged in the CSV (up to 12 h, 1-min cadence).
for i in $(seq 1 720); do
  N=$(($(wc -l < results/tables/e10b_nulls.csv) - 1))
  [ "$N" -ge 100 ] && break
  sleep 60
done

N=$(($(wc -l < results/tables/e10b_nulls.csv) - 1))
if [ "$N" -lt 100 ]; then
  echo "[finalizer] ABORT: CSV only has $N nulls after wait $(date)" >> "$LOG"
  exit 1
fi

# 2. Run stats HERE and require the 100-null result (supervisor also runs
#    stats; the second call is idempotent and overwrites the same file).
echo "[finalizer] running stats at N=$N $(date)" >> "$LOG"
py -m src.experiments.run_e10b stats >> "$LOG" 2>&1 \
  || { echo "[finalizer] ABORT: stats failed $(date)" >> "$LOG"; exit 1; }

VN=$(py -c "import json;print(json.load(open('results/tables/e10b_results.json'))['n_nulls_completed'])" 2>/dev/null)
if [ "$VN" != "100" ]; then
  echo "[finalizer] ABORT: stats reports n=$VN (expected 100) $(date)" >> "$LOG"
  exit 1
fi
echo "[finalizer] stats OK (n_nulls_completed=100) $(date)" >> "$LOG"

# 3. Figures (Fig6 auto-upgrades to the 100-null results file).
py -m src.experiments.run_e15_figures >> "$LOG" 2>&1 \
  && echo "[finalizer] figures OK" >> "$LOG" \
  || echo "[finalizer] figures FAILED" >> "$LOG"

# 4. Full test suite.
py -m pytest -q > results/tables/final_pytest.log 2>&1 \
  && echo "[finalizer] pytest OK" >> "$LOG" \
  || echo "[finalizer] pytest FAILED (see results/tables/final_pytest.log)" >> "$LOG"

# 5. Freeze canonical copies.
mkdir -p results/final results/e10b
cp results/tables/e10b_results.json results/final/e10b_final.json
cp results/tables/e10b_nulls.csv results/e10b/e10b_nulls.csv
cp results/tables/e10b_results.json results/e10b/e10b_results.json
cp results/tables/final_pytest.log results/e10b/ 2>/dev/null
echo "[finalizer] freeze OK $(date)" >> "$LOG"

# 6. Completion stamp.
{
  echo "FINALIZATION COMPLETE $(date)"
  echo "nulls=100"
  echo "stats verified n_nulls_completed=100 before freeze"
  echo "figures+tests+freeze executed; see $LOG for per-step status"
} > results/final/FINALIZE_DONE.stamp
echo "[finalizer] done $(date)" >> "$LOG"
