import os
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


class AdminLoginRequest(BaseModel):
    admin_id: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)


class AdminAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: str


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


@router.post("/admin/login", response_model=AdminAuthResponse, status_code=status.HTTP_200_OK, tags=["Admin"], summary="Admin Login")
def admin_login(payload: AdminLoginRequest):
    admin_id = os.getenv("ADMIN_ID")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_id or not admin_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials not configured on server",
        )

    # Support both direct match or hashed password verification
    is_valid_password = (payload.password == admin_password)
    if not is_valid_password:
        try:
            is_valid_password = verify_password(payload.password, admin_password)
        except Exception:
            is_valid_password = False

    if payload.admin_id != admin_id or not is_valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    access_token = create_access_token(
        data={"sub": admin_id, "role": "admin"}
    )
    return AdminAuthResponse(
        access_token=access_token,
        token_type="bearer",
        admin_id=admin_id,
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
