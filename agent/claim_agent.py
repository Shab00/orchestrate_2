"""Damage claim verification agent using Gemini Flash vision."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import google.generativeai as genai

from agent.safety import run_safety_gates
from agent.schemas import ClaimVerdict, safe_fallback_verdict
from data.loader import encode_image_base64, filter_evidence_for_object, resolve_image_path
from prompts.system import CLAIM_SYSTEM_PROMPT


def _get_model() -> genai.GenerativeModel:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=CLAIM_SYSTEM_PROMPT,
    )


def _load_images(image_paths_str: str) -> tuple[list[dict[str, str]], bool]:
    """Load images from semicolon-separated paths. Returns (image_list, all_missing)."""
    refs = [p.strip() for p in image_paths_str.split(";") if p.strip()]
    if not refs:
        return [], True
    images: list[dict[str, str]] = []
    for ref in refs:
        full_path = resolve_image_path(ref)
        if not full_path.exists():
            continue
        suffix = Path(ref).suffix.lower().lstrip(".")
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
        b64 = encode_image_base64(full_path)
        images.append({"mime": mime, "data": b64})
    return images, len(images) == 0


def _format_evidence_requirements(requirements: list[dict[str, Any]]) -> str:
    if not requirements:
        return "No specific evidence requirements."
    lines = [f"- [{r.get('requirement_id', '')}] {r.get('minimum_image_evidence', '')}" for r in requirements]
    return "\n".join(lines)


def _format_user_history(history: dict[str, Any]) -> str:
    if not history:
        return "No user history available."
    return (
        f"Past claims: {history.get('past_claim_count', 'N/A')}, "
        f"Accepted: {history.get('accept_claim', 'N/A')}, "
        f"Rejected: {history.get('rejected_claim', 'N/A')}, "
        f"Last 90 days: {history.get('last_90_days_claim_count', 'N/A')}, "
        f"Flags: {history.get('history_flags', 'none')}, "
        f"Summary: {history.get('history_summary', 'none')}"
    )


def _build_parts(
    row: dict[str, Any],
    user_history: dict[str, Any],
    evidence_requirements: list[dict[str, Any]],
    images: list[dict[str, str]],
) -> list[Any]:
    """Build Gemini content parts: text block + image blobs."""
    object_requirements = filter_evidence_for_object(evidence_requirements, row.get("claim_object", ""))
    text = (
        f"Claim object: {row.get('claim_object', '')}\n"
        f"User claim: {row.get('user_claim', '')}\n"
        f"User history: {_format_user_history(user_history)}\n"
        f"Evidence requirements:\n{_format_evidence_requirements(object_requirements)}\n"
        "Analyse the images and return the JSON verdict."
    )
    parts: list[Any] = [text]
    for img in images:
        import base64
        parts.append({"mime_type": img["mime"], "data": base64.b64decode(img["data"])})
    return parts


def _call_vision(model: genai.GenerativeModel, parts: list[Any]) -> str:
    """Make a single Gemini vision call and return the raw text response."""
    response = model.generate_content(parts)
    return response.text or ""


def _retry_call(model: genai.GenerativeModel, parts: list[Any], raw: str) -> str:
    """Retry with an explicit instruction to return only JSON."""
    retry_parts = parts + [
        "Your previous response was not valid JSON. Return ONLY valid JSON, no prose or fences.",
        raw,
    ]
    return _call_vision(model, retry_parts)


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


def _parse_verdict(raw: str) -> ClaimVerdict | None:
    """Attempt to parse a JSON string into ClaimVerdict. Returns None on failure."""
    try:
        cleaned = _strip_json_fences(raw)
        data = json.loads(cleaned)
        return ClaimVerdict.model_validate(data)
    except Exception:
        return None


def process_claim(
    row: dict[str, Any],
    user_history: dict[str, Any],
    evidence_requirements: list[dict[str, Any]],
) -> ClaimVerdict:
    """Process a single damage claim row and return a structured verdict."""
    safety = run_safety_gates(row.get("user_claim", ""))
    if not safety["passed"]:
        return safe_fallback_verdict("Prompt injection detected in user claim.")

    images, all_missing = _load_images(row.get("image_paths", ""))
    if all_missing and row.get("image_paths", "").strip():
        return safe_fallback_verdict("All referenced images are missing.")

    model = _get_model()
    parts = _build_parts(row, user_history, evidence_requirements, images)

    raw = _call_vision(model, parts)
    verdict = _parse_verdict(raw)
    if verdict is not None:
        return verdict

    raw2 = _retry_call(model, parts, raw)
    verdict = _parse_verdict(raw2)
    return verdict if verdict is not None else safe_fallback_verdict("Failed to parse model response.")
