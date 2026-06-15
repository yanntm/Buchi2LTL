#!/usr/bin/env bash
#
# tests/kinska_sweep.sh — run the front-end survey over the Kinská benchmark
# corpus (tests/samples/kinska) with the DEFAULT portfolio only, one flat log.
#
# This is the survey_sweep.sh idea narrowed to a single dataset and a single
# technique: no --use citations to compare, just the hand-tuned default over
# every Büchi automaton (HOA) and source LTL formula list found under the tree.
# Inputs are discovered by walking subfolders; survey.py routes each by content
# (an `HOA:` file -> --hoa as ONE input; a plain text file -> its lines as LTL
# formulas). Per input the per-phase budget is a STRICT 15s, enforced by
# survey.py via `timeout --signal=INT` so a runaway GAP is reaped, never leaked.
#
# We keep, in $OUTDIR:
#   kinska.csv    the dense per-input CSV (DAG/tree/equiv/...)
#   kinska.txt    the survey's own stdout report
#   SUMMARY.txt   the one-line roll-up (printed too) — read THAT at a glance.
#
# Usage:
#   tests/kinska_sweep.sh                              # full corpus -> reference dir
#   tests/kinska_sweep.sh tests/logs/kinska_quick PATHS...   # dev: throwaway dir, subset
#
# $1 is the output dir (default the committed reference dir); any remaining args
# are input paths (dirs or files) to RESTRICT the run to — for the slow-first
# develop-on-a-small-subset workflow. With no restriction the whole tree runs.
# The output dir is CLEARED of prior kinska.* logs before each run.
set -u
cd "$(dirname "$0")/.."   # project root

CORPUS="tests/samples/kinska"
OUTDIR="${1:-$CORPUS/logs/reference}"
[ "$#" -gt 0 ] && shift                 # remaining args (if any) restrict inputs
ROOTS=("$@"); [ "${#ROOTS[@]}" -eq 0 ] && ROOTS=("$CORPUS")

# Discover every regular input file under the requested roots (HOA automata and
# LTL formula lists alike — survey.py tells them apart by content). Prune the
# logs/ subtree: the output dir lives inside the corpus, so without this the
# sweep re-ingests its own kinska.txt/SUMMARY.txt and feeds them to the tool
# (spot then chokes with "ignoring trailing garbage").
mapfile -t FILES < <(find "${ROOTS[@]}" -type f -name '*.txt' -not -path '*/logs/*' | sort)
if [ "${#FILES[@]}" -eq 0 ]; then
  echo "no .txt inputs under: ${ROOTS[*]}" >&2
  exit 1
fi

mkdir -p "$OUTDIR"
rm -f "$OUTDIR"/kinska.csv "$OUTDIR"/kinska.txt "$OUTDIR"/SUMMARY.txt "$OUTDIR"/sweep.log

echo "=== kinska sweep -> $OUTDIR  (${#FILES[@]} inputs, default --use, ${KR_SURVEY_TIMEOUT:-15}s/run) ==="
# stdout (the compact summary) -> kinska.txt; stderr (per-input trace) -> sweep.log.
KR_SURVEY_CSV="$OUTDIR/kinska.csv" python3 tests/survey.py "${FILES[@]}" \
  > "$OUTDIR/kinska.txt" 2>"$OUTDIR/sweep.log"
cat "$OUTDIR/kinska.txt"

# One-line roll-up over the single CSV (same column convention as survey_sweep:
# 5 dag_nodes, 6 temporals, 9 build_s, 10 equiv; none is preceded by a
# comma-bearing field, so -F, is safe). answers = built (not declined / not a
# build problem); sums are over answers only.
summary="$OUTDIR/SUMMARY.txt"
csv="$OUTDIR/kinska.csv"
{
  printf "%-10s %5s %5s %5s %5s %5s %6s %5s %5s %9s %7s %8s\n" \
         corpus cases answ valid false decl bTO bCR unver DAGsum tempsum build
  if [ -f "$csv" ]; then
    awk -F, 'NR>1 {
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
        printf "%-10s %5d %5d %5d %5d %5d %6d %5d %5d %9d %7d %8.2f\n",
               "kinska", n, ans, v, f, d, bto, bcr, uv, dag, tmp, bld
      }' "$csv"
    false_n=$(awk -F, 'NR>1 && $10=="FALSE"{c++} END{print c+0}' "$csv")
    echo
    [ "$false_n" -gt 0 ] && echo "FAIL" || echo "SUCCESS"
  else
    echo "(no CSV produced)"
  fi
} | tee "$summary"

echo
echo "logs: $OUTDIR   summary: $summary"
