"""Tests for ClaimVerdict schema and loader utilities."""
from __future__ import annotations

import base64
import csv
import json
import os
import tempfile
from pathlib import Path

import pytest

from agent.schemas import ClaimVerdict, safe_fallback_verdict


# ---------------------------------------------------------------------------
# ClaimVerdict model tests
# ---------------------------------------------------------------------------

def _valid_verdict_data() -> dict:
    return {
        "evidence_standard_met": True,
        "evidence_standard_met_reason": "Clear image of damaged bumper.",
        "risk_flags": "none",
        "issue_type": "dent",
        "object_part": "front_bumper",
        "claim_status": "supported",
        "claim_status_justification": "img_1 shows a dent on the front bumper.",
        "supporting_image_ids": "img_1",
        "valid_image": True,
        "severity": "medium",
    }


def test_claim_verdict_valid_instantiation() -> None:
    verdict = ClaimVerdict(**_valid_verdict_data())
    assert verdict.claim_status == "supported"
    assert verdict.issue_type == "dent"
    assert verdict.severity == "medium"


def test_claim_verdict_invalid_claim_status() -> None:
    data = _valid_verdict_data()
    data["claim_status"] = "invalid_status"
    with pytest.raises(Exception):
        ClaimVerdict(**data)


def test_claim_verdict_invalid_issue_type() -> None:
    data = _valid_verdict_data()
    data["issue_type"] = "explosion"
    with pytest.raises(Exception):
        ClaimVerdict(**data)


def test_claim_verdict_invalid_severity() -> None:
    data = _valid_verdict_data()
    data["severity"] = "catastrophic"
    with pytest.raises(Exception):
        ClaimVerdict(**data)


def test_claim_verdict_to_csv_row_column_order() -> None:
    verdict = ClaimVerdict(**_valid_verdict_data())
    row = {"user_id": "u1", "image_paths": "images/img_1.jpg", "user_claim": "My car has a dent.", "claim_object": "car"}
    csv_row = verdict.to_csv_row(row)
    expected_keys = [
        "user_id", "image_paths", "user_claim", "claim_object",
        "evidence_standard_met", "evidence_standard_met_reason",
        "risk_flags", "issue_type", "object_part", "claim_status",
        "claim_status_justification", "supporting_image_ids",
        "valid_image", "severity",
    ]
    assert list(csv_row.keys()) == expected_keys
    assert csv_row["user_id"] == "u1"
    assert csv_row["claim_status"] == "supported"


def test_claim_verdict_to_csv_row_passes_input_fields() -> None:
    verdict = ClaimVerdict(**_valid_verdict_data())
    row = {"user_id": "u42", "image_paths": "images/a.jpg", "user_claim": "Cracked screen.", "claim_object": "laptop"}
    csv_row = verdict.to_csv_row(row)
    assert csv_row["user_id"] == "u42"
    assert csv_row["claim_object"] == "laptop"


def test_safe_fallback_verdict_defaults() -> None:
    verdict = safe_fallback_verdict()
    assert verdict.claim_status == "not_enough_information"
    assert verdict.valid_image is False
    assert verdict.evidence_standard_met is False
    assert verdict.severity == "unknown"
    assert "manual_review_required" in verdict.risk_flags


def test_safe_fallback_verdict_custom_reason() -> None:
    verdict = safe_fallback_verdict("Test reason.")
    assert verdict.evidence_standard_met_reason == "Test reason."
    assert verdict.claim_status_justification == "Test reason."


def test_claim_verdict_model_validate_json() -> None:
    data = _valid_verdict_data()
    verdict = ClaimVerdict.model_validate_json(json.dumps(data))
    assert verdict.claim_status == "supported"


# ---------------------------------------------------------------------------
# Loader utility tests
# ---------------------------------------------------------------------------

def test_filter_evidence_for_object() -> None:
    from data.loader import filter_evidence_for_object

    requirements = [
        {"claim_object": "car", "applies_to": "dent", "minimum_image_evidence": "Show full panel"},
        {"claim_object": "laptop", "applies_to": "crack", "minimum_image_evidence": "Show screen"},
        {"claim_object": "all", "applies_to": "any", "minimum_image_evidence": "Show damage clearly"},
    ]
    car_reqs = filter_evidence_for_object(requirements, "car")
    assert len(car_reqs) == 2
    assert all(r["claim_object"] in ("car", "all") for r in car_reqs)

    laptop_reqs = filter_evidence_for_object(requirements, "laptop")
    assert len(laptop_reqs) == 2


def test_resolve_image_path() -> None:
    from data.loader import resolve_image_path

    path = resolve_image_path("images/test/case_001/img_1.jpg")
    assert str(path) == "claims/images/test/case_001/img_1.jpg"


def test_encode_image_base64_roundtrip() -> None:
    from data.loader import encode_image_base64

    content = b"fake image bytes"
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(content)
        tmp_path = Path(f.name)

    try:
        encoded = encode_image_base64(tmp_path)
        decoded = base64.b64decode(encoded)
        assert decoded == content
    finally:
        tmp_path.unlink()


def test_load_claims_returns_list_of_dicts() -> None:
    from data.loader import load_claims

    csv_content = "user_id,image_paths,user_claim,claim_object\nu1,images/a.jpg,My car has a dent.,car\nu2,images/b.jpg,Screen is cracked.,laptop\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        tmp_path = Path(f.name)

    try:
        rows = load_claims(tmp_path)
        assert len(rows) == 2
        assert rows[0]["user_id"] == "u1"
        assert rows[1]["claim_object"] == "laptop"
    finally:
        tmp_path.unlink()


def test_load_user_history_keyed_by_user_id() -> None:
    from data.loader import load_user_history

    csv_content = "user_id,past_claim_count,history_flags\nu1,3,none\nu2,10,fraud_suspected\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        tmp_path = Path(f.name)

    try:
        history = load_user_history(tmp_path)
        assert "u1" in history
        assert history["u1"]["past_claim_count"] == "3"
        assert history["u2"]["history_flags"] == "fraud_suspected"
    finally:
        tmp_path.unlink()
