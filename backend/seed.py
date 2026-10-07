"""Idempotent reference data for production appointment booking."""

from datetime import time
from decimal import Decimal

from sqlalchemy import select

from backend.database.db import SessionLocal
from backend.models.data_models import Department, Doctor, DoctorWorkingDay


DEPARTMENTS = {
    "Cardiology": "Diagnosis and treatment of heart and circulatory conditions.",
    "Dermatology": "Care for skin, hair, nail, and related conditions.",
    "Orthopedics": "Treatment of bones, joints, muscles, and sports injuries.",
    "Neurology": "Care for disorders of the brain, spine, and nervous system.",
    "ENT": "Ear, nose, throat, and head-and-neck care.",
    "General Medicine": "Primary care and treatment of common adult illnesses.",
}

DOCTORS = [
    ("Dr. Ananya Sharma", "Cardiology", 14, "900.00"),
    ("Dr. Rohan Mehta", "Cardiology", 9, "750.00"),
    ("Dr. Neha Kapoor", "Dermatology", 11, "700.00"),
    ("Dr. Vikram Nair", "Dermatology", 8, "650.00"),
    ("Dr. Arjun Rao", "Orthopedics", 16, "950.00"),
    ("Dr. Priya Iyer", "Orthopedics", 10, "800.00"),
    ("Dr. Karan Malhotra", "Neurology", 15, "1100.00"),
    ("Dr. Meera Joshi", "Neurology", 7, "850.00"),
    ("Dr. Siddharth Bose", "ENT", 12, "700.00"),
    ("Dr. Kavya Menon", "ENT", 6, "600.00"),
    ("Dr. Amit Verma", "General Medicine", 18, "650.00"),
    ("Dr. Sneha Gupta", "General Medicine", 9, "550.00"),
]

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def seed_reference_data() -> None:
    """Create or update the catalogue used by the booking workflow."""
    with SessionLocal() as session:
        for name, description in DEPARTMENTS.items():
            department = session.scalar(select(Department).where(Department.name == name))
            if department is None:
                session.add(Department(name=name, description=description))
            else:
                department.description = description
        session.flush()

        departments = {
            department.name: department
            for department in session.scalars(select(Department)).all()
        }
        for name, department_name, experience, fee in DOCTORS:
            doctor = session.scalar(
                select(Doctor).where(
                    Doctor.name == name,
                    Doctor.department_id == departments[department_name].id,
                )
            )
            if doctor is None:
                doctor = Doctor(
                    name=name,
                    department=departments[department_name],
                    experience=experience,
                    consultation_fee=Decimal(fee),
                    work_start_time=time(9),
                    work_end_time=time(17),
                )
                session.add(doctor)
                session.flush()
            else:
                doctor.experience = experience
                doctor.consultation_fee = Decimal(fee)
                doctor.work_start_time = time(9)
                doctor.work_end_time = time(17)

            existing_days = set(
                session.scalars(
                    select(DoctorWorkingDay.day_of_week).where(
                        DoctorWorkingDay.doctor_id == doctor.id
                    )
                ).all()
            )
            for day in WEEKDAYS:
                if day not in existing_days:
                    session.add(DoctorWorkingDay(doctor=doctor, day_of_week=day))

        session.commit()
