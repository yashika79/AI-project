from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_venues_endpoint():
    res = client.get("/venues")
    assert res.status_code == 200
    venues = res.json()
    assert isinstance(venues, list)
    assert len(venues) > 0
    assert any("Auditorium" in v["name"] for v in venues)


def test_get_single_venue_endpoint():
    res_list = client.get("/venues")
    first_id = res_list.json()[0]["id"]
    res = client.get(f"/venues/{first_id}")
    assert res.status_code == 200
    assert res.json()["id"] == first_id


def test_schedule_recommend_endpoint():
    now = datetime.now() + timedelta(days=2)
    start_str = now.replace(hour=10, minute=0, second=0).isoformat()
    end_str = now.replace(hour=12, minute=0, second=0).isoformat()

    payload = {
        "event_name": "AI Workshop",
        "attendees": 50,
        "start_time": start_str,
        "end_time": end_str,
        "required_facilities": ["projector", "wifi"],
        "preferred_venue_type": "indoor",
    }
    res = client.post("/schedule/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["feasible"] is True
    assert len(data["recommendations"]) > 0


def test_schedule_search_csp_and_astar():
    now = datetime.now() + timedelta(days=3)
    start_str = now.replace(hour=14, minute=0, second=0).isoformat()
    end_str = now.replace(hour=16, minute=0, second=0).isoformat()

    payload = {
        "events": [
            {
                "id": 1,
                "name": "Machine Learning Lab",
                "attendees": 35,
                "start_time": start_str,
                "end_time": end_str,
                "required_facilities": ["wifi"],
                "preferred_venue_type": "indoor",
                "priority": 1,
            }
        ],
        "algorithm": "csp",
    }
    res = client.post("/schedule/search", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["assignments"]) == 1

    # Now test astar
    payload["algorithm"] = "astar"
    res_astar = client.post("/schedule/search", json=payload)
    assert res_astar.status_code == 200
    assert res_astar.json()["success"] is True


def test_rules_evaluate_endpoint():
    res_list = client.get("/venues")
    first_id = res_list.json()[0]["id"]

    now = datetime.now() + timedelta(days=4)
    start_str = now.replace(hour=10, minute=0, second=0).isoformat()
    end_str = now.replace(hour=12, minute=0, second=0).isoformat()

    payload = {
        "venue_id": first_id,
        "event_name": "Departmental Seminar",
        "attendees": 40,
        "start_time": start_str,
        "end_time": end_str,
        "required_facilities": ["projector"],
        "preferred_venue_type": "indoor",
        "noise_level": "low",
        "requires_catering": False,
        "setup_buffer_minutes": 15,
    }
    res = client.post("/rules/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "is_feasible" in data
    assert "overall_compliance_score" in data
    assert "details" in data


def test_agents_plan_endpoint():
    now = datetime.now() + timedelta(days=5)
    start_str = now.replace(hour=11, minute=0, second=0).isoformat()
    end_str = now.replace(hour=13, minute=0, second=0).isoformat()

    payload = {
        "event_name": "Hackathon Demo Day",
        "attendees": 180,
        "start_time": start_str,
        "end_time": end_str,
        "required_facilities": ["projector", "wifi"],
        "preferred_venue_type": "indoor",
        "priority": 2,
        "noise_level": "medium",
        "requires_catering": False,
        "setup_buffer_minutes": 15,
    }
    res = client.post("/agents/plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_feasible"] is True
    assert len(data["agent_dialogue"]) >= 4
    assert data["assigned_venue_name"] is not None
    assert data["status"] in ("APPROVED", "CONDITIONALLY_APPROVED")


def test_rag_query_endpoint():
    payload = {
        "query": "Can we host high noise live music past 8 PM outdoors?",
        "top_k": 3,
    }
    res = client.post("/rag/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["citations"]) > 0
    assert data["compliance_status"] in ("NON_COMPLIANT", "CONDITIONAL_APPROVAL")
    assert "20:00" in data["answer"]


def test_evaluation_benchmark_endpoint():
    res_scenarios = client.get("/evaluation/scenarios")
    assert res_scenarios.status_code == 200
    scenarios = res_scenarios.json()["scenarios"]
    assert len(scenarios) >= 4

    res = client.post("/evaluation/benchmark", json={"scenario_name": "light"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] == 4
    assert len(data["evaluations"]) == 4
    assert data["recommendation"] != ""


def test_create_and_delete_booking_endpoint():
    # Test creating booking with code string (e.g. b34a)
    now = datetime.now() + timedelta(days=6)
    start_str = now.replace(hour=14, minute=0, second=0).isoformat()
    end_str = now.replace(hour=16, minute=0, second=0).isoformat()

    post_res = client.post(
        "/bookings",
        json={
            "venue_id": "b34a",
            "start_time": start_str,
            "end_time": end_str,
            "status": "confirmed",
        },
    )
    assert post_res.status_code == 200
    booking = post_res.json()
    assert booking["id"] > 0
    assert "Block 34" in booking["venue_name"] or "Venue" in booking["venue_name"]

    # Test deleting booking
    del_res = client.delete(f"/bookings/{booking['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_dashboard_ui_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert "University Event Planner" in res.text
