from pathlib import Path
from datetime import datetime

import pandas as pd


CM_COLS = ["TP", "TN", "FP", "FN"]

DEFAULT_INPUT_DIR = Path("outputs/")
DEFAULT_OUTPUT_ROOT = Path("outputs/analysis")
DEFAULT_VIGNETTES_PATH = Path("data/vignettes.csv")


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


def summarize_file(
    path: Path,
    only_with_vignette_text: bool = False,
    text_vignette_ids: set[str] | None = None,
) -> dict:
    df = pd.read_csv(path)

    if only_with_vignette_text:
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

            df = df[mask].copy()
        else:
            text_col = df["vignette_text"].astype("string")
            df = df[text_col.notna() & text_col.str.strip().ne("")].copy()

    df = ensure_confusion(df)
    if df[CM_COLS].isna().any().any():
        na_rows = df[df[CM_COLS].isna().any(axis=1)].index.tolist()
        raise ValueError(f"NA found in TP/TN/FP/FN for {path.name} at rows {na_rows[:10]}")

    tp, tn, fp, fn = (int(df[c].sum()) for c in CM_COLS)
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
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

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(summary_sorted["file"], summary_sorted["accuracy"], label="accuracy")
    ax.bar(summary_sorted["file"], summary_sorted["F1"], alpha=0.7, label="F1")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("score")
    ax.set_title("Model performance")
    ax.tick_params(axis="x", rotation=35)
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
    f1_df = summary[["file", "F1"]].copy()

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
    variant_colors = {
        "theory": "#E94B3C",        # rust red
        "theory+normality": "#F1A619",   # gold
        "zero_shot": "#2E8B57",     # sea green
        "few_shot": "#4169E1",      # royal blue
        "cot": "#9370DB"            # medium purple
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
            ax.bar(offset, val, width=width, label=label, color=variant_colors[variant])
            added_labels.add(variant)

    ax.set_xticks(x_centers)
    ax.set_xticklabels(model_order, fontsize=18)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("F1", fontsize=22)
    ax.tick_params(axis="y", labelsize=18)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    legend = ax.legend(title="", loc="upper left", framealpha=0.95, fontsize=17, title_fontsize=18)
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


def build_summary(
    input_dir: Path = DEFAULT_INPUT_DIR,
    pattern: str = "causality_results_*_intuition_all_queries.csv",
    only_with_vignette_text: bool = False,
    text_vignette_ids: set[str] | None = None,
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
    )
    summary_for_print = sort_for_terminal_print(summary)
    print("Summary on vignettes with non-empty vignette_text (used for table + chart):")
    print(summary_for_print.to_string(index=False))

    full_summary = build_summary(
        input_dir=input_dir,
        pattern=pattern,
        only_with_vignette_text=False,
    )
    full_summary_for_print = sort_for_terminal_print(full_summary)
    print("\nAdditional printout: full dataset summary (all rows):")
    print(full_summary_for_print.to_string(index=False))

    summaries_dir, charts_dir = ensure_output_dirs(output_root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Toggle one of these as needed:
    save_summary(summary, summaries_dir, stamp)
    save_selected_chart(summary, charts_dir, stamp, chart="f1")
    # save_selected_chart(summary, charts_dir, stamp, chart="performance")
    # save_selected_chart(summary, charts_dir, stamp, chart="confusion")
