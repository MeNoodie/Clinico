"""Intent-related constants shared by the workflow and API layer."""

from __future__ import annotations



# Required fields per intent that must be non-None before the workflow runs.
REQUIRED_FIELDS: dict[str, list[str]] = {
    "BOOK_APPOINTMENT":       ["problem", "appointment_datetime"],
    "CANCEL_APPOINTMENT":     ["appointment_id"],
    "RESCHEDULE_APPOINTMENT": ["appointment_id", "appointment_datetime"],
    "FOLLOWUP_APPOINTMENT":   ["appointment_id"],
    "UPLOAD_DOCUMENT":        ["uploaded_file"],
}

# Greeting returned immediately when a button is clicked (no LLM call yet).
INTENT_GREETING: dict[str, str] = {
    "BOOK_APPOINTMENT": (
        "I'll help you book an appointment. "
        "Please describe your health concern and tell me your preferred date and time."
    ),
    "CANCEL_APPOINTMENT": (
        "I'll help you cancel an appointment. "
        "Please provide the appointment id you want to cancel."
    ),
    "RESCHEDULE_APPOINTMENT": (
        "I'll help you reschedule an appointment. "
        "Please provide the appointment id you want to reschedule and the new date and time."
    ),
    "FOLLOWUP_APPOINTMENT": (
        "I'll help you schedule a follow-up. "
    ),
    "UPLOAD_DOCUMENT": (
        "Please upload your document and I will store it for you."
    ),
}

# Per-field clarifying questions asked when a single field is still missing.
FIELD_QUESTIONS: dict[str, str] = {
    "problem":              "What health concern or symptom are you experiencing?",
    "appointment_datetime": "What date and time would you prefer? (e.g. 28 July at 10 AM)",
    "reschedule_datetime":  "What new date and time would you prefer? (e.g. 28 July at 10 AM)",
    "followup_datetime":    "What date and time would you prefer for your follow-up? (e.g. 28 July at 10 AM)",
    "appointment_id":       "Please provide your Appointment ID.",
    "uploaded_file":        "Please upload your medical document.",
}


def get_intent_greeting(intent: str | None, appointment_id: int | None = None) -> str:
    """Generate dynamic greeting for guided workflow, contextualizing appointment_id if present."""
    if appointment_id and intent:
        if intent == "CANCEL_APPOINTMENT":
            return f"I see you'd like to cancel appointment #{appointment_id}. Are you sure you want to proceed?"
        if intent == "RESCHEDULE_APPOINTMENT":
            return f"I see you'd like to reschedule appointment #{appointment_id}. What date and time would you prefer?"
        if intent == "FOLLOWUP_APPOINTMENT":
            return f"I see you'd like to schedule a follow-up for appointment #{appointment_id}. Processing your follow-up request..."
    return INTENT_GREETING.get(intent or "", "How can I help you today?")
