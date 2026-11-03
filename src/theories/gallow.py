import itertools
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .ac_conditions import check_ac1


Edge = Tuple[str, str]
Network = frozenset[Edge]


def _generate_paths(
    children_map: Dict[str, List[str]], # dict of parent -> list of children
    start: str,
    target: str,
) -> List[List[Edge]]:
    """Return all simple directed paths from ``start`` to ``target``."""

    paths: List[List[Edge]] = []

    # DFS to find all paths
    def visit(current: str, visited: Set[str], path: List[Edge]) -> None:
        if current == target:
            paths.append(path.copy())
            return
        for child in children_map.get(current, []):
            if child in visited:
                continue
            visit(child, visited | {child}, path + [(current, child)])

    visit(start, {start}, [])
    return paths


def _generate_networks_for_cause_tuple(
    children_map: Dict[str, List[str]],
    cause_variables: List[str],
    effect_variable: str,
) -> List[Network]:
    """Generate unions of paths with one non-empty path set per cause."""
    per_cause: List[List[Network]] = [] # list of lists of networks, one list per cause variable
    # For each cause variable, generate all paths to the effect variable and create networks from combinations of those paths
    for cause_variable in cause_variables:
        paths = _generate_paths(children_map, cause_variable, effect_variable)
        options: Set[Network] = set()
        for size in range(1, len(paths) + 1):
            for selected in itertools.combinations(paths, size):
                options.add(frozenset(edge for path in selected for edge in path))
        if not options:
            return []
        per_cause.append(list(options))

    networks: Set[Network] = set()
    for selection in itertools.product(*per_cause):
        networks.add(frozenset(edge for network in selection for edge in network))
    # todo: assert that all causes are connected to the effect in each network
    # todo: could filter out non-minimal networks here
    return list(networks)


def _parents_in_network(network: Network) -> Dict[str, Set[str]]:
    """turns a set of edges into a parent map"""
    parents: Dict[str, Set[str]] = {}
    for parent, child in network:
        parents.setdefault(child, set()).add(parent)
    return parents


def _evaluate_structural_equation(
    vignette: Any,
    variable: str,
    values: Dict[str, int],
) -> int:
    equation = vignette.equations.get(variable)
    if equation is None:
        raise ValueError(f"Structural equation for {variable} required.")
    return int(equation(values))


def _local_dependence(
    vignette: Any,
    variable: str,
    network_parents: Set[str],
    contrasts: Dict[str, int],
) -> bool:
    """Check Gallow's local dependence condition for one network variable."""
    #todo check if this is correct
    actual_values = dict(vignette.values_in_example)
    contrast_values = dict(actual_values)
    for parent in network_parents:
        if parent not in contrasts:
            return False
        contrast_values[parent] = contrasts[parent]

    actual_result = _evaluate_structural_equation(vignette, variable, actual_values)
    contrast_result = _evaluate_structural_equation(vignette, variable, contrast_values)
    return (
        actual_result == vignette.values_in_example[variable]
        and contrast_result == contrasts[variable]
    )


def _is_more_deviant(vignette: Any, variable: str, value: int, contrast: int) -> bool:
    """Use the dataset's default-value encoding as Gallow's deviance ordering."""
    # todo: implement more general ordering in whole codebase
    # if no defaults are specified, assume 0 is the default value
    defaults = vignette.default_values.get(variable)
    if not defaults:
        defaults = [0]
    return value not in defaults and contrast in defaults


def _network_parents_and_nodes(network: Network) -> Tuple[Dict[str, Set[str]], Set[str]]:
    """Return the parent map and node set for a network."""
    parents = _parents_in_network(network)
    nodes = set(parents)
    nodes.update(parent for edge in network for parent in edge[:1])
    return parents, nodes


def _path_exists(
    children_map: Dict[str, List[str]],
    start: str,
    target: str,
    allowed_edges: Optional[Network] = None,
) -> bool:
    for path in _generate_paths(children_map, start, target):
        if allowed_edges is None or frozenset(path).issubset(allowed_edges):
            return True
    return False


def _departure_return_pairs(
    vignette: Any,
    network: Network,
) -> Set[Tuple[str, str]]:
    """Find network departure/return pairs with an omitted route between them."""
    _, nodes = _network_parents_and_nodes(network)
    network_children: Dict[str, List[str]] = {}
    for parent, child in network:
        network_children.setdefault(parent, []).append(child)

    pairs: Set[Tuple[str, str]] = set()
    for departure in nodes:
        for return_variable in nodes - {departure}:
            if not _path_exists(network_children, departure, return_variable):
                continue
            all_paths = _generate_paths(
                vignette.children, departure, return_variable
            )
            if any(not frozenset(path).issubset(network) for path in all_paths):
                pairs.add((departure, return_variable))
    return pairs


def _is_causal_network(
    vignette: Any,
    network: Network,
    cause_variables: List[str],
    effect_variable: str,
    productive: bool,
) -> Optional[Dict[str, Any]]:
    parents, nodes = _network_parents_and_nodes(network)
    contrasts_by_variable: Dict[str, List[int]] = {}
    for variable in nodes:
        # A contrast may equal the actual value. The effect is restricted
        # separately below to require a distinct contrast.
        contrasts_by_variable[variable] = list(vignette.ranges[variable])

    # Iterate over all combinations of contrasts for the network variables
    for contrast_values in itertools.product(
        *(contrasts_by_variable[variable] for variable in nodes)
    ):
        contrasts = dict(zip(nodes, contrast_values))
        if contrasts[effect_variable] == vignette.values_in_example[effect_variable]:
            continue

        # Check local dependence for all non-cause variables in the network
        valid = True
        for variable in nodes - set(cause_variables):
            if not _local_dependence(
                vignette, variable, parents.get(variable, set()), contrasts
            ):
                valid = False
                break
        if not valid:
            continue

        # PRODUCTIVE NETWORK also requires deviant values along the whole network
        # CAUSAL NETWORK only requires deviant values along the departure-return pairs
        if productive:
            deviant_variables = nodes
        else:
            deviant_variables = {
                variable
                for pair in _departure_return_pairs(
                    vignette, network
                )
                for variable in pair
            }
        if any(
            not _is_more_deviant(
                vignette,
                variable,
                vignette.values_in_example[variable],
                contrasts[variable],
            )
            for variable in deviant_variables
        ):
            continue

        return {
            "network": network,
            "contrasts": contrasts,
        }
    return None


def _has_proper_causal_subnetwork(
    vignette: Any,
    network: Network,
    cause_variables: List[str],
    effect_variable: str,
) -> bool:
    """Check minimality condition over subnetworks and cause subtuples."""
    for size in range(1, len(cause_variables) + 1):
        for subset in itertools.combinations(cause_variables, size):
            for candidate in _generate_networks_for_cause_tuple(
                vignette.children, list(subset), effect_variable
            ):
                if candidate >= network:
                    continue
                if _is_causal_network(
                    vignette, candidate, list(subset), effect_variable, productive=False
                ):
                    return True
    return False


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
    del query, subset_is_cause

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
            "details": "Gallow theories require `vignette.children` adjacency map.",
        }

    productive = theory_variant == "gallow_productive"
    if theory_variant not in {"gallow", "gallow_productive"}:
        raise ValueError(f"Unknown Gallow variant: {theory_variant}")

    networks = _generate_networks_for_cause_tuple(
        vignette.children, cause_variables, effect_variable
    )
    for network in networks:
        witness = _is_causal_network(
            vignette, network, cause_variables, effect_variable, productive=productive
        )
        if witness is None:
            continue
        if _has_proper_causal_subnetwork(
            vignette, network, cause_variables, effect_variable
        ):
            continue

        if productive and any(
            not _is_more_deviant(
                vignette,
                variable,
                vignette.values_in_example[variable],
                witness["contrasts"][variable],
            )
            for variable in (set(cause_variables) | {effect_variable})
        ):
            continue

        return {
            "terminal": False,
            "result": True,
            "witness": (
                f"Network={sorted(network)}, "
                f"Contrasts={witness['contrasts']}"
            ),
            "details": None,
        }

    return {
        "terminal": False,
        "result": False,
        "witness": None,
        "details": None,
    }


def evaluate_gallow(
    vignette: Any,
    query: Any,
    cause_variables: List[str],
    cause_values: List[int],
    effect_variable: str,
    effect_value: int,
    subset_is_cause: Callable[[List[str], List[int]], bool],
) -> Dict[str, Any]:
    return _evaluate_gallow_variant(
        theory_variant="gallow",
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
