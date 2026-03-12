from fastapi import APIRouter, HTTPException
from typing import List
from database import get_database
from models import Doctor, DoctorCreate
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/doctors", tags=["doctors"])

@router.post("", response_model=Doctor)
async def create_doctor(doctor: DoctorCreate):
    """Create a new doctor"""
    db = get_database()
    
    existing = await db.doctors.find_one({"phone": doctor.phone, "clinic_id": doctor.clinic_id})
    if existing:
        raise HTTPException(status_code=400, detail="Doctor with this phone already exists in this clinic")
    
    doctor_dict = doctor.model_dump()
    doctor_dict["id"] = str(uuid.uuid4())
    doctor_dict["is_active"] = True
    doctor_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.doctors.insert_one(doctor_dict)
    
    return Doctor(**doctor_dict)

@router.get("", response_model=List[Doctor])
async def list_doctors(clinic_id: str = None):
    """List all doctors"""
    db = get_database()
    
    query = {}
    if clinic_id:
        query["clinic_id"] = clinic_id
    
    doctors = await db.doctors.find(query, {"_id": 0}).to_list(1000)
    return [Doctor(**doc) for doc in doctors]

@router.get("/{doctor_id}", response_model=Doctor)
async def get_doctor(doctor_id: str):
    """Get a doctor by ID"""
    db = get_database()
    
    doctor = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return Doctor(**doctor)
