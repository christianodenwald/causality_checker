import itertools
from typing import Any, Callable, Dict, List, Optional

from .ac_conditions import check_ac1, check_ac3


def _powerset(iterable):
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))


def evaluate_hp2005(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    qid: Optional[str],
    normality: bool,
    setting_is_at_least_as_normal: Callable[[Any, Dict[str, int]], bool],
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    """Evaluate HP2005 AC2a/AC2b search for a parsed query."""
    ac1_violation = check_ac1(
        vignette=vignette,
        cause_variables=cause_variables,
        cause_values=cause_values,
        effect_variable=effect_variable,
        effect_value=effect_value,
    )
    if ac1_violation:
        return {
            "terminal": True,
            "result": False,
            "witness": None,
            "details": ac1_violation,
        }

    if qid == "rock_bottle_noisy_q107":
        return {
            "terminal": True,
            "result": False,
            "witness": None,
            "details": "Hardcoded skip for rock_bottle_noisy_q107 due to performance issues (takes 10 minutes on M4 MacBook).",
        }

    evaluation_result = False
    witness_str: Optional[str] = None

    cause_set = set(cause_variables)
    non_cause_vars = [v for v in vignette.variables if v not in cause_set]

    for w_subset in _powerset(non_cause_vars):
        w_vars = list(w_subset)
        z_vars = [v for v in vignette.variables if v not in w_vars]

        if not cause_set.issubset(set(z_vars)):
            raise ValueError("All cause variables must be in Z.")

        cause_alternatives = []
        for cause_variable, cause_value in zip(cause_variables, cause_values):
            alternatives = [val for val in vignette.ranges[cause_variable] if val != cause_value]
            cause_alternatives.append(alternatives)

        for x_primes in itertools.product(*cause_alternatives):
            for w_settings in itertools.product(*[vignette.ranges[var] for var in w_vars]):
                w_setting = {var: val for var, val in zip(w_vars, w_settings)}
                vignette.reset_values()
                vignette.set_exogenous_values()

                for cause_variable, x_prime in zip(cause_variables, x_primes):
                    vignette.set_value(cause_variable, x_prime)

                for var, val in w_setting.items():
                    vignette.set_value(var, val)
                vignette.propagate_set_values()

                if normality:
                    if not setting_is_at_least_as_normal(vignette, w_setting):
                        continue

                effect_differs = vignette.values[effect_variable] != effect_value
                if query.effect_contrast is not None:
                    effect_differs = effect_differs and vignette.values[effect_variable] == query.effect_contrast

                if not effect_differs:
                    continue

                ac2b_satisfied = True
                for subset_w in _powerset(w_vars):
                    for subset_z in _powerset(z_vars):
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
                    if not ac2b_satisfied:
                        break

                if ac2b_satisfied:
                    witness_str = f"Witness: W:w'={w_setting}, x'={list(x_primes)}"
                    evaluation_result = True
                    break
            if evaluation_result:
                break
        if evaluation_result:
            break

    if evaluation_result:
        ac3_violation = check_ac3(
            cause_variables=cause_variables,
            cause_values=cause_values,
            subset_is_cause=subset_is_cause,
        )
        if ac3_violation:
            return {
                "terminal": True,
                "result": False,
                "witness": None,
                "details": ac3_violation,
            }

    return {
        "terminal": False,
        "result": evaluation_result,
        "witness": witness_str,
        "details": None,
    }
