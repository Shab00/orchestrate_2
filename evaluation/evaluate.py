"""Evaluate claim agent predictions against sample_claims.csv ground truth."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd

from agent.claim_agent import process_claim
from data.loader import load_evidence_requirements, load_user_history

SAMPLE_CLAIMS_PATH = Path("claims/sample_claims.csv")
USER_HISTORY_PATH = Path("claims/user_history.csv")
EVIDENCE_REQUIREMENTS_PATH = Path("claims/evidence_requirements.csv")
OUTPUT_PATH = Path("evaluation/sample_predictions.csv")

EVAL_FIELDS = [
    "evidence_standard_met",
    "claim_status",
    "issue_type",
    "object_part",
    "severity",
    "valid_image",
]

OUTPUT_COLUMNS = [
    "user_id", "image_paths", "user_claim", "claim_object",
    "evidence_standard_met", "evidence_standard_met_reason",
    "risk_flags", "issue_type", "object_part", "claim_status",
    "claim_status_justification", "supporting_image_ids",
    "valid_image", "severity",
]


def _load_sample_claims() -> list[dict[str, Any]]:
    df = pd.read_csv(SAMPLE_CLAIMS_PATH, dtype=str).fillna("")
    return df.to_dict(orient="records")


def _normalise(value: Any) -> str:
    """Normalise a value for comparison (lowercase string)."""
    return str(value).strip().lower()


def _compare_fields(predicted: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    """Compare predicted vs expected for each eval field."""
    results: dict[str, bool] = {}
    for field in EVAL_FIELDS:
        pred_val = _normalise(predicted.get(field, ""))
        exp_val = _normalise(expected.get(field, ""))
        if field == "evidence_standard_met" or field == "valid_image":
            pred_val = pred_val in ("true", "1", "yes")
            exp_val = exp_val in ("true", "1", "yes")
        results[field] = pred_val == exp_val
    return results


def _print_accuracy_table(field_matches: dict[str, list[bool]]) -> None:
    print(f"\n{'Field':<30} {'Correct':>8} {'Total':>8} {'Accuracy':>10}")
    print("-" * 60)
    for field, matches in field_matches.items():
        correct = sum(matches)
        total = len(matches)
        accuracy = correct / total if total > 0 else 0.0
        print(f"{field:<30} {correct:>8} {total:>8} {accuracy:>9.1%}")
    print()


def run_evaluation() -> None:
    """Run agent on sample claims and print per-field accuracy."""
    samples = _load_sample_claims()
    user_history = load_user_history(USER_HISTORY_PATH)
    evidence_requirements = load_evidence_requirements(EVIDENCE_REQUIREMENTS_PATH)

    field_matches: dict[str, list[bool]] = {f: [] for f in EVAL_FIELDS}
    rows: list[dict[str, Any]] = []

    for i, row in enumerate(samples, start=1):
        print(f"Evaluating sample {i}/{len(samples)} — user_id: {row.get('user_id', '')}")
        history = user_history.get(row.get("user_id", ""), {})
        verdict = process_claim(row, history, evidence_requirements)
        csv_row = verdict.to_csv_row(row)
        rows.append(csv_row)

        comparisons = _compare_fields(csv_row, row)
        for field, match in comparisons.items():
            field_matches[field].append(match)

        time.sleep(1)

    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(OUTPUT_PATH, index=False)
    print(f"\nPredictions saved to {OUTPUT_PATH}")
    _print_accuracy_table(field_matches)


if __name__ == "__main__":
    run_evaluation()
