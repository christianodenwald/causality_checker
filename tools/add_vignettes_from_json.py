import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

VIGNETTE_REQUIRED = ["v_id", "se_id", "vignette_text", "variable_order", "context", "title"]
VARIABLE_REQUIRED = ["se_id", "variable_name", "range", "structural_equation"]
QUERY_REQUIRED = ["v_id", "cause", "effect", "query_text"]


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _validate_columns(df: pd.DataFrame, required: List[str], name: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _as_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value)
    return str(value)


def _build_vignette_row(vignette: Dict[str, Any], columns: List[str]) -> Dict[str, str]:
    metadata = vignette.get("metadata", {})

    row = {col: "" for col in columns}
    row["v_id"] = str(vignette.get("v_id", "")).strip()
    row["se_id"] = str(vignette.get("se_id", "")).strip()
    row["vignette_text"] = _as_csv_cell(vignette.get("vignette_text"))
    row["variable_order"] = _as_csv_cell(vignette.get("variable_order"))
    row["context"] = _as_csv_cell(vignette.get("context"))
    row["title"] = _as_csv_cell(vignette.get("title"))

    for col in columns:
        if col in {"v_id", "se_id", "vignette_text", "variable_order", "context", "title"}:
            continue
        if col in metadata:
            row[col] = _as_csv_cell(metadata[col])
        elif col in vignette:
            row[col] = _as_csv_cell(vignette[col])

    return row


def _build_variable_rows(se_id: str, variables: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for variable in variables:
        row = {col: "" for col in columns}
        row["se_id"] = se_id
        for col in columns:
            if col == "se_id":
                continue
            if col in variable:
                row[col] = _as_csv_cell(variable[col])
        rows.append(row)
    return rows


def _build_query_rows(v_id: str, queries: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for query in queries:
        row = {col: "" for col in columns}
        row["v_id"] = v_id
        for col in columns:
            if col == "v_id":
                continue
            if col in query:
                row[col] = _as_csv_cell(query[col])
        rows.append(row)
    return rows


def _validate_new_vignette(
    vignette: Dict[str, Any],
    existing_v_ids: set,
    existing_se_ids: set,
    new_v_ids: set,
    new_se_ids: set,
) -> None:
    v_id = str(vignette.get("v_id", "")).strip()
    se_id = str(vignette.get("se_id", "")).strip()
    variables = vignette.get("variables", [])
    queries = vignette.get("queries", [])

    if not v_id:
        raise ValueError("Each vignette must have a non-empty 'v_id'.")
    if not se_id:
        raise ValueError(f"Vignette '{v_id}' must have a non-empty 'se_id'.")
    if v_id in existing_v_ids or v_id in new_v_ids:
        raise ValueError(f"Duplicate vignette id found: '{v_id}'.")

    if not isinstance(vignette.get("variable_order", []), list):
        raise ValueError(f"Vignette '{v_id}': 'variable_order' must be a list.")
    if not isinstance(vignette.get("context", []), list):
        raise ValueError(f"Vignette '{v_id}': 'context' must be a list.")
    if len(vignette.get("context", [])) > len(vignette.get("variable_order", [])):
        raise ValueError(f"Vignette '{v_id}': context cannot be longer than variable_order.")

    if not isinstance(variables, list):
        raise ValueError(f"Vignette '{v_id}': 'variables' must be a list.")
    if not isinstance(queries, list):
        raise ValueError(f"Vignette '{v_id}': 'queries' must be a list.")
    if not queries:
        raise ValueError(f"Vignette '{v_id}' must include at least one query.")

    if se_id in existing_se_ids and variables:
        raise ValueError(
            f"Vignette '{v_id}' uses existing se_id '{se_id}' but also provides variables. "
            "Either use a new se_id or leave variables empty to reuse the existing setting."
        )
    if se_id not in existing_se_ids and not variables and se_id not in new_se_ids:
        raise ValueError(
            f"Vignette '{v_id}' uses new se_id '{se_id}' but provides no variables."
        )

    for variable in variables:
        if not isinstance(variable, dict):
            raise ValueError(f"Vignette '{v_id}': each variable must be an object.")
        for field in ["variable_name", "range"]:
            if field not in variable or str(variable[field]).strip() == "":
                raise ValueError(f"Vignette '{v_id}': variable is missing '{field}'.")

    for query in queries:
        if not isinstance(query, dict):
            raise ValueError(f"Vignette '{v_id}': each query must be an object.")
        for field in ["cause", "effect", "query_text"]:
            if field not in query or str(query[field]).strip() == "":
                raise ValueError(f"Vignette '{v_id}': query is missing '{field}'.")


def add_new_vignettes_from_json(
    json_path: Path,
    data_dir: Path = DEFAULT_DATA_DIR,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Add one or more new vignettes (with variables and queries) from a JSON file.

    JSON format expects:
    {
      "vignettes": [
        {
          "v_id": "...",
          "se_id": "...",
          "vignette_text": "...",
          "variable_order": ["A", "B", "E"],
          "context": [1, 0, 1],
          "title": "...",
          "metadata": {... optional vignette columns ...},
          "variables": [...],
          "queries": [...]
        }
      ]
    }
    """
    json_path = Path(json_path)
    data_dir = Path(data_dir)

    with json_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if "vignettes" not in payload or not isinstance(payload["vignettes"], list):
        raise ValueError("JSON file must contain a top-level 'vignettes' list.")

    vignettes_csv = data_dir / "vignettes.csv"
    variables_csv = data_dir / "variables.csv"
    queries_csv = data_dir / "queries.csv"

    vignettes_df = _load_csv(vignettes_csv)
    variables_df = _load_csv(variables_csv)
    queries_df = _load_csv(queries_csv)

    _validate_columns(vignettes_df, VIGNETTE_REQUIRED, "vignettes.csv")
    _validate_columns(variables_df, VARIABLE_REQUIRED, "variables.csv")
    _validate_columns(queries_df, QUERY_REQUIRED, "queries.csv")

    existing_v_ids = set(vignettes_df["v_id"].astype(str).str.strip())
    existing_se_ids = set(variables_df["se_id"].astype(str).str.strip())
    new_v_ids: set = set()
    new_se_ids: set = set()

    vignette_rows: List[Dict[str, str]] = []
    variable_rows: List[Dict[str, str]] = []
    query_rows: List[Dict[str, str]] = []

    for vignette in payload["vignettes"]:
        if not isinstance(vignette, dict):
            raise ValueError("Each vignette entry must be an object.")

        _validate_new_vignette(vignette, existing_v_ids, existing_se_ids, new_v_ids, new_se_ids)

        v_id = str(vignette["v_id"]).strip()
        se_id = str(vignette["se_id"]).strip()
        variables = vignette.get("variables", [])
        queries = vignette.get("queries", [])

        vignette_rows.append(_build_vignette_row(vignette, list(vignettes_df.columns)))
        if variables:
            variable_rows.extend(_build_variable_rows(se_id, variables, list(variables_df.columns)))
            new_se_ids.add(se_id)
        query_rows.extend(_build_query_rows(v_id, queries, list(queries_df.columns)))
        new_v_ids.add(v_id)

    if not vignette_rows:
        raise ValueError("No new vignettes found in JSON.")

    updated_vignettes = pd.concat(
        [vignettes_df, pd.DataFrame(vignette_rows, columns=vignettes_df.columns)],
        ignore_index=True,
    )
    updated_variables = pd.concat(
        [variables_df, pd.DataFrame(variable_rows, columns=variables_df.columns)],
        ignore_index=True,
    )
    updated_queries = pd.concat(
        [queries_df, pd.DataFrame(query_rows, columns=queries_df.columns)],
        ignore_index=True,
    )

    if not dry_run:
        updated_vignettes.to_csv(vignettes_csv, index=False)
        updated_variables.to_csv(variables_csv, index=False)
        updated_queries.to_csv(queries_csv, index=False)

    return {
        "vignettes_added": len(vignette_rows),
        "variables_added": len(variable_rows),
        "queries_added": len(query_rows),
        "dry_run": int(dry_run),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add new vignettes from a JSON file into data/vignettes.csv, data/variables.csv, and data/queries.csv."
    )
    parser.add_argument(
        "--json",
        default=str(DEFAULT_DATA_DIR / "new_vignettes_template.json"),
        help="Path to the JSON file containing new vignettes.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing vignettes.csv, variables.csv, and queries.csv.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show what would be added without writing CSV files.",
    )
    args = parser.parse_args()

    summary = add_new_vignettes_from_json(
        json_path=Path(args.json),
        data_dir=Path(args.data_dir),
        dry_run=args.dry_run,
    )
    print(
        "Added entries -> "
        f"vignettes: {summary['vignettes_added']}, "
        f"variables: {summary['variables_added']}, "
        f"queries: {summary['queries_added']}, "
        f"dry_run: {bool(summary['dry_run'])}"
    )


if __name__ == "__main__":
    main()
