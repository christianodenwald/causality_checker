# Causality Checker

Accompanying code for "A Comprehensive Collection of Vignettes for Actual Causation". Implements Halpern–Pearl 2005/2015 definitions and evaluates LLM causality judgments.

## Setup

```bash
conda create -n causality_checker python=3.11 -y
conda activate causality_checker
pip install numpy pandas sympy ollama
```

For LLM evaluation: `brew install ollama && ollama pull llama3.2`

## Usage

**Deterministic evaluation** (HP2005/HP2015):
```python
from src.main import load_vignettes, load_queries, evaluate_all_queries

vignettes = load_vignettes('data/vignettes.csv', 'data/variables.csv')
queries = load_queries('data/queries.csv')
df = evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', save=True)
```

**LLM evaluation** (requires Ollama):
```bash
python src/llm.py  # Edit model/cot settings in __main__
```

**Single query**:
```python
from src.main import run_single_query
run_single_query(vignettes, queries, query_id='rock_bottle_q6', theory='HP2015')
```

## Data

- `data/vignettes.csv`: vignettes with natural language text, variables, and context values
- `data/variables.csv`: structural equations and ranges per variable
- `data/queries.csv`: cause-effect queries with ground-truth labels (intuition, HP05, HP15, etc.)
- `outputs/`: evaluation results saved as `causality_results_{theory}_{gt}_{scope}.csv`

Convert Excel sources: `python src/update_csv.py`

## Citation

Please cite the accompanying paper when using this code or dataset.
