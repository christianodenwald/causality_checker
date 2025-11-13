import itertools
from typing import List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd

from data.paper_examples import *

# Paths to data files
vignettes_path = "../data/vignettes.csv"
variables_path = "../data/variables.csv"
queries_path = "../data/queries.csv"

### IMPORTED HELPER FUNCTIONS
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

    def __init__(self, vignette_id, title, description, variables, ranges, values, default_values, equations, context):
        self.vignette_id = vignette_id
        self.title = title
        self.description = description
        self.variables = variables
        self.context = context
        self.ranges = ranges
        self.values = values
        self.default_values = default_values

        self.equations = self.parse_equations(equations)
        self.values_in_example = {}
        self.values_in_example = self.set_values_in_example_from_context()

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
    def __init__(self, v_id, cause, effect, intuition, HP01, HP05, HP15, H01, H07, Hall, Baumgartner13, AG24, G21):
        self.v_id = v_id
        self.cause = cause
        self.effect = effect
        self.groundtruth = {
            'intuition': intuition,
            'HP01': HP01,
            'HP05': HP05,
            'HP15': HP15,
            'H01': H01,
            'H07': H07,
            'Hall': Hall,
            'Baumgartner13': Baumgartner13,
            'AG24': AG24,
            'G21': G21
        }

    def __repr__(self):
        return (f"Query(v_id={self.v_id}, cause={self.cause}, effect={self.effect}, "
                f"groundtruth={self.groundtruth})")


#### FUNCTIONS

def load_vignettes(vignettes_csv_path, variables_csv_path):
    """Loads vignettes from a CSV file."""

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


    for j, vignette_data in enumerate(vignettes_df.itertuples(index=True)):
        variable_data = variables_df.loc[variables_df.se_id == vignette_data.se_id]

        variables = vignette_data.variable_order

        values = {var: int(vignette_data.context[i]) if i < len(vignette_data.context) else np.nan for i, var in
                  enumerate(variables)}

        # default_values = dict()
        # for var in variables:
        #     # default_values[var] = variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] if any(variable_data['variable_name'] == var) else None
        #     default_values[var] = int(variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0]) if variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] else np.nan

        default_values = {
            var: (
                int(variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[0])
                if (
                        not variable_data[variable_data['variable_name'] == var]['default_values'].isna().all()
                        and isinstance(
                    variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[0],
                    (int, float))
                        and variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[
                            0].is_integer()
                )
                else np.nan
            )
            for var in variable_data['variable_name'].unique()
        }
        # default value is 0 if not given
        default_values = {var: value if not pd.isna(value) else 0 for var, value in default_values.items()}

        equations = dict()
        for index, row in variable_data.iterrows():
            if row['structural_equation'] is not np.nan:
                equations[row['variable_name']] = row['structural_equation']

        context = dict()
        context_length = len(vignette_data.context)
        context_vars = vignette_data.variable_order[:context_length]
        for i in range(context_length):
            context[context_vars[i]] = int(vignette_data.context[i])


        ranges = dict()
        for var in variables:
            range_str = variable_data.loc[variable_data['variable_name'] == var, 'range'].iloc[0] if any(
                variable_data['variable_name'] == var) else None
            if range_str is not None:
                ranges[var] = [int(x) for x in range_str]
            else:
                ranges[var] = None
        # values_in_example = dict()

        print(f"Vignette ID: {vignette_data.v_id}")
        vignettes[vignette_data.v_id] = Vignette(
                vignette_id=f'v{j}_' + vignette_data.v_id,
                title=vignette_data.title,
                description=vignette_data.description,
                variables=variables,
                context = context,
                ranges=ranges,
                values=values,
                default_values=default_values,
                equations=equations,
                # values_in_example=values_in_example,
            )

    return vignettes

# Function to create Query objects from CSV file
def load_queries(csv_path):
    # Load the DataFrame from the CSV file
    df = pd.read_csv(csv_path)

    query_objects = []
    for _, row in df.iterrows():
        # Replace NaN or empty strings with None
        query = Query(
            v_id=row['v_id'] if pd.notna(row['v_id']) and row['v_id'] != '' else None,
            cause=row['cause'] if pd.notna(row['cause']) and row['cause'] != '' else None,
            effect=row['effect'] if pd.notna(row['effect']) and row['effect'] != '' else None,
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
            G21=int(row['G21']) if pd.notna(row['G21']) and row['G21'] != '' else None
        )
        query_objects.append(query)
    return query_objects

def check_causality(theory, vignette, query, gt='intuition', verbose=True):

    """
        Determines whether a given query satisfies causality conditions based on a specified theory
        in the context of a given vignette. It checks conditions using the query's cause-effect
        relationship and evaluated results. The function can provide verbose output optionally.

        Parameters:
            theory: str
                The causality theory to be verified (e.g., 'HP2015', 'HP2005').
            vignette: object
                A vignette model containing variables, equations, and their relationships.
            query: dict
                A JSON-like structured dictionary containing details of causality queries with cause-effect pairs and results.
            verbose: bool, optional (default=True)
                Flag to enable detailed printed output during the evaluation process.

        Returns:
            None

        Raises:
            ValueError
                If cause or effect variable is not in the vignette.
                If AC1 condition is violated for the cause or effect variable.
                If no alternative value for the cause variable is found.
                If an invalid theory is provided.

        Notes:
            This function currently implements logic for HP2015 theory only. HP2005 and other theories
            are placeholders and need further implementation.
            Requires the vignette object to have methods for resetting variable values, setting
            exogenous values, applying custom values, and propagating these values based on equations.
    """
    if verbose:
        print(f"{vignette.title} ", end='')

    if isinstance(query, Query):
        if len(query.cause.split('=')) == 2: # todo treatment for compound queries
            cause_variable, cause_value = query.cause.split('=')
            cause_value = int(cause_value)
            effect_variable, effect_value = query.effect.split('=')
            effect_value = int(effect_value)
        else:
            # warnings.warn('Query format not supported. Probably a compound query.')
            print('\nWarning: Query format not supported. Probably a compound query.\n\n====================\n')
            return
    else:
        cause = query["query"]["cause"]
        effect = query["query"]["effect"]
        cause_variable, cause_value = next(iter(cause.items()))
        effect_variable, effect_value = next(iter(effect.items()))

    ### Preparation
    exogenous_vars = {var for var in vignette.variables if var not in vignette.equations}
    endogenous_vars = set(vignette.variables) - exogenous_vars

    if cause_variable not in vignette.variables or effect_variable not in vignette.variables:
        raise ValueError("Cause or effect variable is not in the vignette.")

    ## AC1 is implied
    if vignette.values_in_example[cause_variable] != cause_value:
        if verbose:
            # print(query)
            # print(vignette)
            print(f"(Theory: {theory})")
            print(f"Query: {cause_variable}={cause_value} is actual cause of {effect_variable}={effect_value}")
            # if query.query_text:
            #     print(f"— {query.query_text}") # todo: add query text to Query class
            if query.groundtruth[gt] in {0, 1}:
                print(f'Evaluation: FALSE\nGround truth: {"TRUE" if query.groundtruth[gt] else "FALSE"}')
            print(
                f"AC1 condition violated: Actual value of cause '{cause_variable}' ({vignette.values_in_example[cause_variable]}) "
                f"does not match expected value {cause_value}.\n\n====================\n"
            )
        return False

    if vignette.values_in_example[effect_variable] != effect_value:
        print(
            f"AC1 condition violated: Actual value of effect '{effect_variable}' ({vignette.values_in_example[effect_variable]}) "
            f"does not match expected value {effect_value}.\n"
        )
        return False

    if theory == 'HP2015':
        evaluation_result = False
        if verbose:
            print(f"(Theory: {theory})")
            print(f"Query: {cause_variable}={cause_value} is actual cause of {effect_variable}={effect_value}")

        ### AC2am
        # Find x' (an alternative value for the cause variable)
        x_prime= next((val for val in vignette.ranges[cause_variable] if val != cause_value), None)
        # x_prime = next(
        #     (val for val in vignette.variables[cause_variable]['range'] if val != cause_value),
        #     None
        # )

        if x_prime is None:
            raise ValueError(f"No alternative value found for {cause_variable}.")

        # Iterate over all subsets of variables excluding the cause variable
        for subset_w in powerset(set(vignette.variables) - {cause_variable}):
            # Restore defaults and set initial exogenous values
            vignette.reset_values()
            vignette.set_exogenous_values()

            # Set X = x' and W = w'
            vignette.set_value(cause_variable, x_prime)
            for var in subset_w:
                vignette.set_value(var, vignette.values_in_example[var])
            # vignette.set_value(cause_variable, x_prime)
            vignette.propagate_set_values()

            # Check the effect
            if vignette.values[effect_variable] != effect_value:
                evaluation_result = True
                if verbose:
                    print('Evaluation: TRUE\t', end='')
                    print(f"Witness: W={list(subset_w)}, w={[vignette.values[var] for var in subset_w]}, x'={x_prime}")
                break
        else:
            if verbose:
                print('Evaluation: FALSE')

        if verbose:
            if query.groundtruth[gt] in {0, 1}:
                # print(f'Ground truth: {"TRUE" if query["results"][theory] else "FALSE"}\n')
                print(f"Ground truth: {'TRUE' if query.groundtruth[gt] else 'FALSE'}\n")
            else:
                print("Ground truth not provided.\n")
            print("====================\n")
        return evaluation_result

    elif theory == 'HP2005':
        if verbose:
            print(f"(Theory: {theory})")
            print(f"Query: {cause_variable}={cause_value} is actual cause of {effect_variable}={effect_value}")

        evaluation_result = False
        for Z, W in all_splits_with_mandatory_element(vignette.variables, cause_variable):
            for x_prime in vignette.ranges[cause_variable]:
                if x_prime == cause_value:
                    continue
                for w_setting in (
                        {var: value for var, value in zip(W, w_settings)}
                        for w_settings in itertools.product(*[vignette.ranges[var] for var in W])
                ):
                    vignette.reset_values()
                    vignette.set_exogenous_values()
                    vignette.set_value(cause_variable, x_prime)
                    for var, val in w_setting.items():
                        vignette.set_value(var, val)
                    vignette.propagate_set_values()
                    if vignette.values[effect_variable] == effect_value:  # AC2a satisfied
                        continue
                    ac2b_satisfied = True
                    for subset_w, subset_z in itertools.product(powerset(W), powerset(Z)):
                        vignette.reset_values()
                        vignette.set_exogenous_values()
                        for w in subset_w:
                            vignette.set_value(w, w_setting[w])
                        for z in subset_z:
                            vignette.set_value(z, vignette.values_in_example[z])
                        vignette.propagate_set_values()
                        if vignette.values[effect_variable] != effect_value:
                            ac2b_satisfied = False
                            break
                    if ac2b_satisfied:
                        witness = f"Witness: W={list(subset_w)}, w'={w_setting}, x'={x_prime}"
                        evaluation_result = True
                        break
                if evaluation_result:
                    break
            if evaluation_result:
                break

        if verbose:
            if evaluation_result:
                print("Evaluation: TRUE\t", end='')
                print(witness)
            else:
                print("Evaluation: FALSE")
            if query.groundtruth[gt] in {0, 1}:
                print(f"Ground truth: {'TRUE' if query.groundtruth[gt] else 'FALSE'}\n")
            else:
                print("Ground truth not provided.\n")
            print("====================\n")
        return evaluation_result



    else:
        raise ValueError("Invalid theory")


### EVALUATION FUNCTIONS

def evaluate_theories(queries, theories: list):
    results = pd.DataFrame()

    for query in queries:
        query_results = dict()
        for theory in theories:
            pass
        pd.DataFrame.concat([query_results, results[theory]], ignore_index=True) # not sure if this is correct
    return results

def evaluate_all_queries(vignettes, queries, theory='HP2015', gt='intuition', skip:List=None):
    results = dict()
    print("\n====================\n")
    for i, query in enumerate(queries):
        if skip and query.v_id in skip:
            print(f"Skipping query {i} for vignette {query.v_id}\n====================\n")
            continue
        print(f"Evaluating query {i}")
        check_causality(theory, vignettes[query.v_id], query, gt=gt)

def reproduce_paper_results(vignettes, queries, query_list=HP2005_examples, theory='HP2005', gt='intuition', skip:List=None):
    results = dict()
    if not query_list:
        query_list = HP2005_examples
    print("\n====================\n")
    for i, query in enumerate(queries):
        if query.v_id in query_list:
            if skip and query.v_id in skip:
                print(f"Skipping query {i} for vignette {query.v_id}\n\n====================\n")
            else:
                print(f"Evaluating query {i}")
                check_causality(theory, vignettes[query.v_id], query, gt=gt)


if __name__ == "__main__":
    vignettes = load_vignettes(vignettes_path, variables_path)
    queries = load_queries(queries_path)
    # check_causality('HP2005', vignettes['ff_disj'], queries[0]) # test call for single query
    skip = ['rock_bottle_noisy', 'rock_bottle_time']
    # skip = []
    # evaluate_all_queries_csv(vignettes, queries, theory='HP2005', gt='intuition', skip=skip)

    reproduce_paper_results(vignettes=vignettes, queries=queries, query_list=HP2005_examples, theory='HP2005', gt='HP05', skip=skip)
    # todo: april rains returns TRUE, since this implementation considers any change in the effect variable as satisfying AC2a, while the paper seems to require a specific change (from 1 to 0).
    # todo: cannot handle query monday_treatment_deadly: Cause for being alive (B=0 or B=1 or B=2)
    # todo: is spell casting trumping different than command trumping?
    # reproduce_paper_results(vignettes=vignettes, queries=queries, query_list=HP2015_examples, theory='HP2015', gt='HP15', skip=skip)


print()
