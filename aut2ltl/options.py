"""
aut2ltl/options.py — Options: the flags compartment of the runtime context.

An open key-value store for configuration flags (mostly bool, some int limits),
threaded EXPLICITLY through construction — never a singleton, never module state.
This is the contract FLOOR: it defines the store and the spec and imports no
engine. Each PACKAGE declares the keys it reads as `OptionSpec`s in its own
`<pkg>/options.py` (its OPTIONS contract); the ROOT / front end aggregates those
declarations and layers env/CLI/API overrides to build the default `Options`.

Defaults live in the `OptionSpec`, not in the store: `Options.get(SPEC)` resolves
lazily — the stored value if set, else `spec.default`. So the store holds only
OVERRIDES, a bare `Options()` behaves as "everything at its declared default",
and a call site reads like documentation:

    if options.get(bls.options.FOLD_FIN_REACH):   # store value, else spec.default
        ...

Keys are dotted and package-owned (`bls.fold_fin_reach`, `portfolio.gate.verify`)
so the open store stays collision-free and self-documenting. `OptionSpec.env` is
the migration bridge: seeding from the legacy env var reproduces today's behaviour
while the `os.environ` call sites are repointed to `options.get(SPEC)` one package
at a time.

Caches and shared infra (`bdd_dict` / DAG unifier) are SEPARATE compartments,
added in later iterations; this module is flags only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Union


@dataclass(frozen=True)
class OptionSpec:
    """One declared option — the single source of its default and its doc.

    `key`     dotted, package-owned (e.g. "bls.fold_fin_reach").
    `default` the native value (bool/int/...); also fixes the coercion type when
              seeding from a string env var.
    `doc`     one line: what this option controls (the contract).
    `env`     the legacy env var that seeds it (migration bridge), or None.
    """

    key: str
    default: Any
    doc: str
    env: Optional[str] = None


def _coerce(value: str, like: Any) -> Any:
    """Coerce an env string to the native type of `like` (the spec default).
    Bool follows the codebase convention: anything but "0" is True."""
    if isinstance(like, bool):
        return value != "0"
    if isinstance(like, int):
        try:
            return int(value)
        except ValueError:
            return like
    return value


class Options:
    """The flags compartment: an open key-value store, threaded explicitly.

    Mutable during setup (build it from specs + env + CLI/API overrides), then
    read-only by convention at run time (translators only `.get`). `clone` makes a
    configuration variant (the A/B move). Holds only flags.
    """

    def __init__(self, values: Optional[Dict[str, Any]] = None) -> None:
        self._values: Dict[str, Any] = dict(values or {})

    # --- reads (lazy default via the spec) ---
    def get(self, key: Union[str, OptionSpec], default: Any = None) -> Any:
        """Resolve a flag. Given an `OptionSpec`, the fallback is `spec.default`
        (so the store need only hold overrides); given a bare key, `default`."""
        if isinstance(key, OptionSpec):
            return self._values.get(key.key, key.default)
        return self._values.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __contains__(self, key: str) -> bool:
        return key in self._values

    # --- writes (setup / variants) ---
    def set(self, key: str, value: Any) -> "Options":
        """Set an override (chainable). Read-only by convention after setup."""
        self._values[key] = value
        return self

    def clone(self, overrides: Optional[Dict[str, Any]] = None) -> "Options":
        """A configuration variant: copy the flags, apply `overrides`."""
        values = dict(self._values)
        if overrides:
            values.update(overrides)
        return Options(values)

    # --- construction from declared specs ---
    @classmethod
    def from_specs(
        cls,
        specs: Iterable["OptionSpec"],
        *,
        env: bool = True,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> "Options":
        """Seed overrides from the declared specs: for each spec whose env var is
        set (when `env`), store the coerced value; then apply explicit `overrides`.
        Unset flags are NOT stored — they resolve to `spec.default` via `get`."""
        values: Dict[str, Any] = {}
        for spec in specs:
            if env and spec.env is not None:
                raw = os.environ.get(spec.env)
                if raw is not None:
                    values[spec.key] = _coerce(raw, spec.default)
        if overrides:
            values.update(overrides)
        return cls(values)

    # --- introspection (opt-in; reads stay pure) ---
    def effective(self, specs: Iterable["OptionSpec"]) -> Dict[str, Any]:
        """The full effective config over `specs` (override-or-default per key) —
        for `--help` / logging "what config ran". Does not mutate the store."""
        return {spec.key: self.get(spec) for spec in specs}

    def as_dict(self) -> Dict[str, Any]:
        """The stored overrides (not the resolved defaults)."""
        return dict(self._values)

    def __repr__(self) -> str:
        return f"Options({self._values!r})"


# --- the root package's own declared options (no subpackage owns these) ---
# Front-end output concerns that belong to aut2ltl itself rather than to bls /
# language / portfolio.

MD5_LENGTH = OptionSpec(
    "aut2ltl.md5_length", 12,
    "hex-char length of the --dagmd5 DAG fingerprint (1..32); raise it for a huge "
    "corpus where 12 hex (48 bits) is no longer collision-comfortable",
    env="AUT2LTL_MD5_LENGTH")

ROOT_OPTIONS = [MD5_LENGTH]

__all__ = ["OptionSpec", "Options", "MD5_LENGTH", "ROOT_OPTIONS"]
