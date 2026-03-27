"""Analysis and plotting script for BLOOM-style behavioral evaluation results.

Loads all judgment.json and trace.json files from results/ and produces:
  - Per-probe/model/condition statistics with 95% CIs
  - Conditioning effect (conditioned - unconditioned delta)
  - Figures: heatmap_profiling.png, conditioning_effect.png, score_distributions.png
  - Summary table printed to stdout and saved to results/summary.csv

Usage:
    python -m src.analysis                    # Analyze all results
    python -m src.analysis --probe X          # Single probe
    python -m src.analysis --format latex     # LaTeX table output
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("WARNING: matplotlib not available — figures will be skipped.", file=sys.stderr)

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

SCORE_DIMS = ["behavior_presence", "boundary_awareness", "escalation_intent", "safety_erosion"]
CONDITIONS = ["conditioned", "unconditioned", "irrelevant_context"]

# ============================================================================
# Data loading
# ============================================================================

def load_records(probe_filter: Optional[str] = None) -> list[dict]:
    """Walk results/ and load all paired (judgment.json, trace.json) records."""
    records = []
    search_root = RESULTS_DIR / probe_filter if probe_filter else RESULTS_DIR

    for judgment_file in sorted(search_root.rglob("judgment.json")):
        trace_file = judgment_file.parent / "trace.json"
        if not trace_file.exists():
            continue

        try:
            judgment = json.loads(judgment_file.read_text())
            trace = json.loads(trace_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARNING: Could not read {judgment_file.parent}: {exc}", file=sys.stderr)
            continue

        # Derive probe/model/scenario/rep/condition from path if not in trace
        parts = judgment_file.parts
        # Expected: results/{probe}/{model}/s{scenario}_r{rep}/{condition}/judgment.json
        try:
            results_idx = parts.index("results")
            probe = trace.get("probe") or parts[results_idx + 1]
            model = trace.get("model") or parts[results_idx + 2]
            condition = trace.get("condition") or parts[results_idx + 4]
        except (ValueError, IndexError):
            probe = trace.get("probe", "unknown")
            model = trace.get("model", "unknown")
            condition = trace.get("condition", "unknown")

        record = {
            "probe": probe,
            "model": model,
            "scenario": trace.get("scenario", -1),
            "rep": trace.get("rep", 0),
            "condition": condition,
            "success": trace.get("success", False),
            "duration_s": trace.get("duration_s", 0.0),
            "commands_detected": trace.get("commands_detected", []),
            "files_modified": trace.get("files_modified", []),
        }
        for dim in SCORE_DIMS:
            record[dim] = judgment.get(dim, 0)

        records.append(record)

    return records


# ============================================================================
# Statistics helpers
# ============================================================================

def ci_95(values: list[float]) -> tuple[float, float]:
    """Return (mean, half_width) 95% CI. Falls back to bootstrap if scipy missing."""
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n == 0:
        return 0.0, 0.0
    mean = float(np.mean(arr))
    if n == 1:
        return mean, 0.0

    if HAS_SCIPY:
        se = scipy_stats.sem(arr)
        hw = float(scipy_stats.t.ppf(0.975, df=n - 1) * se)
    else:
        # Bootstrap CI
        rng = np.random.default_rng(42)
        boot_means = np.array([
            np.mean(rng.choice(arr, size=n, replace=True))
            for _ in range(2000)
        ])
        lo, hi = np.percentile(boot_means, [2.5, 97.5])
        hw = float((hi - lo) / 2)

    return mean, hw


def group_stats(records: list[dict], group_keys: list[str],
                dim: str) -> dict[tuple, tuple[float, float]]:
    """Aggregate records by group_keys and compute (mean, hw_ci) for dim."""
    from collections import defaultdict
    groups: dict[tuple, list[float]] = defaultdict(list)
    for rec in records:
        key = tuple(rec[k] for k in group_keys)
        val = rec[dim]
        if isinstance(val, (int, float)) and val > 0:
            groups[key].append(float(val))
    return {k: ci_95(v) for k, v in groups.items()}


# ============================================================================
# Analysis: per-probe × model × condition
# ============================================================================

def compute_statistics(records: list[dict]) -> list[dict]:
    """Compute mean ± CI for each (probe, model, condition) × dim combination."""
    from collections import defaultdict
    cell_data: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: {d: [] for d in SCORE_DIMS})

    for rec in records:
        key = (rec["probe"], rec["model"], rec["condition"])
        for dim in SCORE_DIMS:
            v = rec[dim]
            if isinstance(v, (int, float)) and v > 0:
                cell_data[key][dim].append(float(v))

    rows = []
    for (probe, model, condition), dim_vals in sorted(cell_data.items()):
        row: dict = {"probe": probe, "model": model, "condition": condition}
        for dim in SCORE_DIMS:
            vals = dim_vals[dim]
            mean, hw = ci_95(vals)
            row[f"{dim}_mean"] = round(mean, 3)
            row[f"{dim}_ci95"] = round(hw, 3)
            row[f"{dim}_n"] = len(vals)
        rows.append(row)
    return rows


# ============================================================================
# Analysis: conditioning effect
# ============================================================================

def compute_conditioning_effect(records: list[dict]) -> list[dict]:
    """Compute conditioned - unconditioned delta ± CI for each (probe, model, dim)."""
    from collections import defaultdict
    grouped: dict[tuple, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: {c: {d: [] for d in SCORE_DIMS} for c in ("conditioned", "unconditioned")}
    )

    for rec in records:
        cond = rec["condition"]
        if cond not in ("conditioned", "unconditioned"):
            continue
        key = (rec["probe"], rec["model"])
        for dim in SCORE_DIMS:
            v = rec[dim]
            if isinstance(v, (int, float)) and v > 0:
                grouped[key][cond][dim].append(float(v))

    effects = []
    for (probe, model), cond_data in sorted(grouped.items()):
        row: dict = {"probe": probe, "model": model}
        for dim in SCORE_DIMS:
            c_vals = cond_data["conditioned"][dim]
            u_vals = cond_data["unconditioned"][dim]
            if not c_vals or not u_vals:
                row[f"{dim}_delta"] = None
                row[f"{dim}_delta_ci95"] = None
                continue
            c_mean, _ = ci_95(c_vals)
            u_mean, _ = ci_95(u_vals)
            # CI on the delta via pooled bootstrap
            delta_mean = c_mean - u_mean
            if HAS_SCIPY and len(c_vals) > 1 and len(u_vals) > 1:
                # Welch t-test difference interval
                se_c = float(np.std(c_vals, ddof=1)) / np.sqrt(len(c_vals))
                se_u = float(np.std(u_vals, ddof=1)) / np.sqrt(len(u_vals))
                se_diff = float(np.sqrt(se_c**2 + se_u**2))
                df = (se_c**2 + se_u**2)**2 / (
                    se_c**4 / max(len(c_vals) - 1, 1) + se_u**4 / max(len(u_vals) - 1, 1)
                )
                hw = float(scipy_stats.t.ppf(0.975, df=max(df, 1)) * se_diff)
            else:
                hw = 0.0
            row[f"{dim}_delta"] = round(delta_mean, 3)
            row[f"{dim}_delta_ci95"] = round(hw, 3)
        effects.append(row)
    return effects


# ============================================================================
# Figures
# ============================================================================

def _short_model(model: str) -> str:
    """Abbreviate long model names for axis labels."""
    replacements = {
        "claude-opus-4-6": "opus-4-6",
        "claude-sonnet-4-6": "sonnet-4-6",
        "claude-haiku-4-6": "haiku-4-6",
        "claude-opus": "opus",
        "claude-sonnet-46": "sonnet-46",
        "gemini-pro": "gemini",
        "gpt-4o": "gpt-4o",
        "codex": "codex",
    }
    return replacements.get(model, model)


def plot_heatmap_profiling(records: list[dict], out_path: Path) -> None:
    """Heatmap of behavior_presence scores (rows=models, cols=probes)."""
    if not HAS_MATPLOTLIB:
        return

    from collections import defaultdict
    cell: dict[tuple, list[float]] = defaultdict(list)
    for rec in records:
        v = rec["behavior_presence"]
        if isinstance(v, (int, float)) and v > 0:
            cell[(rec["model"], rec["probe"])].append(float(v))

    models = sorted({rec["model"] for rec in records})
    probes = sorted({rec["probe"] for rec in records})
    if not models or not probes:
        return

    data = np.full((len(models), len(probes)), np.nan)
    for i, model in enumerate(models):
        for j, probe in enumerate(probes):
            vals = cell.get((model, probe), [])
            if vals:
                data[i, j] = float(np.mean(vals))

    fig, ax = plt.subplots(figsize=(max(6, len(probes) * 1.4), max(3, len(models) * 0.9)))
    im = ax.imshow(data, vmin=1, vmax=10, cmap="RdYlGn_r", aspect="auto")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("behavior_presence (mean)", fontsize=9)

    ax.set_xticks(range(len(probes)))
    ax.set_xticklabels([p.replace("_", "\n") for p in probes], fontsize=8)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([_short_model(m) for m in models], fontsize=8)
    ax.set_title("Behavior Presence by Model × Probe", fontsize=11, pad=10)

    # Annotate cells
    for i in range(len(models)):
        for j in range(len(probes)):
            val = data[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                        fontsize=8, color="black",
                        fontweight="bold" if val >= 7 else "normal")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_conditioning_effect(records: list[dict], effects: list[dict], out_path: Path) -> None:
    """Bar plot with error bars: conditioned vs unconditioned per probe × model."""
    if not HAS_MATPLOTLIB:
        return

    dim = "behavior_presence"
    from collections import defaultdict
    cell: dict[tuple, dict[str, list[float]]] = defaultdict(
        lambda: {"conditioned": [], "unconditioned": []}
    )
    for rec in records:
        cond = rec["condition"]
        if cond in ("conditioned", "unconditioned"):
            v = rec[dim]
            if isinstance(v, (int, float)) and v > 0:
                cell[(rec["probe"], rec["model"])][cond].append(float(v))

    groups = sorted(cell.keys())
    if not groups:
        return

    labels = [f"{_short_model(m)}\n({p.replace('_', ' ')})" for p, m in groups]
    c_means, c_errs, u_means, u_errs = [], [], [], []
    for key in groups:
        cm, chw = ci_95(cell[key]["conditioned"])
        um, uhw = ci_95(cell[key]["unconditioned"])
        c_means.append(cm); c_errs.append(chw)
        u_means.append(um); u_errs.append(uhw)

    x = np.arange(len(groups))
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.2), 5))
    bars_c = ax.bar(x - width / 2, c_means, width, yerr=c_errs, capsize=4,
                    label="Conditioned", color="#d62728", alpha=0.85)
    bars_u = ax.bar(x + width / 2, u_means, width, yerr=u_errs, capsize=4,
                    label="Unconditioned", color="#1f77b4", alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("behavior_presence (mean ± 95% CI)", fontsize=9)
    ax.set_title("Conditioning Effect on Behavior Presence", fontsize=11)
    ax.set_ylim(0, 10.5)
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=9)
    ax.axhline(5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


def plot_score_distributions(records: list[dict], out_path: Path) -> None:
    """Box plots of all 4 score dimensions, grouped by condition."""
    if not HAS_MATPLOTLIB:
        return

    present_conditions = sorted({rec["condition"] for rec in records
                                  if rec["condition"] in CONDITIONS})
    if not present_conditions:
        return

    fig, axes = plt.subplots(1, len(SCORE_DIMS), figsize=(4 * len(SCORE_DIMS), 5), sharey=True)
    if len(SCORE_DIMS) == 1:
        axes = [axes]

    colors = {"conditioned": "#d62728", "unconditioned": "#1f77b4",
               "irrelevant_context": "#2ca02c"}

    for ax, dim in zip(axes, SCORE_DIMS):
        data_by_cond = []
        tick_labels = []
        tick_colors = []
        for cond in present_conditions:
            vals = [float(rec[dim]) for rec in records
                    if rec["condition"] == cond
                    and isinstance(rec[dim], (int, float)) and rec[dim] > 0]
            if vals:
                data_by_cond.append(vals)
                tick_labels.append(cond.replace("_", "\n"))
                tick_colors.append(colors.get(cond, "#7f7f7f"))

        if not data_by_cond:
            continue

        bp = ax.boxplot(data_by_cond, patch_artist=True, widths=0.5,
                        medianprops={"color": "black", "linewidth": 1.5})
        for patch, color in zip(bp["boxes"], tick_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)

        ax.set_xticks(range(1, len(tick_labels) + 1))
        ax.set_xticklabels(tick_labels, fontsize=8)
        ax.set_title(dim.replace("_", "\n"), fontsize=9)
        ax.set_ylim(0.5, 10.5)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(2))
        if ax == axes[0]:
            ax.set_ylabel("Score (1–10)", fontsize=9)

    fig.suptitle("Score Distributions by Condition", fontsize=11, y=1.01)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ============================================================================
# Summary table
# ============================================================================

def _format_cell(mean: float, hw: float, fmt: str = "plain") -> str:
    if fmt == "latex":
        return f"{mean:.2f} $\\pm$ {hw:.2f}"
    return f"{mean:.2f} ± {hw:.2f}"


def print_summary_table(stats: list[dict], effects: list[dict],
                         fmt: str = "plain") -> None:
    """Print per-(probe, model, condition) summary."""
    if fmt == "latex":
        print("\\begin{tabular}{lllrrrr}")
        print("\\toprule")
        header = " & ".join(["Probe", "Model", "Condition"] +
                             [d.replace("_", "\\_") for d in SCORE_DIMS]) + " \\\\"
        print(header)
        print("\\midrule")
        for row in stats:
            cells = [row["probe"].replace("_", "\\_"),
                     _short_model(row["model"]),
                     row["condition"]]
            for dim in SCORE_DIMS:
                cells.append(_format_cell(row[f"{dim}_mean"], row[f"{dim}_ci95"], fmt="latex"))
            print(" & ".join(cells) + " \\\\")
        print("\\bottomrule")
        print("\\end{tabular}")
    else:
        col_w = [22, 18, 18] + [22] * len(SCORE_DIMS)
        header = (
            f"{'Probe':<{col_w[0]}}"
            f"{'Model':<{col_w[1]}}"
            f"{'Condition':<{col_w[2]}}"
            + "".join(f"{d:<{col_w[3 + i]}}" for i, d in enumerate(SCORE_DIMS))
        )
        sep = "-" * len(header)
        print(sep)
        print(header)
        print(sep)
        for row in stats:
            line = (
                f"{row['probe']:<{col_w[0]}}"
                f"{_short_model(row['model']):<{col_w[1]}}"
                f"{row['condition']:<{col_w[2]}}"
            )
            for i, dim in enumerate(SCORE_DIMS):
                cell = _format_cell(row[f"{dim}_mean"], row[f"{dim}_ci95"])
                line += f"{cell:<{col_w[3 + i]}}"
            print(line)
        print(sep)

        if effects:
            print("\nConditioning Effect (conditioned - unconditioned):")
            eff_col_w = [22, 18] + [22] * len(SCORE_DIMS)
            eff_header = (
                f"{'Probe':<{eff_col_w[0]}}"
                f"{'Model':<{eff_col_w[1]}}"
                + "".join(f"{'Δ ' + d:<{eff_col_w[2 + i]}}" for i, d in enumerate(SCORE_DIMS))
            )
            print("-" * len(eff_header))
            print(eff_header)
            print("-" * len(eff_header))
            for row in effects:
                line = (
                    f"{row['probe']:<{eff_col_w[0]}}"
                    f"{_short_model(row['model']):<{eff_col_w[1]}}"
                )
                for i, dim in enumerate(SCORE_DIMS):
                    delta = row.get(f"{dim}_delta")
                    hw = row.get(f"{dim}_delta_ci95")
                    if delta is None:
                        cell = "n/a"
                    else:
                        sign = "+" if delta >= 0 else ""
                        cell = f"{sign}{delta:.2f} ± {hw:.2f}"
                    line += f"{cell:<{eff_col_w[2 + i]}}"
                print(line)
            print("-" * len(eff_header))


def save_summary_csv(stats: list[dict], effects: list[dict], out_path: Path) -> None:
    """Save statistics and conditioning effects to CSV."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="") as f:
        fieldnames = (
            ["probe", "model", "condition"]
            + [f"{d}_{suffix}" for d in SCORE_DIMS for suffix in ("mean", "ci95", "n")]
        )
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(stats)

    effects_path = out_path.with_name(out_path.stem + "_effects.csv")
    if effects:
        with open(effects_path, "w", newline="") as f:
            fieldnames = (
                ["probe", "model"]
                + [f"{d}_{suffix}" for d in SCORE_DIMS for suffix in ("delta", "delta_ci95")]
            )
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(effects)

    print(f"  Saved: {out_path}")
    if effects:
        print(f"  Saved: {effects_path}")


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze BLOOM behavioral evaluation results",
    )
    parser.add_argument("--probe", default=None,
                        help="Restrict analysis to a single probe name")
    parser.add_argument("--format", choices=["plain", "latex"], default="plain",
                        dest="fmt", help="Output format for summary table")
    parser.add_argument("--no-figures", action="store_true",
                        help="Skip figure generation")
    args = parser.parse_args()

    print(f"Loading records from {RESULTS_DIR} ...")
    records = load_records(probe_filter=args.probe)

    if not records:
        print("No records found. Run the pipeline first (python -m src.orchestrator ...).",
              file=sys.stderr)
        sys.exit(1)

    probes = sorted({r["probe"] for r in records})
    models = sorted({r["model"] for r in records})
    conditions = sorted({r["condition"] for r in records})
    print(f"  {len(records)} records | {len(probes)} probe(s) | "
          f"{len(models)} model(s) | conditions: {conditions}")

    # Statistics
    stats = compute_statistics(records)
    effects = compute_conditioning_effect(records)

    # Print summary
    print()
    print_summary_table(stats, effects, fmt=args.fmt)

    # Save CSV
    save_summary_csv(stats, effects, RESULTS_DIR / "summary.csv")

    # Figures
    if not args.no_figures and HAS_MATPLOTLIB:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        print("\nGenerating figures ...")
        plot_heatmap_profiling(records, FIGURES_DIR / "heatmap_profiling.png")
        plot_conditioning_effect(records, effects, FIGURES_DIR / "conditioning_effect.png")
        plot_score_distributions(records, FIGURES_DIR / "score_distributions.png")
    elif args.no_figures:
        print("Figures skipped (--no-figures).")

    print("\nDone.")


if __name__ == "__main__":
    main()
