import json

class AutoUpdatingObject:
    def __init__(self, variables, default_values, equations):
        self.variables = variables
        self.values = {var: val for var, val in zip(variables, default_values)}
        self.default_values = {var: val for var, val in zip(variables, default_values)}  # Store default values
        self.equations = self.parse_equations(equations)

    def parse_equations(self, equations):
        """Converts equation strings into callable functions."""
        parsed_equations = {}
        for var, eq in equations.items():
            # Create a lambda that evaluates the equation in the context of self.values
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
        return f"{self.values}"

# Load JSON
with open("../data/test.json", "r") as file:
    data = json.load(file)

# Create the object from JSON
config = data["a"]
obj = AutoUpdatingObject(
    variables=config["variables"],
    default_values=config["default_values"],
    equations=config["equations"]
)

# Example usage
print(obj)  # Initial values
obj.set_value("A", 5)  # Change A to 5
print(obj)  # Updated values
obj.restore_default_values()  # Restore default values
print(obj)  # Default values restored
