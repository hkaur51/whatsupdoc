from fastapi import APIRouter, HTTPException
from typing import List
from database import get_database
from models import Patient, PatientCreate
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/patients", tags=["patients"])

@router.post("", response_model=Patient)
async def create_patient(patient: PatientCreate):
    """Create a new patient"""
    db = get_database()
    
    existing = await db.patients.find_one({"phone": patient.phone})
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone already exists")
    
    patient_dict = patient.model_dump()
    patient_dict["id"] = str(uuid.uuid4())
    patient_dict["consent_status"] = "pending"
    patient_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    patient_dict["last_contact"] = None
    
    await db.patients.insert_one(patient_dict)
    
    return Patient(**patient_dict)

@router.get("", response_model=List[Patient])
async def list_patients():
    """List all patients"""
    db = get_database()
    
    patients = await db.patients.find({}, {"_id": 0}).to_list(1000)
    return [Patient(**doc) for doc in patients]

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a patient by ID"""
    db = get_database()
    
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return Patient(**patient)
