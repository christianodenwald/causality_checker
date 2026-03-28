# Causality Checker

Accompanying code for "A Comprehensive Collection of Vignettes for Actual Causation". Implements Halpern–Pearl 2005/2015 definitions and evaluates LLM causality judgments.

## Setup

```bash
conda create -n causality_checker python=3.11 -y
conda activate causality_checker
pip install numpy pandas ollama
```

To run with OpenAI models:

```bash
pip install openai
export OPENAI_API_KEY="your_api_key_here"
```

For Ollama-based LLM evaluation: `brew install ollama && ollama pull MODEL`

## Usage

**Theories of actual causation** (HP2005/HP2015):

in ```src/main.py```:

```python
vignettes = load_vignettes(vignettes_path, variables_path)
queries = load_queries(queries_path)
df = evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', save=True)
```

Single query:
```python
result = run_single_query(vignettes, queries, query_id='rock_bottle_noisy_q111', theory='HP2005', gt='HP05', verbose=True)

```

**LLM evaluation** (Ollama or OpenAI):

in ```src/llm.py```:

```python
queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)
llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, cot=False, model=model)

```

Provider selection is inferred from `model`:
- OpenAI: if it starts with `gpt`
- Ollama: any other model string (for example `llama3.2`, `gemma3`, `ministral-3`)


## Data

- `data/vignettes.csv`: vignettes with natural language text, variables, and context values
- `data/variables.csv`: structural equations and ranges per variable
- `data/queries.csv`: cause-effect queries with ground-truth labels (intuition, HP05, HP15, etc.)
- `data/VERSION.md`: manual data version and change log
- `outputs/`: evaluation results saved as `causality_results_{theory/model}_{gt}_{scope}.csv`

## Add New Vignettes

Use the JSON template in `data/new_vignettes_template.json` to add one or more new vignettes with their variables and queries.
For detailed field-by-field instructions and expected variable values, see `data/JSON_VIGNETTE_GUIDE.md`.

1. Fill out `data/new_vignettes_template.json` (or copy it to a new JSON file).
2. Validate without writing files:

```bash
python tools/add_vignettes_from_json.py --json data/new_vignettes_template.json --dry-run
```

3. If validation succeeds, write the rows into the CSVs:

```bash
python tools/add_vignettes_from_json.py --json data/new_vignettes_template.json
```

This appends entries to:
- `data/vignettes.csv`
- `data/variables.csv`
- `data/queries.csv`

<!-- ## Citation

Please cite the accompanying paper when using this code or dataset. -->
