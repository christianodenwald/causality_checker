import itertools
from typing import Any, Dict, List, Optional


def _powerset(iterable):
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))


def evaluate_hp2015(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
) -> Dict[str, Any]:
    """Evaluate HP2015 AC2-style search for a parsed query."""
    cause_alternatives = []
    for cause_variable, cause_value in zip(cause_variables, cause_values):
        alternatives = [val for val in vignette.ranges[cause_variable] if val != cause_value]
        if not alternatives:
            return {
                "terminal": True,
                "result": None,
                "witness": None,
                "details": f"No alternative value found for {cause_variable}.",
            }
        cause_alternatives.append(alternatives)

    evaluation_result = False
    witness_str: Optional[str] = None

    for x_primes in itertools.product(*cause_alternatives):
        non_cause_vars = set(vignette.variables) - set(cause_variables)
        for subset_w in _powerset(non_cause_vars):
            vignette.reset_values()
            vignette.set_exogenous_values()

            for cause_variable, x_prime in zip(cause_variables, x_primes):
                vignette.set_value(cause_variable, x_prime)

            for var in subset_w:
                vignette.set_value(var, vignette.values_in_example[var])
            vignette.propagate_set_values()

            effect_differs = vignette.values[effect_variable] != effect_value
            if query.effect_contrast is not None:
                effect_differs = effect_differs and vignette.values[effect_variable] == query.effect_contrast

            if effect_differs:
                evaluation_result = True
                witness_str = f"Witness: W={list(subset_w)}, w={[vignette.values[var] for var in subset_w]}, x'={list(x_primes)}"
                break

        if evaluation_result:
            break

    return {
        "terminal": False,
        "result": evaluation_result,
        "witness": witness_str,
        "details": None,
    }
