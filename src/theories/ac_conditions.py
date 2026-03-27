import itertools
from typing import Any, Callable, List, Optional, Tuple


def check_ac1(
    vignette: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
) -> Optional[str]:
    """Return None if AC1 passes; otherwise return a human-readable violation message."""
    for cause_variable, cause_value in zip(cause_variables, cause_values):
        actual = vignette.values_in_example.get(cause_variable)
        if actual != cause_value:
            return f"AC1 violated: cause {cause_variable} actual={actual} != {cause_value}"

    actual_effect = vignette.values_in_example.get(effect_variable)
    if actual_effect != effect_value:
        return f"AC1 violated: effect actual={actual_effect} != {effect_value}"

    return None


def proper_subsets(cause_variables: List[str], cause_values: List[int]) -> List[Tuple[List[str], List[int]]]:
    """Generate all non-empty proper subsets of the cause assignment."""
    subsets: List[Tuple[List[str], List[int]]] = []
    for r in range(1, len(cause_variables)):
        for subset_indices in itertools.combinations(range(len(cause_variables)), r):
            subset_vars = [cause_variables[i] for i in subset_indices]
            subset_vals = [cause_values[i] for i in subset_indices]
            subsets.append((subset_vars, subset_vals))
    return subsets


def check_ac3(
    cause_variables: List[str],
    cause_values: List[int],
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Optional[str]:
    """Return AC3 violation details if a proper subset is also a cause; otherwise None."""
    if len(cause_variables) <= 1:
        return None

    for subset_vars, subset_vals in proper_subsets(cause_variables, cause_values):
        if subset_is_cause(subset_vars, subset_vals):
            subset_cause_str = " and ".join(
                [f"{var}={val}" for var, val in zip(subset_vars, subset_vals)]
            )
            return f"AC3 violated: proper subset {subset_cause_str} is also a cause"

    return None