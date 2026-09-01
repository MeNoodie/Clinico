from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root is in sys.path when running scripts directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime
import pytest

from backend.tools.appointment_tools import process_booking_request


def test_booking_request():
    booking_request = {
        "patient_id": 1,
        "department_name": "cardiology",
        "appointment_datetime": datetime(2026, 7, 27, 11, 0),
        "patient_problem": "chest pain",
    }

    result = process_booking_request(**booking_request)
    assert result is not None
    assert "status" in result
    assert result["status"] in ("BOOKED", "SUGGEST_SLOT")
    if result["status"] == "BOOKED":
        assert result["appointment_id"] is not None
        assert result["doctor_name"] is not None
    elif result["status"] == "SUGGEST_SLOT":
        assert "available_slots" in result


if __name__ == "__main__":
    pytest.main([__file__])