import itertools
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .ac_conditions import check_ac1, check_ac3


Edge = Tuple[str, str]


def _generate_paths(
    children_map: Dict[str, List[str]],
    cause_variables: List[str],
    effect_variable: str,
) -> Dict[str, List[List[Edge]]]:
    """Generate all directed paths from each cause variable to the effect variable."""

    def dfs(
        current: str,
        target: str,
        visited: List[str],
        edge_path: List[Edge],
        paths: List[List[Edge]],
    ) -> None:
        if current == target:
            paths.append(edge_path.copy())
            return
        for child in children_map.get(current, []):
            if child in visited:
                continue
            visited.append(child)
            edge_path.append((current, child))
            dfs(child, target, visited, edge_path, paths)
            edge_path.pop()
            visited.pop()

    result: Dict[str, List[List[Edge]]] = {}
    for cause_var in cause_variables:
        all_paths: List[List[Edge]] = []
        dfs(cause_var, effect_variable, [cause_var], [], all_paths)
        result[cause_var] = all_paths
    return result


def _generate_networks_per_cause(paths_from_causes: Dict[str, List[List[Edge]]]) -> Dict[str, List[Set[Edge]]]:
    """Create networks as unions of non-empty subsets of paths per cause."""
    networks_from_cause: Dict[str, List[Set[Edge]]] = {}
    for cause_var, paths in paths_from_causes.items():
        networks_for_cause: List[Set[Edge]] = []
        seen: Set[frozenset[Edge]] = set()
        n = len(paths)
        for r in range(1, n + 1):
            for combo in itertools.combinations(paths, r):
                edges_union: Set[Edge] = set()
                for path in combo:
                    for edge in path:
                        edges_union.add(edge)
                key = frozenset(edges_union)
                if key in seen:
                    continue
                seen.add(key)
                networks_for_cause.append(edges_union)
        networks_from_cause[cause_var] = networks_for_cause
    return networks_from_cause


def _generate_networks(networks_from_cause: Dict[str, List[Set[Edge]]]) -> List[Set[Edge]]:
    """Combine one network per cause into full networks."""
    per_cause_options: List[List[Set[Edge]]] = [nets for nets in networks_from_cause.values()]
    if not per_cause_options:
        return []

    combined_networks: List[Set[Edge]] = []
    seen: Set[frozenset[Edge]] = set()
    for selection in itertools.product(*per_cause_options):
        edges_union: Set[Edge] = set()
        for net in selection:
            edges_union.update(net)

        key = frozenset(edges_union)
        if key in seen:
            continue
        seen.add(key)
        combined_networks.append(edges_union)
    return combined_networks


def _evaluate_gallow_variant(
    theory_variant: str,
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    """Preliminary Gallow-style evaluator with placeholders for non-prelim variants."""
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

    if not hasattr(vignette, "children") or not isinstance(vignette.children, dict):
        return {
            "terminal": True,
            "result": None,
            "witness": None,
            "details": "gallow_* theories require `vignette.children` adjacency map.",
        }

    paths_from_causes = _generate_paths(vignette.children, cause_variables, effect_variable)
    networks_from_cause = _generate_networks_per_cause(paths_from_causes)
    networks = _generate_networks(networks_from_cause)

    evaluation_result = False
    witness_str: Optional[str] = None

    if theory_variant == "gallow_prelim":
        for net in networks:
            parents_in_net: Dict[str, List[str]] = {}
            for u, v in net:
                if v not in parents_in_net:
                    parents_in_net[v] = []
                parents_in_net[v].append(u)

            effect_alternatives = [val for val in vignette.ranges[effect_variable] if val != effect_value]
            if not effect_alternatives:
                continue

            net_vars: Set[str] = set()
            for u, v in net:
                net_vars.add(u)
                net_vars.add(v)

            contrast_options: Dict[str, List[int]] = {}
            for var in net_vars:
                actual_val = vignette.values_in_example.get(var)
                alternatives = [val for val in vignette.ranges[var] if val != actual_val]
                contrast_options[var] = alternatives if alternatives else [actual_val]

            net_vars_list = list(net_vars)
            for contrast_combination in itertools.product(*[contrast_options[v] for v in net_vars_list]):
                contrast_assignment = dict(zip(net_vars_list, contrast_combination))

                def check_dependency_chain(var: str, contrast_val: int, visited: Optional[Set[str]] = None) -> bool:
                    if visited is None:
                        visited = set()
                    if var in visited:
                        return True
                    visited.add(var)

                    parents = parents_in_net.get(var, [])
                    if not parents:
                        if var in cause_variables:
                            cause_idx = cause_variables.index(var)
                            expected_val = cause_values[cause_idx]
                            return contrast_val != expected_val
                        return True

                    vignette.reset_values()
                    vignette.set_exogenous_values()
                    for parent in parents:
                        vignette.set_value(parent, vignette.values_in_example[parent])
                    vignette.propagate_set_values()

                    vignette.reset_values()
                    vignette.set_exogenous_values()
                    for parent in parents:
                        vignette.set_value(parent, contrast_assignment[parent])
                    vignette.propagate_set_values()
                    contrast_result = vignette.values[var]

                    if contrast_result != contrast_val:
                        return False

                    for parent in parents:
                        if not check_dependency_chain(parent, contrast_assignment[parent], visited):
                            return False
                    return True

                if check_dependency_chain(effect_variable, contrast_assignment[effect_variable]):
                    evaluation_result = True
                    witness_str = f"Witness: Network={list(net)}, Contrasts={contrast_assignment}"
                    break

            if evaluation_result:
                break

    elif theory_variant == "gallow_causal":
        # Placeholder for stricter checks than gallow_prelim.
        for _net in networks:
            pass

    elif theory_variant == "gallow_productive":
        # Placeholder for productive causation checks.
        pass

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


def evaluate_gallow_prelim(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    return _evaluate_gallow_variant(
        theory_variant="gallow_prelim",
        vignette=vignette,
        query=query,
        cause_variables=cause_variables,
        cause_values=cause_values,
        effect_variable=effect_variable,
        effect_value=effect_value,
        subset_is_cause=subset_is_cause,
    )


def evaluate_gallow_causal(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    return _evaluate_gallow_variant(
        theory_variant="gallow_causal",
        vignette=vignette,
        query=query,
        cause_variables=cause_variables,
        cause_values=cause_values,
        effect_variable=effect_variable,
        effect_value=effect_value,
        subset_is_cause=subset_is_cause,
    )


def evaluate_gallow_productive(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    return _evaluate_gallow_variant(
        theory_variant="gallow_productive",
        vignette=vignette,
        query=query,
        cause_variables=cause_variables,
        cause_values=cause_values,
        effect_variable=effect_variable,
        effect_value=effect_value,
        subset_is_cause=subset_is_cause,
    )