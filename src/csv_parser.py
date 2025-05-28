import pandas as pd
import numpy as np
from main import Vignette
vignettes_csv_path = "../data/vignettes.csv"
variables_csv_path = "../data/variables.csv"
queries_csv_path = "../data/queries.csv"





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
        # default value is 0 if not given
        default_values = {var: value if not pd.isna(value) else 0 for var, value in default_values.items()}

        equations = dict()
        for index, row in variable_data.iterrows():
            if row['structural_equation'] is not np.nan:
                equations[row['variable_name']] = row['structural_equation']

        context = dict()
        context_length = len(vignette_data.context)
        context_vars = vignette_data.variable_order[:context_length]
        for i in range(context_length):
            context[context_vars[i]] = vignette_data.context[i]


        ranges = dict()
        for var in variables:
            ranges[var] = variable_data.loc[variable_data['variable_name'] == var, 'range'].iloc[0] if any(variable_data['variable_name'] == var) else None

        # values_in_example = dict()

        print(f"Vignette ID: {vignette_data.v_id}")
        vignettes[vignette_data.v_id] = Vignette(
                vignette_id=f'v{j}_' + vignette_data.v_id,
                title=vignette_data.title,
                description=vignette_data.description,
                variables=variables,
                context = context,
                ranges=ranges,
                values=values,
                default_values=default_values,
                equations=equations,
                # values_in_example=values_in_example,
            )

    return vignettes



class Query:
    def __init__(self, v_id, cause, effect, intuition, HP01, HP05, HP15, H01, H07, Hall, Baumgartner13, AG24, G21):
        self.v_id = v_id
        self.cause = cause
        self.effect = effect
        self.groundtruth = {
            'intuition': intuition,
            'HP01': HP01,
            'HP05': HP05,
            'HP15': HP15,
            'H01': H01,
            'H07': H07,
            'Hall': Hall,
            'Baumgartner13': Baumgartner13,
            'AG24': AG24,
            'G21': G21
        }

    def __repr__(self):
        return (f"Query(v_id={self.v_id}, cause={self.cause}, effect={self.effect}, "
                f"groundtruth={self.groundtruth})")


# Function to create Query objects from CSV file
def load_queries_csv(csv_path):
    # Load the DataFrame from the CSV file
    df = pd.read_csv(csv_path)

    query_objects = []
    for _, row in df.iterrows():
        # Replace NaN or empty strings with None
        query = Query(
            v_id=row['v_id'] if pd.notna(row['v_id']) and row['v_id'] != '' else None,
            cause=row['cause'] if pd.notna(row['cause']) and row['cause'] != '' else None,
            effect=row['effect'] if pd.notna(row['effect']) and row['effect'] != '' else None,
            intuition=int(row['intuition']) if pd.notna(row['intuition']) and row['intuition'] != '' else None,
            HP01=int(row['HP01']) if pd.notna(row['HP01']) and row['HP01'] != '' else None,
            HP05=int(row['HP05']) if pd.notna(row['HP05']) and row['HP05'] != '' else None,
            HP15=int(row['HP15']) if pd.notna(row['HP15']) and row['HP15'] != '' else None,
            H01=int(row['H01']) if pd.notna(row['H01']) and row['H01'] != '' else None,
            H07=int(row['H07']) if pd.notna(row['H07']) and row['H07'] != '' else None,
            Hall=int(row['Hall']) if pd.notna(row['Hall']) and row['Hall'] != '' else None,
            Baumgartner13=int(row['Baumgartner13']) if pd.notna(row['Baumgartner13']) and row[
                'Baumgartner13'] != '' else None,
            AG24=int(row['AG24']) if pd.notna(row['AG24']) and row['AG24'] != '' else None,
            G21=int(row['G21']) if pd.notna(row['G21']) and row['G21'] != '' else None
        )
        query_objects.append(query)
    return query_objects

if __name__ == '__main__':
    vignettes = load_vignettes_csv(vignettes_csv_path, variables_csv_path)
    # queries = load_queries_csv(queries_csv_path)
    queries = load_queries_csv(queries_csv_path)
print()