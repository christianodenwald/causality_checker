vignettes_json = {
    "vignettes": [
        {
            "id": "v01-ff_disj",
            "title": "FF Disjunctive",
            "description": "A match lit or a lightning strike causes a forest fire.",
            "variables": {
                "ML": {
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
                "FF": "ML or L"
            },
            "notes": "The forest fire occurs if either the match is lit or a lightning strike happens."
        },
        {
            "id": "v02-ff_conj",
            "title": "FF Conjunctive",
            "description": "Both a match lit and a lightning strike are required to cause a forest fire.",
            "variables": {
                "ML": {
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
                "FF": "ML and L"
            },
            "notes": "The forest fire occurs only if both the match is lit and a lightning strike happens."
        },
        {
            "id": "v03-bottle_shatters",
            "title": "Bottle Shatters",
            "description": "A stone thrown causes the bottle to shatter, with additional dependencies.",
            "variables": {
                "ST": {
                    "description": "Suzy throws",
                    "range": [0, 1],
                    "notes": "1 if Suzy throws, 0 if not"
                },
                "BT": {
                    "description": "Billy throws",
                    "range": [0, 1],
                    "notes": "1 if Billy throws, 0 if not"
                },
                "SH": {
                    "description": "Suzy hits",
                    "range": [0, 1],
                    "notes": "1 if Suzy hits, 0 if not"
                },
                "BH": {
                    "description": "Billy hits",
                    "range": [0, 1],
                    "notes": "1 if Billy hits, 0 if not"
                },
                "BS": {
                    "description": "Bottle shatters",
                    "range": [0, 1],
                    "notes": "1 if bottle shatters, 0 if not"
                }
            },
            "structural_equations": {
                "SH": "ST",
                "BH": "BT and not SH",
                "BS": "SH or BH"
            },
            "notes": "The bottle shatters depending on Suzy's throw and Billy's throw dynamics."
        }
    ]
}


settings_json = {
    "initial_values": [
        {
            "setting_id": "s01-ff_disj-1",
            "vignette_id": "v01-ff_disj",
            "initial_values": {
                "ML": 1,
                "L": 1,
                "FF": 1
            }
        },
        {
            "setting_id": "s02-ff_conj-1",
            "vignette_id": "v02-ff_conj",
            "initial_values": {
                "ML": 1,
                "L": 1,
                "FF": 1
            }
        },
        {
            "setting_id": "s03-bottle_shatters-1",
            "vignette_id": "v03-bottle_shatters",
            "initial_values": {
                "ST": 1,
                "BT": 1,
                "SH": 1,
                "BH": 0,
                "BS": 1
            }
        }
    ]
}

queries_json = {
    "queries": [
        {
            "query_id": "q01-ff_disj-ML_FF-1",
            "vignette_id": "v01-ff_disj",
            "setting_id": "s01-ff_disj-1",
            "query": {
                "cause": "ML",
                "effect": "FF",
                "question": "Is the match lit a cause of the forest fire?"
            },
            "results": {}
        },
        {
            "query_id": "q02-ff_conj-ML_FF-1",
            "vignette_id": "v02-ff_conj",
            "setting_id": "s02-ff_conj-1",
            "query": {
                "cause": "ML",
                "effect": "FF",
                "question": "Is the match lit a cause of the forest fire?"
            },
            "results": {}
        },
        {
            "query_id": "q03-bottle_shatters-ST_BS-1",
            "vignette_id": "v03-bottle_shatters",
            "setting_id": "s03-bottle_shatters-1",
            "query": {
                "cause": "ST",
                "effect": "BS",
                "question": "Is the stone throw a cause of the bottle shattering?"
            },
            "results": {}
        },
        {
            "query_id": "q03-bottle_shatters-BT_BS-1",
            "vignette_id": "v03-bottle_shatters",
            "setting_id": "s03-bottle_shatters-1",
            "query": {
                "cause": "BT",
                "effect": "BS",
                "question": "Is the bottle tipped a cause of the bottle shattering?"
            },
            "results": {}
        }

    ]
}




