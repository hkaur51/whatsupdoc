#!/usr/bin/env python3
"""
Seed database with test data for comprehensive testing
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import uuid
from datetime import datetime, timezone, timedelta

async def seed_test_data():
    """Seed database with test data"""
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.DB_NAME]
    
    print("🌱 Seeding test data...\n")
    
    # Clean up existing test data
    print("🧹 Cleaning up old test data...")
    await db.clinics.delete_many({"phone": {"$regex": "^\\+9198765"}})
    await db.doctors.delete_many({"phone": {"$regex": "^\\+9191234"}})
    await db.patients.delete_many({"phone": {"$regex": "^\\+9199998"}})
    await db.appointments.delete_many({})
    await db.calendar_blocks.delete_many({})
    await db.conversation_states.delete_many({})
    print("✅ Cleanup complete\n")
    
    # Create clinic
    clinic_id = str(uuid.uuid4())
    clinic_doc = {
        "id": clinic_id,
        "name": "Dr. Sharma's Clinic",
        "phone": "+919876543210",
        "working_hours": {
            "start": "09:00",
            "end": "18:00",
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        },
        "holidays": [],
        "escalation_keywords": [
            "pain", "dard", "swelling", "sujan", "bleeding", "khoon",
            "emergency", "urgent", "severe", "fever", "bukhar"
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    await db.clinics.insert_one(clinic_doc)
    print(f"✅ Created clinic: {clinic_doc['name']} (ID: {clinic_id})")
    
    # Create doctor
    doctor_id = str(uuid.uuid4())
    doctor_doc = {
        "id": doctor_id,
        "clinic_id": clinic_id,
        "name": "Dr. Amit Sharma",
        "phone": "+919123456789",
        "specialization": "Dentist",
        "preferred_language": "en",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.doctors.insert_one(doctor_doc)
    print(f"✅ Created doctor: {doctor_doc['name']} (Phone: {doctor_doc['phone']})")
    
    # Create test patients with different languages
    patients = [
        {
            "name": "Ramesh Kumar",
            "phone": "+919999888811",
            "preferred_language": "hi",
            "consent_status": "given"
        },
        {
            "name": "Neha Singh",
            "phone": "+919999888822",
            "preferred_language": "en",
            "consent_status": "given"
        },
        {
            "name": "Priya Patel",
            "phone": "+919999888833",
            "preferred_language": "hi",
            "consent_status": "given"
        },
        {
            "name": "Rajesh Verma",
            "phone": "+919999888844",
            "preferred_language": "pa",
            "consent_status": "given"
        },
        {
            "name": "Anjali Reddy",
            "phone": "+919999888855",
            "preferred_language": "te",
            "consent_status": "given"
        },
        {
            "name": "Main Test Patient",
            "phone": "+919999888877",
            "preferred_language": "en",
            "consent_status": "given"
        }
    ]
    
    for patient_data in patients:
        patient_id = str(uuid.uuid4())
        patient_doc = {
            "id": patient_id,
            "phone": patient_data["phone"],
            "name": patient_data["name"],
            "preferred_language": patient_data["preferred_language"],
            "consent_status": patient_data["consent_status"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_contact": None
        }
        await db.patients.insert_one(patient_doc)
        print(f"✅ Created patient: {patient_data['name']} ({patient_data['phone']}) - Lang: {patient_data['preferred_language']}")
    
    print("\n" + "="*80)
    print("📊 TEST DATA SUMMARY")
    print("="*80)
    print(f"\n📍 Clinic Phone: {clinic_doc['phone']}")
    print(f"👨‍⚕️  Doctor Phone: {doctor_doc['phone']}")
    print(f"\n👥 Patient Phones:")
    for p in patients:
        print(f"   - {p['name']}: {p['phone']} ({p['preferred_language']})")
    
    print("\n" + "="*80)
    print("✅ Test data seeded successfully!")
    print("="*80 + "\n")
    
    print("🔍 You can now test with:")
    print(f"   Doctor: {doctor_doc['phone']}")
    print(f"   Patient: {patients[-1]['phone']}")
    print("\nOr run: python3 tests/mock_whatsapp_simulator.py\n")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_test_data())
