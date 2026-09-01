from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.db import get_db
from backend.models.data_models import Patient, User


class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=20)


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """Fetch user profile details by user ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserProfileResponse)
@router.put("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(user_id: int,data: UserProfileUpdate,db: Session = Depends(get_db),):
    """Update name, phone number, and/or email for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate email uniqueness if changing email
    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].strip().lower()
        update_data["email"] = new_email
        existing = db.query(User).filter(User.email == new_email, User.id != user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered by another user",
            )

    # Validate phone uniqueness if changing phone
    if "phone" in update_data and update_data["phone"]:
        new_phone = update_data["phone"].strip()
        update_data["phone"] = new_phone
        existing = db.query(User).filter(User.phone == new_phone, User.id != user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number is already registered by another user",
            )

    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()

    # Update User model fields
    for field, value in update_data.items():
        setattr(user, field, value)

    # Also update linked Patient model fields if a patient profile exists
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if patient:
        for field, value in update_data.items():
            if hasattr(patient, field):
                setattr(patient, field, value)

    db.commit()
    db.refresh(user)

    return user