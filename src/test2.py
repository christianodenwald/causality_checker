import json
import itertools
from HP2015 import *

# Paths to JSON files
vignettes_path = "../data/vignettes.json"
settings_path = "../data/settings.json"
queries_path = "../data/queries.json"

class Vignette:
    def __init__(self, vignette_id, title, description, variables, ranges, default_values, equations, notes):
        self.vignette_id = vignette_id
        self.title = title
        self.description = description
        self.variables = variables
        self.ranges = ranges
        self.values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.default_values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.equations = self.parse_equations(equations)
        self.notes = notes

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
        for var, value in self.default_values.items():
            self.set_value(var, None)

    def propagate_set_values(self):
        for var, value in self.values.items():
            if value is None:
                new_value = self.equations[var](self.values)
                self.set_value(var, new_value)


    def __repr__(self):
        return f"Vignette({self.vignette_id}, {self.title}, {self.values})"



# Function to load vignettes from JSON
def load_vignettes(json_path):
    """Loads vignettes from a JSON file."""
    with open(json_path, "r") as file:
        data = json.load(file)

    vignettes = []
    for vignette_data in data["vignettes"]:
        variables = vignette_data["variables"]
        default_values = [0 for _ in variables.keys()]  # Default values are initially set to 0
        equations = vignette_data["structural_equations"]
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
                notes=vignette_data["notes"],
            )
        )
    return vignettes


# Example usage
vignettes = load_vignettes(vignettes_path)
# for vignette in vignettes:
#     print(vignette)

###############################
# Test if setting values works properly

def test_vignettes(vignettes):
    for vignette in vignettes:
        print(f"\nTesting Vignette: {vignette.title} ({vignette.vignette_id})")
        print("Initial values:", vignette.values)

        # Test setting values and updating equations
        for var in vignette.values:
            try:
                # Set a test value (toggle between 0 and 1)
                test_value = 1 if vignette.values[var] == 0 else 0
                print(f"Setting {var} to {test_value}")
                vignette.set_value_and_update(var, test_value)
                print("Updated values:", vignette.values)
            except Exception as e:
                print(f"Error while testing {var}: {e}")

        # Restore default values and verify
        print("Restoring default values...")
        vignette.restore_default_values()
        print("Default values restored:", vignette.values)


# Run tests
# test_vignettes(vignettes)

#############

def load_settings(settings_path):
    """Load settings from the JSON file."""
    with open(settings_path, 'r') as f:
        return json.load(f)

def create_vignettes_with_settings(vignettes_path, settings_path):
    """Create vignettes with settings applied."""
    # Load vignettes and settings
    vignettes_data = load_vignettes(vignettes_path)
    settings_data = load_settings(settings_path)

    # Dictionary to map vignette IDs to vignette objects
    vignette_map = {vignette.vignette_id: vignette for vignette in vignettes_data}

    # Create instances based on settings
    vignette_instances = []
    for setting in settings_data['initial_values']:
        vignette_id = setting['vignette_id']
        if vignette_id in vignette_map:
            # Clone the vignette and apply the setting
            original_vignette = vignette_map[vignette_id]
            vignette = Vignette(
                vignette_id=setting['setting_id'],
                title=original_vignette.title,
                description=original_vignette.description,
                variables=original_vignette.variables,
                ranges=original_vignette.ranges,
                default_values=list(setting['initial_values'].values()),
                equations=original_vignette.equations,
                notes=original_vignette.notes
            )
            vignette.restore_default_values()  # Ensure default values are set
            vignette_instances.append(vignette)
        else:
            print(f"Warning: Vignette ID {vignette_id} not found in vignettes.json")

    return vignette_instances



# Create vignette instances with settings applied
vignette_instances = create_vignettes_with_settings(vignettes_path, settings_path)

# Display the initialized vignettes
# for vignette in vignette_instances:
#     print(vignette)


########################

# def load_queries(query_path):
#     with open(query_path, 'r') as f:
#         return json.load(f)
#
# queries = load_queries(queries_path)["queries"]

########################

def check_causality(theory, vignette, query_json):
    """
    Checks causality based on a given theory using the updated Vignette class.
    :param theory: The theory to apply ('HP2015', 'HP2005').
    :param vignette: A Vignette object.
    :param cause_variable: The cause variable name.
    :param cause_value: The cause variable value.
    :param effect_variable: The effect variable name.
    :param effect_value: The effect variable value.
    """
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

    ### AC1 is implied

    if theory == 'HP2015':
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
                print('Evaluation: TRUE\t', end='')
                print(f"Witness: W={list(subset_w)}, w={[vignette.values[var] for var in subset_w]}, x'={x_prime}")
                break
        else:
            print('Evaluation: FALSE')

        print(f'Ground truth: {"TRUE" if query_json["results"][theory] else "FALSE"}\n')
        print("====================\n")

    elif theory == 'HP2005':
        pass  # Implement if needed

    else:
        raise ValueError("Invalid theory")



def load_queries(query_path):
    with open(query_path, 'r') as f:
        return json.load(f)
queries = load_queries(queries_path)
query_json = queries['queries'][4]



check_causality('HP2015', vignette_instances[4], queries['queries'][4]) # Suzy throws
check_causality('HP2015', vignette_instances[4], queries['queries'][5]) # Billy throws






print()