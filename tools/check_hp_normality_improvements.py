from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402


# Change this single line when running the script directly without CLI args.
DEFAULT_THEORY = "HP2015"


def _to_bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return None


def run_check(
    theory: str = DEFAULT_THEORY,
    gt_label: str = "intuition",
    skip_vignettes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    vignettes = main.load_vignettes(main.vignettes_path, main.variables_path)
    queries = main.load_queries(main.queries_path)
    skip_set = set(skip_vignettes or [])

    changed: List[Dict[str, Any]] = []
    improvements = 0
    regressions = 0
    neutral = 0
    unknown = 0

    for q in queries:
        if q.v_id not in vignettes:
            continue
        if q.v_id in skip_set:
            continue

        off = main.check_causality(theory, vignettes[q.v_id], q, gt=gt_label, normality=False)
        on = main.check_causality(theory, vignettes[q.v_id], q, gt=gt_label, normality=True)

        if (off.result == on.result) and (off.witness == on.witness):
            continue

        gt = _to_bool_or_none(q.groundtruth.get(gt_label) if hasattr(q, "groundtruth") else None)
        off_result = _to_bool_or_none(off.result)
        on_result = _to_bool_or_none(on.result)

        off_correct = None if gt is None or off_result is None else (off_result == gt)
        on_correct = None if gt is None or on_result is None else (on_result == gt)

        if off_correct is None or on_correct is None:
            verdict = "unknown"
            unknown += 1
        elif on_correct and not off_correct:
            verdict = "improvement"
            improvements += 1
        elif off_correct and not on_correct:
            verdict = "regression"
            regressions += 1
        else:
            verdict = "neutral"
            neutral += 1

        changed.append(
            {
                "query_id": q.query_id,
                "v_id": q.v_id,
                "cause": q.cause,
                "effect": q.effect,
                "groundtruth": gt,
                "result_normality_false": off_result,
                "result_normality_true": on_result,
                "off_correct": off_correct,
                "on_correct": on_correct,
                "verdict": verdict,
                "witness_normality_false": off.witness,
                "witness_normality_true": on.witness,
            }
        )

    return {
        "theory": theory,
        "gt_label": gt_label,
        "skipped_vignettes": sorted(skip_set),
        "total_changed": len(changed),
        "improvements": improvements,
        "regressions": regressions,
        "neutral": neutral,
        "unknown": unknown,
        "rows": changed,
    }


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "query_id",
        "v_id",
        "cause",
        "effect",
        "groundtruth",
        "result_normality_false",
        "result_normality_true",
        "off_correct",
        "on_correct",
        "verdict",
        "witness_normality_false",
        "witness_normality_true",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a theory with/without normality and score changed cases against ground truth."
    )
    parser.add_argument("--theory", default=DEFAULT_THEORY, help="Theory to evaluate (e.g., HP2005, HP2015)")
    parser.add_argument("--gt", default="intuition", help="Ground-truth label to compare against (default: intuition)")
    parser.add_argument(
        "--skip-vignettes",
        default=None,
        help="Comma-separated vignette IDs to skip (default for HP2005: rock_bottle_noisy,rock_bottle_time)",
    )
    parser.add_argument("--csv", default=None, help="Optional output CSV path for per-query changed rows")
    args = parser.parse_args()

    if args.skip_vignettes:
        skip_vignettes = [v.strip() for v in args.skip_vignettes.split(",") if v.strip()]
    elif args.theory == "HP2005":
        skip_vignettes = ["rock_bottle_noisy", "rock_bottle_time"]
    else:
        skip_vignettes = []

    result = run_check(theory=args.theory, gt_label=args.gt, skip_vignettes=skip_vignettes)

    print(f"Theory: {result['theory']}")
    print(f"GT label: {result['gt_label']}")
    if result["skipped_vignettes"]:
        print("Skipped vignettes:", ", ".join(result["skipped_vignettes"]))
    print(f"Changed queries: {result['total_changed']}")
    print(f"Improvements: {result['improvements']}")
    print(f"Regressions: {result['regressions']}")
    print(f"Neutral: {result['neutral']}")
    print(f"Unknown: {result['unknown']}")

    improvement_ids = [row["query_id"] for row in result["rows"] if row.get("verdict") == "improvement"]
    regression_ids = [row["query_id"] for row in result["rows"] if row.get("verdict") == "regression"]

    print("Improvement query IDs:")
    if improvement_ids:
        for qid in improvement_ids:
            print(qid)
    else:
        print("(none)")

    print("Regression query IDs:")
    if regression_ids:
        for qid in regression_ids:
            print(qid)
    else:
        print("(none)")

    if args.csv:
        out_path = Path(args.csv)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        _write_csv(out_path, result["rows"])
        print(f"Wrote changed rows to: {out_path}")


if __name__ == "__main__":
    main_cli()
