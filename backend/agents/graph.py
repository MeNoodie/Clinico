"""Clinico Appointment Workflow Graph.

Builds and executes the LangGraph state machine coordinating safety,
intent coordination, routing, appointment booking, and response generation.
"""

from __future__ import annotations

import sqlite3
import re
import uuid
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END

from backend.agents.state import AgentState
from backend.agents.agent import (
    invoke_safety_agent,
    invoke_coordinator_agent,
    invoke_router_agent,
    invoke_appointment_agent,
    invoke_reschedule_agent,
    invoke_cancel_agent,
    invoke_followup_agent,
    invoke_response_agent,
)
from backend.session.store import REQUIRED_FIELDS
from backend.tools.get_appointment_details import get_appointment_details

# Timezone
IST = timezone(timedelta(hours=5, minutes=30))
current_date = datetime.now(IST).date().isoformat()

_DATE_OR_TIME_REPLY = re.compile(
    r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b|\b\d{1,2}\s*(?:am|pm|bje|baje)\b|"
    r"\b(?:today|tomorrow|tonight|morning|afternoon|evening|"
    r"january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec|"
    r"kal|parso|aaj|subah|dopahar|shaam|baje|bje|am|pm)\b",
    re.IGNORECASE,
)
_FOLLOWUP_BOOKING_REQUEST = re.compile(
    r"\b(?:help me with|schedule|book|want|need|get|make).{0,30}follow[ -]?up\b|"
    r"\bfollow[ -]?up.{0,20}\b(?:lena|chahiye|book|schedule)\b|"
    r"\b(?:again|come back|return|next visit|see (?:the )?doctor)\b|"
    r"(?:vapas|wapas|dobara|phir se|dikhana)",
    re.IGNORECASE,
)


# =========================================================
# 1. SAFETY NODE & ROUTE
# =========================================================

def safety_node(state: AgentState) -> dict:
    """Classify user query for acute emergencies."""
    query = state.get("query", "")
    result = invoke_safety_agent(query)

    is_emergency = result.status == "EMERGENCY"
    return {
        "safety_status": result.status,
        "safety_reason": result.reason,
        "emergency_message": state.get("emergency_message") if is_emergency else None,
        "error": None,
        "current_step": "safety_done",
    }


def safety_route(
    state: AgentState,
) -> Literal["emergency", "coordinator"]:
    """Route emergencies to immediate medical triage."""
    if state.get("safety_status") == "EMERGENCY":
        return "emergency"
    return "coordinator"


# =========================================================
# 2. EMERGENCY NODE
# =========================================================

def emergency_node(state: AgentState) -> dict:
    """Handle medical emergencies with urgent guidance."""
    message = (
        "Your symptoms may require urgent medical attention. "
        "Please contact local emergency services (108 / 112) or go to "
        "the nearest emergency department immediately. "
        "Do not wait for an appointment."
    )

    history = list(state.get("conversation_history") or [])
    history.append({
        "role": "assistant",
        "content": message,
    })

    return {
        "intent": "EMERGENCY",
        "emergency_message": message,
        "final_message": message,
        "conversation_history": history,
        "current_step": "emergency_done",
        "awaiting_fields": [],
    }


# =========================================================
# 3. COORDINATOR NODE & ROUTE
# =========================================================

def coordinator_node(state: AgentState) -> dict:
    """Extract intent and core medical problems, normalize patient query."""
    query = state.get("query", "").strip()
    history = list(state.get("conversation_history") or [])
    prev_step = state.get("current_step")
    is_completed = (prev_step in ("completed", "emergency_done", "cancel_done") and state.get("appointment_id") is not None)

    last_appointment_id = state.get("appointment_id")
    last_doctor_name = state.get("doctor_name")
    last_department = state.get("department")
    existing_problem = state.get("problem")
    existing_datetime = state.get("appointment_datetime")

    context = ""
    if history:
        context = "\n".join(
            f"{item['role']}: {item['content']}"
            for item in history[-12:]
        )

    if is_completed and last_appointment_id:
        coordinator_query = (
            f"Note: An existing appointment was already booked (ID #{last_appointment_id}, Dr. {last_doctor_name}, Department: {last_department}).\n"
            f"Recent conversation:\n{context}\n\n"
            f"Current patient message: {query}"
        )
    elif context:
        coordinator_query = (
            f"Recent conversation:\n{context}\n\n"
            f"Current patient message: {query}"
        )
    else:
        coordinator_query = query

    result = invoke_coordinator_agent(coordinator_query)
    normalized_query = result.normalized_query
    new_problem = result.problem
    intent = result.intent or state.get("intent") or "BOOK_APPOINTMENT"

    action_intents = {
        "RESCHEDULE_APPOINTMENT",
        "CANCEL_APPOINTMENT",
        "FOLLOWUP_APPOINTMENT",
    }
    workflow_intents = action_intents | {"BOOK_APPOINTMENT"}
    active_intent = state.get("intent")
    prior_awaiting = state.get("awaiting_fields") or []
    pending_intent = state.get("pending_intent") or (
        active_intent if active_intent in workflow_intents else None
    )
    pending_awaiting = (
        prior_awaiting
        if active_intent in workflow_intents
        else state.get("pending_awaiting_fields", [])
    )
    appointment_id_just_provided = False
    awaiting_id = "appointment_id" in (prior_awaiting or pending_awaiting) and not state.get("appointment_id")
    awaiting_datetime = "appointment_datetime" in (prior_awaiting or pending_awaiting)
    followup_request_in_current_message = bool(_FOLLOWUP_BOOKING_REQUEST.search(query))
    followup_booking_requested = (
        followup_request_in_current_message
        or state.get("followup_booking_pending", False)
    )
    if followup_request_in_current_message:
        # Handle an explicit request for another visit as a scheduling flow;
        # the ID is needed to load the prior visit's clinical context.
        intent = "FOLLOWUP_APPOINTMENT"
    if followup_booking_requested and (
        intent == "FOLLOWUP_APPOINTMENT" or active_intent == "FOLLOWUP_APPOINTMENT"
    ):
        intent = "FOLLOWUP_APPOINTMENT"

    # Extract appointment ID if explicitly stated, or reuse last appointment ID
    extracted_appt_id = getattr(result, "appointment_id", None)
    if not extracted_appt_id and awaiting_id:
        # The coordinator can miss a bare reply such as "18"; accept it only
        # when the workflow is explicitly waiting for an appointment ID.
        match = re.fullmatch(
            r"\s*(?:appointment\s*(?:id)?\s*[:#-]?\s*)?#?([0-9]+)\s*",
            query,
            re.IGNORECASE,
        )
        if match:
            extracted_appt_id = int(match.group(1))
            appointment_id_just_provided = True
            intent = pending_intent or intent

    # Preserve an action only when this reply looks like an answer to the field
    # we just asked for. Side questions should be classified and answered on
    # their own instead of being forced through the pending action.
    if (
        pending_intent in workflow_intents
        and (state.get("appointment_id") or pending_intent == "BOOK_APPOINTMENT")
        and awaiting_datetime
        and _DATE_OR_TIME_REPLY.search(query)
        and intent in {"BOOK_APPOINTMENT", "OTHER", pending_intent, "FOLLOWUP_APPOINTMENT"}
    ):
        intent = pending_intent
    appointment_id = extracted_appt_id or state.get("appointment_id") or last_appointment_id

    appointment_details = state.get("appointment_details")
    appointment_lookup_error = None
    if appointment_id and (
        intent in action_intents
        or pending_intent == "FOLLOWUP_APPOINTMENT"
        or active_intent == "FOLLOWUP_APPOINTMENT"
    ):
        try:
            appointment_details = get_appointment_details(
                appointment_id=appointment_id,
                patient_id=state["patient_id"],
            )
            new_problem = new_problem or appointment_details.get("patient_problem")
        except (ValueError, TypeError):
            appointment_lookup_error = (
                "I couldn't find that appointment under your account. "
                "Please check the Appointment ID and try again."
            )
            appointment_id = None

    is_followup_booking = (
        (
            intent == "FOLLOWUP_APPOINTMENT"
            or pending_intent == "FOLLOWUP_APPOINTMENT"
            or active_intent == "FOLLOWUP_APPOINTMENT"
        )
        and followup_booking_requested
        and bool(appointment_details)
    )
    if is_followup_booking:
        # A dated request to return is a new booking, not a status lookup.
        intent = "BOOK_APPOINTMENT"
        appointment_id = None

    # Track reschedule reason and follow-up inquiry in state
    reschedule_reason = (
        getattr(result, "reschedule_reason", None)
        or state.get("reschedule_reason")
        or state.get("reason")
    )
    followup_query = (
        getattr(result, "followup_query", None)
        or (query if intent == "FOLLOWUP_APPOINTMENT" else None)
        or state.get("followup_query")
    )

    booked_datetime = state.get("booked_datetime")

    if is_completed:
        if intent == "BOOK_APPOINTMENT":
            # A previous appointment was completed. A follow-up booking may
            # reuse its clinical context, while a regular booking starts fresh.
            problem = (
                (appointment_details or {}).get("patient_problem") or new_problem
                if is_followup_booking
                else new_problem
            )
            appointment_datetime = None
            appointment_id = None
            department = (appointment_details or {}).get("department_name") if is_followup_booking else None
            doctor_name = (appointment_details or {}).get("doctor_name") if is_followup_booking else None
            alt_slots = []
            booked_datetime = None
        else:
            # Action on the completed appointment (reschedule, cancel, follow-up)
            problem = new_problem or existing_problem
            appointment_datetime = None if intent == "RESCHEDULE_APPOINTMENT" else existing_datetime
            department = (appointment_details or {}).get("department_name") or last_department
            doctor_name = (appointment_details or {}).get("doctor_name") or last_doctor_name
            alt_slots = []
    else:
        # In-progress workflow
        if intent in ("OTHER", "FOLLOWUP_APPOINTMENT"):
            # Preserve in-progress booking state while answering side-question or checking status
            problem = existing_problem
            appointment_datetime = existing_datetime
            department = (appointment_details or {}).get("department_name") or state.get("department")
            doctor_name = (appointment_details or {}).get("doctor_name") or state.get("doctor_name")
            alt_slots = state.get("alt_slots", [])
        elif intent == "RESCHEDULE_APPOINTMENT":
            problem = new_problem or existing_problem
            # The old date is available in appointment_details; reserve this
            # field for the new date requested by the patient.
            appointment_datetime = None if appointment_id_just_provided else existing_datetime
            department = (appointment_details or {}).get("department_name") or state.get("department")
            doctor_name = (appointment_details or {}).get("doctor_name") or state.get("doctor_name")
            alt_slots = state.get("alt_slots", [])
        else:
            # Active booking turn: adopt new problem if provided, else keep existing
            problem = new_problem or existing_problem
            appointment_datetime = existing_datetime
            department = (
                (appointment_details or {}).get("department_name")
                if is_followup_booking
                else state.get("department")
            )
            doctor_name = (
                (appointment_details or {}).get("doctor_name")
                if is_followup_booking
                else state.get("doctor_name")
            )
            alt_slots = state.get("alt_slots", [])

    history.append({"role": "user", "content": query})

    required = REQUIRED_FIELDS.get(intent, [])
    current = {
        "problem": problem,
        "appointment_datetime": appointment_datetime,
        "appointment_id": appointment_id,
        "appointment_details": appointment_details,
        "appointment_id_just_provided": appointment_id_just_provided,
        "appointment_lookup_error": appointment_lookup_error,
        "followup_booking_pending": (
            state.get("followup_booking_pending", False)
            or is_followup_booking
            or (followup_booking_requested and intent == "FOLLOWUP_APPOINTMENT")
        ),
    }

    awaiting = [
        field for field in required if not current.get(field)
    ]

    if intent in workflow_intents and awaiting:
        pending_intent = intent
        pending_awaiting = awaiting
    elif intent in {"OTHER", "FOLLOWUP_APPOINTMENT"} and pending_intent and intent != pending_intent:
        # Handle this question while keeping the unfinished action available
        # for the patient's next reply.
        pending_awaiting = pending_awaiting or ["appointment_datetime"]
    else:
        pending_intent = None
        pending_awaiting = []

    return {
        "intent": intent,
        "problem": problem,
        "reschedule_reason": reschedule_reason,
        "reason": reschedule_reason,
        "followup_query": followup_query,
        "normalized_query": normalized_query,
        "appointment_datetime": appointment_datetime,
        "appointment_id": appointment_id,
        "department": department,
        "doctor_name": doctor_name,
        "alt_slots": alt_slots,
        "booked_datetime": booked_datetime,
        "awaiting_fields": awaiting,
        "pending_intent": pending_intent,
        "pending_awaiting_fields": pending_awaiting,
        "conversation_history": history,
        "current_step": "coordinator_done",
        "error": None,
    }


def coordinator_route(
    state: AgentState,
) -> Literal["router", "reschedule", "cancel", "followup", "response", "ask_missing"]:
    """Direct requests to appropriate action or routing node; general questions to response; otherwise prompt for missing details."""
    intent = state.get("intent")
    awaiting = state.get("awaiting_fields") or []

    if state.get("appointment_lookup_error"):
        return "ask_missing"

    if intent == "BOOK_APPOINTMENT":
        return "router"

    if intent == "RESCHEDULE_APPOINTMENT":
        if "appointment_id" in awaiting or not state.get("appointment_id"):
            return "ask_missing"
        if state.get("appointment_id_just_provided") and not state.get("appointment_datetime"):
            return "ask_missing"
        if "appointment_datetime" in awaiting or not state.get("appointment_datetime"):
            return "router"
        return "reschedule"

    if intent == "CANCEL_APPOINTMENT":
        if "appointment_id" in awaiting or not state.get("appointment_id"):
            return "ask_missing"
        return "cancel"

    if intent == "FOLLOWUP_APPOINTMENT":
        if "appointment_id" in awaiting or not state.get("appointment_id"):
            return "ask_missing"
        return "followup"

    if intent == "OTHER":
        return "response"

    return "ask_missing"

# =========================================================
# 4. ROUTER NODE & ROUTE
# =========================================================

def router_node(state: AgentState) -> dict:
    """Identify medical department and parse preferred appointment date/time."""
    query = state.get("normalized_query") or state.get("query", "")
    history = list(state.get("conversation_history") or [])
    if history:
        recent_context = "\n".join(
            f"{item['role']}: {item['content']}" for item in history[-12:]
        )
        query = (
            f"Recent conversation (use it to resolve a date when the current message gives only a time):\n"
            f"{recent_context}\n\nCurrent patient message: {state.get('query', query)}"
        )
    result = invoke_router_agent(
        query=query,
        problem=state.get("problem"),
        current_date=current_date,
    )

    if result.status == "ERROR":
        return {
            "error": "Unable to determine department or appointment date.",
            "current_step": "router_error",
        }

    department = result.department or state.get("department")
    appointment_datetime = result.appointment_datetime or state.get("appointment_datetime")
    problem = state.get("problem")
    intent = state.get("intent", "BOOK_APPOINTMENT")

    # If the user changed the department during booking (e.g. from Orthopedics to Cardiology), clear the previous knee pain problem
    if intent == "BOOK_APPOINTMENT":
        previous_dept = state.get("department")
        if result.department and previous_dept and result.department.strip().lower() != previous_dept.strip().lower():
            problem = None

    awaiting = []
    if intent == "RESCHEDULE_APPOINTMENT":
        if not state.get("appointment_id"):
            awaiting.append("appointment_id")
        if not appointment_datetime:
            awaiting.append("appointment_datetime")
    else:
        if not problem:
            awaiting.append("problem")
        if not department:
            awaiting.append("department")
        if not appointment_datetime:
            awaiting.append("appointment_datetime")

    return {
        "problem": problem,
        "department": department,
        "appointment_datetime": appointment_datetime,
        "awaiting_fields": awaiting,
        "current_step": "router_done",
        "error": None,
    }


def router_route(
    state: AgentState,
) -> Literal["appointment", "reschedule", "ask_missing"]:
    """Verify all booking or rescheduling prerequisites before calling the action agent."""
    if state.get("error"):
        return "ask_missing"

    intent = state.get("intent")
    if intent == "RESCHEDULE_APPOINTMENT":
        if state.get("appointment_id") and state.get("appointment_datetime"):
            return "reschedule"
        return "ask_missing"

    if not state.get("problem") or not state.get("department") or not state.get("appointment_datetime"):
        return "ask_missing"

    return "appointment"


# =========================================================
# 5. ASK MISSING NODE
# =========================================================

def ask_missing_node(state: AgentState) -> dict:
    """Prompt the patient for any missing required information."""
    awaiting = state.get("awaiting_fields") or []
    intent = state.get("intent")

    if state.get("appointment_lookup_error"):
        question = state["appointment_lookup_error"]
    elif state.get("error"):
        question = f"{state.get('error')} What date and time would you prefer for your appointment?"
    elif intent == "RESCHEDULE_APPOINTMENT":
        if "appointment_id" in awaiting or not state.get("appointment_id"):
            question = "Please provide the Appointment ID you would like to reschedule."
        elif "appointment_datetime" in awaiting or not state.get("appointment_datetime"):
            question = "What new date and time would you prefer for your appointment?"
        else:
            question = "Please provide the missing details to reschedule your appointment."
    elif intent == "CANCEL_APPOINTMENT":
        question = "Please provide the Appointment ID you want to cancel."
    elif intent == "FOLLOWUP_APPOINTMENT":
        question = "Please provide your Appointment ID so I can look up your appointment details."
    elif intent == "BOOK_APPOINTMENT":
        if not state.get("problem"):
            dept = state.get("department")
            if dept:
                question = f"Could you please describe the health concern or symptoms you'd like to consult the {dept} department for?"
            else:
                question = "What symptoms or medical problem would you like help with?"
        elif not state.get("department"):
            question = "Could you clarify the medical department or type of specialist you need?"
        elif not state.get("appointment_datetime"):
            question = "What date and time would you prefer for your appointment?"
        else:
            question = "Could you provide the missing appointment information?"
    else:
        question = "Could you clarify what you would like to do: book, cancel, reschedule, or check an appointment?"

    history = list(state.get("conversation_history") or [])
    history.append({
        "role": "assistant",
        "content": question,
    })

    return {
        "final_message": question,
        "conversation_history": history,
        "current_step": "waiting_for_user",
        "error": None,
    }


# =========================================================
# 6. ACTION NODES: BOOK, RESCHEDULE, CANCEL, FOLLOWUP
# =========================================================

def appointment_node(state: AgentState) -> dict:
    """Execute appointment booking via the dedicated booking tool."""
    try:
        result = invoke_appointment_agent(
            patient_id=state["patient_id"],
            department_name=state["department"],
            appointment_datetime=state["appointment_datetime"],
            patient_problem=state.get("problem") or "",
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "current_step": "appointment_error",
        }

    status = result.get("status")
    if status == "BOOKED":
        return {
            "appointment_id": result.get("appointment_id"),
            "booked_datetime": result.get("appointment_datetime"),
            "doctor_name": result.get("doctor_name"),
            "alt_slots": [],
            "current_step": "appointment_done",
            "error": None,
        }
    elif status == "SUGGEST_SLOT" or result.get("available_slots"):
        return {
            "alt_slots": result.get("available_slots", []),
            "requested_datetime": state.get("appointment_datetime"),
            "appointment_datetime": None,
            "current_step": "appointment_slots_shown",
            "error": None,
        }
    else:
        return {
            "error": result.get("error", "Failed to book appointment"),
            "current_step": "appointment_error",
        }


def reschedule_node(state: AgentState) -> dict:
    """Execute appointment rescheduling via the dedicated reschedule agent."""
    try:
        result = invoke_reschedule_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
            appointment_datetime=state["appointment_datetime"],
            reason=state.get("reschedule_reason") or state.get("reason"),
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "current_step": "reschedule_error",
        }

    status = result.get("status")
    if status == "RESCHEDULED":
        return {
            "appointment_id": result.get("appointment_id"),
            "booked_datetime": result.get("appointment_datetime"),
            "alt_slots": [],
            "current_step": "reschedule_done",
            "error": None,
        }
    elif status == "SUGGEST_SLOT" or result.get("available_slots"):
        return {
            "alt_slots": result.get("available_slots", []),
            "requested_datetime": state.get("appointment_datetime"),
            "appointment_datetime": None,
            "current_step": "appointment_slots_shown",
            "error": None,
        }
    else:
        return {
            "error": result.get("error", "Failed to reschedule appointment"),
            "current_step": "reschedule_error",
        }


def cancel_node(state: AgentState) -> dict:
    """Execute appointment cancellation via the dedicated cancellation agent."""
    try:
        result = invoke_cancel_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "current_step": "cancel_error",
        }

    if result.get("status") == "CANCELLED":
        return {
            "cancel_status": "CANCELLED",
            "current_step": "cancel_done",
            "error": None,
        }
    else:
        return {
            "error": result.get("error", "Failed to cancel appointment"),
            "current_step": "cancel_error",
        }


def followup_node(state: AgentState) -> dict:
    """Retrieve appointment details for patient follow-up inquiry."""
    try:
        result = invoke_followup_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
            user_query=state.get("followup_query") or state.get("query"),
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "current_step": "followup_error",
        }

    if result.get("status") == "ERROR":
        return {
            "error": result.get("error", "Could not retrieve appointment details"),
            "current_step": "followup_error",
        }

    return {
        "appointment_details": result,
        "doctor_name": result.get("doctor_name"),
        "department": result.get("department_name") or result.get("department"),
        "appointment_datetime": result.get("appointment_datetime"),
        "current_step": "followup_done",
        "error": None,
    }


def appointment_route(
    state: AgentState,
) -> Literal["appointment_slots", "response"]:
    """In multi-turn sessions with slot conflicts, show alternative slots and pause."""
    if state.get("current_step") == "appointment_slots_shown":
        return "appointment_slots"
    return "response"


def reschedule_route(
    state: AgentState,
) -> Literal["appointment_slots", "response"]:
    """If requested slot is occupied during reschedule, show alternative slots; otherwise respond."""
    if state.get("current_step") == "appointment_slots_shown":
        return "appointment_slots"
    return "response"


# =========================================================
# 7. APPOINTMENT SLOTS NODE
# =========================================================

def appointment_slots_node(state: AgentState) -> dict:
    """Present slot suggestions and pause for patient choice."""
    facts = {
        "intent": state.get("intent", "BOOK_APPOINTMENT"),
        "current_step": "appointment_slots_shown",
        "status": "SUGGEST_SLOT",
        "patient_query": state.get("normalized_query") or state.get("query", ""),
        "problem": state.get("problem"),
        "reschedule_reason": state.get("reschedule_reason") or state.get("reason"),
        "reason": state.get("reason") or state.get("reschedule_reason"),
        "followup_query": state.get("followup_query"),
        "department": state.get("department"),
        "appointment_id": None,
        "appointment_datetime": state.get("requested_datetime") or state.get("appointment_datetime"),
        "doctor_name": state.get("doctor_name"),
        "alt_slots": state.get("alt_slots", []),
        "cancel_status": None,
        "appointment_details": None,
        "emergency_message": None,
        "awaiting_fields": ["appointment_datetime"],
        "error": None,
    }
    message = invoke_response_agent(**facts)

    history = list(state.get("conversation_history") or [])
    history.append({
        "role": "assistant",
        "content": message,
    })

    return {
        "final_message": message,
        "conversation_history": history,
        "awaiting_fields": ["appointment_datetime"],
        "current_step": "waiting_for_user",
    }


# =========================================================
# 8. RESPONSE NODE
# =========================================================

def response_node(state: AgentState) -> dict:
    """Synthesize natural patient response for completed actions, conflicts, or errors."""
    step = state.get("current_step")
    is_terminal = step in ("appointment_done", "reschedule_done", "cancel_done", "followup_done")

    if step == "appointment_done":
        status = "BOOKED"
    elif step == "reschedule_done":
        status = "RESCHEDULED"
    elif step == "cancel_done":
        status = "CANCELLED"
    elif state.get("error"):
        status = "ERROR"
    else:
        status = "SUCCESS"

    facts = {
        "intent": state.get("intent", "BOOK_APPOINTMENT"),
        "current_step": state.get("current_step"),
        "status": status,
        "patient_query": state.get("normalized_query") or state.get("query", ""),
        "problem": state.get("problem"),
        "reschedule_reason": state.get("reschedule_reason") or state.get("reason"),
        "reason": state.get("reason") or state.get("reschedule_reason"),
        "followup_query": state.get("followup_query"),
        "department": state.get("department"),
        "appointment_id": state.get("appointment_id"),
        "appointment_datetime": state.get("booked_datetime") or state.get("appointment_datetime"),
        "doctor_name": state.get("doctor_name"),
        "alt_slots": state.get("alt_slots", []),
        "cancel_status": state.get("cancel_status"),
        "appointment_details": state.get("appointment_details"),
        "emergency_message": state.get("emergency_message"),
        "awaiting_fields": state.get("awaiting_fields", []),
        "error": state.get("error"),
    }
    if status == "BOOKED":
        # Booking success is already confirmed by the booking tool. Format its
        # returned fields locally to avoid an extra response LLM round trip.
        lines = ["Your appointment has been successfully booked!"]
        if facts["appointment_id"] is not None:
            lines.append(f"Appointment ID: {facts['appointment_id']}")
        if facts["department"]:
            lines.append(f"Department: {facts['department']}")
        if facts["doctor_name"]:
            lines.append(f"Doctor: {facts['doctor_name']}")
        if facts["appointment_datetime"]:
            try:
                booked_at = datetime.fromisoformat(str(facts["appointment_datetime"]))
                formatted_time = booked_at.strftime("%d %B %Y at %I:%M %p")
            except ValueError:
                formatted_time = str(facts["appointment_datetime"])
            lines.append(f"Date and time: {formatted_time}")
        message = "\n".join(lines)
    else:
        message = invoke_response_agent(**facts)

    history = list(state.get("conversation_history") or [])
    history.append({
        "role": "assistant",
        "content": message,
    })

    next_step = "completed" if is_terminal else "waiting_for_user"

    keep_pending_action = (
        is_terminal
        and step == "followup_done"
        and state.get("pending_intent")
        and state.get("pending_intent") != "FOLLOWUP_APPOINTMENT"
    )

    return {
        "final_message": message,
        "conversation_history": history,
        "current_step": next_step,
        "followup_booking_pending": False if is_terminal else state.get("followup_booking_pending", False),
        "pending_intent": state.get("pending_intent") if keep_pending_action else (None if is_terminal else state.get("pending_intent")),
        "pending_awaiting_fields": state.get("pending_awaiting_fields", []) if keep_pending_action else ([] if is_terminal else state.get("pending_awaiting_fields", [])),
    }


# =========================================================
# GRAPH BUILDER
# =========================================================

def build_graph(checkpointer=None):
    """Build and compile the Clinico workflow graph."""
    graph = StateGraph(AgentState)

    # 1. Register Nodes
    graph.add_node("safety", safety_node)
    graph.add_node("emergency", emergency_node)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("ask_missing", ask_missing_node)
    graph.add_node("router", router_node)
    graph.add_node("appointment", appointment_node)
    graph.add_node("reschedule", reschedule_node)
    graph.add_node("cancel", cancel_node)
    graph.add_node("followup", followup_node)
    graph.add_node("appointment_slots", appointment_slots_node)
    graph.add_node("response", response_node)

    # 2. Edges: START -> Safety
    graph.add_edge(START, "safety")

    # 3. Safety routing: Emergency halts, normal continues to coordinator
    graph.add_conditional_edges(
        "safety",
        safety_route,
        {
            "emergency": "emergency",
            "coordinator": "coordinator",
        },
    )
    graph.add_edge("emergency", END)

    # 4. Coordinator routing
    graph.add_conditional_edges(
        "coordinator",
        coordinator_route,
        {
            "router": "router",
            "reschedule": "reschedule",
            "cancel": "cancel",
            "followup": "followup",
            "ask_missing": "ask_missing",
            "response": "response",
        },
    )

    # 5. Router routing
    graph.add_conditional_edges(
        "router",
        router_route,
        {
            "appointment": "appointment",
            "reschedule": "reschedule",
            "ask_missing": "ask_missing",
        },
    )

    # 6. Missing info pauses for user response
    graph.add_edge("ask_missing", END)

    # 7. Action execution routing
    graph.add_conditional_edges(
        "appointment",
        appointment_route,
        {
            "appointment_slots": "appointment_slots",
            "response": "response",
        },
    )
    graph.add_conditional_edges(
        "reschedule",
        reschedule_route,
        {
            "appointment_slots": "appointment_slots",
            "response": "response",
        },
    )
    graph.add_edge("cancel", "response")
    graph.add_edge("followup", "response")

    # 8. Slot suggestions pause; completed responses finish
    graph.add_edge("appointment_slots", END)
    graph.add_edge("response", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# =========================================================
# CHECKPOINTER & COMPILED GRAPH INSTANCE
# =========================================================

DB_PATH = Path(
    os.getenv(
        "LANGGRAPH_CHECKPOINT_DB_PATH",
        (Path(__file__).resolve().parents[2] / "clinico_memory.sqlite").as_posix(),
    )
).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(
    DB_PATH.as_posix(),
    check_same_thread=False,
)

checkpointer = SqliteSaver(conn)
checkpointer.setup()

graph = build_graph(checkpointer=checkpointer)


# =========================================================
# WORKFLOW EXECUTION HELPERS
# =========================================================

def get_thread_state(thread_id: str) -> dict | None:
    """Retrieve saved state for a thread if it exists."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
        if snapshot and snapshot.values:
            return snapshot.values
    except Exception:
        pass
    return None


def run_booking_workflow(
    initial_state: dict,
    thread_id: str | None = None,
) -> dict:
    """Execute workflow for a new thread or single-shot invocation."""
    t_id = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": t_id}}
    return graph.invoke(initial_state, config=config)


def resume_workflow(thread_id: str, message: str) -> dict:
    """Resume an existing thread with a new user message."""
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"query": message}, config=config)


def run_workflow(
    query: str,
    patient_id: int,
    thread_id: str,
) -> dict:
    """Convenience wrapper returning a simplified summary dict."""
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "query": query,
        "patient_id": patient_id,
        "multi_turn": True,
    }

    try:
        result = graph.invoke(input_state, config=config)
        return {
            "thread_id": thread_id,
            "intent": result.get("intent"),
            "status": result.get("current_step"),
            "message": result.get("final_message"),
            "awaiting_fields": result.get("awaiting_fields", []),
            "appointment_id": result.get("appointment_id"),
            "appointment_details": result.get("appointment_details"),
            "available_slots": result.get("alt_slots", []),
            "error": result.get("error"),
        }
    except Exception as exc:
        print(f"[WARN] Workflow error: {exc}")
        return {
            "thread_id": thread_id,
            "status": "ERROR",
            "message": "Something went wrong. Please try again.",
            "error": str(exc),
        }
