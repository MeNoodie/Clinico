"""SQLAlchemy ORM models for Clinico's appointment database."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.db import Base


class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    doctors: Mapped[list[Doctor]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )
    appointments: Mapped[list[Appointment]] = relationship(back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    experience: Mapped[int] = mapped_column()
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    work_start_time: Mapped[time] = mapped_column(Time)
    work_end_time: Mapped[time] = mapped_column(Time)

    department: Mapped[Department] = relationship(back_populates="doctors")
    working_days: Mapped[list[DoctorWorkingDay]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )
    appointments: Mapped[list[Appointment]] = relationship(back_populates="doctor")

    __table_args__ = (
        CheckConstraint("experience >= 0", name="ck_doctors_experience_nonnegative"),
        CheckConstraint(
            "consultation_fee >= 0", name="ck_doctors_consultation_fee_nonnegative"
        ),
        CheckConstraint("work_end_time > work_start_time", name="ck_doctors_work_hours"),
        UniqueConstraint("name", "department_id", name="uq_doctors_name_department"),
    )


class DoctorWorkingDay(Base):
    __tablename__ = "doctor_working_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    day_of_week: Mapped[str] = mapped_column(String(10))

    doctor: Mapped[Doctor] = relationship(back_populates="working_days")

    __table_args__ = (
        UniqueConstraint("doctor_id", "day_of_week", name="uq_doctor_working_day"),
    )


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Existing seeded patients may not have an account yet, hence nullable.
    # Every patient created through signup receives exactly one user_id.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    user: Mapped[User | None] = relationship(back_populates="patient")
    appointments: Mapped[list[Appointment]] = relationship(back_populates="patient")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    patient: Mapped[Patient | None] = relationship(back_populates="user", uselist=False)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    appointment_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    patient_problem: Mapped[str] = mapped_column(Text)
    status: Mapped[AppointmentStatus] = mapped_column(
        SqlEnum(AppointmentStatus, native_enum=False, create_constraint=True),
        default=AppointmentStatus.BOOKED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    patient: Mapped[Patient] = relationship(back_populates="appointments")
    doctor: Mapped[Doctor] = relationship(back_populates="appointments")
    department: Mapped[Department] = relationship(back_populates="appointments")

    __table_args__ = (
        UniqueConstraint(
            "patient_id", "doctor_id", "appointment_datetime",
            name="uq_appointment_patient_doctor_datetime",
        ),
        Index("ix_appointments_doctor_datetime", "doctor_id", "appointment_datetime"),
        Index("ix_appointments_department_datetime", "department_id", "appointment_datetime"),
    )


class ActionType(str, Enum):
    BOOK = "BOOK"
    CANCEL = "CANCEL"
    RESCHEDULE = "RESCHEDULE"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    action_type: Mapped[ActionType] = mapped_column(
        SqlEnum(ActionType, native_enum=False, create_constraint=True),
        nullable=False,
    )
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    patient: Mapped[Patient] = relationship()


class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    patient: Mapped[Patient] = relationship()
    appointment: Mapped[Appointment | None] = relationship()

