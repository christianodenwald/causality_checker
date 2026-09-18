from pathlib import Path

import pandas as pd


data_dir = Path(__file__).resolve().parent
vignettes = pd.read_csv(data_dir / "vignettes.csv")
models = pd.read_csv(data_dir / "models.csv")
queries = pd.read_csv(data_dir / "queries.csv")


def non_empty(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("")


vignette_ids_with_nl = set(vignettes.loc[non_empty(vignettes["vignette_text"]), "v_id"])
models_with_nl = models[models["vignette_id"].isin(vignette_ids_with_nl)]

# The benchmark selects the best-performing model for each vignette. The
# selection does not affect its size because alternative models for a vignette
# have matching total and NL query counts.
query_stats_by_model = (
    queries.assign(has_nl=non_empty(queries["query_text"]))
    .groupby("model_id", as_index=True)
    .agg(query_count=("model_id", "size"), nl_query_count=("has_nl", "sum"))
)

model_stats = models[["v_id", "vignette_id"]].copy()
model_stats = model_stats.join(query_stats_by_model, on="v_id")
model_stats[["query_count", "nl_query_count"]] = (
    model_stats[["query_count", "nl_query_count"]].fillna(0).astype(int)
)

counts_per_vignette = model_stats.groupby("vignette_id")[["query_count", "nl_query_count"]].nunique()
inconsistent_vignettes = counts_per_vignette[(counts_per_vignette > 1).any(axis=1)].index.tolist()
if inconsistent_vignettes:
    raise ValueError(
        "Benchmark query count depends on which model is selected for: "
        + ", ".join(inconsistent_vignettes)
    )

benchmark_stats = model_stats.groupby("vignette_id")[["query_count", "nl_query_count"]].first()

summary = pd.DataFrame(
    [
        {
            "Vignettes (NL)": f"{len(vignettes)} ({len(vignette_ids_with_nl)})",
            "Models (NL)": f"{len(models)} ({len(models_with_nl)})",
            "Benchmark queries (NL)": (
                f"{int(benchmark_stats['query_count'].sum())} "
                f"({int(benchmark_stats['nl_query_count'].sum())})"
            ),
        }
    ]
)

print("=" * 60)
print("DATASET STATISTICS")
print("=" * 60)
print(summary.to_string(index=False))
