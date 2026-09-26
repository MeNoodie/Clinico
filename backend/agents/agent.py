
from google.genai._gaos.models import updatetrigger
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
        return CoordinatorOutput(intent="BOOK_APPOINTMENT")   # 


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


@traceable(name="AppointmentAgent")
def invoke_appointment_agent(
    patient_id: int,
    department_name: str,
    appointment_datetime: str,
    patient_problem: str
):
    """Help book an appointment."""

    message = {
        "messages": [{
                "role": "user",
                "content": (
                    f"Book an appointment.\n"
                    f"Patient ID: {patient_id}\n"
                    f"Department: {department_name}\n"
                    f"Appointment datetime: {appointment_datetime}\n"
                    f"Patient problem: {patient_problem}")}]}

    try:
        return appointment_agent.invoke(message)

    except Exception as exc:
        print(f"[WARN] AppointmentAgent error: {exc}")
        return {"status": "ERROR", "error": str(exc)}


