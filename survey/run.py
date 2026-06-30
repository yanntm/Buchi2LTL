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
                equiv_timeout: int) -> Tuple[str, str]:
    """The validation verdict and its check wall-time `(token, check_s)`, in one
    vocabulary across LTL and NOT_LTL rows: OFF when verification is disabled; SIZE
    when an LTL formula was too large to send to spot; else the oracle verdict
    (TRUE / FAIL / TIMEOUT / ERROR). An LTL row checks formula equivalence; a
    NOT_LTL row replays its witness (FAIL if the family does not toggle or is
    incomplete/absent — an uncertified NOT_LTL claim is unsound). Other statuses are
    ineligible (empty). `check_s` is empty when no oracle ran."""
    if br.status in ("NOT_LTL", "PROBABLY_NOT_LTL"):
        if not verify:
            return ("OFF", "")
        return _verify.verify_witness(ex.value, br.witness, is_hoa=ex.is_hoa,
                                      timeout=equiv_timeout)
    if br.status != "OK":
        return ("", "")
    if not verify:
        return ("OFF", "")
    rec = str(br.rec or "")
    if rec.startswith("<unflattened"):
        return ("SIZE", "")
    vr = _verify.verify(ex.value, rec, is_hoa=ex.is_hoa, timeout=equiv_timeout)
    eq = vr.equiv
    if eq is True:
        tok = "TRUE"
    elif eq is False:
        tok = "FAIL"
    elif eq == "SPOT_TIMEOUT":
        tok = "TIMEOUT"
    elif isinstance(eq, str) and eq.startswith("SPOT_ERR"):
        tok = "ERROR"
    else:
        tok = str(eq)
    return (tok, vr.check_s)


def _record(ex: Example, technique: Optional[str], *, verify: bool,
            build_timeout: int, equiv_timeout: int) -> Dict[str, object]:
    br = _build.build(ex.value, is_hoa=ex.is_hoa, technique=technique,
                      timeout=build_timeout)
    validation, check_s = _validation(ex, br, verify=verify, equiv_timeout=equiv_timeout)
    return report.row(ex.display, br, validation, ex.source, check_s=check_s)


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

    # Open the CSV up front and stream a flushed row per record, so the file
    # exists and grows during the run (live progress, crash-safe). A file under
    # --logs, else stdout; the summary is the only end-of-run output.
    csv_path: Optional[Path] = None
    if logs_dir is not None:
        logs_dir = Path(logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = logs_dir / f"survey_{ts}.csv"
        fh: "object" = csv_path.open("w", newline="", encoding="utf-8")
        print(f"CSV: {csv_path}", file=sys.stderr)
    else:
        fh = sys.stdout

    groups: List[Tuple[str, List[Dict[str, object]]]] = []
    all_rows: List[Dict[str, object]] = []
    try:
        stream = report.CsvStream(fh)  # type: ignore[arg-type]
        for technique in techniques:
            rows: List[Dict[str, object]] = []
            for ex in examples:
                row = _record(ex, technique, verify=verify,
                              build_timeout=build_timeout, equiv_timeout=equiv_timeout)
                stream.write(row)
                rows.append(row)
                all_rows.append(row)
                if verbose:
                    _trace(row)
            groups.append((technique or "default", rows))
    finally:
        if csv_path is not None:
            fh.close()  # type: ignore[union-attr]

    for label, rows in groups:
        for line in report.summarize(rows, label):
            print(line)

    return 1 if any(r.get("validation") == "FAIL" for r in all_rows) else 0
