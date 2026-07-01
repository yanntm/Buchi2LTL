# Tracing the in-proc vs out-of-proc spot-translate divergence

> Untracked working note (like the scratch logs) — scratchpad for an open trace,
> not a committed artifact.

## Context

`aut2ltl/spotrun/translate` is the single seam that turns a formula into an
automaton. It has two backends (see `aut2ltl/spotrun/__init__.py`):

- **in-process** `f.translate()` — the Spot Python binding, unbounded;
- **out-of-process** — the same binding run in a killable child via `_child.py`
  (NOT the `ltl2tgba` CLI), under a wall-time budget, so one runaway node degrades
  that node, not the whole build.

Which backend runs is policy, controlled by env knobs:

| knob (OptionSpec) | default | effect |
|---|---|---|
| `KR_TRANSLATE_TIMEOUT` (`spotrun.translate_timeout`) | 3 | `0` ⇒ **in-proc always**, unbounded |
| `KR_TRANSLATE_INPROC_TREE_LIMIT` (`spotrun.inproc_tree_limit`) | 100 | flat size ≤ this ⇒ in-proc; low (≤3) ⇒ force out-of-proc |
| `KR_TRANSLATE_INPROC_TEMPORAL_LIMIT` (`spotrun.inproc_temporal_limit`) | 16 | temporal count ≤ this ⇒ in-proc; `0` ⇒ disable fast path ⇒ force out-of-proc |

**The finding.** The two backends translate the *same* formula but can return
*equivalent-but-not-identical* automata ("Soundness rests on equivalence, not
identity" — `translate` docstring). The reconstruction faithfully reflects the
automaton it is handed, so the in-proc and out-of-proc runs can yield **different
LTL formulas** (and different sizes) for the same input. This note isolates the
smallest such divergences, to trace where the two automata differ and whether it
is worth pinning the backend.

Both settings are **sound** (every output validated TRUE; the survey diff reports
`0 FAIL, 0 CLASH`). This is a size/shape divergence, not a correctness bug.

## The two A/B settings

- **A — in-proc, unbounded**: `KR_TRANSLATE_TIMEOUT=0`
- **B — forced out-of-proc, 3 s child**: `KR_TRANSLATE_INPROC_TEMPORAL_LIMIT=0`
  (equivalently `KR_TRANSLATE_INPROC_TREE_LIMIT=3`)

Default recipe, benchmark corpus. Across 334 inputs the two agree everywhere
except **2 both-resolve cases** (the rest of the gap is 10 counting-automaton
timeouts that only B hits, under its 3 s child).

## Example 1 — term030 (the clean one) — trace this first

Input: `X(a | FG(!b | X(!b M !c)))`
(`samples/benchmark/inputs/fixtures/terminal_2scc.ltl:30`)

| setting | DAG | tree | technique | build |
|---|---|---|---|---|
| A in-proc | 22 | 38 | `acc2+daisy+daisy2+daisystardet+deep_roundtrip+partscc+strength2` | 0.2 s |
| B out-of-proc | 23 | 39 | *same* | 1.4 s |

```
A: X(a | (GF!b & F((!b & X(!b & XG(!b | X!c))) | (b & X(!c & G(!b | X!c))))))
B: X(a | X(GF!b & F((!b & X(!b & XG(!b | X!c))) | (b & X(!c & G(!b | X!c))))))
```

**Identical technique stack**, a single-node delta (the extra leading `X` inside
the disjunction). Nothing downstream differs, so the divergence is *entirely* in
the `translate` seam — the ideal case to diff the two automata directly.

```bash
KR_TRANSLATE_TIMEOUT=0                python3 -m aut2ltl --ltl 'X(a | FG(!b | X(!b M !c)))'
KR_TRANSLATE_INPROC_TEMPORAL_LIMIT=0  python3 -m aut2ltl --ltl 'X(a | FG(!b | X(!b M !c)))'
# stats are on stderr, formula on stdout:  ... 2>&1 1>/dev/null   to see only the report
```

## Example 2 — term036 (the amplified one)

Input: `GF((a & Xb) | (!a & X!b))`
(`samples/benchmark/inputs/fixtures/terminal_2scc.ltl:36`)

| setting | DAG | tree | technique | build |
|---|---|---|---|---|
| A in-proc | 77 | 1088 | `buchi+daisy+daisystardet+deep_roundtrip+inv+strength2` | 1.9 s |
| B out-of-proc | 99 | 1318 | `…+inv+`**`scc2`**`+strength2` | 13.1 s |

A tiny input where the different automaton sends the build down a **different
decomposition path** (B picks up `scc2`), so the divergence compounds and build
nears the 15 s wall. Shows how a small backend difference amplifies through the
portfolio.

```bash
KR_TRANSLATE_TIMEOUT=0                python3 -m aut2ltl --ltl 'GF((a & Xb) | (!a & X!b))'
KR_TRANSLATE_INPROC_TEMPORAL_LIMIT=0  python3 -m aut2ltl --ltl 'GF((a & Xb) | (!a & X!b))'
```

## How the examples were found — the probe

`tests/probes/smallest_size_diff.py` (committed) finds the **smallest** input on
which two survey runs both produce an LTL formula but of *different* size — i.e. a
traceable divergence, not a timeout/decline gap. Keyed on `source`; keeps only rows
where both sides are `result==LTL` with a numeric, differing `dag`; sorts by
`max(dagL, dagR)` ascending so the smallest divergence is first; prints source, the
dag pair, and both formulas.

```bash
# regenerate the A/B runs (default recipe, benchmark) into scratch logs/
mkdir -p logs/inproc_cmp/A logs/inproc_cmp/B
KR_TRANSLATE_TIMEOUT=0               python3 -m survey --folder samples/benchmark --logs logs/inproc_cmp/A
KR_TRANSLATE_INPROC_TEMPORAL_LIMIT=0 python3 -m survey --folder samples/benchmark --logs logs/inproc_cmp/B

# the two views
python3 -m survey.diff.results            logs/inproc_cmp/A/survey_*.csv logs/inproc_cmp/B/survey_*.csv
python3 -m tests.probes.smallest_size_diff logs/inproc_cmp/A/survey_*.csv logs/inproc_cmp/B/survey_*.csv --limit 8
```

The runs used for this note live (untracked) under `logs/inproc_cmp/inproc` (A) and
`logs/default_cmp/t0` (B).

## Open question

Trace term030's two automata side by side (the in-proc and the child output for the
relevant sub-language) to see exactly where they differ, then decide whether
`translate` should canonicalise (e.g. a fixed post-pass) so the reconstruction is
backend-stable — vs accepting the divergence as benign (both sound, ~1 node).

## Session log — tracing the divergence to a brick (not a cache)

Reproduce the A/B divergence and the diagnostics run this session. All output
goes under `logs/trace_inproc/` (never /tmp). Global trace knob is
`TRANSLATOR_TRACE_ON=1` (lights every brick's trace at once).

```bash
D=logs/trace_inproc; mkdir -p "$D"; F='X(a | FG(!b | X(!b M !c)))'
# A = in-proc, B = out-of-proc (tree-limit form; NOT temporal=0, that disables the limit)
TRANSLATOR_TRACE_ON=1 KR_TRANSLATE_TIMEOUT=0           python3 -m aut2ltl --ltl "$F" >"$D/hA.out" 2>"$D/hA.trace"
TRANSLATOR_TRACE_ON=1 KR_TRANSLATE_INPROC_TREE_LIMIT=3 python3 -m aut2ltl --ltl "$F" >"$D/hB.out" 2>"$D/hB.trace"
grep LTL: "$D/hA.out" "$D/hB.out"        # A: no leading X (dag 19) ; B: leading X (dag 20)
diff "$D/hA.trace" "$D/hB.trace" | head -1   # first divergence: best_of:deep_nobls_arm out
```

**Cache bypasses (all env-gated probes added this session) — none changed the
result, so no toggleable cache is responsible:**

```bash
DEEP_ROUNDTRIP_NOMEMO=1 …   # deep_roundtrip per-call node dict off
MEMO_NOMEMO=1 …             # Language-keyed Memo off
KR_SIMP_NODE=0 …            # _simp_memo / per-node simplify off (both forms get uglier, still diverge)
```

**Proof the two backends produce the SAME automaton (id trace + HOA dump):**

```bash
# [language.of]/[language.of_ltl] id lines (added to aut2ltl/language.py)
diff <(grep '\[language.of\] '  "$D/hA.trace") <(grep '\[language.of\] '  "$D/hB.trace")  # empty: all of() ids identical
# dump the pulled twa by normalized id, then find same-content / different-id files
AUT2LTL_TRACE_VERBOSITY=full AUT2LTL_TRACE_DIR="$D/dump" TRANSLATOR_TRACE_ON=1 KR_TRANSLATE_TIMEOUT=0 python3 -m aut2ltl --ltl "$F" -q
for f in "$D"/dump/*.hoa; do printf '%s  %s\n' "$(md5sum <"$f"|cut -d" " -f1)" "$(basename "$f")"; done \
  | sort | awk '{h[$1]=h[$1]" "$2} END{for(k in h){n=split(h[k],a," "); if(n>1) print h[k]}}'
# -> the Xfree formula id (4df61…) and Xpref formula id (89cfd…) share HOA content 6eb59…
```

Findings: technique stack is identical (`acc2+daisy+daisy2+daisystardet+deep_roundtrip+partscc+strength2`,
**no bls/buchi**); the automata are identical; the `X` is introduced by a brick's
read-off, not a cache. Root cause not yet pinned — the trace was **incomplete**
(some bricks did not print in/out), which is the current blocker.

## Proper instrumentation — daisystar as the template

`daisystar` was the caught example: it traced only delegations + the gate, and
was **silent on `in` and every `out`** (including the success path that builds a
`LEAVE` form full of `X φ` exit terms). Fixed to match the `daisy` pattern — see
the daisystar commit right after this note landed:

- `[<name>] in ` + `format_language(lang, aut)` at entry;
- an `_out(res)` wrapper printing `[<name>] out ` + `format_result(res)`, applied
  to **every** return (declined paths and the success path alike);
- delegation lines kept.

Every translator brick should follow this: on `TRANSLATOR_TRACE_ON`, print start
(input language), output (LTL result), and sensitive points (delegations). The
remaining bricks (`daisy2`, `daisystardet`, `partscc`, `inv`, `strength`, `scc`,
`acceptance`) still need the same audit.
