"""genaut/analyze_frontier.py — one consistent "frontier" report from a census CSV.

Pure CSV post-processing (NO tool re-run): given a survey CSV produced by
`python3 -m survey` over the genaut corpus (current schema:
input,result,technique,build_s,formula,dag,temporals,tree,sharing,validation,
source), it summarises how the corpus *collapses* —

  * the answer frontier      : how many inputs are decided not-LTL, reconstructed,
                               time out, or otherwise fail;
  * the formula collapse     : how the LTL answers concentrate onto a small idiom
                               vocabulary (distinct count + top-N histogram);
  * the size frontier        : the flattened formula-size (tree-node) distribution,
                               and what proportion lands "small" (< SMALL nodes);
  * routes to `true`         : which portfolio technique produced the universal `1`;
  * build time / timeouts    : per-class build-time stats and the timeout tail;
  * verification             : the spot-oracle validation breakdown.

It supersedes the earlier piecemeal probes (analyze_census.py etc.): one report,
one CSV read, both as text on stdout and a multi-page PDF with plots.

Sections are independent `report_*` functions returning a `Section`; add a new
diagnosis by writing one and appending it to `SECTIONS`.

Usage:
  python3 genaut/analyze_frontier.py [CSV] [--out PDF] [--top N]
    CSV    survey CSV to analyse   (default: genaut/logs/default.csv)
    --out  output PDF              (default: <CSV dir>/frontier.pdf)
    --top  idiom-histogram depth   (default: 15)
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import matplotlib

matplotlib.use("Agg")  # headless: render straight to PDF, never a display
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

HERE = os.path.dirname(__file__)
DEFAULT_CSV = os.path.join(HERE, "logs", "default.csv")

# A reconstructed formula counts as "small" when its flattened tree stays under
# this many nodes — the readable-idiom regime we care about.
SMALL = 20

# result-column buckets (current survey schema).
ANSWERED = "LTL"
NOT_LTL = "NOT_LTL"
TIMEOUT = "TIMEOUT"


@dataclass
class Section:
    """One report section.

    `lines`  — the full text, rendered into the PDF.
    `terse`  — a fixed-size digest (a few lines) echoed to stdout so the report
               can be read back cheaply; never a variable-length dump. Falls back
               to `lines` only if left empty.
    `figures`— the section's plots, appended to the PDF after its text page.
    """

    title: str
    lines: List[str] = field(default_factory=list)
    terse: List[str] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:5.1f}%" if total else "  n/a"


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def report_overview(df: pd.DataFrame, top: int) -> Section:
    # Ventilate the corpus into three disjoint classes. Only the timeouts are
    # ambiguous: a build timeout decides nothing, so we do not know whether those
    # languages are LTL-definable. The LTL / not-LTL classes are decided answers.
    s = Section("Ventilation — LTL / not-LTL / ambiguous")
    total = len(df)
    counts = df["result"].value_counts()
    n_ltl = int(counts.get(ANSWERED, 0))
    n_not = int(counts.get(NOT_LTL, 0))
    n_amb = int(counts.get(TIMEOUT, 0))
    other = total - n_ltl - n_not - n_amb
    s.lines.append(f"corpus inputs: {total}")
    s.lines.append(f"  LTL-definable (formula built) : {n_ltl:5d}  ({_pct(n_ltl, total)})")
    s.lines.append(f"  not-LTL (decided)             : {n_not:5d}  ({_pct(n_not, total)})")
    s.lines.append(f"  ambiguous (timeout, unknown)  : {n_amb:5d}  ({_pct(n_amb, total)})")
    if other:
        s.lines.append(f"  other (crash/decline)         : {other:5d}  ({_pct(other, total)})")
    s.lines.append(f"decided (LTL or not-LTL): {n_ltl + n_not}  "
                   f"({_pct(n_ltl + n_not, total)})")
    s.terse = [f"{total} inputs: {n_ltl} LTL-definable, {n_not} not-LTL, "
               f"{n_amb} ambiguous(timeout)"]

    fig, ax = plt.subplots(figsize=(7, 4))
    order = [c for c in (ANSWERED, NOT_LTL, TIMEOUT) if c in counts.index]
    order += [c for c in counts.index if c not in order]
    vals = [int(counts[c]) for c in order]
    ax.bar(order, vals, color="#4c72b0")
    for i, v in enumerate(vals):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
    ax.set_title("Answer frontier (by result)")
    ax.set_ylabel("inputs (log)")
    ax.set_yscale("log")
    fig.tight_layout()
    s.figures.append(fig)
    return s


def report_collapse(df: pd.DataFrame, top: int) -> Section:
    s = Section("Formula collapse — idiom concentration")
    built = df[df["result"] == ANSWERED]
    n_built = len(built)
    forms = built["formula"].fillna("").astype(str)
    gated = forms.str.startswith("<unflattened").sum()
    readable = forms[~forms.str.startswith("<unflattened")]
    counts = readable.value_counts()
    s.lines.append(f"LTL answers: {n_built}   ({gated} gated/unflattened strings)")
    s.lines.append(f"distinct readable formulas: {len(counts)}")
    if len(counts):
        # how few idioms cover 80% / 90% of the readable answers
        n_readable = int(counts.sum())
        cum = counts.cumsum()
        for frac in (0.80, 0.90):
            need = min(int((cum < frac * n_readable).sum()) + 1, len(counts))
            s.lines.append(f"  {int(frac*100)}% of readable answers covered by the "
                           f"top {need} idiom(s)")
    s.lines.append(f"top {top} idioms:")
    for form, n in counts.head(top).items():
        label = form if len(form) <= 48 else form[:45] + "..."
        s.lines.append(f"  {n:5d}  ({_pct(int(n), n_built)})  {label}")

    top5 = "; ".join(f"{f!r}x{int(n)}" for f, n in counts.head(5).items())
    s.terse = [f"{n_built} LTL answers -> {len(counts)} distinct idioms "
               f"({gated} gated). top5: {top5}"]

    if len(counts):
        head = counts.head(top)[::-1]
        fig, ax = plt.subplots(figsize=(8, max(3, 0.35 * len(head) + 1)))
        labels = [f if len(f) <= 36 else f[:33] + "..." for f in head.index]
        ax.barh(labels, head.values, color="#55a868")
        for i, v in enumerate(head.values):
            ax.text(v, i, f" {v}", va="center", fontsize=8)
        ax.set_title(f"Top {len(head)} reconstructed idioms")
        ax.set_xlabel("inputs (log)")
        ax.set_xscale("log")
        fig.tight_layout()
        s.figures.append(fig)
    return s


def report_size(df: pd.DataFrame, top: int) -> Section:
    s = Section("Size frontier — flattened formula size")
    built = df[df["result"] == ANSWERED].copy()
    tree = pd.to_numeric(built["tree"], errors="coerce").dropna()
    n = len(tree)
    if not n:
        s.lines.append("no LTL answers with a tree size.")
        return s
    trivial = int((tree <= 1).sum())          # `1`/`0` — true / false
    small = int((tree < SMALL).sum())
    s.lines.append(f"LTL answers with a size: {n}")
    s.lines.append(f"  trivial (tree<=1, i.e. true/false): {trivial}  ({_pct(trivial, n)})")
    s.lines.append(f"  small   (tree<{SMALL}):               {small}  ({_pct(small, n)})")
    s.lines.append(f"  larger  (tree>={SMALL}):              {n-small}  ({_pct(n-small, n)})")
    s.lines.append(f"  tree nodes: median {tree.median():.0f}  mean {tree.mean():.1f}  "
                   f"max {tree.max():.0f}")
    s.terse = [f"{n} sized: trivial {_pct(trivial,n)}, small<{SMALL} {_pct(small,n)}, "
               f">= {SMALL} {_pct(n-small,n)} | median tree {tree.median():.0f}"]

    fig, ax = plt.subplots(figsize=(7, 4))
    # cap the bin count hard — genaut has a few astronomically large trees, so an
    # unbounded clip_hi would make range() explode into millions of bins.
    clip_hi = max(SMALL + 1, min(int(tree.quantile(0.95)) + 1, 2 * SMALL))
    shown = tree.clip(upper=clip_hi)
    ax.hist(shown, bins=range(0, clip_hi + 2), color="#c44e52", align="left")
    ax.axvline(SMALL - 0.5, color="black", ls="--", lw=1, label=f"small < {SMALL}")
    n_over = int((tree > clip_hi).sum())
    ax.set_title(f"Flattened size (tree nodes); clipped at {clip_hi} "
                 f"({n_over} larger pooled at right)")
    ax.set_xlabel("tree nodes")
    ax.set_ylabel("inputs (log)")
    ax.set_yscale("log")
    ax.legend()
    fig.tight_layout()
    s.figures.append(fig)
    return s


def report_routes_to_true(df: pd.DataFrame, top: int) -> Section:
    s = Section("Routes to `true` — which technique built the universal 1")
    built = df[df["result"] == ANSWERED]
    true_rows = built[built["formula"].astype(str).str.strip() == "1"]
    n = len(true_rows)
    s.lines.append(f"universal answers (formula == '1'): {n}")
    if not n:
        return s
    techs = true_rows["technique"].fillna("?").value_counts()
    for tech, c in techs.items():
        s.lines.append(f"  {int(c):5d}  ({_pct(int(c), n)})  {tech}")
    builds = pd.to_numeric(true_rows["build_s"], errors="coerce").dropna()
    if len(builds):
        s.lines.append(f"build_s over true rows: total {builds.sum():.1f}s  "
                       f"mean {builds.mean():.3f}s  max {builds.max():.3f}s")
    routes = ", ".join(f"{t}x{int(c)}" for t, c in techs.items())
    s.terse = [f"true (formula=='1'): {n} via {routes}"]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(techs.index.astype(str), techs.values, color="#8172b3")
    for i, v in enumerate(techs.values):
        ax.text(i, v, str(int(v)), ha="center", va="bottom", fontsize=9)
    ax.set_title("Routes to `true` (technique)")
    ax.set_ylabel("inputs (log)")
    ax.set_yscale("log")
    fig.tight_layout()
    s.figures.append(fig)
    return s


def report_build_time(df: pd.DataFrame, top: int) -> Section:
    s = Section("Build time & timeouts")
    build = pd.to_numeric(df["build_s"], errors="coerce")
    s.lines.append(f"total build: {build.sum():.1f}s   "
                   f"mean {build.mean():.3f}s   max {build.max():.3f}s")
    for label in (ANSWERED, NOT_LTL):
        sub = build[df["result"] == label].dropna()
        if len(sub):
            s.lines.append(f"  {label:<10} n={len(sub):4d}  mean {sub.mean():.3f}s  "
                           f"max {sub.max():.3f}s")
    timeouts = df[df["result"] == TIMEOUT]
    s.lines.append(f"timeouts: {len(timeouts)}")
    for _, r in timeouts.head(20).iterrows():
        s.lines.append(f"    {r['input']}")
    s.terse = [f"build total {build.sum():.0f}s, mean {build.mean():.3f}s, "
               f"max {build.max():.3f}s | {len(timeouts)} timeouts"]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(build.dropna(), bins=30, color="#937860")
    ax.set_title("Build-time distribution")
    ax.set_xlabel("build_s")
    ax.set_ylabel("inputs (log)")
    ax.set_yscale("log")
    fig.tight_layout()
    s.figures.append(fig)
    return s


def report_verification(df: pd.DataFrame, top: int) -> Section:
    s = Section("Verification — spot-oracle validation")
    built = df[df["result"] == ANSWERED]
    val = built["validation"].fillna("").replace("", "(blank)").value_counts()
    s.lines.append(f"validation over {len(built)} LTL answers:")
    for k, c in val.items():
        s.lines.append(f"  {str(k):<14} {int(c):5d}  ({_pct(int(c), len(built))})")
    bad = int(built["validation"].fillna("").eq("FALSE").sum())
    s.lines.append(f"NOT-equivalent (FALSE): {bad}   "
                   f"{'CLEAN' if bad == 0 else '*** REGRESSION ***'}")
    ok = int(built["validation"].fillna("").eq("TRUE").sum())
    s.terse = [f"verified TRUE {ok}/{len(built)}, FALSE {bad} -> "
               f"{'CLEAN' if bad == 0 else 'REGRESSION'}"]
    return s


SECTIONS: List[Callable[[pd.DataFrame, int], Section]] = [
    report_overview,
    report_collapse,
    report_size,
    report_routes_to_true,
    report_build_time,
    report_verification,
]


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _text_pages(title: str, lines: List[str], per_page: int = 46) -> List[Figure]:
    figs: List[Figure] = []
    for start in range(0, max(1, len(lines)), per_page):
        chunk = lines[start:start + per_page]
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
        fig.text(0.06, 0.95, title, fontsize=14, weight="bold", va="top")
        fig.text(0.06, 0.90, "\n".join(chunk), fontsize=9, family="monospace",
                 va="top")
        figs.append(fig)
    return figs


def run(csv_path: str, out_pdf: str, top: int) -> None:
    df = pd.read_csv(csv_path)
    sections = [fn(df, top) for fn in SECTIONS]

    # stdout: a terse, fixed-size digest (the full text lives in the PDF).
    print(f"frontier  |  {os.path.basename(csv_path)}  |  rows: {len(df)}")
    for sec in sections:
        for line in (sec.terse or sec.lines[:2]):
            print(f"  [{sec.title.split(' ')[0].lower()}] {line}")

    # PDF: a text page per section, then that section's figures.
    with PdfPages(out_pdf) as pdf:
        cover_lines = [f"source CSV : {csv_path}",
                       f"corpus rows: {len(df)}", "",
                       "sections:"] + [f"  - {s.title}" for s in sections]
        for fig in _text_pages("genaut — frontier report", cover_lines):
            pdf.savefig(fig)
            plt.close(fig)
        for sec in sections:
            for fig in _text_pages(sec.title, sec.lines):
                pdf.savefig(fig)
                plt.close(fig)
            for fig in sec.figures:
                pdf.savefig(fig)
                plt.close(fig)
    print(f"\nPDF written: {out_pdf}")


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Frontier report from a survey CSV.")
    ap.add_argument("csv", nargs="?", default=DEFAULT_CSV,
                    help=f"survey CSV (default: {DEFAULT_CSV})")
    ap.add_argument("--out", default=None,
                    help="output PDF (default: <CSV dir>/frontier.pdf)")
    ap.add_argument("--top", type=int, default=15, help="idiom histogram depth")
    args = ap.parse_args(argv)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.csv)),
                                   "frontier.pdf")
    run(args.csv, out, args.top)


if __name__ == "__main__":
    main()
