"""LangGraph workflow for Clinico."""

from __future__ import annotations

from backend.agents.state import AgentState
from backend.agents.agent import (
    invoke_safety_agent,
    invoke_coordinator_agent,
    invoke_router_agent,
    invoke_appointment_agent,
    invoke_cancel_agent,
    invoke_reschedule_agent,
    invoke_followup_agent,
    invoke_response_agent,
)

from langgraph.graph import START, END, StateGraph


EMERGENCY_MESSAGE = (
    "⚠️ This sounds like a medical emergency. "
    "Please call the hospital emergency line immediately: 108 (Ambulance) or 112 (Emergency). "
    "Do NOT wait for an appointment — go to the nearest emergency room now."
)


# =============================================================================
# Nodes
# =============================================================================

def coordinator_node(state: AgentState) -> AgentState:
    result = invoke_coordinator_agent(state["query"])

    return {
        **state,
        "intent": result.intent,
        "problem": result.problem,
        "department": result.department,
        "appointment_datetime": result.appointment_datetime,
        "current_step": "coordinator_done",
    }


def safety_node(state: AgentState) -> AgentState:
    result = invoke_safety_agent(state["query"])

    return {
        **state,
        "safety_status": result.status,
        "safety_reason": result.reason,
        "current_step": "safety_done",
    }


def router_node(state: AgentState) -> AgentState:
    if state.get("department"):
        return {
            **state,
            "current_step": "router_done",
        }

    result = invoke_router_agent(
        problem=state.get("problem") or state["query"]
    )

    return {
        **state,
        "department": result.department,
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
        return {
            **state,
            "error": str(exc),
            "current_step": "appointment_done",
        }

    status = result.get("status")

    if status == "BOOKED":
        return {
            **state,
            "appointment_id": result["appointment_id"],
            "booked_datetime": result["appointment_datetime"],
            "doctor_name": result.get("doctor_name"),
            "current_step": "appointment_done",
        }

    return {
        **state,
        "alt_slots": result.get("available_slots", []),
        "current_step": "appointment_done",
    }


def cancel_node(state: AgentState) -> AgentState:
    try:
        result = invoke_cancel_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
        )
    except Exception as exc:
        return {
            **state,
            "error": str(exc),
            "current_step": "cancel_done",
        }

    return {
        **state,
        "cancel_status": result["status"],
        "current_step": "cancel_done",
    }


def reschedule_node(state: AgentState) -> AgentState:
    try:
        result = invoke_reschedule_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
            appointment_datetime=state["appointment_datetime"],
            problem=state.get("problem"),
        )
    except Exception as exc:
        return {
            **state,
            "error": str(exc),
            "current_step": "reschedule_done",
        }

    status = result.get("status")
    if status == "RESCHEDULED":
        return {
            **state,
            "appointment_id": result.get("appointment_id", state.get("appointment_id")),
            "booked_datetime": result.get("new_datetime", result.get("appointment_datetime")),
            "current_step": "reschedule_done",
        }

    return {
        **state,
        "alt_slots": result.get("available_slots", []),
        "current_step": "reschedule_done",
    }


def followup_node(state: AgentState) -> AgentState:
    try:
        result = invoke_followup_agent(
            appointment_id=state["appointment_id"],
            patient_id=state["patient_id"],
        )
    except Exception as exc:
        return {
            **state,
            "error": str(exc),
            "current_step": "followup_done",
        }

    # If successful, extract details for response node
    if result.get("status") == "SUCCESS":
        return {
            **state,
            "appointment_details": result,
            "department": result.get("department_name"),
            "doctor_name": result.get("doctor_name"),
            "appointment_id": result.get("appointment_id"),  # ensure set
            "booked_datetime": result.get("appointment_datetime"),  # ISO string
            "problem": result.get("patient_problem"),
            "error": None,  # clear any previous error
            "alt_slots": [],  # not applicable for followup
            "current_step": "followup_done",
        }
    else:
        # error case
        return {
            **state,
            "appointment_details": result,
            "error": result.get("error", "Unknown error"),
            "current_step": "followup_done",
        }


def emergency_node(state: AgentState) -> AgentState:
    """Administrative emergency escalation — provide emergency info, never diagnose."""
    return {
        **state,
        "emergency_message": EMERGENCY_MESSAGE,
        "final_message": EMERGENCY_MESSAGE,
        "current_step": "emergency_done",
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

    return {
        **state,
        "final_message": message,
        "current_step": "completed",
    }


# =============================================================================
# Conditional Routing
# =============================================================================

def safety_route(state: AgentState):
    if state["safety_status"] == "EMERGENCY":
        return "emergency"
    return "router"


def intent_route(state: AgentState):
    intent = state["intent"]

    if intent == "BOOK_APPOINTMENT":
        return "appointment"

    if intent == "CANCEL_APPOINTMENT":
        return "cancel"

    if intent == "RESCHEDULE_APPOINTMENT":
        return "reschedule"

    if intent == "FOLLOWUP_APPOINTMENT":
        return "followup"

    return "response"


# =============================================================================
# Graph
# =============================================================================

def build_graph():

    graph = StateGraph(AgentState)

    graph.add_node("coordinator", coordinator_node)
    graph.add_node("safety", safety_node)
    graph.add_node("router", router_node)
    graph.add_node("appointment", appointment_node)
    graph.add_node("cancel", cancel_node)
    graph.add_node("reschedule", reschedule_node)
    graph.add_node("followup", followup_node)
    graph.add_node("emergency", emergency_node)
    graph.add_node("response", response_node)

    # START → coordinator → safety
    graph.add_edge(START, "coordinator")
    graph.add_edge("coordinator", "safety")

    # safety branches: EMERGENCY → emergency node, else → router
    graph.add_conditional_edges(
        "safety",
        safety_route,
        {
            "router": "router",
            "emergency": "emergency",
        },
    )

    # router branches by intent
    graph.add_conditional_edges(
        "router",
        intent_route,
        {
            "appointment": "appointment",
            "cancel": "cancel",
            "reschedule": "reschedule",
            "followup": "followup",
            "response": "response",
        },
    )

    # all action nodes → response → END
    graph.add_edge("appointment", "response")
    graph.add_edge("cancel", "response")
    graph.add_edge("reschedule", "response")
    graph.add_edge("followup", "response")
    graph.add_edge("emergency", END)
    graph.add_edge("response", END)

    return graph.compile()


booking_graph = build_graph()


def run_booking_workflow(initial_state: AgentState):
    return booking_graph.invoke(initial_state)