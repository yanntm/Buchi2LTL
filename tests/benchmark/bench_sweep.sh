#!/usr/bin/env bash
#
# tests/benchmark/bench_sweep.sh — the portfolio bench: sweep the benchmark corpus
# (tests/benchmark/inputs) with the DEFAULT portfolio and with --use best, then
# diff the two by output size (tests/survey_diff.py). Pure reuse of the survey
# engine — survey.py routes each input (HOA by content -> --hoa; .ltl read one
# formula per line, # comments / blanks skipped) under a STRICT per-input budget,
# so a multiply-exponential blowup TIMES OUT as a finding, never hangs the sweep.
#
# .md files are documentation and are NOT collected. Discovery is by extension
# (.ltl / .hoa); content routing is survey.py's job.
#
# Usage:
#   tests/benchmark/bench_sweep.sh                      # whole corpus -> tests/benchmark/logs
#   tests/benchmark/bench_sweep.sh OUTDIR PATHS...      # subset (dirs/files) for dev
#   KR_SURVEY_TIMEOUT=8 tests/benchmark/bench_sweep.sh  # tighter per-input budget
#
# Logs in $OUTDIR: default.csv / best.csv (dense per-input), *.txt (summaries),
# *.sweep.log (per-input stderr trace). CSVs/logs are gitignored (throwaway).
set -u
cd "$(dirname "$0")/../.."   # project root

INPUTS="tests/benchmark/inputs"
OUTDIR="${1:-tests/benchmark/logs}"
[ "$#" -gt 0 ] && shift
ROOTS=("$@"); [ "${#ROOTS[@]}" -eq 0 ] && ROOTS=("$INPUTS")

mapfile -t FILES < <(find "${ROOTS[@]}" -type f \( -name '*.ltl' -o -name '*.hoa' \) | sort)
if [ "${#FILES[@]}" -eq 0 ]; then
  echo "no .ltl/.hoa inputs under: ${ROOTS[*]}" >&2
  exit 1
fi

mkdir -p "$OUTDIR"
TO="${KR_SURVEY_TIMEOUT:-15}"
echo "=== bench sweep -> $OUTDIR  (${#FILES[@]} files, default vs best, ${TO}s/input) ==="

for label in default best; do
  use_args=(); [ "$label" = best ] && use_args=(--use best)
  KR_SURVEY_TIMEOUT="$TO" KR_SURVEY_CSV="$OUTDIR/$label.csv" \
    python3 tests/survey.py "${use_args[@]}" "${FILES[@]}" \
    > "$OUTDIR/$label.txt" 2>"$OUTDIR/$label.sweep.log"
  echo "--- $label ---"; tail -4 "$OUTDIR/$label.txt"
done

echo
echo "=== default vs best (size delta) ==="
python3 tests/survey_diff.py "$OUTDIR/default.csv" "$OUTDIR/best.csv"
echo
echo "logs: $OUTDIR"
