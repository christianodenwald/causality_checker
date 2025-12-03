import ollama
from dataclasses import asdict

from main import *
from main import _format_and_print_result

queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)


def llm_answer(vignette: Vignette, query: Query, model) -> EvaluationResult:
    # results = {}
    # for query in queries:
    if query.query_text and vignettes[query.v_id].vignette_text:
        prompt = f'Answer the question about the following scenario with just "Yes" or "No". Do not use any other words. Use only one word. \n Scenario: {vignettes[query.v_id].vignette_text}\n Question: {query.query_text}'
        result = ollama.generate(model=model, prompt=prompt)
        response = result['response'].strip().replace('.', '')
        if response == 'Yes':
            response_bool = True
        elif response == 'No':
            response_bool = False
        else:
            raise ValueError(f"Unexpected LLM response: {response}")
        # results[query.query_id] = response_bool
        return EvaluationResult(
                    v_id=query.v_id, 
                    query_id=query.query_id, 
                    cause=query.cause, 
                    effect=query.effect, 
                    effect_contrast=query.effect_contrast, 
                    theory=model,
                    result=response_bool, 
                    witness=None, 
                    gt_label= 'intuition', 
                    groundtruth=query.groundtruth.get('intuition'),
                    details=f"LLM response: {response}",
                )
    else:
        print(f"Skipping query {query.query_id} for vignette {query.v_id} due to missing text or vignette description.")

def run_llm_queries(vignettes: Dict[str, Vignette], 
                    queries: List[Query], 
                    gt: str = 'intuition', 
                    skip: Optional[List[str]] = None, 
                    verbose: bool = False, 
                    save: bool = False,
                    result_scope: str = 'all',
                    model: str = 'llama3.2') -> pd.DataFrame:

    records: List[Dict[str, Any]] = []
    skip = set(skip or [])
    for i, query in enumerate(queries):
        if query.v_id in skip:
            if verbose:
                print(f"Skipping query {i} for vignette {query.v_id}\n====================\n")
            continue
        if query.v_id not in vignettes:
            if verbose:
                print(f"Warning: vignette {query.v_id} not found. Skipping.")
            continue

        res = llm_answer(vignettes[query.v_id], query, model=model)
        _format_and_print_result(res, vignette_title=vignettes[query.v_id].title if query.v_id in vignettes else None, verbose=verbose)
        if res is not None and hasattr(res, '__dataclass_fields__'):
            records.append(asdict(res))

    df = pd.DataFrame.from_records(records)

    # Ensure `effect_contrast` is integer dtype with NA support if present
    if 'effect_contrast' in df.columns:
        df['effect_contrast'] = pd.to_numeric(df['effect_contrast'], errors='coerce').astype('Int64')

    # New column: agreement between computed `result` (bool) and `groundtruth` (0/1).
    if 'groundtruth' in df.columns:
        def _agreement(row):
            if pd.isna(row['groundtruth']) or pd.isna(row.get('result')):
                return pd.NA
            return bool(row['result']) == bool(int(row['groundtruth']))
        df['agreement'] = df.apply(_agreement, axis=1)
    else:
        df['agreement'] = pd.NA
    if save:
        scope_suffix_map = {
            'all': 'all_queries',
            'paper': 'paper_queries',
            'nonpaper': 'non_paper_queries',
        }
        suffix = scope_suffix_map.get(result_scope, result_scope)
        out_path = OUTPUT_DIR / f'causality_results_{model}_{gt}_{suffix}.csv'
        df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")


    return df
    

if __name__ == "__main__":  
    model = 'llama3.2'
    llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, model=model)

print()