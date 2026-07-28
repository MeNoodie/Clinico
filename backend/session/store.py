"""Lightweight session ownership store for Clinico.

LangGraph's MemorySaver handles all conversation state persistence.
This module only tracks the mapping  session_id → patient_id  so that the
API layer can verify that a session belongs to the right patient.

It also centralises the intent-related constants used by both the graph
and the API layer.
"""

from __future__ import annotations

import threading
import time
import uuid


# ---------------------------------------------------------------------------
# Intent constants (imported by graph.py and api/chat.py)
# ---------------------------------------------------------------------------

# Required fields per intent that must be non-None before the workflow runs.
REQUIRED_FIELDS: dict[str, list[str]] = {
    "BOOK_APPOINTMENT":       ["problem", "appointment_datetime"],
    "CANCEL_APPOINTMENT":     ["appointment_id"],
    "RESCHEDULE_APPOINTMENT": ["appointment_id", "appointment_datetime"],
    "FOLLOWUP_APPOINTMENT":   ["appointment_id"],
    "UPLOAD_DOCUMENT":        [],
}

# Greeting returned immediately when a button is clicked (no LLM call yet).
INTENT_GREETING: dict[str, str] = {
    "BOOK_APPOINTMENT": (
        "I'll help you book an appointment. "
        "Please describe your health concern and tell me your preferred date and time."
    ),
    "CANCEL_APPOINTMENT": (
        "I'll help you cancel an appointment. "
        "Please provide your Appointment ID."
    ),
    "RESCHEDULE_APPOINTMENT": (
        "I'll help you reschedule an appointment. "
        "Please provide your Appointment ID and your preferred new date and time."
    ),
    "FOLLOWUP_APPOINTMENT": (
        "I'll help you schedule a follow-up. "
        "Please provide your Appointment ID."
    ),
    "UPLOAD_DOCUMENT": (
        "Please upload your document and I will store it for you."
    ),
}

# Per-field clarifying questions asked when a single field is still missing.
FIELD_QUESTIONS: dict[str, str] = {
    "problem":              "What health concern or symptom are you experiencing?",
    "appointment_datetime": "What date and time would you prefer? (e.g. 28 July at 10 AM)",
    "appointment_id":       "Please provide your Appointment ID.",
}


# ---------------------------------------------------------------------------
# Session ownership store
# ---------------------------------------------------------------------------

_DEFAULT_TTL: int = 30 * 60  # 30 minutes


class _OwnerEntry:
    __slots__ = ("patient_id", "intent", "expires_at")

    def __init__(self, patient_id: int, intent: str | None, ttl: int) -> None:
        self.patient_id = patient_id
        self.intent = intent
        self.expires_at = time.monotonic() + ttl


class SessionOwnerStore:
    """Thread-safe store that maps session_id → (patient_id, intent).

    All conversation state lives in LangGraph's MemorySaver; this store only
    exists so the API layer can authenticate that a reply belongs to the
    correct patient.
    """

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._entries: dict[str, _OwnerEntry] = {}
        self._lock = threading.Lock()

    def register(
        self,
        patient_id: int,
        intent: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Create and return a new session_id."""
        self._cleanup()
        sid = session_id or str(uuid.uuid4())
        with self._lock:
            self._entries[sid] = _OwnerEntry(patient_id, intent, self._ttl)
        return sid

    def get(self, session_id: str) -> _OwnerEntry | None:
        """Return the entry for *session_id*, or None if missing/expired."""
        self._cleanup()
        with self._lock:
            entry = self._entries.get(session_id)
        if entry is None or time.monotonic() > entry.expires_at:
            return None
        return entry

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._entries.pop(session_id, None)

    def _cleanup(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [sid for sid, e in self._entries.items() if now > e.expires_at]
            for sid in expired:
                del self._entries[sid]


# Module-level singleton used by the API layer.
store = SessionOwnerStore()
