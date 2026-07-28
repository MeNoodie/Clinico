"""LangGraph workflow for Clinico — with MemorySaver in-memory checkpointing.

Architecture
------------
The graph supports two entry modes:

1. Natural-language (single-shot or multi-turn via /chat/appointments or /chat/test):
   The Coordinator detects intent + extracts all fields.  If called via the
   session API (multi_turn=True) and fields are still missing, the graph
   pauses at the ``waiting_for_user`` node and saves state via MemorySaver.
   The next /session/reply call resumes with the same thread_id.

2. Guided / button-click (multi_turn=True, intent pre-seeded):
   The Coordinator skips intent detection and only extracts the missing fields
   from the user's latest message.  Same pause/resume mechanic via MemorySaver.

Single-shot calls (/chat/test, /chat/appointments) always use multi_turn=False
so they never hit the waiting_for_user node.
"""

from __future__ import annotations

import uuid

import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, END, StateGraph
from backend.database.db import DATABASE_PATH

from backend.agents.state import AgentState
from backend.agents.agent import (
    invoke_safety_agent,
    invoke_coordinator_agent,
    invoke_coordinator_guided,
    invoke_router_agent,
    invoke_appointment_agent,
    invoke_cancel_agent,
    invoke_reschedule_agent,
    invoke_followup_agent,
    invoke_response_agent,
)
from backend.session.store import REQUIRED_FIELDS, FIELD_QUESTIONS


EMERGENCY_MESSAGE = (
    "⚠️ This sounds like a medical emergency. "
    "Please call the hospital emergency line immediately: 108 (Ambulance) or 112 (Emergency). "
    "Do NOT wait for an appointment — go to the nearest emergency room now."
)


# =============================================================================
# Nodes
# =============================================================================

def coordinator_node(state: AgentState) -> AgentState:
    """Coordinator node — dual-mode: natural-language or guided multi-turn.

    Natural-language mode (``intent`` not in state):
        LLM extracts intent + all booking facts from the raw query.

    Guided mode (``intent`` already set by button-click):
        LLM extracts only the still-missing fields from the user's reply.
        Existing non-None values are never overwritten.

    In both modes, ``awaiting_fields`` is (re-)computed after extraction so the
    ``coordinator_complete_route`` can decide whether to pause or proceed.
    """
    existing_intent: str | None = state.get("intent")

    if existing_intent:
        # ── Guided / multi-turn mode ──────────────────────────────────────────
        result = invoke_coordinator_guided(
            intent=existing_intent,
            user_message=state["query"],
            conversation_history=state.get("conversation_history", []),
            awaiting_fields=state.get("awaiting_fields", []),
        )

        merged_problem    = state.get("problem")    or result.problem
        merged_datetime   = state.get("appointment_datetime") or result.appointment_datetime
        merged_appt_id    = state.get("appointment_id")  or result.appointment_id
        merged_dept       = state.get("department")  or result.department
        merged_doctor     = state.get("preferred_doctor") or result.preferred_doctor

        # Recompute which required fields are still missing
        required = REQUIRED_FIELDS.get(existing_intent, [])
        current  = {
            "problem":              merged_problem,
            "appointment_datetime": merged_datetime,
            "appointment_id":       merged_appt_id,
        }
        awaiting = [f for f in required if not current.get(f)]

        # Append user turn to conversation history
        history = list(state.get("conversation_history") or [])
        history.append({"role": "user", "content": state["query"]})

        return {
            **state,
            "problem":              merged_problem,
            "department":           merged_dept,
            "appointment_datetime": merged_datetime,
            "appointment_id":       merged_appt_id,
            "preferred_doctor":     merged_doctor,
            "awaiting_fields":      awaiting,
            "conversation_history": history,
            "current_step":         "coordinator_done",
        }

    # ── Natural-language mode ─────────────────────────────────────────────────
    result = invoke_coordinator_agent(state["query"])

    intent   = result.intent
    required = REQUIRED_FIELDS.get(intent, [])
    current  = {
        "problem":              result.problem,
        "appointment_datetime": result.appointment_datetime,
        "appointment_id":       state.get("appointment_id"),
    }
    awaiting = [f for f in required if not current.get(f)]

    return {
        **state,
        "intent":               result.intent,
        "problem":              result.problem,
        "department":           result.department,
        "appointment_datetime": result.appointment_datetime,
        "awaiting_fields":      awaiting,
        "current_step":         "coordinator_done",
    }


def waiting_for_user_node(state: AgentState) -> AgentState:
    """Pause point: ask the next clarifying question and save state via checkpointer.

    The graph ends at this node.  The next call with the same thread_id will
    restore the full state and re-run from the coordinator with the new query.
    """
    awaiting = state.get("awaiting_fields") or []
    if awaiting:
        question = FIELD_QUESTIONS.get(awaiting[0], f"Please provide your {awaiting[0]}.")
    else:
        question = "I have everything I need. Processing your request…"

    return {
        **state,
        "final_message": question,
        "current_step":  "waiting_for_user",
    }


def safety_node(state: AgentState) -> AgentState:
    result = invoke_safety_agent(state["query"])
    return {
        **state,
        "safety_status": result.status,
        "safety_reason": result.reason,
        "current_step":  "safety_done",
    }


def router_node(state: AgentState) -> AgentState:
    if state.get("department"):
        return {**state, "current_step": "router_done"}

    result = invoke_router_agent(problem=state.get("problem") or state["query"])
    return {
        **state,
        "department":   result.department,
        "current_step": "router_done",
    }


def appointment_node(state: AgentState) -> AgentState:
    try:
        result = invoke_appointment_agent(
            patient_id=state["patient_id"],
            department_name=state["department"],
            appointment_datetime=state["appointment_datetime"],
            problem=state.get("problem") or state["query"],
        )
    except Exception as exc:
        return {**state, "error": str(exc), "current_step": "appointment_done"}

    if result.get("status") == "BOOKED":
        return {
            **state,
            "appointment_id":  result["appointment_id"],
            "booked_datetime": result["appointment_datetime"],
            "doctor_name":     result.get("doctor_name"),
            "current_step":    "appointment_done",
        }
    return {**state, "alt_slots": result.get("available_slots", []), "current_step": "appointment_done"}


def cancel_node(state: AgentState) -> AgentState:
    try:
        result = invoke_cancel_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
        )
    except Exception as exc:
        return {**state, "error": str(exc), "current_step": "cancel_done"}

    return {**state, "cancel_status": result["status"], "current_step": "cancel_done"}


def reschedule_node(state: AgentState) -> AgentState:
    try:
        result = invoke_reschedule_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
            appointment_datetime=state["appointment_datetime"],
            problem=state.get("problem"),
        )
    except Exception as exc:
        return {**state, "error": str(exc), "current_step": "reschedule_done"}

    if result.get("status") == "RESCHEDULED":
        return {
            **state,
            "appointment_id":  result.get("appointment_id", state.get("appointment_id")),
            "booked_datetime": result.get("new_datetime", result.get("appointment_datetime")),
            "current_step":    "reschedule_done",
        }
    return {**state, "alt_slots": result.get("available_slots", []), "current_step": "reschedule_done"}


def followup_node(state: AgentState) -> AgentState:
    try:
        result = invoke_followup_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
        )
    except Exception as exc:
        return {**state, "error": str(exc), "current_step": "followup_done"}

    if result.get("status") == "SUCCESS":
        return {
            **state,
            "appointment_details": result,
            "department":          result.get("department_name"),
            "doctor_name":         result.get("doctor_name"),
            "appointment_id":      result.get("appointment_id"),
            "booked_datetime":     result.get("appointment_datetime"),
            "problem":             result.get("patient_problem"),
            "error":               None,
            "alt_slots":           [],
            "current_step":        "followup_done",
        }
    return {
        **state,
        "appointment_details": result,
        "error":               result.get("error", "Unknown error"),
        "current_step":        "followup_done",
    }


def emergency_node(state: AgentState) -> AgentState:
    """Administrative emergency escalation — never diagnose."""
    return {
        **state,
        "emergency_message": EMERGENCY_MESSAGE,
        "final_message":     EMERGENCY_MESSAGE,
        "current_step":      "emergency_done",
    }


def response_node(state: AgentState) -> AgentState:
    message = invoke_response_agent(
        department=state.get("department"),
        doctor_name=state.get("doctor_name"),
        appointment_id=state.get("appointment_id"),
        booked_datetime=state.get("booked_datetime"),
        alt_slots=state.get("alt_slots", []),
        error=state.get("error"),
        problem=state.get("problem"),
    )
    return {**state, "final_message": message, "current_step": "completed"}


# =============================================================================
# Conditional Routing
# =============================================================================

def coordinator_complete_route(state: AgentState) -> str:
    """After coordinator: pause for user input or proceed to safety.

    Single-shot calls (multi_turn=False) always proceed — they never pause.
    Session-based calls (multi_turn=True) pause when fields are still missing.
    """
    if state.get("multi_turn") and state.get("awaiting_fields"):
        return "waiting_for_user"
    return "safety"


def safety_route(state: AgentState) -> str:
    if state["safety_status"] == "EMERGENCY":
        return "emergency"
    return "router"


def intent_route(state: AgentState) -> str:
    intent = state["intent"]
    if intent == "BOOK_APPOINTMENT":       return "appointment"
    if intent == "CANCEL_APPOINTMENT":     return "cancel"
    if intent == "RESCHEDULE_APPOINTMENT": return "reschedule"
    if intent == "FOLLOWUP_APPOINTMENT":   return "followup"
    return "response"


# =============================================================================
# Graph
# =============================================================================

# Single shared SQLite checkpointer
_conn = sqlite3.connect(DATABASE_PATH.as_posix(), check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
_checkpointer.setup()


def build_graph():
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("coordinator",      coordinator_node)
    graph.add_node("waiting_for_user", waiting_for_user_node)
    graph.add_node("safety",           safety_node)
    graph.add_node("router",           router_node)
    graph.add_node("appointment",      appointment_node)
    graph.add_node("cancel",           cancel_node)
    graph.add_node("reschedule",       reschedule_node)
    graph.add_node("followup",         followup_node)
    graph.add_node("emergency",        emergency_node)
    graph.add_node("response",         response_node)

    # START → coordinator
    graph.add_edge(START, "coordinator")

    # coordinator → waiting_for_user (pause) OR → safety (proceed)
    graph.add_conditional_edges(
        "coordinator",
        coordinator_complete_route,
        {
            "waiting_for_user": "waiting_for_user",
            "safety":           "safety",
        },
    )

    # waiting_for_user → END (state checkpointed; next call resumes here)
    graph.add_edge("waiting_for_user", END)

    # safety branches: EMERGENCY → emergency, else → router
    graph.add_conditional_edges(
        "safety",
        safety_route,
        {"router": "router", "emergency": "emergency"},
    )

    # router branches by intent
    graph.add_conditional_edges(
        "router",
        intent_route,
        {
            "appointment": "appointment",
            "cancel":      "cancel",
            "reschedule":  "reschedule",
            "followup":    "followup",
            "response":    "response",
        },
    )

    # all action nodes → response → END
    graph.add_edge("appointment", "response")
    graph.add_edge("cancel",      "response")
    graph.add_edge("reschedule",  "response")
    graph.add_edge("followup",    "response")
    graph.add_edge("emergency",   END)
    graph.add_edge("response",    END)

    return graph.compile(checkpointer=_checkpointer)


booking_graph = build_graph()


# =============================================================================
# Public API helpers
# =============================================================================

def run_booking_workflow(
    initial_state: AgentState,
    thread_id: str | None = None,
) -> AgentState:
    """Invoke the graph from scratch (or resume an existing thread).

    * Single-shot calls (``/chat/test``, ``/chat/appointments``): pass
      ``thread_id=None``; a fresh UUID is created so each call is isolated.
    * First reply in a guided session: pass the ``session_id`` as
      ``thread_id``; this creates the checkpoint for that thread.
    """
    t_id   = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": t_id}}
    return booking_graph.invoke(initial_state, config=config)


def resume_workflow(thread_id: str, query: str) -> AgentState:
    """Resume a paused guided session by injecting the user's new message.

    LangGraph restores all checkpointed fields and overwrites only ``query``
    before re-running from the coordinator node.
    """
    config = {"configurable": {"thread_id": thread_id}}
    # Pass only the new query — LangGraph merges with the saved checkpoint
    return booking_graph.invoke({"query": query}, config=config)


def get_thread_state(thread_id: str) -> AgentState | None:
    """Return the latest checkpointed state for *thread_id*, or None."""
    config   = {"configurable": {"thread_id": thread_id}}
    snapshot = booking_graph.get_state(config)
    if snapshot is None or not snapshot.values:
        return None
    return snapshot.values  # type: ignore[return-value]