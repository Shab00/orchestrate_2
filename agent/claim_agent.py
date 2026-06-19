"""Damage claim verification agent using GPT-4o vision."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from agent.safety import run_safety_gates
from agent.schemas import ClaimVerdict, safe_fallback_verdict
from data.loader import encode_image_base64, filter_evidence_for_object, resolve_image_path
from prompts.system import CLAIM_SYSTEM_PROMPT


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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


def _build_user_content(
    row: dict[str, Any],
    user_history: dict[str, Any],
    evidence_requirements: list[dict[str, Any]],
    images: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Build the user message content list for the vision API call."""
    object_requirements = filter_evidence_for_object(evidence_requirements, row.get("claim_object", ""))
    text_block = {
        "type": "text",
        "text": (
            f"Claim object: {row.get('claim_object', '')}\n"
            f"User claim: {row.get('user_claim', '')}\n"
            f"User history: {_format_user_history(user_history)}\n"
            f"Evidence requirements:\n{_format_evidence_requirements(object_requirements)}\n"
            "Analyse the images and return the JSON verdict."
        ),
    }
    image_blocks = [
        {"type": "image_url", "image_url": {"url": f"data:{img['mime']};base64,{img['data']}"}}
        for img in images
    ]
    return [text_block, *image_blocks]


def _call_vision(client: OpenAI, user_content: list[dict[str, Any]]) -> str:
    """Make a single GPT-4o vision call and return the raw text response."""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1000,
        messages=[
            {"role": "system", "content": CLAIM_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content or ""


def _retry_call(client: OpenAI, user_content: list[dict[str, Any]], raw: str) -> str:
    """Retry the call with an explicit instruction to return only JSON."""
    retry_content = [
        {"type": "text", "text": "Your previous response was not valid JSON. Return ONLY valid JSON, no prose or fences."},
        {"type": "text", "text": raw},
    ]
    return _call_vision(client, user_content + retry_content)


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

    client = _get_client()
    user_content = _build_user_content(row, user_history, evidence_requirements, images)

    raw = _call_vision(client, user_content)
    verdict = _parse_verdict(raw)
    if verdict is not None:
        return verdict

    raw2 = _retry_call(client, user_content, raw)
    verdict = _parse_verdict(raw2)
    return verdict if verdict is not None else safe_fallback_verdict("Failed to parse model response.")
