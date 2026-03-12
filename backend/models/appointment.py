from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class AppointmentCreate(BaseModel):
    clinic_id: str
    doctor_id: str
    patient_id: str
    appointment_date: str
    appointment_time: str
    duration_minutes: int = 30
    reason: Optional[str] = None

class Appointment(BaseModel):
    id: str
    clinic_id: str
    doctor_id: str
    patient_id: str
    appointment_date: str
    appointment_time: str
    duration_minutes: int = 30
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
