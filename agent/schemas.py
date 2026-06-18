from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    justification: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


def coerce_structured_output(raw_content: str) -> AgentResponse:
    payload = json.loads(raw_content)
    return AgentResponse.model_validate(payload)
