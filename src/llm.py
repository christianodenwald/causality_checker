import ollama

from main import *

queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)

results = {}
for query in queries:
    prompt = f'Answer the question about the following scenario with just "Yes" or "No". Do not use any other words. \n Scenario: {vignettes[query.v_id].description}\n Question: {query.query_text}'
    result = ollama.generate(model='llama3.2', prompt=prompt)
    response = result['response'].strip().replace('.', '')
    if response == 'Yes':
        response_bool = True
    elif response == 'No':
        response_bool = False
    else:
        response
    results[query.query_id] = response_bool


result = ollama.generate(model='llama3.2', prompt="prompt")
print(result['response'])