#!/usr/bin/env python3
"""Setup script to initialize WhatsUpDoc with sample clinic and doctor data"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import uuid
from datetime import datetime, timezone

async def setup_clinic():
    """Initialize clinic, doctor, and test patient"""
    print("\n=" * 80)
    print("WhatsUpDoc Setup Script")
    print("=" * 80)
    
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.DB_NAME]
    
    print(f"\nConnected to MongoDB: {settings.DB_NAME}")
    
    # Check if clinic already exists
    existing_clinic = await db.clinics.find_one({"is_active": True})
    if existing_clinic:
        print("\n⚠️  Active clinic already exists:")
        print(f"   Clinic ID: {existing_clinic['id']}")
        print(f"   Name: {existing_clinic['name']}")
        print(f"   Phone: {existing_clinic['phone']}")
        
        response = input("\nDo you want to create a new clinic anyway? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("\nSetup cancelled.")
            client.close()
            return
    
    # Create clinic
    clinic_id = str(uuid.uuid4())
    clinic_phone = input("\nEnter clinic WhatsApp phone number (with country code, e.g., +919876543210): ")
    clinic_name = input("Enter clinic name: ") or "Dr. Sharma's Dental Clinic"
    
    clinic_doc = {
        "id": clinic_id,
        "name": clinic_name,
        "phone": clinic_phone,
        "working_hours": {
            "start": "09:00",
            "end": "18:00",
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        },
        "holidays": [],
        "escalation_keywords": [
            "pain", "swelling", "bleeding", "emergency", "urgent", "severe",
            "dard", "sujan", "khoon", "turant", "bukhar"
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    
    await db.clinics.insert_one(clinic_doc)
    print(f"\n✅ Clinic created: {clinic_name} (ID: {clinic_id})")
    
    # Create doctor
    doctor_id = str(uuid.uuid4())
    doctor_phone = input("\nEnter doctor WhatsApp phone number (with country code): ")
    doctor_name = input("Enter doctor name: ") or "Dr. Sharma"
    
    doctor_doc = {
        "id": doctor_id,
        "clinic_id": clinic_id,
        "name": doctor_name,
        "phone": doctor_phone,
        "specialization": "Dentist",
        "preferred_language": "en",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.doctors.insert_one(doctor_doc)
    print(f"\n✅ Doctor created: {doctor_name} (ID: {doctor_id})")
    
    # Create test patient
    test_patient = input("\nCreate a test patient? (yes/no): ")
    if test_patient.lower() in ['yes', 'y']:
        patient_id = str(uuid.uuid4())
        patient_phone = input("Enter test patient phone number: ")
        patient_name = input("Enter test patient name: ") or "Ramesh Kumar"
        
        patient_doc = {
            "id": patient_id,
            "phone": patient_phone,
            "name": patient_name,
            "preferred_language": "en",
            "consent_status": "given",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_contact": None
        }
        
        await db.patients.insert_one(patient_doc)
        print(f"\n✅ Test patient created: {patient_name} (ID: {patient_id})")
    
    print("\n" + "=" * 80)
    print("Setup Complete!")
    print("=" * 80)
    print("\nYour WhatsUpDoc system is ready.")
    print(f"\nClinic Phone: {clinic_phone}")
    print(f"Doctor Phone: {doctor_phone}")
    print("\nNOTE: System is in MOCK mode. WhatsApp messages will be logged to console.")
    print("      To enable real WhatsApp, update .env with actual WhatsApp API credentials.")
    print("\nTry these APIs:")
    print("  - GET  /api/health")
    print("  - GET  /api/doctors")
    print("  - GET  /api/patients")
    print("  - POST /api/webhook/whatsapp (for WhatsApp messages)")
    print("\n" + "=" * 80)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(setup_clinic())
