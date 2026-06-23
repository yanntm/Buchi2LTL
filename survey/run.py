"""survey.run — orchestrate a survey: examples × techniques → rows → CSV/report.

For each requested technique, reconstruct every example (and, unless disabled,
validate it), into one flat CSV (a file under --logs, or stdout). A compact
summary per technique goes to stdout; the per-input live trace goes to stderr
under --verbose.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from survey import build as _build
from survey import report
from survey import verify as _verify
from survey.example import Example
from survey.techniques import resolve


def _validation(ex: Example, br: "_build.BuildResult", *, verify: bool,
                equiv_timeout: int) -> str:
    """The single validation token for a row. Empty for non-LTL (ineligible);
    OFF when verification is disabled; SIZE when the formula was too large to
    send to spot; else the oracle verdict (TRUE / FAIL / TIMEOUT / ERROR)."""
    if br.status != "OK":
        return ""
    if not verify:
        return "OFF"
    rec = str(br.rec or "")
    if rec.startswith("<unflattened"):
        return "SIZE"
    eq = _verify.verify(ex.value, rec, is_hoa=ex.is_hoa, timeout=equiv_timeout).equiv
    if eq is True:
        return "TRUE"
    if eq is False:
        return "FAIL"
    if eq == "SPOT_TIMEOUT":
        return "TIMEOUT"
    if isinstance(eq, str) and eq.startswith("SPOT_ERR"):
        return "ERROR"
    return str(eq)


def _record(ex: Example, technique: Optional[str], *, verify: bool,
            build_timeout: int, equiv_timeout: int) -> Dict[str, object]:
    br = _build.build(ex.value, is_hoa=ex.is_hoa, technique=technique,
                      timeout=build_timeout)
    validation = _validation(ex, br, verify=verify, equiv_timeout=equiv_timeout)
    return report.row(ex.display, br, validation, ex.source)


def _trace_header() -> None:
    hdr = (f"  {'input':26s} {'result':6s} {'technique':16s} "
           f"{'build':>7s}  validation")
    print(hdr, file=sys.stderr)
    print("  " + "-" * (len(hdr) - 2), file=sys.stderr)


def _trace(row: Dict[str, object]) -> None:
    bs = f"{row['build_s']}s" if row["build_s"] != "" else "-"
    print(f"  {str(row['input']):26.26s} {str(row['result']):6s} "
          f"{str(row['technique']):16.16s} {bs:>7s}  {row['validation']}",
          file=sys.stderr)


def run(examples: Sequence[Example], uses: Sequence[str], *,
        logs_dir: Optional[Path] = None, verify: bool = True,
        verbose: bool = False, build_timeout: int = 15,
        equiv_timeout: int = 15) -> int:
    """Run every example under every resolved technique. Returns 1 iff a verified
    NON-equivalent answer occurred (only possible with verify), else 0."""
    techniques = resolve(uses)
    if verbose:
        _trace_header()

    groups: List[Tuple[str, List[Dict[str, object]]]] = []
    all_rows: List[Dict[str, object]] = []
    for technique in techniques:
        rows: List[Dict[str, object]] = []
        for ex in examples:
            row = _record(ex, technique, verify=verify,
                          build_timeout=build_timeout, equiv_timeout=equiv_timeout)
            rows.append(row)
            all_rows.append(row)
            if verbose:
                _trace(row)
        groups.append((technique or "default", rows))

    # One flat CSV: to a file under --logs, else to stdout.
    if logs_dir is not None:
        logs_dir = Path(logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = logs_dir / f"survey_{ts}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            report.write_csv(all_rows, fh)
        print(f"CSV: {csv_path}", file=sys.stderr)
    else:
        report.write_csv(all_rows, sys.stdout)

    for label, rows in groups:
        for line in report.summarize(rows, label):
            print(line)

    return 1 if any(r.get("validation") == "FAIL" for r in all_rows) else 0
