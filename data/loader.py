"""Utilities for loading CSV data files and encoding images to base64."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pandas as pd


CLAIMS_BASE = Path("claims")


def load_claims(path: Path) -> list[dict[str, Any]]:
    """Load claims CSV and return a list of row dicts."""
    df = pd.read_csv(path, dtype=str).fillna("")
    return df.to_dict(orient="records")


def load_user_history(path: Path) -> dict[str, dict[str, Any]]:
    """Load user_history CSV and return a dict keyed by user_id."""
    df = pd.read_csv(path, dtype=str).fillna("")
    return {row["user_id"]: row for row in df.to_dict(orient="records")}


def load_evidence_requirements(path: Path) -> list[dict[str, Any]]:
    """Load evidence_requirements CSV and return a list of requirement dicts."""
    df = pd.read_csv(path, dtype=str).fillna("")
    return df.to_dict(orient="records")


def encode_image_base64(image_path: Path) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def resolve_image_path(image_ref: str) -> Path:
    """Construct full path for an image reference relative to claims base."""
    return CLAIMS_BASE / image_ref.strip()


def filter_evidence_for_object(
    evidence_requirements: list[dict[str, Any]], claim_object: str
) -> list[dict[str, Any]]:
    """Return evidence requirements applicable to the given claim_object type."""
    return [
        req for req in evidence_requirements
        if req.get("claim_object") in (claim_object, "all")
    ]
