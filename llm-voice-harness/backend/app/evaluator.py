from __future__ import annotations

from app.models import EvalResult, Scenario, ScenarioGoal


def evaluate(
    scenario: Scenario,
    tool_called: str,
    tool_args: dict,
    tool_response: dict,
) -> EvalResult:
    reasons: list[str] = []

    tool_match = tool_called == scenario.goal.value
    if not tool_match:
        reasons.append(f"Expected tool {scenario.goal.value}, got {tool_called}")

    schema_valid = True
    if scenario.goal == ScenarioGoal.BOOK_APPOINTMENT:
        for key in ["patient", "date", "reason"]:
            if not tool_args.get(key):
                schema_valid = False
                reasons.append(f"Missing required field: {key}")
    elif scenario.goal == ScenarioGoal.REFILL_MEDICATION:
        for key in ["patient", "medication"]:
            if not tool_args.get(key):
                schema_valid = False
                reasons.append(f"Missing required field: {key}")
    elif scenario.goal == ScenarioGoal.GET_OFFICE_HOURS:
        if not tool_args.get("location"):
            schema_valid = False
            reasons.append("Missing required field: location")

    success = bool(tool_response.get("ok"))
    if not success:
        reasons.append(tool_response.get("error") or "Tool call failed")

    passed = tool_match and schema_valid and success
    if passed:
        reasons = ["Run passed all checks"]

    return EvalResult(
        **{
            "pass": passed,
            "reasons": reasons,
            "schema_valid": schema_valid,
            "tool_match": tool_match,
            "conversation_success": success,
        }
    )
