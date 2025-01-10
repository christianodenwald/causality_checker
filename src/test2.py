import json

# Paths to JSON files
vignettes_path = "../data/vignettes.json"
settings_path = "../data/settings.json"


class Vignette:
    def __init__(self, vignette_id, title, description, variables, default_values, equations, notes):
        self.vignette_id = vignette_id
        self.title = title
        self.description = description
        self.variables = variables
        self.values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.default_values = {var: val for var, val in zip(variables.keys(), default_values)}
        self.equations = self.parse_equations(equations)
        self.notes = notes

    def parse_equations(self, equations):
        """Converts equation strings into callable functions."""
        parsed_equations = {}
        for var, eq in equations.items():
            parsed_equations[var] = lambda values, eq=eq: int(eval(eq, {}, values))
        return parsed_equations

    def update_values(self):
        """Updates all values based on equations."""
        for var, equation in self.equations.items():
            self.values[var] = equation(self.values)

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
        vignettes.append(
            Vignette(
                vignette_id=vignette_data["id"],
                title=vignette_data["title"],
                description=vignette_data["description"],
                variables=variables,
                default_values=default_values,
                equations=equations,
                notes=vignette_data["notes"],
            )
        )
    return vignettes


# Example usage
vignettes = load_vignettes(vignettes_path)
for vignette in vignettes:
    print(vignette)

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
test_vignettes(vignettes)

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
for vignette in vignette_instances:
    print(vignette)



    
print()