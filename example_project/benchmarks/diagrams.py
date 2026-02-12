"""
Benchmark diagram generator.

Produces clean comparison charts: a consolidated multi-tier chart for SQLite
and a single summary chart for PostgreSQL. Outputs PNG files to diagrams/.
"""

import os
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch

from benchmarks.runner import BenchmarkResult

# Color palette
C_TORTOISE = "#2196F3"
C_DJANGO = "#FF9800"
C_NEUTRAL = "#9E9E9E"

BACKEND_LABELS = {
    "tortoise_objects": "tortoise_objects",
    "django_native": "Django native async",
}

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "diagrams"


def generate_diagrams(
    results: list[BenchmarkResult],
    output_dir: str | Path | None = None,
    db_label: str = "sqlite",
) -> list[Path]:
    """
    Generate comparison charts from benchmark results.

    For SQLite: one consolidated chart with all tiers + one speedup summary.
    For other backends: one speedup summary only.
    Returns list of generated file paths.
    """
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    path = _generate_consolidated_chart(results, output_dir, db_label)
    generated.append(path)

    path = _generate_summary_chart(results, output_dir, db_label)
    generated.append(path)

    return generated


def _generate_consolidated_chart(
    results: list[BenchmarkResult],
    output_dir: Path,
    db_label: str,
) -> Path:
    """
    Single chart with all tiers separated by visual dividers.
    Grouped horizontal bars: tortoise (blue) vs django (orange).
    """
    db_display = db_label.upper()

    tier_order = ["small", "wide", "hierarchy"]
    tier_titles = {
        "small": "Tag (1 field, 100 rows)",
        "wide": "WideModel (23 fields, 100 rows)",
        "hierarchy": "Employee hierarchy (200 rows)",
    }

    by_tier: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for r in results:
        by_tier[r.model_tier].append(r)

    # Build flat list of rows with tier separators
    rows: list[dict] = []
    for tier in tier_order:
        if tier not in by_tier:
            continue
        # Group by operation key within tier — backends may have different names
        # for the same logical operation (e.g. "prefetch" vs "select_related")
        ops: dict[str, dict[str, BenchmarkResult]] = {}
        op_order: list[str] = []
        for r in by_tier[tier]:
            if r.operation not in ops:
                op_order.append(r.operation)
            ops.setdefault(r.operation, {})[r.backend] = r

        rows.append({"type": "header", "label": tier_titles[tier]})
        for op_key in op_order:
            backends = ops[op_key]
            # Build label: use shared name, or tortoise name if they differ
            names = {r.name for r in backends.values()}
            if len(names) == 1:
                label = names.pop()
            else:
                # Use the tortoise name (shorter) as canonical label
                tort_r = backends.get("tortoise_objects")
                label = tort_r.name if tort_r else next(iter(backends.values())).name
            rows.append({"type": "data", "name": label, "backends": backends})

    # Layout
    n_data = sum(1 for r in rows if r["type"] == "data")
    n_headers = sum(1 for r in rows if r["type"] == "header")
    total_height = n_data * 0.7 + n_headers * 0.6 + 1.5

    fig, ax = plt.subplots(figsize=(11, max(5, total_height)))

    bar_h = 0.28
    y = 0
    y_ticks = []
    y_labels = []
    header_ys = []

    for row in rows:
        if row["type"] == "header":
            header_ys.append(y)
            y_ticks.append(y)
            y_labels.append(row["label"])
            y += 0.6
        else:
            backends = row["backends"]
            tort_r = backends.get("tortoise_objects")
            dj_r = backends.get("django_native")
            tort_med = tort_r.median_ms if tort_r else 0
            dj_med = dj_r.median_ms if dj_r else 0

            # Tortoise bar (top of pair)
            ax.barh(y - bar_h / 2, tort_med, height=bar_h,
                    color=C_TORTOISE, alpha=0.85, zorder=3)
            # Django bar (bottom of pair)
            ax.barh(y + bar_h / 2, dj_med, height=bar_h,
                    color=C_DJANGO, alpha=0.85, zorder=3)

            # Value labels
            xmax_data = max(tort_med, dj_med)
            offset = ax.get_xlim()[1] * 0.01 if ax.get_xlim()[1] > 0 else 0.02
            if tort_med > 0:
                ax.text(tort_med + offset, y - bar_h / 2,
                        f"{tort_med:.2f}",
                        va="center", ha="left", fontsize=7.5,
                        color=C_TORTOISE, fontweight="bold", zorder=4)
            if dj_med > 0:
                ax.text(dj_med + offset, y + bar_h / 2,
                        f"{dj_med:.2f}",
                        va="center", ha="left", fontsize=7.5,
                        color=C_DJANGO, fontweight="bold", zorder=4)

            y_ticks.append(y)
            y_labels.append(row["name"])
            y += 0.7

    # Style tick labels: bold for headers, normal for ops
    ax.set_yticks(y_ticks)
    tick_labels = []
    for i, lbl in enumerate(y_labels):
        tick_labels.append(lbl)
    ax.set_yticklabels(tick_labels, fontsize=8.5)

    # Bold the header labels
    for i, row in enumerate(rows):
        pass  # matplotlib doesn't support mixed bold easily; use color instead

    # Color header labels differently
    header_positions = set()
    idx = 0
    for row in rows:
        if row["type"] == "header":
            header_positions.add(idx)
        idx += 1
    for i, label in enumerate(ax.get_yticklabels()):
        if i in header_positions:
            label.set_fontweight("bold")
            label.set_fontsize(9.5)
            label.set_color("#333333")

    # Draw horizontal separators above each tier header
    for hy in header_ys[1:]:
        ax.axhline(y=hy - 0.35, color="#CCCCCC", linewidth=0.8, zorder=1)

    ax.invert_yaxis()
    ax.set_xlim(0, max(r.median_ms for r in results) * 1.35)
    ax.set_xlabel("Median time (ms) — lower is better", fontsize=10)
    ax.set_title(
        f"Benchmark Results [{db_display}] — tortoise_objects vs Django native async",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.grid(axis="x", alpha=0.2, which="both", zorder=0)
    ax.tick_params(axis="y", length=0)

    legend_elements = [
        Patch(facecolor=C_TORTOISE, alpha=0.85, label="tortoise_objects"),
        Patch(facecolor=C_DJANGO, alpha=0.85, label="Django native async"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9,
              framealpha=0.9)

    fig.tight_layout()
    path = output_dir / f"bench_{db_label}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _generate_summary_chart(
    results: list[BenchmarkResult],
    output_dir: Path,
    db_label: str,
) -> Path:
    """
    Speedup ratio chart: bars show how much faster one backend is vs the other.
    Clean, single-color-per-bar design with 1.0x reference line.
    """
    db_display = db_label.upper()

    # Pair results by (tier, operation) → compute ratio
    # Use operation (not name) since backends may have different names for same op
    pairs: dict[tuple[str, str], dict[str, BenchmarkResult]] = {}
    for r in results:
        key = (r.model_tier, r.operation)
        pairs.setdefault(key, {})[r.backend] = r

    tier_labels = {"small": "S", "wide": "W", "hierarchy": "H"}

    labels = []
    ratios = []
    colors = []

    for (tier, op), backends in sorted(pairs.items()):
        tort_r = backends.get("tortoise_objects")
        dj_r = backends.get("django_native")
        if not tort_r or not dj_r:
            continue

        ratio = dj_r.median_ms / tort_r.median_ms  # >1 = tortoise faster
        # Use the shorter/common name for the label
        if tort_r.name == dj_r.name:
            display_name = tort_r.name
        else:
            display_name = tort_r.name
        labels.append(f"[{tier_labels[tier]}] {display_name}")
        ratios.append(ratio)
        colors.append(C_TORTOISE if ratio >= 1.0 else C_DJANGO)

    n = len(labels)
    fig, ax = plt.subplots(figsize=(10, max(4, n * 0.42 + 1.5)))

    y = list(range(n))
    bars = ax.barh(y, ratios, color=colors, alpha=0.85, height=0.55, zorder=3)

    # Ratio labels
    for bar, ratio, color in zip(bars, ratios, colors):
        w = bar.get_width()
        if ratio >= 1.0:
            ax.text(w + 0.03, bar.get_y() + bar.get_height() / 2,
                    f"{ratio:.1f}x", va="center", ha="left",
                    fontsize=8, fontweight="bold", color=C_TORTOISE)
        else:
            ax.text(w + 0.03, bar.get_y() + bar.get_height() / 2,
                    f"{1/ratio:.1f}x", va="center", ha="left",
                    fontsize=8, fontweight="bold", color=C_DJANGO)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()

    # Reference line at 1.0
    ax.axvline(x=1.0, color="#666666", linewidth=1.2, linestyle="--", alpha=0.6, zorder=2)

    # Axis labels
    ax.set_xlabel("Speedup ratio (django / tortoise median) — right = tortoise faster", fontsize=9)
    ax.set_title(
        f"Performance Summary [{db_display}]",
        fontsize=13, fontweight="bold", pad=14,
    )

    legend_elements = [
        Patch(facecolor=C_TORTOISE, alpha=0.85, label="tortoise_objects faster"),
        Patch(facecolor=C_DJANGO, alpha=0.85, label="Django native faster"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9, framealpha=0.9)
    ax.grid(axis="x", alpha=0.2, zorder=0)
    ax.tick_params(axis="y", length=0)

    fig.tight_layout()
    path = output_dir / f"bench_{db_label}_summary.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
