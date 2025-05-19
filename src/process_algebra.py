import pandas as pd

vignettes_csv_path = "../data_new/vignettes.csv"
variables_csv_path = "../data_new/variables.csv"


def generate_process_algebra_latex(structural_equations_dict):
    """
    Generate LaTeX code for process algebra from a dictionary of structural equations.
    Each key is a vignette ID, and each value is a list of structural equations.
    """
    latex_code = ""

    # Iterate over each vignette in the dictionary
    for v_id, equations in structural_equations_dict.items():
        if not equations:  # Skip if no equations
            continue

        # Initialize lists to store input neurons and output neuron
        input_neurons = []
        output_neuron = None
        output_expression = None

        # Parse structural equations
        try:
            for eq in equations:
                # Skip if equation is empty or invalid
                if not eq or "=" not in eq:
                    continue
                left, right = eq.replace(" ", "").split("=")
                if right == "1":
                    input_neurons.append(left)
                elif "or" in right.lower():  # Case-insensitive check for 'or'
                    output_neuron = left
                    output_expression = right
        except Exception as e:
            print(f"Error parsing equations for vignette {v_id}: {e}")
            continue

        # Generate process algebra expressions
        process_algebra = []

        # For each input neuron (e.g., A, B)
        for neuron in input_neurons:
            # Signal name is neuron + output_neuron (e.g., A -> C becomes 'ac')
            signal = f"{neuron.lower()}{output_neuron.lower()}" if output_neuron else ""
            # Add expression like A_1 = \overline{ac} . A_1
            process_algebra.append(f"{neuron}_1 = \\overline{{{signal}}} . {neuron}_1")

        # For output neuron (e.g., C)
        if output_neuron and output_expression:
            # Get input signals (e.g., ac, bc)
            signals = [f"{n.lower()}{output_neuron.lower()}" for n in input_neurons]
            # Create C_0 = (ac + bc) . C_1
            process_algebra.append(f"{output_neuron}_0 = ({' + '.join(signals)}) . {output_neuron}_1")
            # Add C_1 = 0
            process_algebra.append(f"{output_neuron}_1 = 0")

        # Generate LaTeX section for this vignette
        if process_algebra:  # Only add section if there are valid expressions
            latex_code += f"\\section{{Vignette {v_id}}}\n"
            latex_code += "\\begin{itemize}\n"
            for expr in process_algebra:
                latex_code += f"    \\item ${expr}$,\n"
            latex_code += "\\end{itemize}\n\n"

    # If no valid LaTeX code was generated, add a placeholder
    if not latex_code:
        latex_code = "% No valid process algebra expressions generated.\n"

    return latex_code


def load_vignettes_variables(vignettes_csv_path, variables_csv_path):
    """
    Load vignettes and variables from CSV files.
    """
    try:
        vignettes_df = pd.read_csv(vignettes_csv_path)
        for col in ['variable_order', 'context']:
            vignettes_df[col] = vignettes_df[col].str.split(',')
            vignettes_df[col] = vignettes_df[col].apply(
                lambda x: [item.strip() for item in x] if isinstance(x, list) else x
            )

        variables_df = pd.read_csv(variables_csv_path)
        variables_df['range'] = variables_df['range'].str.split(',')
        variables_df['range'] = variables_df['range'].apply(
            lambda x: [item.strip() for item in x] if isinstance(x, str) else x
        )

        return variables_df, vignettes_df
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return None, None


def generate_structural_equations(vignettes_df, variables_df):
    """
    Generate a dictionary of structural equations from vignettes and variables dataframes.
    """
    equations_dict = {}

    # Iterate through each vignette
    for _, vignette in vignettes_df.iterrows():
        v_id = vignette['v_id']
        se_id = vignette['se_id']
        variable_order = vignette['variable_order']
        context = vignette['context']

        # Create mapping of variable_order to context values
        context_map = dict(zip(variable_order, context))

        # Filter variables_df for the corresponding se_id
        relevant_vars = variables_df[variables_df['se_id'] == se_id]

        # Generate list of structural equations
        equations = []
        for _, var_row in relevant_vars.iterrows():
            var_name = var_row['variable_name']
            equation = var_row['structural_equation']

            # Check if structural equation is provided and not NaN
            if pd.notna(equation) and equation.strip():
                equation_str = f"{var_name} = {equation}"
            else:
                # Use context value if no structural equation
                if var_name in context_map:
                    equation_str = f"{var_name} = {context_map[var_name]}"
                else:
                    equation_str = f"{var_name} = {var_name}"

            equations.append(equation_str)

        equations_dict[v_id] = equations

    return equations_dict


if __name__ == '__main__':
    # Load data
    variables_df, vignettes_df = load_vignettes_variables(vignettes_csv_path, variables_csv_path)

    if variables_df is None or vignettes_df is None:
        print("Failed to load data. Exiting.")
        exit(1)

    # Generate structural equations dictionary
    structural_equations_dict = generate_structural_equations(vignettes_df, variables_df)

    # Generate LaTeX output
    latex_output = generate_process_algebra_latex(structural_equations_dict)

    # Print LaTeX output
    print(latex_output)

    # Save to a .tex file
    try:
        with open("process_algebra.tex", "w") as f:
            f.write(latex_output)
        print("LaTeX output saved to process_algebra.tex")
    except Exception as e:
        print(f"Error saving LaTeX file: {e}")