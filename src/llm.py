import ollama
import os
import importlib
import re
import sys
from textwrap import dedent
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from src.helpers import add_confusion_matrix_columns, _format_and_print_result
except ModuleNotFoundError:
    from helpers import add_confusion_matrix_columns, _format_and_print_result

from main import (
    OUTPUT_DIR,
    EvaluationResult,
    Query,
    Vignette,
    load_queries,
    load_vignettes,
    queries_path,
    variables_path,
    vignettes_path,
)


queries = load_queries(queries_path)
vignettes = load_vignettes(vignettes_path, variables_path, filter_nl=True)


ALLOWED_PROMPT_MODES = {'zero-shot', 'few-shot', 'cot'}


def _normalize_prompt_mode(prompt_mode: str) -> str:
    mode = (prompt_mode or '').strip().lower()
    if mode not in ALLOWED_PROMPT_MODES:
        allowed = ', '.join(sorted(ALLOWED_PROMPT_MODES))
        raise ValueError(f"Unsupported prompt mode '{prompt_mode}'. Expected one of: {allowed}")
    return mode


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
    if isinstance(result, dict):
        response_text = result.get('response')
    else:
        response_text = getattr(result, 'response', None)

    if response_text is None:
        raise ValueError(f"Unexpected Ollama response for model '{provider_model}': {result}")
    return str(response_text).strip()


def _parse_yes_no_response(raw_response: str, prefer_final_answer: bool = False) -> Optional[bool]:
    """Parse a Yes/No answer from model text with tolerant matching."""
    normalized = raw_response.strip().replace('*', '')
    if not normalized:
        return None

    if prefer_final_answer:
        # Prefer explicit CoT endings like "Final: YES" / "Final: NO".
        final_matches = re.findall(r'^\s*final\s*[:\-]\s*(yes|no)\s*$', normalized, flags=re.IGNORECASE | re.MULTILINE)
        if final_matches:
            return final_matches[-1].lower() == 'yes'

        # Backward-compatible fallback for older "Final Answer: Yes/No" style.
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

    return None


def _print_progress(current: int, total: int, prefix: str = 'Progress', bar_width: int = 28) -> None:
    """Render a single-line terminal progress bar with percentage and count."""
    if total <= 0:
        return

    ratio = max(0.0, min(1.0, current / total))
    filled = int(bar_width * ratio)
    bar = '#' * filled + '-' * (bar_width - filled)
    pct = ratio * 100
    message = f"\r{prefix} [{bar}] {pct:6.2f}% ({current}/{total})"
    sys.stdout.write(message)
    sys.stdout.flush()

    if current >= total:
        sys.stdout.write('\n')
        sys.stdout.flush()


def _last_line_or_sentence(text: str) -> str:
    """Return the last non-empty line, or if single-line, the last sentence."""
    if not text:
        return ''

    value = text.strip()
    if value.startswith('LLM response:'):
        value = value.split('LLM response:', 1)[1].strip()

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines[-1]

    one_line = lines[0] if lines else value
    sentence_parts = [part.strip() for part in re.split(r'(?<=[.!?])\s+', one_line) if part.strip()]
    return sentence_parts[-1] if sentence_parts else one_line


def llm_answer(vignette: Vignette,
               query: Query,
               model: str,
               prompt: str = 'zero-shot',
               gt: str = 'intuition') -> Optional[EvaluationResult]:
    if query.query_text and vignette.vignette_text:
        prompt_mode = _normalize_prompt_mode(prompt)

        if prompt_mode == 'cot':
            model_prompt = dedent(f"""\
                You are a careful causal reasoner.
                Analyze the scenario and question.

                Scenario:
                {vignette.vignette_text}

                Question:
                {query.query_text}

                Think through the facts step by step.

                Important output rule:
                After your reasoning, output exactly one final line:
                Final: YES
                or
                Final: NO
                Use uppercase YES/NO and no extra text on that final line.
            """).strip()
            raw_response = _generate_text(model=model, prompt=model_prompt)
            response_bool = _parse_yes_no_response(raw_response, prefer_final_answer=True)
            if response_bool is None:
                retry_prompt = dedent(f"""\
                    Your previous response did not follow the required output format.
                    Read the scenario and question, then respond with exactly one line and nothing else:
                    Final: YES
                    or
                    Final: NO

                    Scenario:
                    {vignette.vignette_text}

                    Question:
                    {query.query_text}
                """).strip()
                retry_raw_response = _generate_text(model=model, prompt=retry_prompt)
                retry_response_bool = _parse_yes_no_response(retry_raw_response, prefer_final_answer=True)
                raw_response = f"{raw_response}\n\n[Retry]\n{retry_raw_response}"
                response_bool = retry_response_bool
        elif prompt_mode == 'few-shot':
            model_prompt = dedent(f"""\
                You are an expert in causal reasoning. Your task is to determine whether one event is an actual cause of another based on the given vignette.

                Answer with ONLY "Yes" or "No". Your answer must be exactly one word. Do not explain your reasoning.

                Here are some examples:

                Vignette: A barometer drops and then a storm occurs. The barometer reading is a signal of pressure, not a mechanism that produces storms.
                Query: Is the barometer drop a cause of the storm?
                Answer: No

                Vignette: A match is struck near dry wood with oxygen present, and the wood ignites.
                Query: Is striking the match a cause of the wood igniting?
                Answer: Yes

                Vignette: Alice was driving her car on a clear road. Suddenly, a dog ran into the street. Alice swerved to avoid the dog and hit a parked car.
                Query: Is the dog a cause of Alice hitting the parked car?
                Answer: Yes

                Vignette: Mark was late to work because of heavy traffic. His boss was already angry because of a previous meeting.
                Query: Is the heavy traffic a cause of Mark's boss being angry?
                Answer: No

                Now analyze the following:

                Vignette: {vignette.vignette_text}
                Question: {query.query_text}
                Answer:
            """).strip()
            raw_response = _generate_text(model=model, prompt=model_prompt)
            response_bool = _parse_yes_no_response(raw_response)
            if response_bool is None:
                retry_prompt = dedent(f"""\
                    Your previous response did not follow the required output format.
                    Read the scenario and query, then respond with exactly one word and nothing else: Yes or No.

                    Vignette: {vignette.vignette_text}
                    Query: {query.query_text}
                    Answer:
                """).strip()
                retry_raw_response = _generate_text(model=model, prompt=retry_prompt)
                retry_response_bool = _parse_yes_no_response(retry_raw_response)
                raw_response = f"{raw_response}\n\n[Retry]\n{retry_raw_response}"
                response_bool = retry_response_bool
        else:   
            model_prompt = dedent(f"""\
                You are a careful causal reasoner.
                Decide whether the candidate cause is an actual cause of the effect.

                Output format:
                Return exactly one token: YES or NO.
                Do not output anything else.

                Scenario:
                {vignette.vignette_text}

                Question:
                {query.query_text}
            """).strip()
            raw_response = _generate_text(model=model, prompt=model_prompt)
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
        return None

def run_llm_queries(vignettes: Dict[str, Vignette], 
                    queries: List[Query], 
                    gt: str = 'intuition', 
                    skip: Optional[List[str]] = None, 
                    verbose: bool = False, 
                    save: bool = False,
                    result_scope: str = 'all',
                    model: str = 'llama3.2',
                    prompt: str = 'zero-shot') -> pd.DataFrame:

    records: List[Dict[str, Any]] = []
    unclear_query_ids: List[str] = []
    skipped_query_ids: List[str] = []
    skip_set = set(skip or [])
    total_queries = len(queries)
    prompt_mode = _normalize_prompt_mode(prompt)
    run_prefix = f"{model} | Prompt={prompt_mode}"

    if total_queries == 0:
        print('No queries to process.')
        return pd.DataFrame()

    for i, query in enumerate(queries):
        _print_progress(i + 1, total_queries, prefix=run_prefix)
        query_label = query.query_id or f'idx_{i}'

        if query.v_id in skip_set:
            skipped_query_ids.append(query_label)
            continue
        if query.v_id not in vignettes:
            skipped_query_ids.append(query_label)
            continue

        res = llm_answer(
            vignettes[query.v_id],
            query,
            model=model,
            prompt=prompt_mode,
            gt=gt,
        )
        # print("Result:", res.result)
        if res is not None:
            _format_and_print_result(res, vignette_title=vignettes[query.v_id].title, verbose=verbose)
            if res.result is None:
                unclear_id = res.query_id or query_label
                unclear_query_ids.append(unclear_id)
                tail_snippet = _last_line_or_sentence(res.details or '')
                print(f"\nUnclear Yes/No for query_id={unclear_id}: {tail_snippet}")
                # print(f"Unclear raw response for {unclear_id}: {res.details}")
        else:
            skipped_query_ids.append(query_label)
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
        prompt_suffix_map = {
            'zero-shot': '',
            'few-shot': '_few_shot',
            'cot': '_cot',
        }
        suffix = scope_suffix_map.get(result_scope, result_scope)
        prompt_suffix = prompt_suffix_map.get(prompt_mode, f"_{prompt_mode.replace('-', '_')}")
        out_path = OUTPUT_DIR / f'causality_results_{model}{prompt_suffix}_{gt}_{suffix}.csv'
        df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")

    if skipped_query_ids:
        print(f"Skipped query_id(s): {', '.join(skipped_query_ids)}")

    if unclear_query_ids:
        print(f"Unclear Yes/No query_id(s): {', '.join(unclear_query_ids)}")
    else:
        print("No unclear Yes/No results detected.")


    return df


def run_single_llm_query(vignettes: Dict[str, Vignette],
                         queries: List[Query],
                         model: str = 'llama3.2',
                         query_id: Optional[str] = None,
                         prompt: str = 'zero-shot',
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
        prompt=prompt,
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
    # prompt = 'cot'  # Options: 'zero-shot', 'few-shot', 'cot'.
    # smoke_test = run_single_llm_query(
    #     vignettes=vignettes,
    #     queries=queries,
    #     model=model,
    #     query_id=query_id,
    #     prompt=prompt,
    #     verbose=True,
    # )

    # Uncomment for full-batch runs:
    # llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, prompt='zero-shot', model=model)
    # llm_results_cot = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, prompt='cot', model=model)

    for model in ['llama3.2', 'gemma3', 'ministral-3', 'gpt-5.4']:
        for prompt in ['zero-shot', 'few-shot', ]:
            print(f"\nRunning model {model} with prompt={prompt}...")
            llm_results = run_llm_queries(vignettes=vignettes, queries=queries, gt='intuition', verbose=False, save=True, prompt=prompt, model=model)

print()