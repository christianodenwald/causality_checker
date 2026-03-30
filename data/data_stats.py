from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

from src.main import load_vignettes, load_queries


data_dir = Path(__file__).resolve().parent
vignettes = load_vignettes(data_dir / 'vignettes.csv', data_dir / 'variables.csv')
queries = load_queries(data_dir / 'queries.csv')

print(f"Number of vignettes: {len(vignettes)}")
print(f"with natural language description: {len([v for v in vignettes.values() if v.vignette_text is not None])}")
print(f"Number of queries: {len(queries)}")
print(f"with natural language description: {len([q for q in queries if vignettes[q.vignette_id].vignette_text is not None])}")