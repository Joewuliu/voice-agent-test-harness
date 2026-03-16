from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ScenarioGoal(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    REFILL_MEDICATION = "refill_medication"
    GET_OFFICE_HOURS = "get_office_hours"


class Scenario(BaseModel):
    id: int
    name: str = Field(min_length=3, max_length=120)
    transcript: str = Field(min_length=5)
    goal: ScenarioGoal
    expected: Dict[str, Any] = Field(default_factory=dict)


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    transcript: str = Field(min_length=5)
    goal: ScenarioGoal
    expected: Dict[str, Any] = Field(default_factory=dict)


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    transcript: Optional[str] = None
    goal: Optional[ScenarioGoal] = None
    expected: Optional[Dict[str, Any]] = None


class BookAppointmentRequest(BaseModel):
    patient: str = Field(min_length=2)
    date: date
    reason: str = Field(min_length=3)


class RefillMedicationRequest(BaseModel):
    patient: str = Field(min_length=2)
    medication: str = Field(min_length=2)
    dob: Optional[date] = None


class OfficeHoursRequest(BaseModel):
    location: str = Field(min_length=2)


class ToolCall(BaseModel):
    tool: ScenarioGoal
    arguments: Dict[str, Any]


class AgentResult(BaseModel):
    intent: ScenarioGoal
    tool_call: ToolCall
    raw_prompt: str


class EvalResult(BaseModel):
    pass_: bool = Field(alias="pass")
    reasons: List[str]
    schema_valid: bool
    tool_match: bool
    conversation_success: bool


class RunStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class RunRecord(BaseModel):
    id: int
    scenario_id: int
    status: RunStatus
    transcript: str
    tool_called: str
    tool_args: Dict[str, Any]
    tool_response: Dict[str, Any]
    evaluation: EvalResult
    created_at: datetime


class BatchRunRequest(BaseModel):
    scenario_ids: Optional[List[int]] = None


class Metrics(BaseModel):
    total_runs: int
    tool_call_accuracy: float
    schema_validation_pass_rate: float
    conversation_success_rate: float


class BatchRunResponse(BaseModel):
    runs: List[RunRecord]
    metrics: Metrics


class OfficeHoursResponse(BaseModel):
    location: str
    hours: str


class ToolResponse(BaseModel):
    ok: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


ALLOWED_MEDS = {"lisinopril", "metformin", "atorvastatin", "albuterol"}


def validate_medication(medication: str) -> str:
    m = medication.strip().lower()
    if m not in ALLOWED_MEDS:
        raise ValueError(f"Unsupported medication: {medication}")
    return m


class StrictRefillMedicationRequest(RefillMedicationRequest):
    @field_validator("medication")
    @classmethod
    def _check_med(cls, value: str) -> str:
        return validate_medication(value)


class LLMDecision(BaseModel):
    intent: Literal[
        "book_appointment", "refill_medication", "get_office_hours"
    ]
    arguments: Dict[str, Any]
