from dataclasses import dataclass
from typing import Dict, Set, List, Callable, Any, Optional
from enum import Enum


class VariableType(Enum):
    EXOGENOUS = "exogenous"
    ENDOGENOUS = "endogenous"


@dataclass
class Variable:
    name: str
    possible_values: Set[Any]
    type: VariableType


class StructuralEquation:
    def __init__(self, target_variable: Variable, equation: Callable):
        self.target_variable = target_variable
        self.equation = equation

    def evaluate(self, variable_values: Dict[str, Any]) -> Any:
        return self.equation(variable_values)


class Vignette:
    def __init__(self, name: str):
        self.name = name
        self.variables: Dict[str, Variable] = {}
        self.structural_equations: Dict[str, StructuralEquation] = {}
        self.initial_conditions: Dict[str, Any] = {}

    def add_variable(self, variable: Variable) -> None:
        self.variables[variable.name] = variable

    def add_structural_equation(self, equation: StructuralEquation) -> None:
        self.structural_equations[equation.target_variable.name] = equation

    def set_initial_condition(self, variable_name: str, value: Any) -> None:
        if variable_name not in self.variables:
            raise ValueError(f"Variable {variable_name} not found in vignette")
        if self.variables[variable_name].type != VariableType.EXOGENOUS:
            raise ValueError(f"Cannot set initial condition for endogenous variable {variable_name}")
        if value not in self.variables[variable_name].possible_values:
            raise ValueError(f"Value {value} not in possible values for {variable_name}")
        self.initial_conditions[variable_name] = value

    def evaluate_model(self, intervention: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Start with initial conditions
        current_values = self.initial_conditions.copy()

        # Apply intervention if provided
        if intervention:
            current_values.update(intervention)

        # Evaluate all structural equations until fixed point
        changed = True
        while changed:
            changed = False
            for var_name, equation in self.structural_equations.items():
                new_value = equation.evaluate(current_values)
                if var_name not in current_values or current_values[var_name] != new_value:
                    current_values[var_name] = new_value
                    changed = True

        return current_values


class Halpern2016Theory:
    @staticmethod
    def is_cause(vignette: Vignette, cause_var: str, effect_var: str) -> bool:
        # Implement Halpern's 2016 definition of actual causation
        # AC1: Actual value of cause and effect
        actual_values = vignette.evaluate_model()
        actual_cause_val = actual_values[cause_var]
        actual_effect_val = actual_values[effect_var]

        # AC2: Check if there exists an alternative value of the cause
        var = vignette.variables[cause_var]
        for alternative_value in var.possible_values:
            if alternative_value == actual_cause_val:
                continue

            # Test intervention with alternative cause value
            intervention = {cause_var: alternative_value}
            alternative_values = vignette.evaluate_model(intervention)

            # If effect changes, potential cause found
            if alternative_values[effect_var] != actual_effect_val:
                return True

        return False


def is_cause(vignette: Vignette, theory: Any, variable_cause: str, variable_effect: str) -> bool:
    """
    Generic function to determine if variable_cause is an actual cause of variable_effect
    in the given vignette according to the specified theory.
    """
    if isinstance(theory, Halpern2016Theory):
        return theory.is_cause(vignette, variable_cause, variable_effect)
    else:
        raise ValueError("Unsupported theory")


# Example usage
def create_forest_fire_vignette() -> Vignette:
    # Create a simple forest fire vignette where match and lightning can cause a fire
    vignette = Vignette("forest_fire")

    # Define variables
    match = Variable("match", {True, False}, VariableType.EXOGENOUS)
    lightning = Variable("lightning", {True, False}, VariableType.EXOGENOUS)
    fire = Variable("fire", {True, False}, VariableType.ENDOGENOUS)

    vignette.add_variable(match)
    vignette.add_variable(lightning)
    vignette.add_variable(fire)

    # Define structural equation for fire
    def fire_equation(values: Dict[str, bool]) -> bool:
        return values["match"] or values["lightning"]

    vignette.add_structural_equation(StructuralEquation(fire, fire_equation))

    # Set initial conditions
    vignette.set_initial_condition("match", True)
    vignette.set_initial_condition("lightning", False)

    return vignette


if __name__ == '__main__':

    print()