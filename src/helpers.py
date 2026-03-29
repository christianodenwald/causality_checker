import itertools
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def add_agreement_column(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with `agreement` derived from `result` vs `groundtruth`."""
    out = df.copy()
    if 'groundtruth' in out.columns:

        def _agreement(row):
            if pd.isna(row['groundtruth']) or pd.isna(row.get('result')):
                return pd.NA
            return bool(row['result']) == bool(int(row['groundtruth']))

        out['agreement'] = out.apply(_agreement, axis=1).astype('boolean')
    else:
        out['agreement'] = pd.NA
    return out


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


def load_other_models_group_map(vignettes_csv_path: Optional[Path] = None) -> Dict[str, str]:
    """Load mapping from vignette id to its model-group key based on `other_models`."""
    csv_path = vignettes_csv_path or resolve_data_path('vignettes.csv')
    vignettes_df = pd.read_csv(csv_path, usecols=['v_id', 'other_models'])

    group_map: Dict[str, str] = {}
    for _, row in vignettes_df.iterrows():
        v_id = str(row['v_id']).strip()
        other_models = row.get('other_models')
        if pd.notna(other_models) and str(other_models).strip() != '':
            group_map[v_id] = str(other_models).strip()
        else:
            group_map[v_id] = v_id

    return group_map


def select_single_model_per_group(df: pd.DataFrame, model_group_map: Dict[str, str]) -> pd.DataFrame:
    """Select one model per `other_models` group and keep only its query rows.

    Selection is done at whole-model level (not per-query) to avoid mixing answers from
    different models inside one group.
    """
    required_cols = {'v_id', 'result', 'groundtruth'}
    if not required_cols.issubset(df.columns):
        return df.copy()

    out = df.copy()
    out['model_group'] = out['v_id'].astype(str).map(model_group_map)
    out['model_group'] = out['model_group'].where(
        out['model_group'].notna() & (out['model_group'].astype(str).str.strip() != ''),
        out['v_id'].astype(str),
    )

    group_cols = ['model_group', 'cause', 'effect', 'effect_contrast', 'gt_label', 'groundtruth']
    for col in group_cols:
        if col not in out.columns:
            out[col] = pd.NA

    selected_frames: List[pd.DataFrame] = []
    grouped_by_model_group = out.groupby('model_group', dropna=False, sort=False)

    for model_group, group_df in grouped_by_model_group:
        model_ids = [str(v) for v in pd.unique(group_df['v_id'])]
        if not model_ids:
            continue

        ranked: List[tuple] = []
        for model_id in model_ids:
            model_df = group_df[group_df['v_id'] == model_id]
            pred_series = pd.to_numeric(model_df['result'], errors='coerce')
            gt_series = pd.to_numeric(model_df['groundtruth'], errors='coerce')

            valid = pred_series.isin([0, 1]) & gt_series.isin([0, 1])
            valid_count = int(valid.sum())
            correct_count = int((pred_series[valid].astype(int) == gt_series[valid].astype(int)).sum())
            all_correct = (valid_count > 0) and (correct_count == valid_count)

            # Prefer models that are fully correct; then highest number correct, then more valid rows,
            # then stable lexical tiebreak on model id.
            ranked.append((all_correct, correct_count, valid_count, model_id))

        ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
        selected_model_id = ranked[0][3]

        chosen = group_df[group_df['v_id'] == selected_model_id].copy()
        chosen['v_id'] = str(model_group)
        selected_frames.append(chosen)

    if not selected_frames:
        return out.iloc[0:0].copy()

    selected_df = pd.concat(selected_frames, axis=0, ignore_index=True)
    selected_df = selected_df.drop(columns=['model_group'], errors='ignore').reset_index(drop=True)
    return selected_df


def print_confusion_matrix_and_f1(df: pd.DataFrame, label: Optional[str] = None) -> None:
    """Print confusion-matrix totals and F1 based on TP/TN/FP/FN columns."""
    missing_cols = [col for col in ('TP', 'TN', 'FP', 'FN') if col not in df.columns]
    if missing_cols:
        print(f"Cannot compute confusion matrix: missing column(s): {', '.join(missing_cols)}")
        return

    cm = df[['TP', 'TN', 'FP', 'FN']].apply(pd.to_numeric, errors='coerce')
    valid = cm.notna().all(axis=1)
    if not valid.any():
        prefix = f"{label} | " if label else ''
        print(f"{prefix}Confusion matrix/F1 unavailable: no rows with valid TP/TN/FP/FN.")
        return

    tp = int(cm.loc[valid, 'TP'].sum())
    tn = int(cm.loc[valid, 'TN'].sum())
    fp = int(cm.loc[valid, 'FP'].sum())
    fn = int(cm.loc[valid, 'FN'].sum())
    total_true = tp + tn
    total_false = fp + fn

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    header = f"{label} confusion matrix and F1" if label else 'Confusion matrix and F1'
    print(f"\n{header}:")
    print(f"TP={tp}, TN={tn}, FP={fp}, FN={fn}")
    print(f"Total correct={total_true}, Total incorrect={total_false}")
    print(f"F1={f1:.4f}")


def setting_is_at_least_as_normal(vignette: Any, w_setting: Dict[str, int]) -> bool:
    """Check if interventions stay within each context variable's equally-normal defaults."""
    for context_var, context_val in vignette.context.items():
        defaults = vignette.default_values.get(context_var, [0])
        if not isinstance(defaults, (list, tuple, set)):
            defaults = [defaults]

        if context_val in defaults:
            intervened_val = w_setting.get(context_var, context_val)
            if intervened_val not in defaults:
                return False
    return True


def get_query_by_id(queries: List[Any], query_id: str) -> Optional[Any]:
    """Return the Query object with matching `query_id`, or None if not found."""
    for q in queries:
        if getattr(q, 'query_id', None) == query_id:
            return q
    return None
