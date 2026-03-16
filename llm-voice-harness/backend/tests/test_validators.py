from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.main import book_appointment
from app.models import BookAppointmentRequest, StrictRefillMedicationRequest


def test_book_appointment_rejects_past_date() -> None:
    payload = BookAppointmentRequest(
        patient="Alice",
        date=date.today() - timedelta(days=1),
        reason="checkup",
    )
    result = book_appointment(payload)
    assert result.ok is False


def test_refill_validator_rejects_unknown_medication() -> None:
    with pytest.raises(ValidationError):
        StrictRefillMedicationRequest(
            patient="Bob", medication="unknownmed", dob=date(1990, 1, 1)
        )
