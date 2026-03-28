import itertools
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd


def resolve_data_path(filename: str) -> Path:
    """Resolve data file path relative to script dir (portable across IDEs/terminals)."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_path = project_root / 'data' / filename
    if not data_path.exists():
        raise FileNotFoundError(f"Missing data file: {data_path}")
    return data_path


def all_splits_with_mandatory_element(lst, mandatory_element):
    if mandatory_element not in lst:
        raise ValueError("The mandatory element must be in the list.")

    lst_without_mandatory = [x for x in lst if x != mandatory_element]
    all_splits = []
    n = len(lst_without_mandatory)

    for i in range(n + 1):
        for combo in itertools.combinations(lst_without_mandatory, i):
            list1 = list(combo) + [mandatory_element]
            list2 = [x for x in lst if x not in list1]
            all_splits.append((list1, list2))

    return all_splits


def powerset(iterable):
    s = list(iterable)
    return list(itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1)))


def _format_and_print_result(res, vignette_title: Optional[str], verbose: bool):
    if not verbose:
        return
    header = f"{vignette_title or res.v_id} (Theory: {res.theory})"
    print(header)
    print(f"Query: {res.cause} is actual cause of {res.effect}")
    if res.result is True:
        eval_str = 'TRUE'
    elif res.result is False:
        eval_str = 'FALSE'
    else:
        eval_str = 'NONE'
    print(f"Evaluation: {eval_str}", end='')
    if res.witness:
        print(f"\t{res.witness}")
    else:
        print()
    if res.groundtruth in {0, 1}:
        print(f"Ground truth: {'TRUE' if res.groundtruth else 'FALSE'}")
    elif res.groundtruth is None:
        print("Ground truth not provided.")
    if res.details:
        print(res.details)
    print("====================\n")


def add_confusion_matrix_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with TP/TN/FP/FN indicator columns derived from result and groundtruth."""
    out = df.copy()

    if 'groundtruth' in out.columns:

        def _confusion_flags(row):
            if pd.isna(row['groundtruth']) or pd.isna(row.get('result')):
                return pd.Series({'TP': pd.NA, 'TN': pd.NA, 'FP': pd.NA, 'FN': pd.NA})

            pred = bool(row['result'])
            gt_val = bool(int(row['groundtruth']))
            return pd.Series(
                {
                    'TP': pred and gt_val,
                    'TN': (not pred) and (not gt_val),
                    'FP': pred and (not gt_val),
                    'FN': (not pred) and gt_val,
                }
            )

        out[['TP', 'TN', 'FP', 'FN']] = out.apply(_confusion_flags, axis=1)
        out[['TP', 'TN', 'FP', 'FN']] = out[['TP', 'TN', 'FP', 'FN']].astype('boolean')
    else:
        out['TP'] = pd.NA
        out['TN'] = pd.NA
        out['FP'] = pd.NA
        out['FN'] = pd.NA

    return out


def setting_is_at_least_as_normal(vignette: Any, w_setting: Any) -> bool:
    """Check if the setting w_setting is at least as normal as the vignette's context."""
    _ = w_setting
    for context_var, context_val in vignette.context.items():
        if context_val == vignette.default_values[context_var]:
            if vignette.values[context_var] != context_val:
                return False
    return True


def get_query_by_id(queries: List[Any], query_id: str) -> Optional[Any]:
    """Return the Query object with matching `query_id`, or None if not found."""
    for q in queries:
        if getattr(q, 'query_id', None) == query_id:
            return q
    return None
