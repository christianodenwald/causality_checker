import pandas as pd
import numpy as np
from main import Vignette
vignettes_csv_path = "../data_new/vignettes.csv"
variables_csv_path = "../data_new/variables.csv"
queries_csv_path = "../data_new/queries.csv"





def load_vignettes_csv(vignettes_csv_path, variables_csv_path):
    """Loads vignettes from a CSV file."""

    vignettes_df = pd.read_csv(vignettes_csv_path)
    for col in ['variable_order', 'context']:
        vignettes_df[col] = vignettes_df[col].str.split(',')
        # Optional: strip whitespace from each item in the lists
        vignettes_df[col] = vignettes_df[col].apply(lambda x: [item.strip() for item in x] if isinstance(x, list) else x)

    variables_df = pd.read_csv(variables_csv_path)
    variables_df['range'] = variables_df['range'].str.split(',')
    # Optional: strip whitespace from each item in the lists
    variables_df['range'] = variables_df['range'].apply(lambda x: [item.strip() for item in x] if isinstance(x, str) else x)

    vignettes = dict()


    for j, vignette_data in enumerate(vignettes_df.itertuples(index=True)):
        variable_data = variables_df.loc[variables_df.se_id == vignette_data.se_id]

        variables = vignette_data.variable_order

        values = {var: int(vignette_data.context[i]) if i < len(vignette_data.context) else np.nan for i, var in
                  enumerate(variables)}

        # default_values = dict()
        # for var in variables:
        #     # default_values[var] = variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] if any(variable_data['variable_name'] == var) else None
        #     default_values[var] = int(variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0]) if variable_data.loc[variable_data['variable_name'] == var, 'default_values'].iloc[0] else np.nan

        default_values = {
            var: (
                int(variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[0])
                if (
                        not variable_data[variable_data['variable_name'] == var]['default_values'].isna().all()
                        and isinstance(
                    variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[0],
                    (int, float))
                        and variable_data[variable_data['variable_name'] == var]['default_values'].dropna().iloc[
                            0].is_integer()
                )
                else np.nan
            )
            for var in variable_data['variable_name'].unique()
        }

        equations = dict()
        for var in variables:
            equations[var] = variable_data.loc[variable_data['variable_name'] == var, 'structural_equation'].iloc[0] if any(variable_data['variable_name'] == var) else None

        ranges = dict()
        for var in variables:
            ranges[var] = variable_data.loc[variable_data['variable_name'] == var, 'range'].iloc[0] if any(variable_data['variable_name'] == var) else None

        print(f"Vignette ID: {vignette_data.v_id}")
        vignettes[vignette_data.v_id] = Vignette(
                vignette_id=f'v_{j}_' + vignette_data.v_id,
                title=vignette_data.title,
                description=vignette_data.description,
                variables=variables,
                ranges=ranges,
                values=values,
                default_values=default_values,
                values_in_example=default_values,
                equations=equations,
            )

    return vignettes

vignettes = load_vignettes_csv(vignettes_csv_path, variables_csv_path)

print()