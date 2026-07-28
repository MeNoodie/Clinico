from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from backend.auth.dependencies import get_current_patient, get_db
from backend.models.data_models import Appointment, Patient

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.get("/history")
def get_appointment_history(
    patient: Annotated[Patient, Depends(get_current_patient)],
    db: Annotated[Session, Depends(get_db)]
):
    """Fetch the appointment history for the authenticated patient."""
    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.department))
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    
    results = []
    for appt in appointments:
        results.append({
            "appointment_id": appt.id,
            "datetime": appt.appointment_datetime.isoformat(),
            "status": appt.status.value,
            "problem": appt.patient_problem,
            "doctor_name": appt.doctor.name if appt.doctor else "Unknown",
            "department_name": appt.department.name if appt.department else "Unknown",
        })
    return {"history": results}
