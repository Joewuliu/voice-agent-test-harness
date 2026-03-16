from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app

init_db()
client = TestClient(app)


def test_run_handles_missing_dob_edge_case() -> None:
    sc = client.post(
        "/scenarios",
        json={
            "name": "Refill without DOB",
            "transcript": "Hi this is John. I need a refill for lisinopril.",
            "goal": "refill_medication",
            "expected": {},
        },
    ).json()

    resp = client.post("/runs", json={"scenario_ids": [sc["id"]]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["runs"][0]["evaluation"]["pass"] is False
    assert any("DOB" in r for r in body["runs"][0]["evaluation"]["reasons"])


def test_run_passes_book_appointment() -> None:
    sc = client.post(
        "/scenarios",
        json={
            "name": "Book physical",
            "transcript": "This is Jane Doe. I need to book an appointment next week for annual physical.",
            "goal": "book_appointment",
            "expected": {},
        },
    ).json()
    resp = client.post("/runs", json={"scenario_ids": [sc["id"]]})
    assert resp.status_code == 200
    run = resp.json()["runs"][0]
    assert run["tool_called"] == "book_appointment"
