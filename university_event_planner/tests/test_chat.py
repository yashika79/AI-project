from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_plan_event_hard_constraints_routes_to_csp():
    payload = {"message": "I need a hall for 200 people next Thursday with a projector"}
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "PLAN_EVENT"
    assert "CSP" in data["algorithm_selected"]
    assert "hard" in data["routing_reason"].lower()
    assert data["plan"] is not None
    assert data["plan"]["assigned_venue_name"] is not None
    assert len(data["subagent_dialogue"]) > 0
    # 3D Presentation layer checks
    assert "venueIds" in data
    assert len(data["venueIds"]) > 0
    assert "chips" in data
    assert len(data["chips"]) > 0


def test_chat_plan_event_optimization_routes_to_astar():
    payload = {"message": "Find the optimal venue to minimize capacity waste for 75 attendees with wifi"}
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "PLAN_EVENT"
    assert "ASTAR" in data["algorithm_selected"]
    assert "optimization" in data["routing_reason"].lower()
    assert data["plan"] is not None
    assert "venueIds" in data
    assert len(data["venueIds"]) > 0


def test_chat_policy_question_routes_to_rag():
    payload = {"message": "Can a student club book the main auditorium past 8 PM?"}
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "POLICY_QUERY"
    assert "RAG" in data["algorithm_selected"]
    assert "20:00" in data["reply"] or "POL-VNU-2026" in data["reply"]


def test_chat_accepts_context_from_frontend():
    payload = {
        "message": "Book this venue for our upcoming hackathon",
        "context": {"type": "hackathon", "n": 200, "pref": "in"},
    }
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "chips" in data
