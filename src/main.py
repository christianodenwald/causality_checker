import itertools
import json

from HP2015 import powerset
from src.HP2015 import all_splits_with_mandatory_element

# Paths to JSON files
vignettes_path = "../data/vignettes_new.json"
queries_path = "../data/queries.json"


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

    def __init__(self, vignette_id, title, description, variables, ranges, default_values, equations):
        self.vignette_id = vignette_id
        self.title = title
        self.description = description
        self.variables = variables
        self.ranges = ranges
        self.values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.default_values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.equations = self.parse_equations(equations)

    def parse_equations(self, equations):
        """
        Converts equation strings into callable functions if they are not already callables.
        """
        parsed_equations = {}
        for var, eq in equations.items():
            if isinstance(eq, str):  # If it's a string, parse it
                parsed_equations[var] = lambda values, eq=eq: int(eval(eq, {}, values))
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

    def restore_default_values(self):
        """Restores all values to their default state without applying equations."""
        self.values = self.default_values.copy()

    def set_exogenous_values(self):
        """Updates exogenous values without triggering updates for dependent values."""
        for var, value in self.values.items():
            if var in self.equations.keys():
                self.set_value(var, None)
            else:
                self.set_value(var, self.default_values[var])

    def reset_values(self):
        """Sets all values to None."""
        for var, value in self.default_values.items():
            self.set_value(var, None)

    def propagate_set_values(self):
        """Propagates values based on equations based on values that are already set."""
        for var, value in self.values.items():
            if value is None:
                new_value = self.equations[var](self.values)
                self.set_value(var, new_value)

    def __repr__(self):
        return f"Vignette({self.vignette_id}, {self.title}, {self.values})"


#### METHODS


def load_vignettes(json_path):
    """Loads vignettes from a JSON file."""
    with open(json_path, "r") as file:
        data = json.load(file)

    vignettes = []
    for vignette_data in data:
        variables = vignette_data["variables"]
        default_values = [details['initial_value'] for details in vignette_data['variables'].values()]
        equations = {var:details['structural_equation'] for var, details in vignette_data['variables'].items() if 'structural_equation' in details}

        # Extract variable ranges
        ranges = {var: info["range"] for var, info in variables.items()}
        vignettes.append(
            Vignette(
                vignette_id=vignette_data["id"],
                title=vignette_data["title"],
                description=vignette_data["description"],
                variables=variables,
                ranges=ranges,
                default_values=default_values,
                equations=equations,
            )
        )
    return vignettes


def load_queries(query_path):
    with open(query_path, 'r') as f:
        return json.load(f)



def check_causality(theory, vignette, query_json, verbose=True):
    """
        Determines whether a given query satisfies causality conditions based on a specified theory
        in the context of a given vignette. It checks conditions using the query's cause-effect
        relationship and evaluated results. The function can provide verbose output optionally.

        Parameters:
            theory: str
                The causality theory to be verified (e.g., 'HP2015', 'HP2005').
            vignette: object
                A vignette model containing variables, equations, and their relationships.
            query_json: dict
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

    cause = query_json["query"]["cause"]
    effect = query_json["query"]["effect"]
    cause_variable, cause_value = next(iter(cause.items()))
    effect_variable, effect_value = next(iter(effect.items()))

    ### Preparation
    exogenous_vars = {var for var in vignette.variables if var not in vignette.equations}
    endogenous_vars = set(vignette.variables) - exogenous_vars

    if cause_variable not in vignette.variables or effect_variable not in vignette.variables:
        raise ValueError("Cause or effect variable is not in the vignette.")

    ## AC1 is implied
    if vignette.default_values[cause_variable] != cause_value:
        print(query_json)
        print(vignette)
        raise ValueError(
            f"AC1 condition violated: Default value of '{cause_variable}' ({vignette.default_values[cause_variable]}) "
            f"does not match expected value {cause_value}."
        )

    if vignette.default_values[effect_variable] != effect_value:
        raise ValueError(
            f"AC1 condition violated: Default value of '{effect_variable}' ({vignette.default_values[effect_variable]}) "
            f"does not match expected value {effect_value}."
        )

    if theory == 'HP2015':
        if verbose:
            print(f"(Theory: {theory})")
            print(f"Query: {cause_variable}={cause_value} is actual cause of {effect_variable}={effect_value}")

        ### AC2am
        # Find x' (an alternative value for the cause variable)
        x_prime = next(
            (val for val in vignette.variables[cause_variable]['range'] if val != cause_value),
            None
        )

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
                vignette.set_value(var, vignette.default_values[var])
            # vignette.set_value(cause_variable, x_prime)
            vignette.propagate_set_values()

            # Check the effect
            if vignette.values[effect_variable] != effect_value:
                if verbose:
                    print('Evaluation: TRUE\t', end='')
                    print(f"Witness: W={list(subset_w)}, w={[vignette.values[var] for var in subset_w]}, x'={x_prime}")
                    break
        else:
            if verbose:
                print('Evaluation: FALSE')

        if query_json["results"][theory] in {0, 1}:
            if verbose:
                print(f'Ground truth: {"TRUE" if query_json["results"][theory] else "FALSE"}\n')
        else:
            if verbose:
                print("Ground truth not provided.\n")
        if verbose:
            print("====================\n")

    elif theory == 'HP2005':
        if verbose:
            print(f"(Theory: {theory})")
            print(f"Query: {cause_variable}={cause_value} is actual cause of {effect_variable}={effect_value}")

        evaluation_result = False
        for Z, W in all_splits_with_mandatory_element(vignette.variables, cause_variable):
            for x_prime in vignette.variables[cause_variable]['range']:
                if x_prime == cause_value:
                    continue
                for w_setting in (
                        {var: value for var, value in zip(W, w_settings)}
                        for w_settings in itertools.product(*[vignette.variables[var]['range'] for var in W])
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
                            vignette.set_value(z, vignette.default_values[z])
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

        if evaluation_result:
            if verbose:
                print("Evaluation: TRUE\t", end='')
                print(witness)
        else:
            if verbose:
                print("Evaluation: FALSE")
        print(f"Ground truth: {'TRUE' if query_json['results'][theory] else 'FALSE'}\n")
        print("====================\n")



    else:
        raise ValueError("Invalid theory")


def evaluate_all_queries(vignettes, queries, theory='HP2015'):
    for query in queries:
        matching_vignettes = [vignette for vignette in vignettes if vignette.vignette_id == query['vignette_id']]
        if not matching_vignettes:
            raise ValueError(f"No matching vignette_id {query['vignette_id']} found for the query.")
        for vignette in matching_vignettes:
            check_causality(theory, vignette, query)


if __name__ == "__main__":
    vignettes = load_vignettes(vignettes_path)
    # vignettes = create_vignettes_with_settings(vignettes_path, settings_path)
    queries = load_queries(queries_path)

    # check_causality('HP2005', vignettes[3], queries[3])

    evaluate_all_queries(vignettes, queries, theory='HP2015')
    evaluate_all_queries(vignettes, queries, theory='HP2005')

print()
