from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyQueryRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class PolicyCitationOut(BaseModel):
    doc_title: str
    section_title: str
    clause_id: str
    excerpt: str
    relevance_score: float


class PolicyQueryResponse(BaseModel):
    query: str
    answer: str
    compliance_status: str
    confidence_score: float
    citations: list[PolicyCitationOut]
    actionable_checklist: list[str]

