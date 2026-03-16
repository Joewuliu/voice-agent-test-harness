from __future__ import annotations

import json
from datetime import datetime

from fastapi import FastAPI, HTTPException

from app.agent import llm_decide
from app.db import conn, init_db, insert_run, parse_row
from app.evaluator import evaluate
from app.models import (
    BatchRunRequest,
    BatchRunResponse,
    BookAppointmentRequest,
    Metrics,
    OfficeHoursRequest,
    OfficeHoursResponse,
    RunRecord,
    RunStatus,
    Scenario,
    ScenarioCreate,
    ScenarioUpdate,
    StrictRefillMedicationRequest,
    ToolResponse,
)

app = FastAPI(title="LLM Voice Agent Test Harness")


@app.on_event("startup")
def _startup() -> None:
    init_db()


# ------- tool endpoints -------
@app.post("/tools/book_appointment", response_model=ToolResponse)
def book_appointment(payload: BookAppointmentRequest) -> ToolResponse:
    if payload.date < datetime.utcnow().date():
        return ToolResponse(ok=False, error="Appointment date must be in the future")
    return ToolResponse(
        ok=True,
        data={
            "confirmation_id": f"APT-{payload.patient[:2].upper()}-{payload.date.isoformat()}",
            "scheduled": payload.model_dump(),
        },
    )


@app.post("/tools/refill_medication", response_model=ToolResponse)
def refill_medication(payload: StrictRefillMedicationRequest) -> ToolResponse:
    if payload.dob is None:
        return ToolResponse(ok=False, error="Missing DOB for refill verification")
    return ToolResponse(
        ok=True,
        data={"request_id": f"RX-{payload.patient[:2].upper()}-01", "approved": True},
    )


@app.post("/tools/get_office_hours", response_model=OfficeHoursResponse)
def get_office_hours(payload: OfficeHoursRequest) -> OfficeHoursResponse:
    hours = {
        "uptown": "Mon-Fri 8:00-17:00",
        "downtown": "Mon-Fri 9:00-18:00",
        "north clinic": "Mon-Sat 8:00-16:00",
        "south clinic": "Mon-Fri 8:30-17:30",
    }
    return OfficeHoursResponse(
        location=payload.location,
        hours=hours.get(payload.location.lower(), "Mon-Fri 9:00-17:00"),
    )


# ------- scenarios -------
@app.get("/scenarios", response_model=list[Scenario])
def list_scenarios() -> list[Scenario]:
    with conn() as c:
        rows = c.execute("SELECT * FROM scenarios ORDER BY id DESC").fetchall()
    return [
        Scenario(
            id=row["id"],
            name=row["name"],
            transcript=row["transcript"],
            goal=row["goal"],
            expected=json.loads(row["expected"]),
        )
        for row in rows
    ]


@app.post("/scenarios", response_model=Scenario)
def create_scenario(payload: ScenarioCreate) -> Scenario:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO scenarios (name, transcript, goal, expected) VALUES (?, ?, ?, ?)",
            (
                payload.name,
                payload.transcript,
                payload.goal.value,
                json.dumps(payload.expected),
            ),
        )
        sid = int(cur.lastrowid)
    return Scenario(id=sid, **payload.model_dump())


@app.put("/scenarios/{scenario_id}", response_model=Scenario)
def update_scenario(scenario_id: int, payload: ScenarioUpdate) -> Scenario:
    with conn() as c:
        row = c.execute("SELECT * FROM scenarios WHERE id=?", (scenario_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Scenario not found")

        data = {
            "name": payload.name or row["name"],
            "transcript": payload.transcript or row["transcript"],
            "goal": (payload.goal.value if payload.goal else row["goal"]),
            "expected": payload.expected if payload.expected is not None else json.loads(row["expected"]),
        }
        c.execute(
            "UPDATE scenarios SET name=?, transcript=?, goal=?, expected=? WHERE id=?",
            (
                data["name"],
                data["transcript"],
                data["goal"],
                json.dumps(data["expected"]),
                scenario_id,
            ),
        )
    return Scenario(id=scenario_id, **data)


# ------- runs -------
def _execute_tool(tool_name: str, args: dict) -> dict:
    try:
        if tool_name == "book_appointment":
            return book_appointment(BookAppointmentRequest(**args)).model_dump()
        if tool_name == "refill_medication":
            return refill_medication(StrictRefillMedicationRequest(**args)).model_dump()
        if tool_name == "get_office_hours":
            result = get_office_hours(OfficeHoursRequest(**args))
            return {"ok": True, "data": result.model_dump()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"Unknown tool {tool_name}"}


@app.post("/runs", response_model=BatchRunResponse)
def run_batch(payload: BatchRunRequest) -> BatchRunResponse:
    with conn() as c:
        if payload.scenario_ids:
            placeholders = ",".join("?" * len(payload.scenario_ids))
            rows = c.execute(
                f"SELECT * FROM scenarios WHERE id IN ({placeholders})",
                tuple(payload.scenario_ids),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM scenarios").fetchall()

    scenarios = [
        Scenario(
            id=row["id"],
            name=row["name"],
            transcript=row["transcript"],
            goal=row["goal"],
            expected=json.loads(row["expected"]),
        )
        for row in rows
    ]

    run_ids: list[int] = []
    for sc in scenarios:
        decision = llm_decide(sc.transcript)
        tool_name = decision.tool_call.tool.value
        tool_args = decision.tool_call.arguments
        tool_response = _execute_tool(tool_name, tool_args)
        ev = evaluate(sc, tool_name, tool_args, tool_response)
        status = RunStatus.PASS if ev.pass_ else RunStatus.FAIL
        rid = insert_run(
            scenario_id=sc.id,
            status=status.value,
            transcript=sc.transcript,
            tool_called=tool_name,
            tool_args=tool_args,
            tool_response=tool_response,
            evaluation=ev.model_dump(by_alias=True),
        )
        run_ids.append(rid)

    with conn() as c:
        placeholders = ",".join("?" * len(run_ids)) if run_ids else "0"
        run_rows = c.execute(
            f"SELECT * FROM runs WHERE id IN ({placeholders}) ORDER BY id DESC",
            tuple(run_ids),
        ).fetchall()

    runs = [
        RunRecord(
            **{
                **parse_row(row),
                "created_at": datetime.fromisoformat(parse_row(row)["created_at"]),
            }
        )
        for row in run_rows
    ]

    total = len(runs)
    tool_ok = sum(1 for r in runs if r.evaluation.tool_match)
    schema_ok = sum(1 for r in runs if r.evaluation.schema_valid)
    convo_ok = sum(1 for r in runs if r.evaluation.conversation_success)

    metrics = Metrics(
        total_runs=total,
        tool_call_accuracy=(tool_ok / total if total else 0),
        schema_validation_pass_rate=(schema_ok / total if total else 0),
        conversation_success_rate=(convo_ok / total if total else 0),
    )
    return BatchRunResponse(runs=runs, metrics=metrics)


@app.get("/runs", response_model=list[RunRecord])
def list_runs() -> list[RunRecord]:
    with conn() as c:
        rows = c.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    out = []
    for row in rows:
        parsed = parse_row(row)
        parsed["created_at"] = datetime.fromisoformat(parsed["created_at"])
        out.append(RunRecord(**parsed))
    return out
