import json


def parse_vignettes_queries_settings(vignettes_json, settings_json, queries_json):
    def create_structural_equations(variables, equations):
        """Create a list of structural equation lambdas."""
        structural_equations = [None] * len(variables)
        for var, eq in equations.items():
            var_index = variables.index(var)
            # Replace variable names in the equation with references to current_values indices
            for v in variables:
                eq = eq.replace(v, f'structure["current_values"][{variables.index(v)}]')
            # Use eval to define a lambda function
            structural_equations[var_index] = eval(f"lambda structure: {eq}")
        return structural_equations

    def parse_vignettes(vignettes, settings):
        """Convert vignettes and settings into the desired Python data structure."""
        parsed_vignettes = {}
        for vignette in vignettes:
            id_ = vignette["id"]
            variables = list(vignette["variables"].keys())
            value_ranges = [
                set(range(vignette["variables"][var]["range"][0], vignette["variables"][var]["range"][1] + 1)) for var
                in variables]
            structural_equations = create_structural_equations(variables, vignette["structural_equations"])

            # Find matching initial values in settings
            initial_values = next(setting["initial_values"] for setting in settings if setting["vignette_id"] == id_)
            initial_values_list = [initial_values[var] for var in variables]

            parsed_vignettes[id_] = {
                "variables": variables,
                "initial_values": initial_values_list,
                "current_values": initial_values_list[:],  # Start with a copy of initial values
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

    # Parse vignettes, settings, and queries
    vignettes = parse_vignettes(vignettes_json["vignettes"], settings_json["initial_values"])
    queries = parse_queries(queries_json["queries"])

    return vignettes, queries


# Example usage
vignettes_json = {
    "vignettes": [
        {
            "id": "v01-ff_disj",
            "title": "Disjunctive Forest Fire",
            "description": "A match lit or a lightning strike causes a forest fire.",
            "variables": {
                "M": {
                    "description": "Match lit",
                    "range": [0, 1],
                    "notes": "1 if the match is lit, 0 if not"
                },
                "L": {
                    "description": "Lightning strike",
                    "range": [0, 1],
                    "notes": "1 if lightning strikes, 0 if not"
                },
                "FF": {
                    "description": "Forest fire",
                    "range": [0, 1],
                    "notes": "1 if forest fire occurs, 0 if not"
                }
            },
            "structural_equations": {
                "FF": "M or L"
            },
            "notes": "The forest fire occurs if either the match is lit or a lightning strike happens."
        }
    ]
}

settings_json = {
    "initial_values": [
        {
            "setting_id": "s01-ff_disj-1",
            "vignette_id": "v01-ff_disj",
            "initial_values": {
                "M": 0,
                "L": 0,
                "FF": 0
            }
        }
    ]
}

queries_json = {
    "queries": [
        {
            "query_id": "q01-ff_disj-M_FF-1",
            "vignette_id": "v01-ff_disj",
            "setting_id": "s01-ff_disj-1",
            "query": {
                "cause": "M",
                "effect": "FF",
                "question": "Is the match lit a cause of the forest fire?"
            },
            "results": {
                "HP2005": "Yes",
                "HP2015": "Yes"
            }
        }
    ]
}

# Parse the JSON input
vignettes, queries = parse_vignettes_queries_settings(vignettes_json, settings_json, queries_json)

# Print parsed results
print("Parsed Vignettes:")
print(json.dumps(vignettes, indent=2))

print("\nParsed Queries:")
print(json.dumps(queries, indent=2))
