import json
from datetime import datetime, timezone, timedelta

from langchain.agents import create_agent
from langchain.tools import tool
from langsmith import traceable

from backend.LLM.cloud_model import get_llm

from backend.prompts.prompt import (
    SAFETY_PROMPT,
    RESPONSE_PROMPT,
    COORDINATOR_PROMPT,
    APPOINTMENT_PROMPT,
    CANCEL_PROMPT,
    RESCHEDULE_PROMPT,
    FOLLOWUP_PROMPT,
    ROUTER_PROMPT,
)
from backend.structured.output_str import (
    SafetyOutput,
    CoordinatorOutput,
    RouterOutput,
)

from backend.tools.appointment_tools import process_booking_request
from backend.tools.cancel_appointment import process_cancel_request
from backend.tools.reschedule_appointment import process_reschedule_request
from backend.tools.get_appointment_details import get_appointment_details

# ----- Time ---------

IST = timezone(timedelta(hours=5, minutes=30))
current_date = datetime.now(IST).date().isoformat()

#------ LLM ----------

fast_llm = get_llm("fast")         
safety_llm = get_llm("llama").with_structured_output(SafetyOutput)
coordinator_llm = get_llm("llama").with_structured_output(CoordinatorOutput)
router_llm = get_llm("fast").with_structured_output(RouterOutput)


#------- tools ------

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


#------- Agnets -----------


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

@traceable(name="SafetyAgent")
def invoke_safety_agent(query: str) -> SafetyOutput:
    """Classify a patient message as NORMAL or EMERGENCY."""
    try:
        return safety_llm.invoke(SAFETY_PROMPT.format(query=query))
    except Exception as exc:
        print(f"[WARN] SafetyAgent error, falling back to NORMAL: {exc}")
        return SafetyOutput(status="NORMAL", reason="Fallback to routine booking.")


@traceable(name="CoordinatorAgent")
def invoke_coordinator_agent(query: str) -> CoordinatorOutput:
    """Extract structured booking facts from a patient message."""
    prompt = COORDINATOR_PROMPT.format(
        query=query,
        current_date=current_date)
    try:
        return coordinator_llm.invoke(prompt)
    except Exception as exc:
        print(f"[WARN] CoordinatorAgent error, falling back: {exc}")
        return  CoordinatorOutput(
            intent="BOOK_APPOINTMENT",
            problem=None,
            normalized_query=query,
        )  


@traceable(name="RouterAgent")
def invoke_router_agent(query:str , problem :str | None , current_date : str) -> RouterOutput:
    """Map a patient problem to a hospital department."""
    prompt = ROUTER_PROMPT.format(query=query,
        problem=problem,
        current_date=current_date)
    try:
        return router_llm.invoke(prompt) 
    except Exception as exc:
        print(f"[WARN] RouterAgent error {exc}")
        return RouterOutput(
        department=None,
        appointment_datetime=None,
        status="ERROR")


def _extract_text(content) -> str:
    """Extract plain text from an LLM response or message content."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "text" in item:
                    parts.append(item.get("text", ""))
            elif hasattr(item, "text"):
                parts.append(getattr(item, "text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)

    return str(content) if content is not None else ""


def _parse_agent_json(content) -> dict:
    """Extract a dict from an LLM response or string."""
    if isinstance(content, dict):
        return content
    text = _extract_text(content).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"status": "ERROR", "error": text}



@traceable(name="AppointmentAgent")
def invoke_appointment_agent(
    patient_id: int,
    department_name: str,
    appointment_datetime: str,
    patient_problem: str,
) -> dict:
    """Help book an appointment."""

    message = {
        "messages": [{
            "role": "user",
            "content": (
                f"Book an appointment.\n"
                f"Patient ID: {patient_id}\n"
                f"Department: {department_name}\n"
                f"Appointment datetime: {appointment_datetime}\n"
                f"Patient problem: {patient_problem}"
            ),
        }]
    }

    try:
        agent_out = appointment_agent.invoke(message)

        if isinstance(agent_out, dict):
            messages = agent_out.get("messages", [])
            # 1. Check last message content
            if messages:
                last_msg = messages[-1]
                content = getattr(last_msg, "content", last_msg)
                parsed = _parse_agent_json(content)
                if isinstance(parsed, dict) and ("status" in parsed or "appointment_id" in parsed):
                    return parsed

            # 2. Check tool messages for direct dict outputs
            for msg in reversed(messages):
                tool_output = getattr(msg, "artifact", None) or getattr(msg, "content", None)
                if isinstance(tool_output, dict) and "status" in tool_output:
                    return tool_output
                parsed = _parse_agent_json(tool_output)
                if isinstance(parsed, dict) and "status" in parsed:
                    return parsed

            if "status" in agent_out:
                return agent_out

        return {"status": "ERROR", "error": "Could not parse appointment booking result."}

    except Exception as exc:
        print(f"[WARN] AppointmentAgent error: {exc}")
        return {"status": "ERROR", "error": str(exc)}


@traceable(name="response_agent")
def invoke_response_agent(
    *,
    intent=None,
    current_step=None,
    status=None,
    problem=None,
    department=None,
    appointment_id=None,
    appointment_datetime=None,
    doctor_name=None,
    alt_slots=None,
    cancel_status=None,
    appointment_details=None,
    emergency_message=None,
    awaiting_fields=None,
    error=None,
) -> str:

    facts = {
        "intent": intent or "UNKNOWN",
        "current_step": current_step or "",
        "status": status or "",
        "problem": problem or "",
        "department": department or "",
        "appointment_id": appointment_id,
        "appointment_datetime": appointment_datetime,
        "doctor_name": doctor_name or "",
        "alt_slots": alt_slots or [],
        "cancel_status": cancel_status or "",
        "appointment_details": appointment_details or {},
        "emergency_message": emergency_message or "",
        "awaiting_fields": awaiting_fields or [],
        "error": error or "",
    }

    try:
        response = fast_llm.invoke(
            RESPONSE_PROMPT.format(**facts)
        )

        text = _extract_text(
            getattr(response, "content", response)
        ).strip()

        if text:
            return text

    except Exception as exc:
        print(f"[WARN] ResponseAgent error: {exc}")

    # Fallback responses
    if facts["emergency_message"]:
        return facts["emergency_message"]

    if facts["error"]:
        return (
            "We couldn't complete your request. "
            "Please try again."
        )

    if facts["awaiting_fields"]:
        field = facts["awaiting_fields"][0]

        questions = {
            "problem": "Could you describe your medical concern?",
            "department": "Which department would you like to consult?",
            "appointment_datetime": "What date and time would you prefer?",
            "appointment_id": "Could you provide your appointment ID?",
        }

        return questions.get(
            field,
            "Could you provide the missing information?"
        )

    return "Your request has been received. How else can I help?"