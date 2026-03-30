from typing import List, Dict, Any, Optional
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd

from dataclasses import dataclass, asdict
from data.paper_examples import *

try:
    from src.theories import THEORY_EVALUATORS
except ModuleNotFoundError:
    from theories import THEORY_EVALUATORS

try:
    from src.helpers import (
        resolve_data_path,
        all_splits_with_mandatory_element,
        powerset,
        _format_and_print_result,
        add_agreement_column,
        add_confusion_matrix_columns,
        load_other_models_group_map,
        print_confusion_matrix_and_f1,
        select_single_model_per_group,
        setting_is_at_least_as_normal,
        get_query_by_id,
    )
except ModuleNotFoundError:
    from helpers import (
        resolve_data_path,
        all_splits_with_mandatory_element,
        powerset,
        _format_and_print_result,
        add_agreement_column,
        add_confusion_matrix_columns,
        load_other_models_group_map,
        print_confusion_matrix_and_f1,
        select_single_model_per_group,
        setting_is_at_least_as_normal,
        get_query_by_id,
    )

#### PATHS TO DATA FILES
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'outputs'

# Set paths (now guaranteed to exist)
vignettes_path = resolve_data_path('vignettes.csv')
variables_path = resolve_data_path('variables.csv')
queries_path = resolve_data_path('queries.csv')

#### CLASSES

class Vignette:
    """
    Represents a configurable vignette model with variables, equations, and settings.

    This class is designed to handle a set of variables, their configurations, as well
    as dependencies between them in the form of equations. It provides mechanisms to
    initialize, update, restore defaults, and perform computations based on the
    provided or computed data. The purpose of this class is to model scenarios where
    variables have interdependent relationships, defined by equations, and allow for
    controlled manipulation and analysis of such relationships and values.

    Attributes:
        vignette_id: Identifier for the vignette.
        setting_id: Optional identifier for the associated settings configuration.
        title: Title of the vignette, typically a brief descriptive name.
        description: Full description of the vignette's purpose, scope, or scenario.
        variables: Dictionary defining the variables and their metadata.
        ranges: Dictionary specifying the allowable ranges for the variables.
        values: Dictionary holding the current values of each variable.
        default_values: Dictionary for the default values of each variable, used for
            resets or restoration purposes.
        equations: Dictionary mapping variables to their respective equations. Each
            equation defines how the variable value is computed.
        notes: Additional notes or metadata for the vignette to provide contextual 
            information.
    """

    def __init__(self, vignette_id, title, vignette_text, variables, ranges, values, default_values, equations, context):
        self.vignette_id = vignette_id
        self.title = title
        self.vignette_text = vignette_text
        self.variables = variables
        self.context = context
        self.ranges = ranges
        self.values = values
        self.default_values = default_values

        self.equations_str = equations  # Keep original string equations for reference
        self.equations = self.parse_equations(equations)
        self.children = self.child_variables()
        self.values_in_example = {}
        self.values_in_example = self.set_values_in_example_from_context()

    def child_variables(self):
        """Determines child variables for each variable based on equations."""
        children = {var: [] for var in self.variables}
        for var, equation in self.equations_str.items():
            # Only string equations can be scanned for parent-variable mentions.
            if not isinstance(equation, str):
                continue
            for potential_parent in self.variables:
                if potential_parent != var and potential_parent in equation:
                    children[potential_parent].append(var)
        return children

    def parse_equations(self, equations):
        """
        Converts equation strings into callable functions if they are not already callables.
        Ensures variables in the values dictionary are converted to integers before evaluation.
        """
        parsed_equations = {}
        for var, eq in equations.items():
            if isinstance(eq, str):  # If it's a string, parse it
                parsed_equations[var] = lambda values, eq=eq: int(
                    eval(eq, {}, {k: int(v) if v is not None else 0 for k, v in values.items()}))
            elif callable(eq):  # If it's already callable, use it directly
                parsed_equations[var] = eq
            else:
                raise ValueError(f"Equation for {var} must be a string or callable.")
        return parsed_equations

    def update_values(self):
        """Updates all values based on equations."""
        for var, equation in self.equations.items():
            self.values[var] = equation(self.values)

    def update_single_value(self, var):
        """
        Updates the value of a single specified variable based on its equation.
        Does nothing if the variable does not have an associated equation.
        """
        if var in self.equations:
            try:
                self.values[var] = self.equations[var](self.values)
            except Exception as e:
                raise ValueError(f"Failed to update value for {var}: {e}")
        else:
            raise ValueError(f"Variable {var} does not have an associated equation.")

    def set_value_and_update(self, var, value):
        """Sets a value and updates the dependent values."""
        if var in self.values:
            self.values[var] = value
            self.update_values()
        else:
            raise ValueError(f"Variable {var} does not exist.")

    def set_value(self, var, value):
        """Sets a value without updating dependent values."""
        if var in self.values:
            self.values[var] = value
        else:
            raise ValueError(f"Variable {var} does not exist.")

    def restore_initial_values(self):
        """Restores all values to their default state without applying equations."""
        self.values = self.values_in_example.copy()

    def set_exogenous_values(self):
        """Updates exogenous values without triggering updates for dependent values."""
        for var, value in self.values.items():
            if var in self.equations.keys():
                self.set_value(var, None)
            else:
                self.set_value(var, self.values_in_example[var])

    def reset_values(self):
        """Sets all values to None."""
        for var, value in self.values_in_example.items():
            self.set_value(var, None)

    def propagate_set_values(self):
        """Propagates values based on equations based on values that are already set."""
        for var, value in self.values.items():
            if value is None:
                new_value = self.equations[var](self.values)
                self.set_value(var, new_value)

    def set_values_in_example_from_context(self):
        values_in_example = {}
        for var in self.variables:
            if var in self.context:
                values_in_example[var] = self.context[var]
            else:
                try:
                    # Use current values_in_example for equation evaluation, defaulting to None for unset variables
                    temp_values = {k: v if v is not None else 0 for k, v in values_in_example.items()}
                    values_in_example[var] = self.equations[var](temp_values)
                except Exception as e:
                    raise ValueError(f"Failed to update value for {var}: {e}")
        self.values_in_example = values_in_example
        return self.values_in_example

    def __repr__(self):
        return f"Vignette({self.vignette_id}, {self.title}, {self.values})"

class Query:
    def __init__(self, v_id=None, cause=None, effect=None, effect_contrast=None, query_text=None, intuition=None, HP01=None, HP05=None, HP15=None,
                    H01=None, H07=None, Hall=None, Baumgartner13=None, AG24=None, G21=None, query_id: Optional[str] = None):
        # Unique identifier for the query (added to allow running single queries)
        self.query_id = query_id
        self.v_id = v_id
        self.cause = cause
        self.effect = effect
        self.effect_contrast = int(effect_contrast) if effect_contrast is not None and pd.notna(effect_contrast) and effect_contrast != '' else None
        self.query_text = query_text if pd.notna(query_text) and query_text != '' else None
        self.groundtruth = {
            'intuition': bool(intuition) if intuition is not None else None,
            'HP01': bool(HP01) if HP01 is not None else None,
            'HP05': bool(HP05) if HP05 is not None else None,
            'HP15': bool(HP15) if HP15 is not None else None,
            'H01': bool(H01) if H01 is not None else None,
            'H07': bool(H07) if H07 is not None else None,
            'Hall': bool(Hall) if Hall is not None else None,
            'Baumgartner13': bool(Baumgartner13) if Baumgartner13 is not None else None,
            'AG24': bool(AG24) if AG24 is not None else None,
            'G21': bool(G21) if G21 is not None else None
        }


    def __repr__(self):
        return (f"Query(v_id={self.v_id}, cause={self.cause}, effect={self.effect}, "
                f"groundtruth={self.groundtruth})")


@dataclass
class EvaluationResult:
    v_id: Optional[str]
    query_id: Optional[str]
    cause: Optional[str]
    effect: Optional[str]
    effect_contrast: Optional[int]
    theory: str
    result: Optional[bool]
    witness: Optional[str]
    gt_label: str
    groundtruth: Optional[int]
    details: Optional[str] = None


#### FUNCTIONS

def load_vignettes(vignettes_csv_path, variables_csv_path, filter_nl: bool = False):
    """Loads vignettes from a CSV file.

    Args:
        vignettes_csv_path: Path to the vignette metadata CSV.
        variables_csv_path: Path to the variables CSV.
        filter_nl: When True, remove vignettes with missing/blank vignette_text.
    """

    vignettes_df = pd.read_csv(vignettes_csv_path)
    for col in ['variable_order', 'context']:
        vignettes_df[col] = vignettes_df[col].str.split(',')
        # Optional: strip whitespace from each item in the lists
        vignettes_df[col] = vignettes_df[col].apply(lambda x: [item.strip() for item in x] if isinstance(x, list) else x)

    variables_df = pd.read_csv(variables_csv_path)
    variables_df['range'] = variables_df['range'].str.split(',')
    # Optional: strip whitespace from each item in the lists
    variables_df['range'] = variables_df['range'].apply(lambda x: [item.strip() for item in x] if isinstance(x, str) else x)

    vignettes = dict()

    def _parse_default_values(raw_default: Any) -> List[int]:
        """Parse default-values cell into a list of equally normal values."""
        if pd.isna(raw_default):
            return [0]

        if isinstance(raw_default, (int, np.integer)):
            return [int(raw_default)]

        if isinstance(raw_default, (float, np.floating)):
            return [int(raw_default)] if float(raw_default).is_integer() else [0]

        if isinstance(raw_default, str):
            normalized = raw_default.strip()
            if not normalized:
                return [0]

            for delimiter in [';', '|', '/']:
                normalized = normalized.replace(delimiter, ',')

            values: List[int] = []
            for token in normalized.split(','):
                cleaned = token.strip()
                if not cleaned or cleaned.lower() in {'nan', 'none'}:
                    continue
                try:
                    parsed = float(cleaned)
                except ValueError:
                    continue
                if parsed.is_integer():
                    values.append(int(parsed))

            return sorted(set(values)) if values else [0]

        return [0]


    for j, (_, vignette_row) in enumerate(vignettes_df.iterrows()):
        variable_data = variables_df.loc[variables_df.se_id == vignette_row['se_id']]

        variables_raw = vignette_row.get('variable_order', [])
        context_raw = vignette_row.get('context', [])
        if not isinstance(variables_raw, list) or not isinstance(context_raw, list):
            raise ValueError(
                f"Invalid list-like values for vignette row {j}: variable_order={type(variables_raw)}, context={type(context_raw)}"
            )

        variables = [str(var).strip() for var in variables_raw]
        context_values = [str(val).strip() for val in context_raw]

        values = {var: int(context_values[i]) if i < len(context_values) else np.nan for i, var in
                  enumerate(variables)}

        # default_values = dict()
        # for var in variables:
        #     # default_values[var] = variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] if any(variable_data['variable_name'] == var) else None
        #     default_values[var] = int(variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0]) if variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] else np.nan

        default_values = {}
        for var in variable_data['variable_name'].unique():
            default_series = variable_data[variable_data['variable_name'] == var]['default_values']
            raw_default = default_series.dropna().iloc[0] if not default_series.dropna().empty else np.nan
            default_values[var] = _parse_default_values(raw_default)

        equations = dict()
        for index, row in variable_data.iterrows():
            if row['structural_equation'] is not np.nan:
                equations[row['variable_name']] = row['structural_equation']

        context = dict()
        context_length = len(context_values)
        context_vars = variables[:context_length]
        for i in range(context_length):
            context[context_vars[i]] = int(context_values[i])


        ranges = dict()
        for var in variables:
            range_str = variable_data.loc[variable_data['variable_name'] == var, 'range'].iloc[0] if any(
                variable_data['variable_name'] == var) else None
            if range_str is not None:
                ranges[var] = [int(x) for x in range_str]
            else:
                ranges[var] = None
        # values_in_example = dict()

        # print(f"Vignette ID: {vignette_row['v_id']}")
        vignettes[vignette_row['v_id']] = Vignette(
            vignette_id=f"v{j}_{vignette_row['v_id']}",
            title=vignette_row['title'],
            vignette_text=vignette_row['vignette_text'] if pd.notna(vignette_row['vignette_text']) and vignette_row['vignette_text'] != '' else None,
                variables=variables,
                context = context,
                ranges=ranges,
                values=values,
                default_values=default_values,
                equations=equations,
                # values_in_example=values_in_example,
            )
    total_vignettes = len(vignettes)
    if filter_nl:
        filtered_vignettes = {
            v_id: vignette
            for v_id, vignette in vignettes.items()
            if vignette.vignette_text and vignette.vignette_text.strip()
        }
        filtered_out = total_vignettes - len(filtered_vignettes)
        print(
            f"Loaded {len(filtered_vignettes)} vignettes "
            f"(filtered out {filtered_out} missing/blank vignette_text entries)."
        )
        return filtered_vignettes

    print(f"Loaded {total_vignettes} vignettes.")
    return vignettes

# Function to create Query objects from CSV file
def load_queries(csv_path):
    # Load the DataFrame from the CSV file
    df = pd.read_csv(csv_path)

    query_objects = []
    for idx, (_, row) in enumerate(df.iterrows()):
        # Replace NaN or empty strings with None
        # create a stable, unique query id (use existing column if present, otherwise derive one)
        if 'query_id' in row.index and pd.notna(row.get('query_id')) and row.get('query_id') != '':
            qid = str(row.get('query_id'))
        else:
            qid = f"{row['v_id']}_q{idx}"

        query = Query(
            v_id=row['v_id'] if pd.notna(row['v_id']) and row['v_id'] != '' else None,
            cause=row['cause'] if pd.notna(row['cause']) and row['cause'] != '' else None,
            effect=row['effect'] if pd.notna(row['effect']) and row['effect'] != '' else None,
            effect_contrast=row.get('effect_contrast') if 'effect_contrast' in row.index and pd.notna(row.get('effect_contrast')) and row.get('effect_contrast') != '' else None,
            query_text=row.get('query_text') if 'query_text' in row.index and pd.notna(row.get('query_text')) and row.get('query_text') != '' else None,
            intuition=int(row['intuition']) if pd.notna(row['intuition']) and row['intuition'] != '' else None,
            HP01=int(row['HP01']) if pd.notna(row['HP01']) and row['HP01'] != '' else None,
            HP05=int(row['HP05']) if pd.notna(row['HP05']) and row['HP05'] != '' else None,
            HP15=int(row['HP15']) if pd.notna(row['HP15']) and row['HP15'] != '' else None,
            H01=int(row['H01']) if pd.notna(row['H01']) and row['H01'] != '' else None,
            H07=int(row['H07']) if pd.notna(row['H07']) and row['H07'] != '' else None,
            Hall=int(row['Hall']) if pd.notna(row['Hall']) and row['Hall'] != '' else None,
            Baumgartner13=int(row['Baumgartner13']) if pd.notna(row['Baumgartner13']) and row[
                'Baumgartner13'] != '' else None,
            AG24=int(row['AG24']) if pd.notna(row['AG24']) and row['AG24'] != '' else None,
            G21=int(row['G21']) if pd.notna(row['G21']) and row['G21'] != '' else None,
            query_id=qid
        )
        query_objects.append(query)
    return query_objects

def check_causality(theory: str, vignette: Vignette, query: Query, gt: str = 'intuition', normality: bool = False) -> EvaluationResult:
    """
    Compute causality according to `theory` for a single `query` in a `vignette`.
    Returns an EvaluationResult with no printing side-effects.
    """
    
    # Extract cause/effect from Query
    qid = getattr(query, 'query_id', None)
    if isinstance(query, Query):
        if query.cause is None or query.effect is None:
            return EvaluationResult(
                v_id=query.v_id,
                query_id=qid,
                cause=query.cause,
                effect=query.effect,
                effect_contrast=query.effect_contrast,
                theory=theory,
                result=None,
                witness=None,
                gt_label=gt,
                groundtruth=query.groundtruth.get(gt),
                details="Missing cause or effect in query."
            )

        cause_text = query.cause
        effect_text = query.effect
        # Parse compound causes (e.g., "MD=1 and L=1")
        cause_parts = [part.strip() for part in cause_text.split(' and ')]
        cause_variables = []
        cause_values = []
        for part in cause_parts:
            if len(part.split('=')) != 2:
                return EvaluationResult(
                    v_id=query.v_id, query_id=qid, cause=query.cause, effect=query.effect, effect_contrast=query.effect_contrast, theory=theory,
                    result=None, witness=None, gt_label=gt, groundtruth=query.groundtruth.get(gt),
                    details=f"Invalid cause format in part: {part}"
                )
            var, val = part.split('=')
            cause_variables.append(var.strip())
            cause_values.append(int(val.strip()))
        
        # Parse effect (single variable for now)
        if len(effect_text.split('=')) != 2:
            return EvaluationResult(
                v_id=query.v_id, query_id=qid, cause=query.cause, effect=query.effect, effect_contrast=query.effect_contrast, theory=theory,
                result=None, witness=None, gt_label=gt, groundtruth=query.groundtruth.get(gt),
                details="Invalid effect format."
            )
        effect_variable, effect_value = effect_text.split('=')
        effect_value = int(effect_value)
    else:
        return EvaluationResult(
            v_id=getattr(query, 'v_id', None), query_id=getattr(query, 'query_id', None),
            cause=str(getattr(query, 'cause', None)),
            effect=str(getattr(query, 'effect', None)),
            effect_contrast=getattr(query, 'effect_contrast', None),
            theory=theory, result=None, witness=None, gt_label=gt,
            groundtruth=None, details="Unsupported query object type."
        )

    # Basic checks
    for cause_variable in cause_variables:
        if cause_variable not in vignette.variables:
            raise ValueError(f"Cause variable {cause_variable} is not in the vignette.")
    if effect_variable not in vignette.variables:
        raise ValueError(f"Effect variable {effect_variable} is not in the vignette.")

    def _subset_is_cause(subset_vars: List[str], subset_vals: List[int]) -> bool:
        subset_cause_str = ' and '.join(
            [f"{var}={val}" for var, val in zip(subset_vars, subset_vals)]
        )
        subset_query = Query(
            v_id=query.v_id,
            cause=subset_cause_str,
            effect=query.effect,
            effect_contrast=query.effect_contrast,
            query_id=f"{qid}_subset"
        )
        subset_result = check_causality(theory, vignette, subset_query, gt=gt, normality=normality)
        return bool(subset_result.result)

    evaluator = THEORY_EVALUATORS.get(theory)
    if evaluator is None:
        return EvaluationResult(
            v_id=getattr(query, 'v_id', None), query_id=qid, cause=getattr(query, 'cause', None),
            effect=getattr(query, 'effect', None), theory=theory, result=None, witness=None, gt_label=gt,
            groundtruth=getattr(query, 'groundtruth', {}).get(gt) if isinstance(query, Query) else None,
            effect_contrast=getattr(query, 'effect_contrast', None), details=f"Invalid/unsupported theory: {theory}"
        )

    if theory == 'HP2005':
        theory_eval = evaluator(
            vignette=vignette,
            query=query,
            cause_variables=cause_variables,
            cause_values=cause_values,
            effect_variable=effect_variable,
            effect_value=effect_value,
            qid=qid,
            normality=normality,
            setting_is_at_least_as_normal=setting_is_at_least_as_normal,
            subset_is_cause=_subset_is_cause,
        )
    elif theory == 'HP2015':
        theory_eval = evaluator(
            vignette=vignette,
            query=query,
            cause_variables=cause_variables,
            cause_values=cause_values,
            effect_variable=effect_variable,
            effect_value=effect_value,
            normality=normality,
            setting_is_at_least_as_normal=setting_is_at_least_as_normal,
            subset_is_cause=_subset_is_cause,
        )
    else:
        theory_eval = evaluator(
            vignette=vignette,
            query=query,
            cause_variables=cause_variables,
            cause_values=cause_values,
            effect_variable=effect_variable,
            effect_value=effect_value,
            subset_is_cause=_subset_is_cause,
        )

    if theory_eval.get('terminal'):
        return EvaluationResult(
            v_id=query.v_id,
            query_id=qid,
            cause=query.cause,
            effect=query.effect,
            effect_contrast=query.effect_contrast,
            theory=theory,
            result=theory_eval.get('result'),
            witness=theory_eval.get('witness'),
            gt_label=gt,
            groundtruth=query.groundtruth.get(gt),
            details=theory_eval.get('details'),
        )

    evaluation_result = theory_eval.get('result')
    witness_str = theory_eval.get('witness')
    theory_details = theory_eval.get('details')

    return EvaluationResult(
        v_id=query.v_id, query_id=qid, cause=query.cause, effect=query.effect, effect_contrast=query.effect_contrast, theory=theory,
        result=evaluation_result, witness=witness_str, gt_label=gt, groundtruth=query.groundtruth.get(gt), details=theory_details
    )


### EVALUATION FUNCTIONS

def evaluate_all_queries(vignettes: Dict[str, Vignette], 
                         queries: List[Query], 
                         theory: str = 'HP2015',
                         gt: str = 'intuition', 
                         skip: Optional[List[str]] = None, 
                         verbose: bool = False, 
                         save: bool = False,
                         normality: bool = False,
                         result_scope: str = 'all',
                         filter_nl: bool = False) -> pd.DataFrame:
    """
    Evaluate many queries, collect structured results, and optionally print per-query output.
    Returns a DataFrame with results.
    """
    records: List[Dict[str, Any]] = []
    skip_set = set(skip or [])
    for i, query in enumerate(queries):
        if query.v_id in skip_set:
            if verbose:
                print(f"Skipping query {i} for vignette {query.v_id}\n====================\n")
            continue
        if query.v_id not in vignettes:
            if verbose:
                print(f"Warning: vignette {query.v_id} not found. Skipping.")
            continue

        if verbose:
            print(f"Evaluating query {i+1}/{len(queries)}: vignette={query.v_id}, cause={query.cause}, effect={query.effect}, effect_contrast={query.effect_contrast}")
        res = check_causality(theory, vignettes[query.v_id], query, gt=gt, normality=normality)
        _format_and_print_result(res, vignette_title=vignettes[query.v_id].title if query.v_id in vignettes else None, verbose=verbose)
        records.append(asdict(res))

    df = pd.DataFrame.from_records(records)

    # Ensure `effect_contrast` is integer dtype with NA support if present
    if 'effect_contrast' in df.columns:
        df['effect_contrast'] = pd.to_numeric(df['effect_contrast'], errors='coerce').astype('Int64')

    df = add_agreement_column(df)

    model_group_map = load_other_models_group_map()
    df = select_single_model_per_group(df, model_group_map)
    df = add_confusion_matrix_columns(df)
    print_confusion_matrix_and_f1(df, label=f"{theory} ({gt}, {result_scope}, single-model-group)")

    if save:
        scope_suffix_map = {
            'all': 'all_queries',
            'paper': 'paper_queries',
            'nonpaper': 'non_paper_queries',
        }
        suffix = scope_suffix_map.get(result_scope, result_scope)
        normality_suffix = '_normality' if normality else ''
        filter_suffix = '_filter_nl' if filter_nl else ''
        out_path = OUTPUT_DIR / f'causality_results_{theory}{normality_suffix}_{gt}_{suffix}{filter_suffix}.csv'
        df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")

    return df

def reproduce_paper_results(vignettes: Dict[str, Vignette], queries: List[Query],
                            query_list: Optional[List[str]] = None, theory: str = 'HP2005',
                            gt: str = 'intuition', skip: Optional[List[str]] = None, verbose: bool = False,
                            save: bool = False,
                            filter_nl: bool = False) -> pd.DataFrame:
    """
    Filter `queries` to those in `query_list` (if provided) and call evaluate_all_queries.
    Returns a DataFrame of results for the selected queries.
    """
    if query_list:
        filtered = [q for q in queries if q.v_id in set(query_list)]
    else:
        filtered = queries
    return evaluate_all_queries(
        vignettes=vignettes,
        queries=filtered,
        theory=theory,
        gt=gt,
        skip=skip,
        verbose=verbose,
        save=save,
        result_scope='paper',
        filter_nl=filter_nl,
    )

def evaluate_non_paper_queries(vignettes: Dict[str, Vignette], queries: List[Query],
                              query_list: Optional[List[str]] = None, theory: str = 'HP2005',
                              gt: str = 'intuition', skip: Optional[List[str]] = None, verbose: bool = False,
                              save: bool = False,
                              filter_nl: bool = False) -> pd.DataFrame:
    """
    Filter `queries` to those NOT in `query_list` (if provided) and call evaluate_all_queries.
    Returns a DataFrame of results for the selected queries.
    """
    if query_list:
        filtered = [q for q in queries if q.v_id not in set(query_list)]
    else:
        filtered = queries
    return evaluate_all_queries(
        vignettes=vignettes,
        queries=filtered,
        theory=theory,
        gt=gt,
        skip=skip,
        verbose=verbose,
        save=save,
        result_scope='nonpaper',
        filter_nl=filter_nl,
    )


def run_single_query(vignettes: Dict[str, Vignette], queries: List[Query], query_id: str,
                     theory: str = 'HP2015', gt: str = 'intuition', verbose: bool = True, normality: bool = False) -> EvaluationResult:
    """Run `check_causality` for a single query identified by `query_id` and return the EvaluationResult.

    Raises a ValueError if the query or vignette cannot be found.
    """
    q = get_query_by_id(queries, query_id)
    if q is None:
        raise ValueError(f"Query with id {query_id} not found")
    if q.v_id not in vignettes:
        raise ValueError(f"Vignette {q.v_id} for query {query_id} not found")

    res = check_causality(theory, vignettes[q.v_id], q, gt=gt, normality=normality)
    _format_and_print_result(res, vignette_title=vignettes[q.v_id].title if q.v_id in vignettes else None, verbose=verbose)
    return res



if __name__ == "__main__":
    # vignettes = load_vignettes(vignettes_path, variables_path, filter_nl=True)
    vignettes = load_vignettes(vignettes_path, variables_path)
    queries = load_queries(queries_path)
    # check_causality('HP2005', vignettes['ff_disj'], queries[0]) # test call for single query
    # skip = ['rock_bottle_noisy', 'rock_bottle_time']
    skip = []
    # evaluate_all_queries(vignettes, queries, theory='HP2005', gt='intuition', skip=skip)

    # df_paper_HP2005 = reproduce_paper_results(vignettes=vignettes, queries=queries, query_list=HP2005_examples, theory='HP2005', gt='HP05', skip=skip, save=True)
    # todo: april rains returns TRUE, since this implementation considers any change in the effect variable as satisfying AC2a, while the paper seems to require a specific change (from 1 to 0).
    # todo: cannot handle query monday_treatment_deadly: Cause for being alive (B=0 or B=1 or B=2)
    # todo: is spell casting trumping different than command trumping?

    # df_paper_HP2015 = reproduce_paper_results(vignettes=vignettes, queries=queries, query_list=HP2015_examples, theory='HP2015', gt='HP15', skip=skip, save=True)

    # fixing compound queries
    # result = run_single_query(vignettes, queries, query_id='engineer1_q40', theory='HP2015', gt='HP15')

    # checking normality
    # result = run_single_query(vignettes, queries, query_id='plant_watering_q53', theory='HP2005', gt='HP05', verbose=True, normality=False)
    # result_normality = run_single_query(vignettes, queries, query_id='plant_watering_q53', theory='HP2005', gt='HP05', verbose=True, normality=True)

    # specific slow query test
    # result = run_single_query(vignettes, queries, query_id='rock_bottle_noisy_q107', theory='HP2005', gt='HP05', verbose=True)

    # evaluate all queries
    # all_HP2005 = evaluate_all_queries(vignettes, queries, theory='HP2005', gt='intuition', verbose=False, skip=skip, save=True)
    # all_HP2015 = evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', verbose=False, skip=skip, save=True)
    # nonpaper_HP2005 = evaluate_non_paper_queries(vignettes, queries, query_list=HP2005_examples, theory='HP2005', gt='intuition', verbose=False, skip=skip, save=True)
    # nonpaper_HP2015 = evaluate_non_paper_queries(vignettes, queries, query_list=HP2015_examples, theory='HP2015', gt='intuition', verbose=False, skip=skip, save=True)

    # find queries with disagreements
    # disagreements_HP2005 = all_HP2005[all_HP2005['agreement'] == False]
    # disagreements_HP2015 = all_HP2015[all_HP2015['agreement'] == False]

    # revisions
    HP2005 = evaluate_all_queries(vignettes, queries, theory='HP2005', gt='intuition', skip=skip, save=True)
    HP2015 = evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', skip=skip, save=True)
    HP2005_norm = evaluate_all_queries(vignettes, queries, theory='HP2005', gt='intuition', skip=skip, save=True, normality=True)
    HP2015_norm = evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', skip=skip, save=True, normality=True)

print()
