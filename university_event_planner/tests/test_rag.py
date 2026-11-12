from app.services.rag import PolicyRAGEngine, HybridPolicyVectorStore


def test_rag_retrieves_noise_policy():
    engine = PolicyRAGEngine()
    ans = engine.query_policy("Can we play loud concert music outdoors after 8 PM?")
    assert len(ans.citations) > 0
    assert any("POL-VNU-2026" in c.doc_title or "Acoustic" in c.doc_title for c in ans.citations)
    assert ans.compliance_status in ("NON_COMPLIANT", "CONDITIONAL_APPROVAL")
    assert "20:00" in ans.answer


def test_rag_retrieves_security_policy_for_large_crowd():
    engine = PolicyRAGEngine()
    ans = engine.query_policy("How many security officers do we need for 600 attendees?")
    assert len(ans.citations) > 0
    assert any("POL-SEC-2026" in c.doc_title or "Security" in c.doc_title for c in ans.citations)
    assert any("EMT" in item or "Security" in item for item in ans.actionable_checklist)


def test_rag_retrieves_catering_policy():
    engine = PolicyRAGEngine()
    ans = engine.query_policy("Can we serve pizza and drinks in the computer lab?")
    assert len(ans.citations) > 0
    assert ans.compliance_status == "NON_COMPLIANT"
    assert "strictly forbidden" in ans.answer or "prohibited" in ans.answer

