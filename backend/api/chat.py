"""Authenticated API for the Clinico appointment workflow.

Endpoints
---------
POST /chat/appointments   — single-shot, JWT-auth, natural-language
POST /chat/test           — single-shot, no JWT (Swagger testing)
POST /chat/session/start  — begin a guided multi-turn session (button click)
POST /chat/session/reply  — send the next message in a guided session
"""

from __future__ import annotations

import uuid
import os
import shutil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field

from backend.agents.graph import (
    get_thread_state,
    resume_workflow,
    run_booking_workflow,
)
from backend.auth.dependencies import get_current_patient
from backend.database.db import SessionLocal
from backend.models.data_models import Patient, MedicalDocument
from backend.session.store import (
    INTENT_GREETING,
    REQUIRED_FIELDS,
    store as session_store,
)


router = APIRouter(prefix="/chat", tags=["Appointments"])


# =============================================================================
# Shared Pydantic models
# =============================================================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2_000)
    problem: str | None = Field(default=None, max_length=2_000)
    department: str | None = Field(default=None, max_length=100)
    appointment_datetime: str | None = Field(
        default=None,
        description="Preferred local ISO-8601 datetime, e.g. 2026-07-27T10:30:00",
    )


class TestChatRequest(BaseModel):
    """Swagger-friendly request — accepts patient_id directly (no JWT)."""

    patient_id: int = Field(description="ID of a seeded patient (1–6)")
    message: str = Field(min_length=2, max_length=2_000)
    session_id: str | None = Field(default=None, description="Optional session ID for multi-turn testing")
    problem: str | None = Field(default=None, max_length=2_000)
    department: str | None = Field(default=None, max_length=100)
    appointment_datetime: str | None = Field(
        default=None,
        description="Preferred local ISO-8601 datetime, e.g. 2026-07-28T10:00:00",
    )
    appointment_id: int | None = Field(
        default=None,
        description="Existing appointment ID (for cancel / reschedule / followup)",
    )


class ChatResponse(BaseModel):
    message: str
    department: str | None = None
    intent: str
    safety_status: str
    appointment_id: int | None = None
    booked_datetime: str | None = None
    alternative_slots: list[str] = Field(default_factory=list)


# =============================================================================
# Session / guided workflow models
# =============================================================================

class SessionStartRequest(BaseModel):
    """Kick off a guided workflow from a UI button click."""

    intent: str | None = Field(
        default=None,
        description=(
            "Pre-seeded intent from the button: BOOK_APPOINTMENT, "
            "CANCEL_APPOINTMENT, RESCHEDULE_APPOINTMENT, "
            "FOLLOWUP_APPOINTMENT, UPLOAD_DOCUMENT. "
            "Omit (or pass null) for natural-language entry."
        ),
    )


class SessionStartResponse(BaseModel):
    session_id: str
    message: str  # First clarifying question / greeting


class SessionReplyRequest(BaseModel):
    session_id: str = Field(description="ID returned by POST /chat/session/start")
    message: str = Field(min_length=1, max_length=2_000)


class SessionReplyResponse(BaseModel):
    """One turn response.

    * ``done=False`` — Coordinator needs more info; ``message`` is the next
      clarifying question.
    * ``done=True``  — Workflow completed; all ChatResponse fields are set.
    """

    done: bool
    message: str
    # Populated only when done=True
    department: str | None = None
    intent: str | None = None
    safety_status: str | None = None
    appointment_id: int | None = None
    booked_datetime: str | None = None
    alternative_slots: list[str] = Field(default_factory=list)


# =============================================================================
# Existing single-shot endpoints (UNCHANGED behaviour)
# =============================================================================

@router.post("/appointments", response_model=ChatResponse)
def create_appointment(
    payload: ChatRequest,
    patient: Annotated[Patient, Depends(get_current_patient)],
) -> ChatResponse:
    state = run_booking_workflow({
        "query":                payload.message,
        "patient_id":           patient.id,
        "problem":              payload.problem or payload.message,
        "department":           payload.department,
        "appointment_datetime": payload.appointment_datetime,
        "multi_turn":           False,  # single-shot — never pause
    })
    return ChatResponse(
        message=state["final_message"],
        department=state.get("department"),
        intent=state["intent"],
        safety_status=state["safety_status"],
        appointment_id=state.get("appointment_id"),
        booked_datetime=state.get("booked_datetime"),
        alternative_slots=state.get("alt_slots", []),
    )


@router.post("/test", response_model=ChatResponse, summary="Test workflow without JWT")
def test_appointment(payload: TestChatRequest) -> ChatResponse:
    """Unauthenticated endpoint for Swagger testing. Uses patient_id directly."""
    if payload.session_id:
        existing = get_thread_state(payload.session_id)
        if existing:
            state = resume_workflow(payload.session_id, payload.message)
        else:
            initial: dict = {
                "query":                payload.message,
                "patient_id":           payload.patient_id,
                "problem":              payload.problem or payload.message,
                "department":           payload.department,
                "appointment_datetime": payload.appointment_datetime,
                "appointment_id":       payload.appointment_id,
                "multi_turn":           True,
            }
            state = run_booking_workflow(initial, thread_id=payload.session_id)
    else:
        initial: dict = {
            "query":                payload.message,
            "patient_id":           payload.patient_id,
            "problem":              payload.problem or payload.message,
            "department":           payload.department,
            "appointment_datetime": payload.appointment_datetime,
            "multi_turn":           False,  # single-shot
        }
        if payload.appointment_id is not None:
            initial["appointment_id"] = payload.appointment_id
        state = run_booking_workflow(initial)
    return ChatResponse(
        message=state.get("final_message", ""),
        department=state.get("department"),
        intent=state.get("intent", "UNKNOWN"),
        safety_status=state.get("safety_status", "UNKNOWN"),
        appointment_id=state.get("appointment_id"),
        booked_datetime=state.get("booked_datetime"),
        alternative_slots=state.get("alt_slots", []),
    )


# =============================================================================
# NEW: Session / guided workflow endpoints
# =============================================================================

@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    summary="Start a guided session (button click)",
)
def session_start(
    payload: SessionStartRequest,
    patient: Annotated[Patient, Depends(get_current_patient)],
) -> SessionStartResponse:
    """Create a new guided session for the authenticated patient.

    * Returns a ``session_id`` (LangGraph thread_id) and the first greeting /
      clarifying question — determined from the intent, no LLM call yet.
    * Pass ``intent=null`` to start in natural-language mode; the Coordinator
      will detect the intent from the patient's first reply.
    """
    session_id = str(uuid.uuid4())
    intent     = payload.intent

    # Register ownership for auth validation in subsequent replies
    session_store.register(
        patient_id=patient.id,
        intent=intent,
        session_id=session_id,
    )

    # Return the greeting immediately without invoking the LLM
    greeting = INTENT_GREETING.get(intent or "", "How can I help you today?")
    return SessionStartResponse(session_id=session_id, message=greeting)


@router.post(
    "/session/reply",
    response_model=SessionReplyResponse,
    summary="Send a reply inside a guided session (multi-turn)",
)
def session_reply(
    payload: SessionReplyRequest,
    patient: Annotated[Patient, Depends(get_current_patient)],
) -> SessionReplyResponse:
    """Process one turn of a multi-turn guided session.

    How it works (LangGraph MemorySaver)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    * **First reply** — no checkpoint exists yet.  We build the full initial
      state (intent + patient_id) and call ``run_booking_workflow`` with the
      session_id as the thread_id.  LangGraph saves the result.

    * **Subsequent replies** — a checkpoint exists.  We call ``resume_workflow``
      which passes only ``{query: message}``; LangGraph restores all other
      fields from the saved checkpoint and re-runs from the coordinator.

    * When the coordinator finds no more ``awaiting_fields``, the graph
      continues through safety → routing → action → response → END.
      The final state has ``current_step == "completed"`` or
      ``"emergency_done"``, and we return ``done=True``.

    * While fields are still missing, the graph routes to ``waiting_for_user``
      → END, checkpoints state, and returns ``done=False`` with the next
      clarifying question.
    """
    # ── Auth & session validation ─────────────────────────────────────────────
    entry = session_store.get(payload.session_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired. Please start a new session.",
        )
    if entry.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not belong to you.",
        )

    # ── Determine if this is the first reply for this thread ──────────────────
    existing = get_thread_state(payload.session_id)

    if existing is None:
        # First reply — no LangGraph checkpoint yet.
        # Build the complete initial state with intent + awaiting_fields.
        intent   = entry.intent
        required = REQUIRED_FIELDS.get(intent or "", [])
        initial_state: dict = {
            "query":                payload.message,
            "patient_id":           patient.id,
            "intent":               intent,
            "problem":              None,
            "department":           None,
            "appointment_datetime": None,
            "appointment_id":       None,
            "preferred_doctor":     None,
            "awaiting_fields":      list(required),
            "conversation_history": [],
            "multi_turn":           True,
        }
        final_state = run_booking_workflow(initial_state, thread_id=payload.session_id)
    else:
        # Subsequent reply — LangGraph merges {query} with the checkpoint.
        final_state = resume_workflow(payload.session_id, payload.message)

    # ── Determine if the workflow completed ───────────────────────────────────
    terminal_steps = {"completed", "emergency_done"}
    done = final_state.get("current_step") in terminal_steps

    if done:
        session_store.delete(payload.session_id)  # clean up ownership entry

    return SessionReplyResponse(
        done=done,
        message=final_state.get("final_message", ""),
        department=final_state.get("department"),
        intent=final_state.get("intent"),
        safety_status=final_state.get("safety_status"),
        appointment_id=final_state.get("appointment_id"),
        booked_datetime=final_state.get("booked_datetime"),
        alternative_slots=final_state.get("alt_slots", []),
    )
