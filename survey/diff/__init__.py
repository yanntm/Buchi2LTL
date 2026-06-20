"""survey.diff — directional language comparison with witness words.

Exports the reusable core so callers need not reach into the modules:

    from survey.diff import diff_report, to_aut

The re-export is lazy (PEP 562) so that running the submodule as a script
(`python -m survey.diff.ltl_diff`) does not eagerly import it here first —
which would trip runpy's "found in sys.modules" double-import warning.
"""
from typing import TYPE_CHECKING

__all__ = ["diff_report", "to_aut"]

if TYPE_CHECKING:  # for type checkers / IDEs only — no runtime eager import
    from survey.diff.ltl_diff import diff_report, to_aut


def __getattr__(name: str):
    if name in __all__:
        from survey.diff import ltl_diff
        return getattr(ltl_diff, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
