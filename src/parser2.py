# Input JSON-like data for structural equations
vignette = {
    "id": "v01-ff_disj",
    "title": "FF Disjunctive",
    "variables": {
        "ML": {"description": "Match lit", "range": [0, 1]},
        "L": {"description": "Lightning strike", "range": [0, 1]},
        "FF": {"description": "Forest fire", "range": [0, 1]},
        "A": {"description": "A", "range": [0, 1]},
        "B": {"description": "B", "range": [0, 1]},
        "C": {"description": "C", "range": [0, 1]},
        "D": {"description": "D", "range": [0, 1]},
        "E": {"description": "E", "range": [0, 1]}
    },
    "structural_equations": {
        "FF": "ML or L",            # Example: Disjunctive
        "A": "ML and L",            # Example: Conjunctive
        "B": "ML and not L",        # Example: Conditional
        "C": "max(ML, L)",          # Example: Max function
        "D": "min(ML, L)",          # Example: Min function
        "E": "ML + L"               # Example: Arithmetic
    }
}

# Step 1: Initialize the vignette dictionary in the required format
vignette_data = {
    'name': vignette['title'],
    'variables': list(vignette['variables'].keys()),
    'initial_values': [1] * len(vignette['variables']),  # Default initial values
    'current_values': [None] * len(vignette['variables']),
    'value_ranges': [set(var['range']) for var in vignette['variables'].values()],
    'structural_equations': [None] * len(vignette['variables'])
}

# Map variables to their indices
variable_indices = {var: idx for idx, var in enumerate(vignette_data['variables'])}

# Step 2: Parse and generate all structural equations dynamically
import math  # For min/max functions in eval

# Helper function to evaluate equations
def generate_lambda(equation, variables):
    # Replace variable names with indices in current_values
    for var, idx in variable_indices.items():
        equation = equation.replace(var, f"vignette_data['current_values'][{idx}]")
    # Return a lambda function that evaluates the equation
    return eval(f"lambda: int({equation})")

# Generate lambdas for all structural equations
for var, equation in vignette['structural_equations'].items():
    vignette_data['structural_equations'][variable_indices[var]] = generate_lambda(equation, vignette_data['variables'])

# Step 3: Add a test function to validate all structural equations
def test_structural_equations():
    # Test cases for current values
    test_cases = [
        [0, 0, None, None, None, None, None, None],  # Test case 1: ML=0, L=0
        [1, 0, None, None, None, None, None, None],  # Test case 1: ML=1, L=0
        [0, 1, None, None, None, None, None, None],  # Test case 2: ML=0, L=1
        [1, 1, None, None, None, None, None, None]   # Test case 3: ML=1, L=1
    ]
    # Process each test case
    for test_case in test_cases:
        vignette_data['current_values'] = test_case
        for var, idx in variable_indices.items():
            equation = vignette_data['structural_equations'][idx]
            if equation is not None:
                vignette_data['current_values'][idx] = equation()
        print(vignette_data['current_values'])  # Outputs evaluated current values for each test case

# Call the test function
test_structural_equations()