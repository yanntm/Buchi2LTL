# tests/

The home for **aut2ltl engine probes and unit tests** — everything that exercises
the `aut2ltl/` sources directly. (The corpora, the survey harness and the
committed reference runs live elsewhere: `samples/`, the `survey` package,
`results/`.)

## Discipline

- **Every probe is a placed script.** No `/tmp`, no `python -c` one-liners — a
  diagnostic worth running is worth committing (see `CLAUDE.md`).
- **Put it in a folder congruent to the module it tests:** a probe for
  `aut2ltl/<mod>` lives in `tests/probes/<mod>/`. See `probes/README.md` for the
  running convention in detail.
- **Run it from the repo root, as a module:**

      python3 -m tests.probes.<module>.<probe>

  e.g. `python3 -m tests.probes.heur.test_fuse2`. Running from root puts the
  working tree on `sys.path` (live sources, no `pip install`); there is no
  `sys.path` bootstrap in any probe, and a probe run by file path will fail to
  import.
- **Diagnostics are self-bound** (≤15s per example); a blown budget is a finding,
  not something to wait on.

## logs/

`tests/logs/` is a scratch area — write smoke output here freely. It is
**gitignored and never committed** (see `tests/.gitignore`).

## Gate

The correctness gate and the procedure to refresh the committed reference runs
are documented in **[`results/README.md`](../results/README.md)**: the survey over
`samples/validation` must end `SUCCESS`, and a reference refresh is rerun → diff →
overwrite. Run it from the root:

    python3 -m survey --folder samples/validation      # must end SUCCESS
