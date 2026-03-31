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

### Theories of Actual Causation (HP2005/HP2015):

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

#### Extensions

Some extensions to the "standard" SCMs are already implemented.
In particular: normality, contrastive causes, and compound causes.

##### Compound Causes
Causes don't have to be primitive events, but they can also be conjuncts of primitive causes.

##### Normality
There are different ways of defining normality in the literature. 
We implement "small worlds" (cf. Halpern and Hitchcock 2015). 
This only requires default and deviant values for each exogenous variables. If these are not given, 0 is taken as default.

##### Contrasts
Some think that causes are contrastive, i.e., it is not enough to ask *"Is C=c a cause of E=e?"*, but one should rather ask *"Is C=c rather than C=c\* a cause of E=e rather than E=e\*?"*. 
Contrastive cause and effect values can be added in `queries.csv`in the respective columns.

In HP-type theories, this will result in AC2 being restricted to c'=c\* and e'=e\* (i.e., in the counterfactual, C and E have to take the specific values c\* and e\* rather than just any values that differ from the actual values c and e). 
In the case of binary variables (which most are), every cause is automatically contrastive.



### LLM Evaluation (Ollama or OpenAI):

in ```src/llm.py```:

```python
queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)
llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, cot=False, model=model)

```

Provider selection is inferred from `model`:
- OpenAI: if it starts with `gpt`
- Ollama: any other model string (for example `llama3.2`, `gemma3`, `ministral-3`)

If running this script for an OpenAI model, ensure the openai package is available and the API key is set.



## Data

- `data/vignettes.csv`: vignettes with natural language text, variables, and context values
- `data/variables.csv`: structural equations and ranges per variable
- `data/queries.csv`: cause-effect queries with ground-truth labels (intuition, HP05, HP15, etc.)
- `data/VERSION.md`: manual data version and change log
- `outputs/`: evaluation results saved as `causality_results_{theory/model}_{gt}_{scope}.csv`

## Add New Vignettes

One way to add a new vignette is to edit the `.csv` files in `data/*.csv`. 

Another way is to use the JSON template in `data/new_vignettes_template.json`.
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
