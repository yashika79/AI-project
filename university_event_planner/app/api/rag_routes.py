from __future__ import annotations

from fastapi import APIRouter
from app.schemas.rag import (
    PolicyCitationOut,
    PolicyQueryRequest,
    PolicyQueryResponse,
)
from app.services.rag import PolicyRAGEngine

router = APIRouter(prefix="/rag", tags=["rag"])
rag_engine = PolicyRAGEngine()


@router.post("/query", response_model=PolicyQueryResponse)
def query_policy_knowledge(payload: PolicyQueryRequest):
    """Grounded policy retrieval and query answering with verified citations."""
    ans = rag_engine.query_policy(query=payload.query, top_k=payload.top_k)

    citations_out = [
        PolicyCitationOut(
            doc_title=c.doc_title,
            section_title=c.section_title,
            clause_id=c.clause_id,
            excerpt=c.excerpt,
            relevance_score=c.relevance_score,
        )
        for c in ans.citations
    ]

    return PolicyQueryResponse(
        query=ans.query,
        answer=ans.answer,
        compliance_status=ans.compliance_status,
        confidence_score=ans.confidence_score,
        citations=citations_out,
        actionable_checklist=ans.actionable_checklist,
    )


@router.get("/documents")
def list_policy_documents():
    """Lists indexed policy documents in the knowledge base."""
    docs = []
    seen = set()
    for chunk in rag_engine.vector_store.chunks:
        if chunk.doc_title not in seen:
            seen.add(chunk.doc_title)
            docs.append({
                "title": chunk.doc_title,
                "sections": list({c.section_title for c in rag_engine.vector_store.chunks if c.doc_title == chunk.doc_title}),
                "clauses_count": sum(1 for c in rag_engine.vector_store.chunks if c.doc_title == chunk.doc_title),
            })
    return {"indexed_documents": docs, "total_chunks": len(rag_engine.vector_store.chunks)}

