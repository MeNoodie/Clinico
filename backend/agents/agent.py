"""

LangChain agents used by the Clinico workflow.

"""

from datetime import date, datetime

from langchain.agents import create_agent
from langchain.tools import tool
from langsmith import traceable

from backend.LLM.cloud_model import get_llm

from backend.prompts.prompt import (
    SAFETY_PROMPT,
    RESPONSE_PROMPT,
    COORDINATOR_PROMPT,
    GUIDED_COORDINATOR_PROMPT,
    APPOINTMENT_PROMPT,
    CANCEL_PROMPT,
    RESCHEDULE_PROMPT,
    FOLLOWUP_PROMPT,
    ROUTER_PROMPT,
)

from backend.structured.output_str import (
    SafetyOutput,
    CoordinatorOutput,
    GuidedCoordinatorOutput,
    RouterOutput,
)

from backend.tools.appointment_tools import process_booking_request
from backend.tools.cancel_appointment import process_cancel_request
from backend.tools.reschedule_appointment import process_reschedule_request
from backend.tools.get_appointment_details import get_appointment_details


# ==============================================================================
# TOOLS
# ==============================================================================

@tool
def process_booking_tool(
    patient_id: int,
    department_name: str,
    appointment_datetime: str,
    patient_problem: str,
) -> dict:
    """Book an appointment."""
    return process_booking_request(
        patient_id=patient_id,
        department_name=department_name,
        appointment_datetime=datetime.fromisoformat(appointment_datetime),
        patient_problem=patient_problem,
    )


@tool
def process_cancel_tool(
    appointment_id: int,
    patient_id: int,
) -> dict:
    """Cancel an appointment."""
    return process_cancel_request(
        appointment_id=appointment_id,
        patient_id=patient_id,
    )


@tool
def process_reschedule_tool(
    appointment_id: int,
    patient_id: int,
    appointment_datetime: str,
    patient_problem: str | None = None,
) -> dict:
    """Reschedule an appointment."""
    return process_reschedule_request(
        appointment_id=appointment_id,
        patient_id=patient_id,
        appointment_datetime=datetime.fromisoformat(appointment_datetime),
        patient_problem=patient_problem,
    )


@tool
def get_appointment_details_tool(
    appointment_id: int,
    patient_id: int,
) -> dict:
    """Fetch appointment details."""
    return get_appointment_details(
        appointment_id=appointment_id,
        patient_id=patient_id,
    )


# ==============================================================================
# LLMs
# ==============================================================================

fast_llm = get_llm("llama")

safety_llm = get_llm("llama").with_structured_output(SafetyOutput)

coordinator_llm = get_llm("llama").with_structured_output(CoordinatorOutput)

guided_coordinator_llm = get_llm("llama").with_structured_output(GuidedCoordinatorOutput)

router_llm = get_llm("llama").with_structured_output(RouterOutput)


# ==============================================================================
# AGENTS
# ==============================================================================

coordinator_agent = create_agent(
    model=coordinator_llm,
    system_prompt=COORDINATOR_PROMPT,
)

router_agent = create_agent(
    model=fast_llm,
    system_prompt=ROUTER_PROMPT,
)

safety_agent = create_agent(
    model=safety_llm,
    system_prompt=SAFETY_PROMPT,
)

appointment_agent = create_agent(
    model=fast_llm,
    tools=[process_booking_tool],
    system_prompt=APPOINTMENT_PROMPT,
)

cancel_agent = create_agent(
    model=fast_llm,
    tools=[process_cancel_tool],
    system_prompt=CANCEL_PROMPT,
)

reschedule_agent = create_agent(
    model=fast_llm,
    tools=[process_reschedule_tool],
    system_prompt=RESCHEDULE_PROMPT,
)

followup_agent = create_agent(
    model=fast_llm,
    tools=[get_appointment_details_tool],
    system_prompt=FOLLOWUP_PROMPT,
)


# ==============================================================================
# INVOKE HELPERS
# ==============================================================================

@traceable(name="SafetyAgent")
def invoke_safety_agent(query: str) -> SafetyOutput:
    """Classify a patient message as NORMAL or EMERGENCY."""
    return safety_llm.invoke(SAFETY_PROMPT.format(query=query))


@traceable(name="CoordinatorAgent")
def invoke_coordinator_agent(query: str) -> CoordinatorOutput:
    """Extract structured booking facts from a patient message."""
    return coordinator_llm.invoke(
        COORDINATOR_PROMPT.format(
            query=query,
            current_date=date.today().isoformat(),
        )
    )


@traceable(name="GuidedCoordinatorAgent")
def invoke_coordinator_guided(
    intent: str,
    user_message: str,
    conversation_history: list[dict],
    awaiting_fields: list[str],
) -> GuidedCoordinatorOutput:
    """Extract only the missing fields from a patient reply during a guided session.

    Used when the intent is already known (button-click entry).  The LLM never
    re-detects intent; it only fills in whichever fields are listed in
    ``awaiting_fields``.
    """
    history_text = "\n".join(
        f"{turn['role'].capitalize()}: {turn['content']}"
        for turn in conversation_history
    ) or "(no prior messages)"

    prompt = GUIDED_COORDINATOR_PROMPT.format(
        intent=intent,
        conversation_history=history_text,
        user_message=user_message,
        awaiting_fields=", ".join(awaiting_fields) if awaiting_fields else "none",
        current_date=date.today().isoformat(),
    )
    return guided_coordinator_llm.invoke(prompt)



@traceable(name="RouterAgent")
def invoke_router_agent(**state) -> RouterOutput:
    """Map a patient problem to a hospital department."""
    return router_llm.invoke(
        ROUTER_PROMPT.format(**state)
    )


@traceable(name="AppointmentAgent")
def invoke_appointment_agent(**state):
    user_msg = (
        f"Book appointment for patient_id={state['patient_id']}, "
        f"department={state['department_name']}, "
        f"datetime={state['appointment_datetime']}, "
        f"problem={state['problem']}"
    )
    result = appointment_agent.invoke({"messages": [("user", user_msg)]})
    last = result["messages"][-1]
    return _parse_agent_response(last, state)


@traceable(name="CancelAgent")
def invoke_cancel_agent(**state):
    user_msg = (
        f"Cancel appointment_id={state['appointment_id']} "
        f"for patient_id={state['patient_id']}"
    )
    result = cancel_agent.invoke({"messages": [("user", user_msg)]})
    last = result["messages"][-1]
    return _parse_agent_response(last, state)


@traceable(name="RescheduleAgent")
def invoke_reschedule_agent(**state):
    user_msg = (
        f"Reschedule appointment_id={state['appointment_id']} "
        f"for patient_id={state['patient_id']} "
        f"to datetime={state['appointment_datetime']}, "
        f"problem={state.get('problem')}"
    )
    result = reschedule_agent.invoke({"messages": [("user", user_msg)]})
    last = result["messages"][-1]
    return _parse_agent_response(last, state)


@traceable(name="FollowupAgent")
def invoke_followup_agent(**state):
    user_msg = (
        f"Get details for appointment_id={state['appointment_id']} "
        f"for patient_id={state['patient_id']}"
    )
    result = followup_agent.invoke({"messages": [("user", user_msg)]})
    last = result["messages"][-1]
    return _parse_agent_response(last, state)


@traceable(name="ResponseAgent")
def invoke_response_agent(**workflow_facts) -> str:
    response = fast_llm.invoke(
        RESPONSE_PROMPT.format(**workflow_facts)
    )
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


# ==============================================================================
# RESPONSE PARSER
# ==============================================================================

import json as _json

def _parse_agent_response(last_message, state: dict) -> dict:
    """Extract a dict from the agent's last AI message."""
    content = getattr(last_message, "content", last_message)
    if isinstance(content, dict):
        return content

    # Try to parse JSON from the text response
    text = str(content).strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        return {"status": "ERROR", "error": text}