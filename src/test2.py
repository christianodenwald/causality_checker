import json

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
            parsed_equations[var] = lambda values, eq=eq: eval(eq, {}, values)
        return parsed_equations

    def update_values(self):
        """Updates all values based on equations."""
        for var, equation in self.equations.items():
            self.values[var] = equation(self.values)

    def set_value(self, var, value):
        """Sets a value and updates the dependent values."""
        if var in self.values:
            self.values[var] = value
            self.update_values()
        else:
            raise ValueError(f"Variable {var} does not exist.")

    def restore_default_values(self):
        """Restores all values to their default state without applying equations."""
        self.values = self.default_values.copy()

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
vignettes = load_vignettes("../data/vignettes.json")
for vignette in vignettes:
    print(vignette)
print()