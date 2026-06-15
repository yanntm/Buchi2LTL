#!/usr/bin/env bash
#
# tests/survey_sweep.sh — sweep the front-end survey across --use configurations,
# one log per configuration, at a single point in time.
#
# Each configuration is a distinct --use citation passed straight through to the
# tool (tests/survey.py -> python3 -m aut2ltl --use ...), so the sweep compares
# techniques/flags head-to-head on the same corpus. The log NAME is the citation
# itself: the comma-separated flags joined with '+' in CITED ORDER (so
# 'decompose,str' -> decompose+str), or 'default' for the no-citation portfolio.
# Per config we keep:
#   $OUTDIR/<name>.csv   the dense per-formula CSV (DAG/tree/equiv/...)
#   $OUTDIR/<name>.txt   the survey's own stdout report
# and finally a cross-config SUMMARY.txt (printed too) — read THAT at a glance.
#
# We test every main producer method (acc/weak/buchi/cobuchi/bls/str/sl) both
# bare AND under the decompose (strength) wrapper; sl_driven is its own method
# (the sl-driven core over the integrated cascade str), likewise with/without
# decompose. 'str' is the integrated default cascade (make_hierarchy_class).
#
# Day-to-day this writes a throwaway dir under tests/logs/ (gitignored). For a
# RELEASE reference, point it at the tracked reference dir so the CSVs are
# committed (see .gitignore re-include of tests/logs/reference/*.csv):
#
#   tests/survey_sweep.sh                         # full corpus, throwaway dir
#   tests/survey_sweep.sh tests/logs/reference    # the committed release reference
#   tests/survey_sweep.sh tests/logs/quick "Ga" "GFa & GFb"   # a few formulas, all configs
#
# A full sweep is slow (configs x corpus x per-phase budgets) — that is expected;
# it is a data-collection run, not a gate.
set -u
cd "$(dirname "$0")/.."   # project root

OUTDIR="${1:-tests/logs/sweep_$(date -u +%Y%m%d)}"
[ "$#" -gt 0 ] && shift   # remaining args (if any) are formulas for survey.py
FORMULAS=("$@")           # empty => the curated corpus
mkdir -p "$OUTDIR"

# The --use citations to sweep, in run order. Empty = the hand-tuned default.
# decompose is cited LEFT of the method (wraps it); cited order is preserved in
# both behaviour and the derived log name.
USES=(
  ""                              # default portfolio (no --use)
  "acc"             "decompose,acc"
  "weak"            "decompose,weak"
  "buchi"           "decompose,buchi"
  "cobuchi"         "decompose,cobuchi"
  "bls"             "decompose,bls"
  "str"             "decompose,str"
  "sl"              "decompose,sl"
  "sl_driven,str"   "decompose,sl_driven,str"
)

name_of() { [ -z "$1" ] && echo "default" || echo "${1//,/+}"; }

echo "=== survey sweep -> $OUTDIR  (${#USES[@]} configs) ==="
for use in "${USES[@]}"; do
  label="$(name_of "$use")"
  csv="$OUTDIR/$label.csv"
  rep="$OUTDIR/$label.txt"
  echo "--- $label  (--use ${use:-<default>}) ---"
  # stdout (the compact summary) -> per-config .txt; stderr (per-formula trace)
  # -> one aggregated sweep.log (a *.log, gitignored), so each .txt stays terse.
  if [ -n "$use" ]; then
    KR_SURVEY_CSV="$csv" python3 tests/survey.py --use "$use" "${FORMULAS[@]}" > "$rep" 2>>"$OUTDIR/sweep.log"
  else
    KR_SURVEY_CSV="$csv" python3 tests/survey.py "${FORMULAS[@]}" > "$rep" 2>>"$OUTDIR/sweep.log"
  fi
  cat "$rep"
done

# Dense cross-config summary. equiv is CSV column 9, dag_nodes column 5; neither
# is preceded by a comma-bearing field, so -F, is safe here.
summary="$OUTDIR/SUMMARY.txt"
{
  # CSV columns: 5 dag_nodes, 6 temporals, 9 build_s, 10 equiv (none preceded by
  # a comma-bearing field, so -F, is safe). answers = built (not declined / not a
  # build problem); totals are over answers only.
  printf "%-26s %5s %5s %5s %5s %5s %6s %5s %5s %9s %7s %8s\n" \
         config cases answ valid false decl bTO bCR unver DAGsum tempsum build
  total_false=0
  for use in "${USES[@]}"; do
    label="$(name_of "$use")"
    csv="$OUTDIR/$label.csv"
    [ -f "$csv" ] || continue
    line=$(awk -F, 'NR>1 {
        n++; e=$10;
        if      (e=="True")            v++;
        else if (e=="FALSE")           f++;
        else if (e=="UNVERIFIED_SIZE") uv++;
        else if (e=="DECLINED")        d++;
        else if (e ~ /^BUILD_TIMEOUT/) bto++;
        else if (e ~ /^CRASH/)         bcr++;
        if (e=="True"||e=="FALSE"||e=="SPOT_TIMEOUT"||e=="UNVERIFIED_SIZE"||e ~ /^SPOT_ERR/) {
          ans++;
          if ($5 ~ /^[0-9]+$/)   dag+=$5;
          if ($6 ~ /^[0-9]+$/)   tmp+=$6;
          if ($9 ~ /^[0-9.]+$/)  bld+=$9;
        }
      } END {
        printf "%-26s %5d %5d %5d %5d %5d %6d %5d %5d %9d %7d %8.2f %d",
               L, n, ans, v, f, d, bto, bcr, uv, dag, tmp, bld, f
      }' L="$label" "$csv")
    f_count="${line##* }"
    printf "%s\n" "${line% *}"
    total_false=$((total_false + f_count))
  done
  echo
  [ "$total_false" -gt 0 ] && echo "FAIL" || echo "SUCCESS"
} | tee "$summary"

echo
echo "logs: $OUTDIR   summary: $summary"
