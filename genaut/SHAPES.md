# genaut shapes — the bestiary map

The shapes the census enumerates, and the tractability wall. A **shape** is
`Shape(n, k, c)` — `n` states, `k` atomic propositions, `c` acceptance sets (see
[`gen/algorithm.md`](gen/algorithm.md)). Each shape's generator-id space is

```
slots = n² · 2^c                       (one edge slot per (src, dst, markset))
N     = (2^(2^k)) ^ slots              (guards = all Boolean functions over k APs)
```

`N` is **doubly exponential in `k`**, exponential in `n²` and `2^c`, so exhaustive
enumeration only reaches small shapes. Rule of thumb: `N ≲ 3·10⁵` enumerates in
seconds to ~a minute; beyond that it is out of reach. Each row below is a one-off
census, written to `corpus/<tag>/` with a `census.md` (regenerable via
`python3 genaut/gen/enumerate.py n,k,c`).

## Feasible shapes (measured)

`kept` = distinct automata after both dedup gates (md5, then polarity∘names);
`polarity` = relabel twins folded by the second gate.

| shape | n | k | c | slots | N (combos) | byte-distinct | polarity | **kept** | status |
|---|---|---|---|---|---|---|---|---|---|
| `1state0ap0acc` | 1 | 0 | 0 | 1 | 2 | 2 | 0 | **2** | |
| `1state0ap1acc` | 1 | 0 | 1 | 2 | 4 | 2 | 0 | **2** | |
| `1state1ap0acc` | 1 | 1 | 0 | 1 | 4 | 4 | 1 | **3** | committed |
| `2state0ap0acc` | 2 | 0 | 0 | 4 | 16 | 3 | 0 | **3** | |
| `1state1ap1acc` | 1 | 1 | 1 | 2 | 16 | 7 | 2 | **5** | |
| `1state2ap0acc` | 1 | 2 | 0 | 1 | 16 | 16 | 10 | **6** | |
| `1state1ap2acc` | 1 | 1 | 2 | 4 | 256 | 10 | 3 | **7** | |
| `2state0ap1acc` | 2 | 0 | 1 | 8 | 256 | 6 | 0 | **6** | |
| `1state2ap1acc` | 1 | 2 | 1 | 2 | 256 | 77 | 52 | **25** | |
| `2state1ap0acc` | 2 | 1 | 0 | 4 | 256 | 53 | 23 | **30** | |
| `1state3ap0acc` | 1 | 3 | 0 | 1 | 256 | 256 | 204 | **52** | |
| `3state0ap0acc` | 3 | 0 | 0 | 9 | 512 | 3 | 0 | **3** | |
| `1state1ap3acc` | 1 | 1 | 3 | 8 | 65536 | 10 | 3 | **7** | |
| `4state0ap0acc` | 4 | 0 | 0 | 16 | 65536 | 3 | 0 | **3** | |
| `2state0ap2acc` | 2 | 0 | 2 | 16 | 65536 | 91 | 0 | **91** | |
| `1state2ap2acc` | 1 | 2 | 2 | 4 | 65536 | 272 | 189 | **83** | |
| `2state1ap1acc` | 2 | 1 | 1 | 8 | 65536 | 1845 | 916 | **929** | committed |
| `1state3ap1acc` | 1 | 3 | 1 | 2 | 65536 | 6553 | 5041 | **1512** | |
| `2state2ap0acc` | 2 | 2 | 0 | 4 | 65536 | 30613 | 19071 | **11542** | |
| `3state0ap1acc` | 3 | 0 | 1 | 18 | 262144 | 281 | 0 | **281** | |
| `3state1ap0acc` | 3 | 1 | 0 | 9 | 262144 | 7908 | 3875 | **4033** | |

## Beyond the wall (first intractable)

| shape | N | why |
|---|---|---|
| `2state2ap1acc` | 16⁸ ≈ 4.3·10⁹ | the true k=2 analog of 2state1ap1acc |
| `1state2ap3acc` | 16⁸ ≈ 4.3·10⁹ | |
| `1state3ap2acc` | 256⁴ ≈ 4.3·10⁹ | |
| `3state2ap0acc` | 16⁹ ≈ 6.9·10¹⁰ | |
| `3state1ap1acc` | 4¹⁸ ≈ 6.9·10¹⁰ | 3-state with both an AP and acceptance |

## Reading the numbers

- **0-AP shapes never fold by polarity** (no literals to flip; the AP-rename is
  trivial), and they collapse hardest of all: over a one-letter alphabet a
  language is fixed by its accepting structure alone, so `2state0ap0acc`,
  `3state0ap0acc`, `4state0ap0acc` all keep just **3** (∅, universal, and one
  middle form). Adding states does almost nothing there.
- **`k` drives the polarity fold**: the relabel group is `2^k · k!`, so the fold
  grows fast with APs — `1state3ap0acc` folds 204 of 256, `2state2ap0acc` folds
  19071 of 30613.
- **`c` (acceptance) inflates `slots` (×2 per set)** but the kept count stays
  modest at 1 state (`1state1ap3acc` keeps only 7 from 65536) — most marksets
  reduce away under Spot.
- **Generation is cheap; surveying is not.** Building a shape is seconds; running
  `aut2ltl` over its `kept` automata (the survey) scales with `kept` — `2/1/1`'s
  929 take ~26 min, so the high-`kept` shapes (`2state2ap0acc` 11542,
  `3state1ap0acc` 4033) are heavy to survey and should be done selectively.
