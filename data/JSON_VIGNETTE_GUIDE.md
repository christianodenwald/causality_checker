# JSON Guide: Adding New Vignettes

This guide explains how to fill in `data/new_vignettes_template.json`.

Use this workflow:
1. Fill the JSON file.
2. Validate without writing:
   - `python tools/add_vignettes_from_json.py --json data/new_vignettes_template.json --dry-run`
3. If validation passes, import:
   - `python tools/add_vignettes_from_json.py --json data/new_vignettes_template.json`

## Top-Level Structure

Your file must contain a top-level key called `vignettes` with a list:

```json
{
  "vignettes": [
    {
      "v_id": "...",
      "se_id": "...",
      "title": "...",
      "vignette_text": "...",
      "variable_order": ["A", "B", "E"],
      "context": [1, 0],
      "metadata": { ... },
      "variables": [ ... ],
      "queries": [ ... ]
    }
  ]
}
```

## Vignette Fields

Required fields:
- `v_id`: unique vignette identifier (string). Must not already exist in `data/vignettes.csv`.
- `se_id`: setting/equation system id (string). Note: some vignettes can share the same structural equations but differ in the context values
- `title`: short label for the vignette. Merely for aesthetics.
- `vignette_text`: natural language scenario text. Needed for LLM evaluation.
- `variable_order`: ordered list of variable names. Note: some vignettes do not have a unique order, but that doesn't matter. The only requirement is that all parent variables are set before the child variable is evaluated.
- `context`: list of values aligned with `variable_order`. Depending on the length of this list, this will set the context (explanation below).

Optional fields:
- `metadata`: object for additional vignette columns such as:
  - `other_names`, `description`, `origin`, `taken_from`, `equivalent_to`, `other_models`, `similar`, `notes`

### Important: `variable_order` and `context`

`context` is positional. Indexes must match `variable_order`.

Example:
- `variable_order = ["A", "B", "E"]`
- `context = [1, 0]`

This means:
- `A=1`
- `B=0`
- `E`is endogenous.

Rules:
- `variable_order` must be a list.
- `context` must be a list.
- `context` cannot be longer than `variable_order`.

## Variable Definitions (`variables`)

`variables` is a list of variable objects. Each object is one row for `data/variables.csv`.

Required variable fields:
- `variable_name`: name of variable (for example `A`, `B`, `E`).
- `range`: allowed values list.

Recommended fields:
- `var_description`: human-readable description.
- `default_values`: default value (if nothing is entered, default is 0. Only needed if normality is being taken into consideration).
- `deviant_values`: deviant value (only needed for normality).
- `structural_equation`: equation for endogenous variables.

### Expected value formats

- Binary variable:
  - `range: [0, 1]`
  - `default_values: 0`
  - `deviant_values: 1`
- Ternary variable:
  - `range: [-1, 0, 1]`
  - choose defaults/deviants from this set.

### Structural equations

- Exogenous variable: keep `structural_equation` empty (`""`).
- Endogenous variable: provide an expression, for example:
  - `"A and B"`
  - `"A or B"`
  - `"not A"`
  - `"(A and B) or C"`

Use variable names consistently with `variable_order` and `variables`.

## Query Definitions (`queries`)

`queries` is a list of query objects. At least one query is required per vignette.

Required query fields:
- `cause` (for example `"A=1"` or `"A=1 and B=1"`)
- `effect` (for example `"E=1"`)
- `query_text` (natural language question)

Optional query fields:
- `cause_contrast`, `effect_contrast`, `core_query`
- theory labels and sources: `intuition`, `HP01`, `HP05`, `HP15`, `H01`, `H07`, `Hall`, `Baumgartner13`, `AG24`, `G21`, `BV18` and their `*_source` columns.
- `notes`

### Label values

For label fields such as `intuition`, `HP05`, `HP15`:
- Use `1` for yes/true.
- Use `0` for no/false.
- Leave empty (`""`) if unknown/not provided.

## Reusing an Existing `se_id`

You can reuse an existing setting id (`se_id`) if you want to use equations that already exist in `data/variables.csv`.

Rules when reusing:
- Set `se_id` to an existing value.
- Leave `variables` empty (`[]`).

Rules for new settings:
- If `se_id` is new, you must provide `variables`.

## Multiple New Vignettes in One File

You can add multiple entries by adding more objects to `vignettes`:

```json
{
  "vignettes": [
    { "v_id": "v1", "se_id": "s1", "title": "...", "vignette_text": "...", "variable_order": ["A"], "context": [1], "variables": [{"variable_name": "A", "range": [0, 1], "structural_equation": ""}], "queries": [{"cause": "A=1", "effect": "A=1", "query_text": "..."}] },
    { "v_id": "v2", "se_id": "s2", "title": "...", "vignette_text": "...", "variable_order": ["B"], "context": [0], "variables": [{"variable_name": "B", "range": [0, 1], "structural_equation": ""}], "queries": [{"cause": "B=0", "effect": "B=0", "query_text": "..."}] }
  ]
}
```

## Final Checklist Before Import

- JSON is valid (no trailing commas, balanced braces/brackets).
- `v_id` values are unique.
- `se_id` usage is consistent with `variables`.
- `variable_order` and `context` are aligned.
- Each vignette has at least one query.
- Dry-run command succeeds.
