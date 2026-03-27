import ollama
import os
import importlib
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from main import (
    OUTPUT_DIR,
    EvaluationResult,
    Query,
    Vignette,
    add_confusion_matrix_columns,
    _format_and_print_result,
    load_queries,
    load_vignettes,
    queries_path,
    variables_path,
    vignettes_path,
)


queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path)


def _infer_provider_and_model(model: str) -> Tuple[str, str]:
    """Infer provider from model name using a simple convention.

    If the model string starts with "gpt" (case-insensitive), use OpenAI.
    Everything else is treated as an Ollama model name.
    """
    model_value = (model or "").strip()
    if model_value.lower().startswith('gpt'):
        return 'openai', model_value
    return 'ollama', model_value


def _generate_text(model: str, prompt: str) -> str:
    provider, provider_model = _infer_provider_and_model(model)

    if provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY is not set. Set it before running with an OpenAI model.')

        try:
            openai_module = importlib.import_module('openai')
            OpenAI = getattr(openai_module, 'OpenAI')
        except (ImportError, AttributeError) as exc:
            raise ImportError('openai package is required for OpenAI models. Install with: pip install openai') from exc

        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=provider_model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0,
        )
        return (completion.choices[0].message.content or '').strip()

    result = ollama.generate(model=provider_model, prompt=prompt)
    if not isinstance(result, dict) or 'response' not in result:
        raise ValueError(f"Unexpected Ollama response for model '{provider_model}': {result}")
    return result['response'].strip()


def _parse_yes_no_response(raw_response: str, prefer_final_answer: bool = False) -> Optional[bool]:
    """Parse a Yes/No answer from model text with tolerant matching."""
    normalized = raw_response.strip().replace('*', '')
    if not normalized:
        print('Warning: Empty response from model.')
        return None

    if prefer_final_answer:
        # Prefer explicit CoT endings like "Final Answer: Yes" on any line.
        final_matches = re.findall(r'final\s+answer\s*[:\-]?\s*(yes|no)\b', normalized, flags=re.IGNORECASE)
        if final_matches:
            return final_matches[-1].lower() == 'yes'

    normalized = normalized.replace('.', '')
    lowered = normalized.lower().strip()

    if lowered in {'yes', 'no'}:
        return lowered == 'yes'

    yes_patterns = [
        r'^(answer|final answer)\s*[:\-]?\s*yes\b',
        r'^yes\b',
        r'\byes\b$',
    ]
    no_patterns = [
        r'^(answer|final answer)\s*[:\-]?\s*no\b',
        r'^no\b',
        r'\bno\b$',
    ]

    for pattern in yes_patterns:
        if re.search(pattern, lowered):
            return True
    for pattern in no_patterns:
        if re.search(pattern, lowered):
            return False

    print(f"Warning: No clear Yes/No found in response: {raw_response}")
    return None


def llm_answer(vignette: Vignette,
               query: Query,
               model: str,
               cot: bool = False,
               gt: str = 'intuition') -> Optional[EvaluationResult]:
    if query.query_text and vignette.vignette_text:
        if cot:
            # prompt = f'Think step by step to answer the question about the following scenario. The final words of your answer should be: "ANSWER: YES" or "ANSWER: NO". \n Scenario: {vignettes[query.v_id].vignette_text}\n Question: {query.query_text}'
            prompt = f'You are a careful reasoner. For the following yes/no question about the scenario, first think step by step about the facts and logic involved. Write your reasoning in detail.\n\nScenario:\n{vignette.vignette_text}\n\nQuestion: {query.query_text}\n\nReasoning:\n\n[Your step-by-step reasoning here]\nFinal Answer: Yes or No (only one word, nothing else)'
            raw_response = _generate_text(model=model, prompt=prompt)
            response_bool = _parse_yes_no_response(raw_response, prefer_final_answer=True)
        else:   
            prompt = f'Answer the question about the following scenario with just "Yes" or "No". Do not use any other words. Use only one word. \n Scenario: {vignette.vignette_text}\n Question: {query.query_text}'
            raw_response = _generate_text(model=model, prompt=prompt)
            response_bool = _parse_yes_no_response(raw_response)
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
                    gt_label=gt,
                    groundtruth=query.groundtruth.get(gt),
                    details=f"LLM response: {raw_response}",
                )
    else:
        print(f"Skipping query {query.query_id} for vignette {query.v_id} due to missing text or vignette description.")
        return None

def run_llm_queries(vignettes: Dict[str, Vignette], 
                    queries: List[Query], 
                    gt: str = 'intuition', 
                    skip: Optional[List[str]] = None, 
                    verbose: bool = False, 
                    save: bool = False,
                    result_scope: str = 'all',
                    model: str = 'llama3.2',
                    cot: bool = False) -> pd.DataFrame:

    records: List[Dict[str, Any]] = []
    unclear_query_ids: List[str] = []
    skip_set = set(skip or [])
    for i, query in enumerate(queries):
        if query.v_id in skip_set:
            if verbose:
                print(f"Skipping query {i} for vignette {query.v_id}\n====================\n")
            continue
        if query.v_id not in vignettes:
            if verbose:
                print(f"Warning: vignette {query.v_id} not found. Skipping.")
            continue
        
        print(f"Processing query {i+1}/{len(queries)}: Vignette ID {query.v_id}, Query ID {query.query_id}...") #, end=' ')
        res = llm_answer(
            vignettes[query.v_id],
            query,
            model=model,
            cot=cot,
            gt=gt,
        )
        # print("Result:", res.result)
        if res is not None:
            _format_and_print_result(res, vignette_title=vignettes[query.v_id].title, verbose=verbose)
            if res.result is None and res.query_id is not None:
                unclear_query_ids.append(res.query_id)
        if res is not None:
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

    df = add_confusion_matrix_columns(df)

    if save:
        scope_suffix_map = {
            'all': 'all_queries',
            'paper': 'paper_queries',
            'nonpaper': 'non_paper_queries',
        }
        suffix = scope_suffix_map.get(result_scope, result_scope)
        out_path = OUTPUT_DIR / f'causality_results_{model}{"_cot" if cot else ""}_{gt}_{suffix}.csv'
        df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")

    if unclear_query_ids:
        print(f"Warning: unclear results for query_id(s): {', '.join(unclear_query_ids)}")
    else:
        print("No unclear results detected.")


    return df


def run_single_llm_query(vignettes: Dict[str, Vignette],
                         queries: List[Query],
                         model: str = 'llama3.2',
                         query_id: Optional[str] = None,
                         cot: bool = False,
                         gt: str = 'intuition',
                         verbose: bool = True) -> EvaluationResult:
    """Run one LLM query for quick smoke tests (for example API-key verification)."""
    if not queries:
        raise ValueError('No queries available to evaluate.')

    selected_query: Optional[Query] = None
    if query_id is None:
        selected_query = queries[0]
    else:
        for query in queries:
            if getattr(query, 'query_id', None) == query_id:
                selected_query = query
                break

    if selected_query is None:
        raise ValueError(f'Query with id {query_id} not found.')

    if selected_query.v_id not in vignettes:
        raise ValueError(f'Vignette {selected_query.v_id} for query {selected_query.query_id} not found.')

    if verbose:
        print(f"Running single LLM query: Vignette ID {selected_query.v_id}, Query ID {selected_query.query_id}")

    result = llm_answer(
        vignettes[selected_query.v_id],
        selected_query,
        model=model,
        cot=cot,
        gt=gt,
    )
    if result is None:
        raise ValueError(f'Failed to evaluate query {selected_query.query_id}.')

    _format_and_print_result(
        result,
        vignette_title=vignettes[selected_query.v_id].title if selected_query.v_id in vignettes else None,
        verbose=verbose,
    )
    return result
    

if __name__ == "__main__":  
    # model = 'llama3.2'
    # model = 'gpt-5.4'
    # model = 'gemma3'
    # model = 'ministral-3'
    # query_id = None  # Set to a specific id (e.g., 'rock_bottle_noisy_q111') to target one query.
    # cot = True  # Set to True to enable chain-of-thought prompting for more detailed reasoning.
    # smoke_test = run_single_llm_query(
    #     vignettes=vignettes,
    #     queries=queries,
    #     model=model,
    #     query_id=query_id,
    #     cot=cot,
    #     verbose=True,
    # )

    # Uncomment for full-batch runs:
    # llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, cot=False, model=model)
    # llm_results_cot = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, cot=True, model=model)

    for model in ['llama3.2', 'gemma3', 'ministral-3', 'gpt-5.4']:
        for cot in [False, True]:
            print(f"\nRunning model {model} with CoT={cot}...")
            llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, cot=cot, model=model)

print()