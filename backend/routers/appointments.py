from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List
from database import get_database
from models import Appointment, AppointmentCreate, AppointmentStatus
from services.calendar_ics_service import generate_ics_for_appointment
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/appointments", tags=["appointments"])

@router.post("", response_model=Appointment)
async def create_appointment(appointment: AppointmentCreate):
    """Create a new appointment"""
    db = get_database()
    
    appointment_dict = appointment.model_dump()
    appointment_dict["id"] = str(uuid.uuid4())
    appointment_dict["status"] = AppointmentStatus.SCHEDULED.value
    appointment_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    appointment_dict["updated_at"] = None
    
    await db.appointments.insert_one(appointment_dict)
    
    return Appointment(**appointment_dict)

@router.get("", response_model=List[Appointment])
async def list_appointments(doctor_id: str = None, patient_id: str = None, date: str = None):
    """List appointments with optional filters"""
    db = get_database()
    
    query = {}
    if doctor_id:
        query["doctor_id"] = doctor_id
    if patient_id:
        query["patient_id"] = patient_id
    if date:
        query["appointment_date"] = date
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(1000)
    return [Appointment(**doc) for doc in appointments]

@router.get("/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str):
    """Get an appointment by ID"""
    db = get_database()
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return Appointment(**appointment)


@router.get("/{appointment_id}/calendar.ics", response_class=PlainTextResponse)
async def get_appointment_ics(appointment_id: str):
    """
    Return ICS file for this appointment so user can add to phone calendar.
    Open this URL on your phone or download to add event to device calendar.
    """
    db = get_database()
    appointment = await db.appointments.find_one({"id": appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.get("status") in ("cancelled",):
        raise HTTPException(status_code=410, detail="Appointment is cancelled")
    patient = await db.patients.find_one({"id": appointment["patient_id"]}, {"_id": 0}) if appointment.get("patient_id") else None
    summary = f"Dental appointment"
    if patient and patient.get("name"):
        summary = f"Dental - {patient['name']}"
    ics = generate_ics_for_appointment(
        appointment_id=appointment_id,
        summary=summary,
        start_date=appointment["appointment_date"],
        start_time=appointment["appointment_time"],
        duration_minutes=appointment.get("duration_minutes", 30),
        description="Booked via DentBot WhatsApp",
    )
    return PlainTextResponse(content=ics, media_type="text/calendar")

@router.patch("/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    db = get_database()
    
    result = await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {
            "status": AppointmentStatus.CANCELLED.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {"status": "cancelled", "appointment_id": appointment_id}
