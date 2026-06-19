from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IssueType = Literal[
    "dent", "scratch", "crack", "glass_shatter", "broken_part", "missing_part",
    "torn_packaging", "crushed_packaging", "water_damage", "stain", "none", "unknown",
]
ClaimStatus = Literal["supported", "contradicted", "not_enough_information"]
Severity = Literal["none", "low", "medium", "high", "unknown"]


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    justification: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ClaimVerdict(BaseModel):
    """Structured verdict for a single damage claim, matching the required output schema."""

    evidence_standard_met: bool
    evidence_standard_met_reason: str
    risk_flags: str
    issue_type: IssueType
    object_part: str
    claim_status: ClaimStatus
    claim_status_justification: str
    supporting_image_ids: str
    valid_image: bool
    severity: Severity

    def to_csv_row(self, row: dict) -> dict:
        """Merge input fields with verdict fields in the required column order."""
        return {
            "user_id": row.get("user_id", ""),
            "image_paths": row.get("image_paths", ""),
            "user_claim": row.get("user_claim", ""),
            "claim_object": row.get("claim_object", ""),
            "evidence_standard_met": self.evidence_standard_met,
            "evidence_standard_met_reason": self.evidence_standard_met_reason,
            "risk_flags": self.risk_flags,
            "issue_type": self.issue_type,
            "object_part": self.object_part,
            "claim_status": self.claim_status,
            "claim_status_justification": self.claim_status_justification,
            "supporting_image_ids": self.supporting_image_ids,
            "valid_image": self.valid_image,
            "severity": self.severity,
        }


def safe_fallback_verdict(reason: str = "Unable to process claim.") -> ClaimVerdict:
    """Return a conservative fallback verdict when processing fails."""
    return ClaimVerdict(
        evidence_standard_met=False,
        evidence_standard_met_reason=reason,
        risk_flags="manual_review_required",
        issue_type="unknown",
        object_part="unknown",
        claim_status="not_enough_information",
        claim_status_justification=reason,
        supporting_image_ids="none",
        valid_image=False,
        severity="unknown",
    )


def coerce_structured_output(raw_content: str) -> AgentResponse:
    payload = json.loads(raw_content)
    return AgentResponse.model_validate(payload)
