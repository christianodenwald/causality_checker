import json

FILE_PATH = '../data/vignettes.json'

def parse_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def save_json(data, file_path='../data/vignettes_new.json'):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)


import json


def custom_indent(data, level=0, max_indent_level=4, current_indent=2):
    """
    Recursively format JSON with indentation only up to a certain level.

    :param data: The JSON-like data (dict, list, etc.)
    :param level: The current depth level in recursion.
    :param max_indent_level: The maximum level up to which indentation is applied.
    :param current_indent: The number of spaces to use for indentation.
    :return: A formatted JSON-like string.
    """
    if isinstance(data, dict):
        if level >= max_indent_level:
            return json.dumps(data)  # Compact JSON from this level onward
        else:
            return (
                    "{\n"
                    + ",\n".join(
                f"{' ' * (level + 1) * current_indent}{json.dumps(k)}: {custom_indent(v, level + 1, max_indent_level, current_indent)}"
                for k, v in data.items()
            )
                    + f"\n{' ' * level * current_indent}}}"
            )
    elif isinstance(data, list):
        if level >= max_indent_level:
            return json.dumps(data)  # Compact JSON from this level onward
        else:
            return (
                    "[\n"
                    + ",\n".join(
                f"{' ' * (level + 1) * current_indent}{custom_indent(v, level + 1, max_indent_level, current_indent)}"
                for v in data
            )
                    + f"\n{' ' * level * current_indent}]"
            )
    else:
        return json.dumps(data)  # Base case: simple values

def save_indented_json(data, file_path='../data/vignettes_new.json'):
    with open(file_path, "w") as file:
        file.write(data)

def clean_data(data):
    for entry in data:
        if 'notes' in entry:
            entry.pop('notes')
        if 'variables' in entry:
            for var in entry['variables'].values():
                if 'notes' in var:
                    var.pop('notes')
    return data

def move_se(data):
    for entry in data:
        for var, se in entry['structural_equations'].items():
            entry['variables'][var]['structural_equation'] = se
        del entry['structural_equations']
    return data


def add_initial_values(vignette_data, settings_data):
    """
    Adds initial values from settings_data to the respective variables in vignette_data.

    :param vignette_data: List of dictionaries containing vignette information.
    :param settings_data: List of dictionaries containing settings information.
    :return: Updated vignette data with initial values added to variables.
    """
    # Create a mapping from vignette_id to settings for quick lookup
    settings_map = {setting['vignette_id']: setting['initial_values'] for setting in settings_data}

    # Update vignette data
    for vignette in vignette_data:
        vignette_id = vignette['id']
        if vignette_id in settings_map:
            initial_values = settings_map[vignette_id]
            # Add initial values to each variable
            for var_name, var_data in vignette['variables'].items():
                var_data['initial_value'] = initial_values.get(var_name, None)  # Default to None if not found

    return vignette_data

if __name__ == '__main__':
    data = parse_json(FILE_PATH)
    settings_json = parse_json('../data/settings.json')
    new_data = clean_data(data)
    se_data = move_se(new_data)
    settings_data = add_initial_values(se_data, settings_json)
    indented_data = custom_indent(settings_data)
    save_indented_json(indented_data)

print()