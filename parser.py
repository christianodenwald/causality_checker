import json

def parse_vignettes_and_queries(vignettes_json, queries_json):
    def create_structural_equations(variables, equations):
        """Create a list of structural equation lambdas."""
        structural_equations = [None] * len(variables)
        for var, eq in equations.items():
            var_index = variables.index(var)
            # Replace variables in the equations with references to current_values indices
            for v in variables:
                eq = eq.replace(v, f'structure["current_values"][{variables.index(v)}]')
            # Use eval to define a lambda function
            structural_equations[var_index] = eval(f"lambda: {eq}")
        return structural_equations

    def parse_vignettes(vignettes):
        """Convert vignettes into the desired Python data structure."""
        parsed_vignettes = {}
        for vignette in vignettes:
            id_ = vignette["id"]
            variables = vignette["variables"]
            initial_values = vignette["initial_values"]
            current_values = vignette["current_values"]
            value_ranges = [set(range(int(r[0]), int(r[1]) + 1)) for r in vignette["value_ranges"]]
            structural_equations = create_structural_equations(variables, vignette["structural_equations"])

            parsed_vignettes[id_] = {
                "variables": variables,
                "initial_values": initial_values,
                "current_values": current_values,
                "value_ranges": value_ranges,
                "structural_equations": structural_equations,
            }
        return parsed_vignettes

    def parse_queries(queries):
        """Convert queries into a structured format."""
        parsed_queries = []
        for query in queries:
            parsed_queries.append({
                "vignette_id": query["vignette_id"],
                "cause": query["query"]["cause"],
                "effect": query["query"]["effect"],
                "question": query["query"]["question"],
                "results": query["results"]
            })
        return parsed_queries

    # Parse vignettes and queries
    vignettes = parse_vignettes(vignettes_json["vignettes"])
    queries = parse_queries(queries_json["queries"])

    return vignettes, queries


# Example usage
vignettes_json = {
    "vignettes": [
        {
            "id": "01_lf",
            "variables": ["L", "F"],
            "initial_values": [1, 1],
            "current_values": [0, 1],
            "value_ranges": [[0, 1], [0, 1]],
            "structural_equations": {
                "F": "L"
            }
        }
    ]
}

queries_json = {
    "queries": [
        {
            "vignette_id": "01_lf",
            "query": {
                "cause": "L",
                "effect": "F",
                "question": "Is lightning a cause of the fire?"
            },
            "results": {
                "HP2005": True,
                "HP2015": True
            }
        }
    ]
}

# Parse the JSON input
vignettes, queries = parse_vignettes_and_queries(vignettes_json, queries_json)

# Print parsed results
print("Parsed Vignettes:")
print(vignettes)

print("\nParsed Queries:")
print(queries)
