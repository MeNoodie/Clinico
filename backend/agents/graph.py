"""Clinico Appointment Workflow Graph.

Builds and executes the LangGraph state machine coordinating safety,
intent coordination, routing, appointment booking, and response generation.
"""

from __future__ import annotations

import sqlite3
import uuid
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
    invoke_response_agent,
)
from backend.session.store import REQUIRED_FIELDS

# Timezone
IST = timezone(timedelta(hours=5, minutes=30))
current_date = datetime.now(IST).date().isoformat()


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
            for item in history[-6:]
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

    booked_datetime = state.get("booked_datetime")

    if is_completed:
        # A previous appointment was fully completed. Start a fresh appointment workflow.
        intent = result.intent or "BOOK_APPOINTMENT"
        problem = new_problem  # Never inherit problem from an already completed appointment
        appointment_datetime = None
        appointment_id = None
        department = None
        doctor_name = None
        alt_slots = []
        booked_datetime = None
    else:
        # In-progress workflow
        intent = result.intent or state.get("intent") or "BOOK_APPOINTMENT"
        if intent in ("OTHER", "FOLLOWUP_APPOINTMENT"):
            # Preserve in-progress booking state while answering side-question
            problem = existing_problem
            appointment_datetime = existing_datetime
            appointment_id = last_appointment_id
            department = state.get("department")
            doctor_name = state.get("doctor_name")
            alt_slots = state.get("alt_slots", [])
        else:
            # Active booking turn: adopt new problem if provided, else keep existing
            problem = new_problem or existing_problem
            appointment_datetime = existing_datetime
            appointment_id = last_appointment_id
            department = state.get("department")
            doctor_name = state.get("doctor_name")
            alt_slots = state.get("alt_slots", [])

    history.append({"role": "user", "content": query})

    required = REQUIRED_FIELDS.get(intent, [])
    current = {
        "problem": problem,
        "appointment_datetime": appointment_datetime,
        "appointment_id": appointment_id,
    }

    awaiting = [
        field for field in required if not current.get(field)
    ]

    return {
        "intent": intent,
        "problem": problem,
        "normalized_query": normalized_query,
        "appointment_datetime": appointment_datetime,
        "appointment_id": appointment_id,
        "department": department,
        "doctor_name": doctor_name,
        "alt_slots": alt_slots,
        "booked_datetime": booked_datetime,
        "awaiting_fields": awaiting,
        "conversation_history": history,
        "current_step": "coordinator_done",
        "error": None,
    }


def coordinator_route(
    state: AgentState,
) -> Literal["router", "response", "ask_missing"]:
    """Direct booking requests to routing; general questions to response; otherwise prompt for missing details."""
    intent = state.get("intent")
    if intent == "BOOK_APPOINTMENT":
        return "router"
    if intent in ("OTHER", "FOLLOWUP_APPOINTMENT"):
        return "response"
    return "ask_missing"




# =========================================================
# 4. ROUTER NODE & ROUTE
# =========================================================

def router_node(state: AgentState) -> dict:
    """Identify medical department and parse preferred appointment date/time."""
    query = state.get("normalized_query") or state.get("query", "")
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

    # If the user changed the department (e.g. from Orthopedics to Cardiology), clear the previous knee pain problem
    previous_dept = state.get("department")
    if result.department and previous_dept and result.department.strip().lower() != previous_dept.strip().lower():
        problem = None

    awaiting = []
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
) -> Literal["appointment", "ask_missing"]:
    """Verify all booking prerequisites (problem, department, datetime) before calling the booking agent."""
    if state.get("error"):
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

    if state.get("error"):
        question = f"{state.get('error')} What date and time would you prefer for your appointment?"
    elif state.get("intent") == "BOOK_APPOINTMENT":
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
    elif "appointment_id" in awaiting:
        question = "Please provide your appointment ID."
    elif "appointment_datetime" in awaiting:
        question = "What new date and time would you prefer?"
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
# 6. APPOINTMENT NODE & ROUTE
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


def appointment_route(
    state: AgentState,
) -> Literal["appointment_slots", "response"]:
    """In multi-turn sessions with slot conflicts, show alternative slots and pause."""
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
    """Synthesize natural patient response for completed bookings, conflicts, or errors."""
    is_booked = state.get("current_step") == "appointment_done"
    status = "BOOKED" if is_booked else ("ERROR" if state.get("error") else "SUCCESS")

    facts = {
        "intent": state.get("intent", "BOOK_APPOINTMENT"),
        "current_step": state.get("current_step"),
        "status": status,
        "patient_query": state.get("normalized_query") or state.get("query", ""),
        "problem": state.get("problem"),
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
    message = invoke_response_agent(**facts)

    history = list(state.get("conversation_history") or [])
    history.append({
        "role": "assistant",
        "content": message,
    })

    next_step = "completed" if is_booked else "waiting_for_user"

    return {
        "final_message": message,
        "conversation_history": history,
        "current_step": next_step,
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

    # 4. Coordinator routing: Bookings go to router, other intents/missing details go to ask_missing, general questions to response
    graph.add_conditional_edges(
        "coordinator",
        coordinator_route,
        {
            "router": "router",
            "ask_missing": "ask_missing",
            "response": "response",
        },
    )

    # 5. Router routing: All fields ready -> appointment; missing details -> ask_missing
    graph.add_conditional_edges(
        "router",
        router_route,
        {
            "appointment": "appointment",
            "ask_missing": "ask_missing",
        },
    )

    # 6. Missing info pauses for user response
    graph.add_edge("ask_missing", END)

    # 7. Appointment execution routing
    graph.add_conditional_edges(
        "appointment",
        appointment_route,
        {
            "appointment_slots": "appointment_slots",
            "response": "response",
        },
    )

    # 8. Slot suggestions pause; completed responses finish
    graph.add_edge("appointment_slots", END)
    graph.add_edge("response", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


# =========================================================
# CHECKPOINTER & COMPILED GRAPH INSTANCE
# =========================================================

DB_PATH = Path(__file__).resolve().parents[2] / "clinico_memory.sqlite"

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
