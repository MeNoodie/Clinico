from __future__ import annotations
from datetime import datetime

from backend.tools.appointment_tools import process_booking_request


def test_booking():
    booking_request = {
        "patient_id": 1,
        "department_name": "cardiology",
        "appointment_datetime": datetime(2026, 7, 27, 11, 0),
        "patient_problem": "chest pain",
    }

    try:
        result = process_booking_request(**booking_request)

        if result["status"] == "BOOKED":
            print("\n✅ Appointment Booked Successfully")
            print("-" * 40)
            print(f"Appointment ID : {result['appointment_id']}")
            print(f"Patient ID     : 1")
            print(f"Doctor ID      : {result['doctor_id']}")
            print(f"Doctor Name    : {result['doctor_name']}")
            print(f"Department     : {result['department']}")
            print(f"Date & Time    : {result['appointment_datetime']}")
            print(f"Problem        : {result['patient_problem']}")
            print(f"Status         : {result['status']}")

        elif result["status"] == "SUGGEST_SLOT":

            print("\n❌ Requested slot unavailable.")
            print("\nAvailable Slots:")

            for slot in result["available_slots"]:
                print(f" • {slot}")

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    test_booking()