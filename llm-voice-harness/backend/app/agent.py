from __future__ import annotations

import re
from datetime import date, timedelta

from app.models import AgentResult, LLMDecision, ScenarioGoal, ToolCall


PROMPT_TEMPLATE = """You are a healthcare call-center agent.
Given a patient transcript, choose exactly one intent:
- book_appointment(patient, date, reason)
- refill_medication(patient, medication, dob?)
- get_office_hours(location)
Return strict JSON: {{"intent": "...", "arguments": {{...}}}}
Transcript: {transcript}
"""


def _parse_patient(text: str) -> str:
    m = re.search(r"(?:i am|this is|my name is)\s+([A-Za-z ]{2,})", text, flags=re.I)
    return m.group(1).strip() if m else "Unknown Patient"


def _extract_date(text: str) -> str:
    iso = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    if "tomorrow" in text.lower():
        return (date.today() + timedelta(days=1)).isoformat()
    if "next week" in text.lower():
        return (date.today() + timedelta(days=7)).isoformat()
    return ""


def _extract_reason(text: str) -> str:
    m = re.search(r"for ([a-zA-Z ]{3,40})", text, flags=re.I)
    return m.group(1).strip() if m else "general consultation"


def _extract_medication(text: str) -> str:
    meds = ["lisinopril", "metformin", "atorvastatin", "albuterol"]
    t = text.lower()
    for med in meds:
        if med in t:
            return med
    return ""


def _extract_location(text: str) -> str:
    for loc in ["uptown", "downtown", "north clinic", "south clinic"]:
        if loc in text.lower():
            return loc
    return "main office"


def llm_decide(transcript: str) -> AgentResult:
    prompt = PROMPT_TEMPLATE.format(transcript=transcript)
    t = transcript.lower()

    if any(k in t for k in ["office hours", "open", "close", "hours"]):
        decision = LLMDecision(
            intent="get_office_hours",
            arguments={"location": _extract_location(transcript)},
        )
    elif any(k in t for k in ["refill", "medication", "prescription"]):
        args = {
            "patient": _parse_patient(transcript),
            "medication": _extract_medication(transcript),
        }
        if dob := re.search(r"(19\d{2}|20\d{2})-(\d{2})-(\d{2})", transcript):
            args["dob"] = dob.group(0)
        decision = LLMDecision(intent="refill_medication", arguments=args)
    else:
        decision = LLMDecision(
            intent="book_appointment",
            arguments={
                "patient": _parse_patient(transcript),
                "date": _extract_date(transcript),
                "reason": _extract_reason(transcript),
            },
        )

    return AgentResult(
        intent=ScenarioGoal(decision.intent),
        tool_call=ToolCall(tool=ScenarioGoal(decision.intent), arguments=decision.arguments),
        raw_prompt=prompt,
    )
