from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_patient, get_current_user, get_db
from backend.auth.register import AuthResponse
from backend.auth.security import create_access_token, verify_password
from backend.models.data_models import Patient, User


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=72)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    patient = db.query(Patient).filter(Patient.user_id == user.id).one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient profile is missing")
    return AuthResponse(
        access_token=create_access_token(user.id), user_id=user.id, patient_id=patient.id
    )


class MeResponse(BaseModel):
    user_id: int
    patient_id: int
    name: str
    email: str
    phone: str


@router.get("/me", response_model=MeResponse)
def me(
    user: Annotated[User, Depends(get_current_user)],
    patient: Annotated[Patient, Depends(get_current_patient)],
):
    return MeResponse(
        user_id=user.id, patient_id=patient.id, name=user.name, email=user.email, phone=user.phone
    )
