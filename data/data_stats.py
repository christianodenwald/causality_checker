from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

from src.main import load_vignettes, load_queries
from src.helpers import load_other_models_group_map

import pandas as pd

data_dir = Path(__file__).resolve().parent
vignettes = load_vignettes(data_dir / 'vignettes.csv', data_dir / 'variables.csv')
queries = load_queries(data_dir / 'queries.csv')

# Load model group map for deduplication
model_group_map = load_other_models_group_map(data_dir / 'vignettes.csv')

# Calculate vignette statistics
total_vignettes = len(vignettes)
vignettes_with_nl = len([v for v in vignettes.values() if v.vignette_text is not None])

# Deduplicated: keep only one per model group
unique_groups = len(set(model_group_map.values()))
unique_groups_with_nl = len(set(
    model_group_map[v_id] 
    for v_id in model_group_map 
    if v_id in vignettes and vignettes[v_id].vignette_text is not None
))

# Calculate query statistics
total_queries = len(queries)
queries_with_nl = len([q for q in queries if q.v_id in vignettes and vignettes[q.v_id].vignette_text is not None])

# Deduplicated queries (select one representative vignette per model_group)
# Select a representative vignette id for each model_group (prefer one that
# actually appears in the queries list) and count the queries for that
# representative. This mirrors how analysis selects a single model per group.
from collections import defaultdict
group_to_vids = defaultdict(list)
for vid, grp in model_group_map.items():
    group_to_vids[grp].append(vid)

rep_counts = 0
rep_counts_nl = 0
for grp, vids in group_to_vids.items():
    vids_in_queries = [v for v in vids if any(q.v_id == v for q in queries)]
    rep = vids_in_queries[0] if vids_in_queries else vids[0]
    q_count = sum(1 for q in queries if q.v_id == rep)
    rep_counts += q_count
    if rep in vignettes and vignettes[rep].vignette_text is not None:
        rep_counts_nl += q_count

unique_query_groups = rep_counts
unique_query_groups_with_nl = rep_counts_nl

# Build a single combined table with vignette and query metrics
metrics = [
    'Total',
    'With NL description',
    'Unique (deduplicated)',
    'Unique + NL',
]

vignette_counts = [
    total_vignettes,
    vignettes_with_nl,
    unique_groups,
    unique_groups_with_nl,
]

query_counts = [
    total_queries,
    queries_with_nl,
    unique_query_groups,
    unique_query_groups_with_nl,
]

combined = pd.DataFrame({
    'Metric': metrics,
    'Vignettes': vignette_counts,
    'Queries': query_counts,
})

print("=" * 60)
print("DATASET STATISTICS")
print("=" * 60)
print(combined.to_string(index=False))