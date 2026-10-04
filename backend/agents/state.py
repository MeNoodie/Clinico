"""State shared by the Clinico appointment workflow."""

from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    
    normalized_query: str
    query: NotRequired[str | None]   # original input before query rewriting
    patient_id: int
    problem: str | None
    department: str | None

    appointment_datetime: str | None
    intent: NotRequired[str]

    safety_status: NotRequired[str]
    safety_reason: NotRequired[str]

    appointment_id: NotRequired[int | None]
    doctor_name: NotRequired[str | None]
    alt_slots: NotRequired[list[str]]
    # preferred_doctor: NotRequired[str | None]

    reschedule_reason: NotRequired[str | None]
    reason: NotRequired[str | None]
    followup_query: NotRequired[str | None]

    booked_datetime: NotRequired[str | None]
    cancel_status: NotRequired[str | None]
    appointment_details: NotRequired[dict | None]
    emergency_message: NotRequired[str | None]
    final_message: NotRequired[str]
    current_step: NotRequired[str]
    error: NotRequired[str | None]


    # --- Guided / multi-turn conversation fields ---
    session_id: NotRequired[str | None]
    conversation_history: NotRequired[list[dict]]  
    awaiting_fields: NotRequired[list[str]]         
    multi_turn: NotRequired[bool]                    
