from pathlib import Path
from datetime import datetime
import sys
import os
import math

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.helpers import (
        load_other_models_group_map,
        select_single_model_per_group,
    )
except ModuleNotFoundError:
    from helpers import (
        load_other_models_group_map,
        select_single_model_per_group,
    )


CM_COLS = ["TP", "TN", "FP", "FN"]

DEFAULT_INPUT_DIR = Path("outputs/")
DEFAULT_OUTPUT_ROOT = Path("outputs/analysis")
DEFAULT_VIGNETTES_PATH = Path("data/vignettes.csv")


def filter_by_model_group(df: pd.DataFrame, vignettes_path: Path = DEFAULT_VIGNETTES_PATH) -> pd.DataFrame:
    """Filter dataframe to single model per group using the model-group map from vignettes.
    
    This is called during analysis to deduplicate models that are variants of the same base model.
    Args:
        df: DataFrame with results (must have 'v_id', 'result', 'groundtruth' columns)
        vignettes_path: Path to vignettes CSV for loading model-group mappings
    
    Returns:
        Filtered DataFrame with single model selected per group
    """
    model_group_map = load_other_models_group_map(vignettes_path)
    return select_single_model_per_group(df, model_group_map)


def short_name(path: Path) -> str:
    name = path.stem
    if "causality_results_" in name:
        name = name.split("causality_results_", 1)[1]
    if "_intuition" in name:
        name = name.split("_intuition", 1)[0]
    return name


def normalize_vignette_id(value: object) -> str:
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def load_vignette_ids_with_text(vignettes_path: Path = DEFAULT_VIGNETTES_PATH) -> set[str]:
    vignettes = pd.read_csv(vignettes_path)
    if "v_id" not in vignettes.columns or "vignette_text" not in vignettes.columns:
        raise ValueError(
            f"Expected columns 'v_id' and 'vignette_text' in {vignettes_path}."
        )
    text_col = vignettes["vignette_text"].astype("string")
    keep = vignettes[text_col.notna() & text_col.str.strip().ne("")]
    return {normalize_vignette_id(v) for v in keep["v_id"]}


def to_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    ).astype("boolean")


def ensure_confusion(df: pd.DataFrame) -> pd.DataFrame:
    if set(CM_COLS).issubset(df.columns):
        out = df.copy()
        for c in CM_COLS:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
        return out

    pred = to_bool(df["result"])
    gt = to_bool(df["groundtruth"])
    d = pred.notna() & gt.notna()
    out = df.copy()
    out["TP"] = ((pred == True) & (gt == True)).where(d, pd.NA).astype("Int64")
    out["TN"] = ((pred == False) & (gt == False)).where(d, pd.NA).astype("Int64")
    out["FP"] = ((pred == True) & (gt == False)).where(d, pd.NA).astype("Int64")
    out["FN"] = ((pred == False) & (gt == True)).where(d, pd.NA).astype("Int64")
    return out


def wilson_ci_95(successes: int, n: int) -> tuple[float, float]:
    """Return the two-sided 95% Wilson confidence interval for a binomial proportion."""
    if n <= 0:
        return 0.0, 0.0

    z = 1.959963984540054
    p_hat = successes / n
    z2_over_n = (z * z) / n
    denom = 1.0 + z2_over_n
    center = (p_hat + (z2_over_n / 2.0)) / denom
    spread = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / n) + ((z * z) / (4.0 * n * n)))
    lo = max(0.0, center - spread)
    hi = min(1.0, center + spread)
    return lo, hi


def bootstrap_f1_ci_95(pred: pd.Series, gt: pd.Series, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """Return percentile bootstrap 95% CI for F1 score from aligned prediction/groundtruth booleans."""
    valid = pred.notna() & gt.notna()
    pred_arr = pred[valid].astype(bool).to_numpy()
    gt_arr = gt[valid].astype(bool).to_numpy()

    n = int(pred_arr.size)
    if n == 0:
        return 0.0, 0.0

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    pred_bs = pred_arr[idx]
    gt_bs = gt_arr[idx]

    tp = np.sum(pred_bs & gt_bs, axis=1)
    fp = np.sum(pred_bs & (~gt_bs), axis=1)
    fn = np.sum((~pred_bs) & gt_bs, axis=1)

    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp, dtype=float), where=(tp + fp) != 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp, dtype=float), where=(tp + fn) != 0)
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision, dtype=float),
        where=(precision + recall) != 0,
    )

    lo, hi = np.percentile(f1, [2.5, 97.5])
    return float(lo), float(hi)


def _apply_text_filter(
    df: pd.DataFrame,
    only_with_vignette_text: bool,
    text_vignette_ids: set[str] | None,
    path: Path,
) -> pd.DataFrame:
    if not only_with_vignette_text:
        return df

    if "vignette_text" not in df.columns:
        if "v_id" not in df.columns:
            raise ValueError(
                f"Neither 'vignette_text' nor 'v_id' is available in {path.name}; cannot apply text-only vignette filter."
            )
        if text_vignette_ids is None:
            raise ValueError(
                f"Column 'vignette_text' is missing in {path.name}; provide text_vignette_ids to filter by v_id."
            )
        normalized_ids = df["v_id"].map(normalize_vignette_id)
        mask = normalized_ids.isin(text_vignette_ids)

        # Some result files use generic v_id labels (e.g., "engineer") while
        # query_id encodes the specific vignette (e.g., "engineer3_q40").
        if "query_id" in df.columns:
            query_prefix = (
                df["query_id"]
                .astype("string")
                .str.split("_q", n=1)
                .str[0]
                .map(normalize_vignette_id)
            )
            mask = mask | query_prefix.isin(text_vignette_ids)

        return df[mask].copy()

    text_col = df["vignette_text"].astype("string")
    return df[text_col.notna() & text_col.str.strip().ne("")].copy()


def _load_eval_frame(
    path: Path,
    only_with_vignette_text: bool,
    text_vignette_ids: set[str] | None,
    apply_model_group_filter_flag: bool,
) -> pd.DataFrame:
    df = pd.read_csv(path)
    if apply_model_group_filter_flag:
        df = filter_by_model_group(df)
    df = _apply_text_filter(df, only_with_vignette_text, text_vignette_ids, path)
    return df


def summarize_file(
    path: Path,
    only_with_vignette_text: bool = False,
    text_vignette_ids: set[str] | None = None,
    apply_model_group_filter_flag: bool = False,
) -> dict:
    df = _load_eval_frame(
        path=path,
        only_with_vignette_text=only_with_vignette_text,
        text_vignette_ids=text_vignette_ids,
        apply_model_group_filter_flag=apply_model_group_filter_flag,
    )

    df = ensure_confusion(df)
    if df[CM_COLS].isna().any().any():
        na_rows = df[df[CM_COLS].isna().any(axis=1)].index.tolist()
        raise ValueError(f"NA found in TP/TN/FP/FN for {path.name} at rows {na_rows[:10]}")

    tp, tn, fp, fn = (int(df[c].sum()) for c in CM_COLS)
    n = tp + tn + fp + fn
    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    acc_ci_low, acc_ci_high = wilson_ci_95(tp + tn, n)
    pred = to_bool(df["result"])
    gt = to_bool(df["groundtruth"])
    f1_ci_low, f1_ci_high = bootstrap_f1_ci_95(pred, gt, n_boot=2000, seed=0)
    return {
        "file": short_name(path),
        "n": int(len(df)),
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "F1": round(f1, 4),
        "accuracy_ci_low": round(acc_ci_low, 4),
        "accuracy_ci_high": round(acc_ci_high, 4),
        "f1_ci_low": round(f1_ci_low, 4),
        "f1_ci_high": round(f1_ci_high, 4),
    }


def ensure_output_dirs(root: Path) -> tuple[Path, Path]:
    summaries_dir = root / "summaries"
    charts_dir = root / "charts"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    return summaries_dir, charts_dir


def save_performance_chart(summary: pd.DataFrame, charts_dir: Path, stamp: str) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
    except ImportError:
        print("Skipping chart generation: matplotlib is not installed.")
        print("Install it with: pip install matplotlib")
        return

    summary_sorted = summary.sort_values("accuracy", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = list(range(len(summary_sorted)))
    width = 0.38

    acc = pd.to_numeric(summary_sorted["accuracy"], errors="coerce").fillna(0.0)
    f1 = pd.to_numeric(summary_sorted["F1"], errors="coerce").fillna(0.0)
    lo = pd.to_numeric(summary_sorted.get("accuracy_ci_low", pd.Series([0.0] * len(summary_sorted))), errors="coerce").fillna(0.0)
    hi = pd.to_numeric(summary_sorted.get("accuracy_ci_high", pd.Series([0.0] * len(summary_sorted))), errors="coerce").fillna(0.0)
    lower_err = (acc - lo).clip(lower=0.0)
    upper_err = (hi - acc).clip(lower=0.0)

    ax.bar(
        [i - width / 2 for i in x],
        acc,
        width=width,
        label="accuracy",
        yerr=[lower_err.to_numpy(), upper_err.to_numpy()],
        capsize=3,
        error_kw={"elinewidth": 1.2, "alpha": 0.9},
    )
    ax.bar([i + width / 2 for i in x], f1, width=width, alpha=0.8, label="F1")

    ax.set_xticks(x)
    ax.set_xticklabels(summary_sorted["file"], rotation=35, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("score")
    ax.set_title("Model performance (accuracy with 95% Wilson CI)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(charts_dir / f"performance_accuracy_f1_{stamp}.png"), dpi=180)
    fig.savefig(str(charts_dir / "performance_accuracy_f1_latest.png"), dpi=180)
    plt.close(fig)


def save_confusion_chart(summary: pd.DataFrame, charts_dir: Path, stamp: str) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
    except ImportError:
        print("Skipping chart generation: matplotlib is not installed.")
        print("Install it with: pip install matplotlib")
        return

    summary_sorted = summary.sort_values("accuracy", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(summary_sorted))
    ax.bar(x, summary_sorted["TP"], label="TP")
    ax.bar(x, summary_sorted["TN"], bottom=summary_sorted["TP"], label="TN")
    ax.bar(
        x,
        summary_sorted["FP"],
        bottom=summary_sorted["TP"] + summary_sorted["TN"],
        label="FP",
    )
    ax.bar(
        x,
        summary_sorted["FN"],
        bottom=summary_sorted["TP"] + summary_sorted["TN"] + summary_sorted["FP"],
        label="FN",
    )
    ax.set_xticks(list(x), summary_sorted["file"], rotation=35, ha="right")
    ax.set_ylabel("count")
    ax.set_title("Confusion matrix totals")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(charts_dir / f"confusion_totals_{stamp}.png"), dpi=180)
    fig.savefig(str(charts_dir / "confusion_totals_latest.png"), dpi=180)
    plt.close(fig)


def save_f1_grouped_chart(summary: pd.DataFrame, charts_dir: Path, stamp: str) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore[reportMissingImports]
    except ImportError:
        print("Skipping chart generation: matplotlib is not installed.")
        print("Install it with: pip install matplotlib")
        return

    # Group prompt variants per base model and plot F1 only.
    f1_df = summary[["file", "F1", "f1_ci_low", "f1_ci_high"]].copy()

    def split_model_variant(name: str) -> tuple[str, str]:
        if name.endswith("_normality"):
            return name[: -len("_normality")], "theory+normality"
        if name.endswith("_few_shot"):
            return name[: -len("_few_shot")], "few_shot"
        if name.endswith("_cot"):
            return name[: -len("_cot")], "cot"
        if name in ("HP2005", "HP2015"):
            return name, "theory"
        return name, "zero_shot"

    parsed = f1_df["file"].map(split_model_variant)
    f1_df["model"] = parsed.map(lambda x: x[0])
    f1_df["variant"] = parsed.map(lambda x: x[1])

    # Separate theories and LLMs
    theory_variants = ["theory", "theory+normality"]
    llm_variants = ["zero_shot", "few_shot", "cot"]
    
    theory_models = {"HP2005", "HP2015"}
    
    # Create pivot table with all possible variants
    all_variants = theory_variants + llm_variants
    pivot = (
        f1_df.pivot_table(index="model", columns="variant", values="F1", aggfunc="first")
        .reindex(columns=all_variants)
        .fillna(0.0)
    )
    pivot_ci_low = f1_df.pivot_table(index="model", columns="variant", values="f1_ci_low", aggfunc="first").reindex(columns=all_variants)
    pivot_ci_high = f1_df.pivot_table(index="model", columns="variant", values="f1_ci_high", aggfunc="first").reindex(columns=all_variants)

    preferred_prefix_order = {"llama": 0, "ministral": 1, "gemma": 2, "gpt": 3, "hp": 4}

    def model_sort_key(model_name: str) -> tuple[int, str]:
        lowered = model_name.lower()
        for prefix, rank in preferred_prefix_order.items():
            if lowered.startswith(prefix):
                return rank, lowered
        return 99, lowered

    model_order = sorted(pivot.index.tolist(), key=model_sort_key)

    fig, ax = plt.subplots(figsize=(14, 6))
    width = 0.3

    # Keep a constant edge-to-edge gap between groups, even when group widths differ.
    group_gap = width * 0.5
    group_sizes = {
        model: (len(theory_variants) if model in theory_models else len(llm_variants))
        for model in model_order
    }
    x_centers: list[float] = []
    for idx, model in enumerate(model_order):
        if idx == 0:
            x_centers.append(0.0)
            continue
        prev_model = model_order[idx - 1]
        prev_span = group_sizes[prev_model] * width
        curr_span = group_sizes[model] * width
        next_center = x_centers[-1] + (prev_span / 2) + group_gap + (curr_span / 2)
        x_centers.append(next_center)
    model_center = {model: center for model, center in zip(model_order, x_centers)}

    variant_labels = {
        "theory": "theory", "theory+normality": "theory+normality",
        "zero_shot": "zero-shot", "few_shot": "few-shot", "cot": "chain-of-thought"
    }
    
    # Define consistent colors for each variant
    # variant_colors = {
    #     "theory": "#E94B3C",        # rust red
    #     "theory+normality": "#F1A619",   # gold
    #     "zero_shot": "#2E8B57",     # sea green
    #     "few_shot": "#4169E1",      # royal blue
    #     "cot": "#9370DB"            # medium purple
    # }

    color_string = "#0088FE #00C49F #FFBB28 #FF8042 #8884d8".split(' ') # colorblind friendly palette
    variant_colors = {
        "theory": color_string[2],
        "theory+normality": color_string[3],
        "zero_shot": color_string[0],
        "few_shot": color_string[1],
        "cot": color_string[4]

    }

    # Plot bars for each model
    added_labels = set()
    for model_idx, model in enumerate(model_order):
        is_theory = model in theory_models
        variants_to_plot = theory_variants if is_theory else llm_variants
        num_variants = len(variants_to_plot)
        center_idx = (num_variants - 1) / 2

        for bar_idx, variant in enumerate(variants_to_plot):
            val = pd.to_numeric(pivot.loc[model, variant], errors="coerce")
            if val == 0.0 and variant not in f1_df[f1_df["model"] == model]["variant"].values:
                continue  # Skip if variant doesn't exist for this model
            offset = model_center[model] + (bar_idx - center_idx) * width
            label = variant_labels[variant] if variant not in added_labels else None
            lo = pd.to_numeric(pivot_ci_low.loc[model, variant], errors="coerce")
            hi = pd.to_numeric(pivot_ci_high.loc[model, variant], errors="coerce")
            lower_err = max(0.0, float(val - lo)) if pd.notna(lo) else 0.0
            upper_err = max(0.0, float(hi - val)) if pd.notna(hi) else 0.0
            ax.bar(
                offset,
                val,
                width=width,
                label=label,
                color=variant_colors[variant],
                yerr=[[lower_err], [upper_err]],
                capsize=3,
                error_kw={"elinewidth": 1.1, "alpha": 0.9},
            )
            added_labels.add(variant)

    ax.set_xticks(x_centers)
    ax.set_xticklabels(model_order, fontsize=18)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("F1", fontsize=22)
    ax.tick_params(axis="y", labelsize=18)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    legend = ax.legend(title="", loc="upper left", framealpha=0.95, fontsize=13.5, title_fontsize=18)
    fig.tight_layout()
    fig.savefig(str(charts_dir / f"f1_grouped_by_model_{stamp}.png"), dpi=180)
    fig.savefig(str(charts_dir / "f1_grouped_by_model_latest.png"), dpi=180)
    plt.close(fig)


def save_selected_chart(summary: pd.DataFrame, charts_dir: Path, stamp: str, chart: str) -> None:
    if chart == "performance":
        save_performance_chart(summary, charts_dir, stamp)
        print("Saved chart: performance_accuracy_f1")
    elif chart == "confusion":
        save_confusion_chart(summary, charts_dir, stamp)
        print("Saved chart: confusion_totals")
    elif chart == "f1":
        save_f1_grouped_chart(summary, charts_dir, stamp)
        print("Saved chart: f1_grouped_by_model")


def _exact_binomial_two_sided_pvalue(n_discordant: int, smaller_count: int) -> float:
    """Exact two-sided p-value for McNemar via Binomial(n_discordant, 0.5)."""
    if n_discordant <= 0:
        return 1.0

    cumulative = 0.0
    for i in range(0, smaller_count + 1):
        cumulative += math.comb(n_discordant, i) * (0.5 ** n_discordant)

    return min(1.0, 2.0 * cumulative)


def run_pairwise_mcnemar_test(
    path_a: Path,
    path_b: Path,
    label_a: str,
    label_b: str,
    only_with_vignette_text: bool,
    text_vignette_ids: set[str] | None,
    apply_model_group_filter: bool,
) -> dict:
    """Run paired McNemar test on query-level correctness between two result files."""
    df_a = _load_eval_frame(
        path=path_a,
        only_with_vignette_text=only_with_vignette_text,
        text_vignette_ids=text_vignette_ids,
        apply_model_group_filter_flag=apply_model_group_filter,
    )
    df_b = _load_eval_frame(
        path=path_b,
        only_with_vignette_text=only_with_vignette_text,
        text_vignette_ids=text_vignette_ids,
        apply_model_group_filter_flag=apply_model_group_filter,
    )

    if "query_id" not in df_a.columns or "query_id" not in df_b.columns:
        raise ValueError("McNemar test requires 'query_id' in both compared result files.")

    eval_a = pd.DataFrame(
        {
            "query_id": df_a["query_id"].astype("string"),
            "pred_a": to_bool(df_a["result"]),
            "gt_a": to_bool(df_a["groundtruth"]),
        }
    )
    eval_b = pd.DataFrame(
        {
            "query_id": df_b["query_id"].astype("string"),
            "pred_b": to_bool(df_b["result"]),
            "gt_b": to_bool(df_b["groundtruth"]),
        }
    )

    eval_a = eval_a.drop_duplicates(subset=["query_id"], keep="first")
    eval_b = eval_b.drop_duplicates(subset=["query_id"], keep="first")
    merged = eval_a.merge(eval_b, on="query_id", how="inner")

    valid = (
        merged["pred_a"].notna()
        & merged["pred_b"].notna()
        & merged["gt_a"].notna()
        & merged["gt_b"].notna()
        & (merged["gt_a"] == merged["gt_b"])
    )
    aligned = merged[valid].copy()

    if aligned.empty:
        raise ValueError("No aligned valid rows found for McNemar test.")

    correct_a = aligned["pred_a"] == aligned["gt_a"]
    correct_b = aligned["pred_b"] == aligned["gt_a"]

    b_count = int((correct_a & (~correct_b)).sum())
    c_count = int(((~correct_a) & correct_b).sum())
    discordant = b_count + c_count

    exact_p = _exact_binomial_two_sided_pvalue(discordant, min(b_count, c_count))
    chi2_cc = ((abs(b_count - c_count) - 1) ** 2 / discordant) if discordant > 0 else 0.0
    approx_p = math.erfc(math.sqrt(chi2_cc / 2.0)) if discordant > 0 else 1.0

    return {
        "model_a": label_a,
        "model_b": label_b,
        "n_aligned": int(len(aligned)),
        "b_a_correct_b_wrong": b_count,
        "c_a_wrong_b_correct": c_count,
        "discordant": discordant,
        "mcnemar_exact_pvalue": exact_p,
        "mcnemar_chi2_cc": chi2_cc,
        "mcnemar_chi2_cc_pvalue": approx_p,
    }


def save_mcnemar_result(result: dict, summaries_dir: Path, stamp: str) -> None:
    out = pd.DataFrame([result])
    stamped = summaries_dir / f"mcnemar_HP2015_normality_vs_gpt-5.4_few_shot_{stamp}.csv"
    latest = summaries_dir / "mcnemar_HP2015_normality_vs_gpt-5.4_few_shot_latest.csv"
    out.to_csv(stamped, index=False)
    out.to_csv(latest, index=False)
    print(f"Saved McNemar test: {stamped}")
    print(f"Updated latest McNemar test: {latest}")


def build_summary(
    input_dir: Path = DEFAULT_INPUT_DIR,
    pattern: str = "causality_results_*_intuition_all_queries.csv",
    only_with_vignette_text: bool = False,
    text_vignette_ids: set[str] | None = None,
    apply_model_group_filter: bool = False,
) -> pd.DataFrame:
    files = sorted(input_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"No files found in {input_dir} matching pattern {pattern}."
        )

    rows = [
        summarize_file(
            p,
            only_with_vignette_text=only_with_vignette_text,
            text_vignette_ids=text_vignette_ids,
            apply_model_group_filter_flag=apply_model_group_filter,
        )
        for p in files
    ]
    summary = pd.DataFrame(rows)
    return summary


def save_summary(summary: pd.DataFrame, summaries_dir: Path, stamp: str) -> None:
    stamped_summary = summaries_dir / f"results_summary_metrics_{stamp}.csv"
    latest_summary = summaries_dir / "results_summary_metrics_latest.csv"
    summary.to_csv(stamped_summary, index=False)
    summary.to_csv(latest_summary, index=False)
    print(f"Saved summary: {stamped_summary}")
    print(f"Updated latest summary: {latest_summary}")


def prettify_model_name(short: str) -> str:
    """Convert internal model id into publication-friendly display name."""
    mapping = {
        "HP2005": "HP 2005",
        "HP2005_normality": "HP 2005 (Normality)",
        "HP2015": "HP 2015",
        "HP2015_normality": "HP 2015 (Normality)",
    }
    if short in mapping:
        return mapping[short]

    parts = short.split("_")
    base = parts[0]
    variant = parts[1] if len(parts) > 1 else ""

    base_map = {
        "llama3.2": "Llama 3.2",
        "ministral-3": "Ministral 3",
        "gemma3": "Gemma 3",
        "gpt-5.4": "GPT-5.4",
    }
    variant_map = {
        "few": "Few-shot",
        "few_shot": "Few-shot",
        "cot": "CoT",
    }

    pretty_base = base_map.get(base, base)
    if short.endswith("_few_shot"):
        return f"{pretty_base} (Few-shot)"
    if short.endswith("_cot"):
        return f"{pretty_base} (CoT)"
    return pretty_base


def format_p_value(p_value: float | None) -> str:
    if p_value is None:
        return "-"
    if p_value < 0.001:
        return "< 0.001"
    return f"{p_value:.3f}"


def build_publication_table(
    summary: pd.DataFrame,
    input_dir: Path,
    pattern: str,
    only_with_vignette_text: bool,
    text_vignette_ids: set[str] | None,
    apply_model_group_filter: bool,
) -> pd.DataFrame:
    files = sorted(input_dir.glob(pattern))
    path_by_short = {short_name(p): p for p in files}

    baseline_short = "HP2015_normality"
    baseline_path = path_by_short.get(baseline_short)

    rows: list[dict] = []
    for _, row in summary.iterrows():
        short = str(row["file"])
        model_label = prettify_model_name(short)
        acc_lo = float(row["accuracy_ci_low"])
        acc_hi = float(row["accuracy_ci_high"])
        f1_lo = float(row["f1_ci_low"])
        f1_hi = float(row["f1_ci_high"])
        acc_ci = f"[{acc_lo:.2f}, {acc_hi:.2f}]"
        f1_ci = f"[{f1_lo:.2f}, {f1_hi:.2f}]"

        p_value: float | None = None
        if baseline_path is not None and short != baseline_short:
            candidate_path = path_by_short.get(short)
            if candidate_path is not None:
                test = run_pairwise_mcnemar_test(
                    path_a=baseline_path,
                    path_b=candidate_path,
                    label_a="HP 2015 (Normality)",
                    label_b=model_label,
                    only_with_vignette_text=only_with_vignette_text,
                    text_vignette_ids=text_vignette_ids,
                    apply_model_group_filter=apply_model_group_filter,
                )
                p_value = float(test["mcnemar_exact_pvalue"])

        rows.append(
            {
                "Model": model_label,
                "n": int(row["n"]),
                "Precision": round(float(row["precision"]), 2),
                "Recall": round(float(row["recall"]), 2),
                "Accuracy": round(float(row["accuracy"]), 2),
                "Accuracy 95% CI": acc_ci,
                "F1-Score": round(float(row["F1"]), 2),
                "F1 95% CI": f1_ci,
                "p-value": format_p_value(p_value),
            }
        )

    out = pd.DataFrame(rows)
    rank = {"HP 2005": 0, "HP 2005 (Normality)": 1, "HP 2015": 2, "HP 2015 (Normality)": 3}
    out["_rank"] = out["Model"].map(lambda m: rank.get(m, 100))
    out = out.sort_values(by=["_rank", "Model"], kind="stable").drop(columns=["_rank"]).reset_index(drop=True)
    return out


def save_publication_table(table: pd.DataFrame, summaries_dir: Path, stamp: str) -> None:
    stamped = summaries_dir / f"results_summary_publication_{stamp}.csv"
    latest = summaries_dir / "results_summary_publication_latest.csv"
    table.to_csv(stamped, index=False)
    table.to_csv(latest, index=False)
    print(f"Saved publication table: {stamped}")
    print(f"Updated latest publication table: {latest}")


def _format_tex_p_value(value: object) -> str:
    p = str(value).strip()
    if p == "< 0.001":
        return "$< 0.001$"
    if p == "-":
        return "--"
    return p


def _format_metric_with_ci(metric: object, ci: object) -> str:
    try:
        metric_value = float(str(metric))
    except ValueError:
        metric_value = 0.0
    return f"{metric_value:.2f} {str(ci)}"


def save_publication_table_tex(table: pd.DataFrame, tex_path: Path) -> None:
    """Write publication table to a LaTeX file for direct paper inclusion."""
    required_cols = {"Model", "Accuracy", "Accuracy 95% CI", "F1-Score", "F1 95% CI", "p-value"}
    missing = [c for c in required_cols if c not in table.columns]
    if missing:
        raise ValueError(f"Cannot write TeX table. Missing columns: {', '.join(sorted(missing))}")

    n_caption = None
    if "n" in table.columns and not table["n"].empty:
        unique_n = pd.to_numeric(table["n"], errors="coerce").dropna().unique()
        if len(unique_n) == 1:
            n_caption = int(unique_n[0])

    caption = "Performance metrics across models. Only includes queries with an accompanying description in natural language"
    if n_caption is not None:
        caption = f"{caption} (n={n_caption})."
    else:
        caption = f"{caption}."

    lines: list[str] = []
    lines.append("\\begin{table}[htbp]")
    lines.append("    \\centering")
    lines.append(f"    \\caption{{{caption}}}")
    lines.append("    \\label{tab:metrics}")
    lines.append("    \\pdfbookmark[2]{Performance Table}{table}")
    lines.append("    \\begin{tabular}{l|c c c}")
    lines.append("    \\toprule")
    lines.append("    Model & Accuracy & F1-Score & p-value \\\\")
    lines.append("    \\midrule")

    for idx, row in table.iterrows():
        model = str(row["Model"])
        accuracy = _format_metric_with_ci(row["Accuracy"], row["Accuracy 95% CI"])
        f1_score = _format_metric_with_ci(row["F1-Score"], row["F1 95% CI"])
        p_value = _format_tex_p_value(row["p-value"])

        lines.append(f"    {model} & {accuracy} & {f1_score} & {p_value} \\\\")
        if idx == 3:
            lines.append("    \\midrule")

    lines.append("    \\bottomrule")
    lines.append("    \\end{tabular}")
    lines.append("\\end{table}")

    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved LaTeX table: {tex_path}")


def sort_for_terminal_print(summary: pd.DataFrame) -> pd.DataFrame:
    model_order = {"llama3.2": 0, "ministral-3": 1, "gemma3": 2, "gpt-5.4": 3}
    variant_order = {"zero_shot": 0, "few_shot": 1, "cot": 2}

    def split_model_variant(name: str) -> tuple[str, str]:
        if name.endswith("_few_shot"):
            return name[: -len("_few_shot")], "few_shot"
        if name.endswith("_cot"):
            return name[: -len("_cot")], "cot"
        return name, "zero_shot"

    out = summary.copy()
    parsed = out["file"].map(split_model_variant)
    out["_base_model"] = parsed.map(lambda x: x[0])
    out["_variant"] = parsed.map(lambda x: x[1])

    # Theory rows first; LLM rows follow in requested order.
    out["_is_llm"] = out["_base_model"].isin(model_order)
    out["_group_rank"] = out["_is_llm"].map(lambda is_llm: 1 if is_llm else 0)
    out["_model_rank"] = out["_base_model"].map(lambda m: model_order.get(m, 99))
    out["_variant_rank"] = out["_variant"].map(lambda v: variant_order.get(v, 99))

    out = out.sort_values(
        by=["_group_rank", "_model_rank", "_variant_rank", "file"],
        kind="stable",
    )
    return out.drop(
        columns=[
            "_base_model",
            "_variant",
            "_is_llm",
            "_group_rank",
            "_model_rank",
            "_variant_rank",
        ]
    )


if __name__ == "__main__":
    input_dir = DEFAULT_INPUT_DIR
    pattern = "causality_results_*_intuition_all_queries.csv"
    output_root = DEFAULT_OUTPUT_ROOT

    text_vignette_ids = load_vignette_ids_with_text(DEFAULT_VIGNETTES_PATH)

    summary = build_summary(
        input_dir=input_dir,
        pattern=pattern,
        only_with_vignette_text=True,
        text_vignette_ids=text_vignette_ids,
        apply_model_group_filter=True,
    )
    summary_for_print = sort_for_terminal_print(summary)
    print("Summary on vignettes with non-empty vignette_text (used for table + chart):")
    print(summary_for_print.to_string(index=False))

    full_summary = build_summary(
        input_dir=input_dir,
        pattern=pattern,
        only_with_vignette_text=False,
        apply_model_group_filter=True,
    )
    full_summary_for_print = sort_for_terminal_print(full_summary)
    print("\nAdditional printout: full dataset summary (all rows):")
    print(full_summary_for_print.to_string(index=False))

    publication_table = build_publication_table(
        summary=summary,
        input_dir=input_dir,
        pattern=pattern,
        only_with_vignette_text=True,
        text_vignette_ids=text_vignette_ids,
        apply_model_group_filter=True,
    )
    print("\nPublication-style table:")
    print(publication_table.to_string(index=False))

    summaries_dir, charts_dir = ensure_output_dirs(output_root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # hp2015_norm_path = input_dir / "causality_results_HP2015_normality_intuition_all_queries.csv"
    # gpt54_few_shot_path = input_dir / "causality_results_gpt-5.4_few_shot_intuition_all_queries.csv"
    # if hp2015_norm_path.exists() and gpt54_few_shot_path.exists():
    #     mcnemar_result = run_pairwise_mcnemar_test(
    #         path_a=hp2015_norm_path,
    #         path_b=gpt54_few_shot_path,
    #         label_a="HP2015+Norm",
    #         label_b="GPT-5.4 few-shot",
    #         only_with_vignette_text=True,
    #         text_vignette_ids=text_vignette_ids,
    #         apply_model_group_filter=True,
    #     )
    #     print("\nPairwise McNemar test (HP2015+Norm vs GPT-5.4 few-shot):")
    #     print(pd.DataFrame([mcnemar_result]).to_string(index=False))
    #     save_mcnemar_result(mcnemar_result, summaries_dir, stamp)
    # else:
    #     print("\nSkipping McNemar test: required result files not found.")
    #     print(f"Expected: {hp2015_norm_path}")
    #     print(f"Expected: {gpt54_few_shot_path}")

    # Toggle one of these as needed:
    save_summary(summary, summaries_dir, stamp)
    save_publication_table(publication_table, summaries_dir, stamp)
    repo_root = Path(__file__).resolve().parents[1]
    save_publication_table_tex(publication_table, repo_root / "paper" / "performance_metrics_table.tex")
    save_selected_chart(summary, charts_dir, stamp, chart="f1")
    # save_selected_chart(summary, charts_dir, stamp, chart="performance")
    # save_selected_chart(summary, charts_dir, stamp, chart="confusion")
