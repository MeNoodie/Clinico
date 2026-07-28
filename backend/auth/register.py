from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_db
from backend.auth.security import create_access_token, hash_password
from backend.models.data_models import Patient, User


router = APIRouter(prefix="/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8, max_length=72)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    patient_id: int


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    email, phone, name = payload.email.strip().lower(), payload.phone.strip(), payload.name.strip()
    existing = db.query(User).filter(or_(User.email == email, User.phone == phone)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or phone is already registered")

    user = User(name=name, email=email, phone=phone, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    # Keep the patient profile for appointments; its id is returned for workflows.
    patient = Patient(user_id=user.id, name=name, email=email, phone=phone)
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or phone is already registered")
    db.refresh(patient)
    return AuthResponse(
        access_token=create_access_token(user.id), user_id=user.id, patient_id=patient.id
    )
