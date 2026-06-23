# aut2ltl

`aut2ltl` reconstructs a Linear Temporal Logic (LTL) formula from an
[ω-automaton](https://en.wikipedia.org/wiki/%CF%89-automaton). Given an automaton in
the [HOA format](https://adl.github.io/hoaf/), it produces an LTL formula defining the
same ω-language, or determines that the language is not LTL-definable. An LTL or PSL
formula may be supplied in place of an automaton, in which case it is translated to an
automaton before reconstruction.

## Quick start

Three dependencies must be installed at system level (they are *not* pip-installable):

- **Python 3**
- **[Spot](https://spot.lre.epita.fr/)** with its `spot` / `buddy` Python bindings
- **[GAP](https://www.gap-system.org/) 4.12+** with the **SgpDec** package — run
  [`install_gap.sh`](install_gap.sh) once to set it up user-locally (`~/.gap/pkg`)

Then install the package itself:

```bash
pip install -e .          # provides `python3 -m aut2ltl` and the `aut2ltl` console script
```

### Example

A **round trip**, LTL → automaton → LTL. Take `F(X!a & ((b R a) W b))` and let Spot
build its TGBA
([`samples/fixtures/hoa/various/collapse_example.hoa`](samples/fixtures/hoa/various/collapse_example.hoa)):

<p align="center"><img src="docs/img/collapse_example.png" alt="the TGBA of F(X!a & ((b R a) W b))" width="320"></p>

`aut2ltl` reads a defining formula back off the automaton:

```console
$ python3 -m aut2ltl samples/fixtures/hoa/various/collapse_example.hoa
technique : daisy+daisystardet
DAG nodes : 6
temporals : 1
tree nodes: 6
sharing   : 1.0x
build time: 0.002s
F(b & X!a)
```

`F(b & X!a)` is far smaller than the formula we started from — and no LTL
*simplifier* closes that gap: `ltlfilt` leaves `F(X!a & ((b R a) W b))` untouched at
every level, up to its strongest `-r3`. Minimal LTL simplification is as hard as LTL
equivalence (PSPACE-complete), so syntactic rewriters are necessarily incomplete;
`aut2ltl` reaches the simpler form by passing through the automaton — the semantic
object — and reconstructing LTL from it.

A second round trip, `GFa & FGb`
([`samples/fixtures/hoa/various/fairness_example.hoa`](samples/fixtures/hoa/various/fairness_example.hoa)),
exercises the **acceptance handling**: recovering this fairness pattern means reading
the Büchi acceptance back as `GF`/`FG`, not just the transition structure.

<p align="center"><img src="docs/img/fairness_example.png" alt="the TGBA of GFa & FGb" width="240"></p>

```console
$ python3 -m aut2ltl samples/fixtures/hoa/various/fairness_example.hoa
technique : acc2+daisy
DAG nodes : 7
temporals : 4
tree nodes: 7
sharing   : 1.0x
build time: 0.002s
G(Fa & FGb)
```

The **formula** is printed on stdout; the **report** above it (the methods used, the
formula's size, build time) goes to stderr. In a pipeline you therefore receive only
the formula:

```bash
python3 -m aut2ltl samples/fixtures/hoa/various/collapse_example.hoa -q | ltlfilt --simplify
```

[`genaut/`](genaut/) is an exhaustive generator of small ω-automata of a fixed
shape, run through `aut2ltl`. Its committed results — CSV,
[`SUMMARY.txt`](genaut/logs/SUMMARY.txt), and a
[`frontier.pdf`](genaut/logs/frontier.pdf) report — are in
[`genaut/logs/`](genaut/logs/).

## Using it

The input is auto-detected as a HOA file or an LTL/PSL formula; force it with
`--ltl` / `--hoa`.

```bash
python3 -m aut2ltl 'G(p -> (q U r))'           # an LTL/PSL formula in
python3 -m aut2ltl model.hoa                    # a HOA automaton file in
python3 -m aut2ltl model.hoa -q -o out.ltl      # -q: formula only; -o: to a file
python3 -m aut2ltl model.hoa --list-options     # every -O knob, its default and doc
python3 -m aut2ltl --help
```

The reconstructed formula is a **hash-consed DAG**: it shares repeated sub-formulas,
and successful outputs are often highly tail-redundant, so the DAG stays compact even
when the flat string is large. By default a large formula is printed only up to a
size gate (raise it with `--flatten-limit N`), or export the DAG itself:

```bash
python3 -m aut2ltl model.hoa --dag | dot -Tpng -o dag.png
```

Fine-tune any declared option with `-O key=value` (see `--list-options`).

## Evaluation

Reference runs of the **default** portfolio are committed as per-formula CSVs —
which GitHub renders as readable tables — one per corpus, under `results/reference/`:

- [`results/reference/validation/default.csv`](results/reference/validation/default.csv) —
  the curated 40-formula validation survey (the correctness gate's corpus), run both
  as LTL and as the equivalent HOA automaton (80 inputs).
- [`results/reference/benchmark/default.csv`](results/reference/benchmark/default.csv)
  — the larger benchmark corpus (the survey set + scalable W/U/R chains + the Kinská
  automata, 333 inputs).
- [`results/reference/kinska/kinska.csv`](results/reference/kinska/kinska.csv)
  — the 165 Kinská Büchi automata on their own (many are not LTL-definable); see
  [`samples/kinska/README.md`](samples/kinska/README.md) for provenance.

Each folder also holds a one-glance **summary** of its CSV —
[`results/reference/benchmark/SUMMARY.txt`](results/reference/benchmark/SUMMARY.txt):
how many answers were verified equivalent / not-LTL / timed out, and the total
reconstructed formula size.

## Project structure

`aut2ltl` is a **portfolio**: most modules are *translators* (a `Language` in, an
LTL result out) and the portfolio composes them, taking the best answer at each step.

```
aut2ltl/
  language.py     the input wrapper: cached, cleaned, language-equivalent automaton views
  result.py       LTLResult — a formula (DAG) or a decline, plus which methods contributed
  __main__.py     the command-line front end  (python3 -m aut2ltl)
  bls/            the systematic construction (Krohn-Rhodes cascade; see bls/README.md)
  daisy/          the self-loop "daisy" peel — a pure local translator
  decomp/         (de)composition approaches, one isolated subpackage each:
                  scc / strength / acceptance / inv
  partscc/        the single-terminal-SCC leaf translator
  ltl/            LTL primitives, metrics, printers, simplifiers
  portfolio/      the combinators that assemble the translators
survey/           the survey harness (the correctness gate) + diff / ltl2hoa tools
samples/          input corpora (validation = the gate, benchmark, kinska, fixtures)
results/          committed reference survey runs (results/reference/<corpus>/)
tests/            probes and per-engine unit tests
docs/             algorithm notes, the construction log, figures
```

## Scope

Translating an ω-automaton to LTL is expensive — the construction is exponential in
several directions — and not always possible, since ω-automata are strictly more
expressive than LTL. `aut2ltl` is **sound** (it never returns a non-equivalent
formula) and **complete** on the LTL-definable fragment (it reconstructs a defining
formula whenever one exists), at the cost of a possibly exponential blow-up in formula
size. When the input language lies outside LTL it **decides** so and reports it — to
our knowledge, `aut2ltl` is among the first tools to actually decide LTL-definability
in practice.

## Algorithms

The systematic core follows Boker, Lehtinen & Sickert, *"On the Translation of
Automata to Linear Temporal Logic"* (FoSSaCS 2022), via a Krohn-Rhodes holonomy
cascade decomposition (SgpDec + GAP) — to our knowledge the first practical
implementation of that construction. It is complemented by a portfolio of additional,
mostly original methods that handle structured fragments directly.

> This material is **unpublished**. Please give us time to write the paper before
> building on this prototype. Feedback and collaboration are very welcome —
> contact **Yann.Thierry-Mieg@lip6.fr** or open a GitHub issue. As a last resort,
> cite this repository.

## License

Distributed under the **GNU General Public License v3.0** (see [`LICENSE`](LICENSE)).

© 2026 Yann Thierry-Mieg, LIP6, Sorbonne Université, CNRS.
