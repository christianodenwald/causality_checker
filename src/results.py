from pathlib import Path

import pandas as pd


CM_COLS = ["TP", "TN", "FP", "FN"]

OUTPUT_DIR = Path("outputs/pre-subm/")


def short_name(path: Path) -> str:
    name = path.stem
    if "causality_results_" in name:
        name = name.split("causality_results_", 1)[1]
    if "_intuition" in name:
        name = name.split("_intuition", 1)[0]
    return name


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


def summarize_file(path: Path) -> dict:
    df = ensure_confusion(pd.read_csv(path))
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
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "F1": round(f1, 4),
    }


def main() -> None:
    files = [
        Path(OUTPUT_DIR / "causality_results_HP2005_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_HP2015_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_llama3.2_intuition_all_queries.csv"),
        # Path(OUTPUT_DIR / "causality_results_llama3.2_cot_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_ministral-3_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_ministral-3_cot_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_gemma3_intuition_all_queries.csv"),
        Path(OUTPUT_DIR / "causality_results_gemma3_cot_intuition_all_queries.csv")
    ]
    save_path = None  # e.g. Path("outputs/results_summary_metrics.csv")

    rows = [summarize_file(p) for p in files]
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    if save_path:
        summary.to_csv(save_path, index=False)


if __name__ == "__main__":
    main()
