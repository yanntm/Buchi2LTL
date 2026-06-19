# kr.gap — the GAP/SgpDec bridge

Automaton in, Krohn–Rhodes **Cascade** out. This package is the one place where
kr shells out to [GAP](https://www.gap-system.org/) + the
[SgpDec](https://github.com/gap-packages/sgpdec) package to compute a holonomy
decomposition.

## API

The package exposes one job — decompose an automaton into a holonomy cascade:

```python
from aut2ltl.bls.gap import decompose_aut

casc = decompose_aut(aut, *, gap_cmd="gap", timeout=180, max_aps=5)  # -> Cascade
```

- **in** — a Spot automaton (HOA). It is normalized *here* to a deterministic,
  complete, minimized, state-based-acceptance parity automaton; that normalized
  `D` is the authoritative input for the rest of kr. The input must be
  normalizable to deterministic parity (always possible for ω-regular languages;
  otherwise `ExtractionError`).
- **out** — a `Cascade` (levels, configs, transitions, cover map). See
  `bls/cascade.py`.
- **config** — `timeout` (per GAP run, seconds), `gap_cmd`, `max_aps`.

Lower-level entry, skipping the Spot normalization to decompose an explicit list
of transformation images:

```python
from aut2ltl.bls.gap import decompose_gens
casc = decompose_gens(generators, *, gap_cmd="gap", timeout=180)  # -> Cascade
```

## Requirements & install

Needs GAP (≥ 4.12) with the SgpDec package on `PATH`. Install once with the
[`install_gap.sh`](../../../install_gap.sh) script at the project root (user-local
under `~/.gap/pkg`, no root needed):

```sh
./install_gap.sh            # install
./install_gap.sh --check-only
```

Probe availability from Python with `check_gap_available()`.

## Modules (one service each)

| module | role |
|---|---|
| `bridge.py` | pure orchestration — `decompose_aut`, `decompose_gens` |
| `export.py` | GAP-source generation — `generate_gap_script` |
| `runner.py` | process spawn — `run_gap_script`, `check_gap_available` |
| `parse.py` | structured-output parser → `Cascade` — `parse_cascade_output` |

The GAP + SgpDec installer ([`install_gap.sh`](../../../install_gap.sh)) lives at the
project root.

The generated GAP script prints an easy-to-parse structured block
(`CASCADE_START` / `KEY: value` / `STATE … CONFIG` / `TRANS` / `PI` lines), so
the Python side stays robust against SgpDec pretty-printer changes.
