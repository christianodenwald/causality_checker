import ollama

from main import *

queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)

results = {}
for query in queries:
    if query.query_text and vignettes[query.v_id].vignette_text:
        prompt = f'Answer the question about the following scenario with just "Yes" or "No". Do not use any other words. \n Scenario: {vignettes[query.v_id].vignette_text}\n Question: {query.query_text}'
        result = ollama.generate(model='llama3.2', prompt=prompt)
        response = result['response'].strip().replace('.', '')
        if response == 'Yes':
            response_bool = True
        elif response == 'No':
            response_bool = False
        else:
            response
        results[query.query_id] = response_bool
    else:
        print(f"Skipping query {query.query_id} for vignette {query.v_id} due to missing text or vignette description.")

print()