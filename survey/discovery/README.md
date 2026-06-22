# survey/discovery — folders → runnable examples

Turn the `--folder` paths into the `Example`s the rest of survey runs. Three
small stages, composed by `discover()`: **walk** the paths into candidate files,
**detect** what each is (or skip it), **read** it into one or more `Example`s.
Unreadable / unrecognized files are silently skipped.

Importable as a module path:

    from survey.discovery import discover
    for ex in discover([Path("samples/kinska")]):
        ...   # each ex is an Example: a HOA automaton, or one LTL formula

## Stages

- **`walk.py`** — recurse each path (a file is yielded as-is, a directory is
  descended in sorted/deterministic order); prune `logs/`, `__pycache__/` and
  hidden dirs. Pure filesystem — no format knowledge.
- **`detect.py`** — classify a candidate by content: a first non-blank line of
  `HOA:` → `"hoa"` (whatever the extension); else a `.ltl`/`.txt` file → `"ltl"`;
  otherwise skip. No technique knowledge.
- **`read.py`** — materialise `Example`s: a HOA file → one Example; an LTL list →
  one per non-blank, non-comment line. Each carries `source` provenance — `file`
  for a HOA, `file:line` for an LTL line.
- **`scan.py`** — composes the three into `discover(paths)`, the package entry.

Run from the repo root (so `import survey.discovery` resolves).
