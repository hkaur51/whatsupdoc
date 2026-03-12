#!/usr/bin/env python3
"""
Comprehensive test suite for Doctor Natural Language Command Engine
Tests 15+ different command scenarios
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from services.doctor_command_service import DoctorCommandService
from services.doctor_command_executor import DoctorCommandExecutor
import uuid
from datetime import datetime, timezone, timedelta
import json

class DoctorCommandTester:
    def __init__(self):
        self.command_service = DoctorCommandService()
        self.command_executor = DoctorCommandExecutor()
        self.client = None
        self.db = None
        self.clinic_id = None
        self.doctor_id = None
        self.doctor_phone = None
        self.test_results = []
    
    async def setup(self):
        """Setup test database"""
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.DB_NAME]
        
        # Create test clinic
        self.clinic_id = str(uuid.uuid4())
        clinic_doc = {
            "id": self.clinic_id,
            "name": "Test Clinic",
            "phone": "+919999999999",
            "working_hours": {"start": "09:00", "end": "18:00", "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]},
            "holidays": [],
            "escalation_keywords": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }
        await self.db.clinics.insert_one(clinic_doc)
        
        # Create test doctor
        self.doctor_id = str(uuid.uuid4())
        self.doctor_phone = "+919876543210"
        doctor_doc = {
            "id": self.doctor_id,
            "clinic_id": self.clinic_id,
            "name": "Dr. Test",
            "phone": self.doctor_phone,
            "specialization": "General",
            "preferred_language": "en",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await self.db.doctors.insert_one(doctor_doc)
        
        # Create test patients
        patients = [
            {"name": "Ramesh", "phone": "+919111111111"},
            {"name": "Neha", "phone": "+919222222222"},
            {"name": "Priya", "phone": "+919333333333"},
            {"name": "Amit", "phone": "+919444444444"}
        ]
        
        for patient in patients:
            patient_id = str(uuid.uuid4())
            patient_doc = {
                "id": patient_id,
                "phone": patient["phone"],
                "name": patient["name"],
                "preferred_language": "en",
                "consent_status": "given",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_contact": None
            }
            await self.db.patients.insert_one(patient_doc)
        
        print("✅ Test environment setup complete\n")
    
    async def cleanup(self):
        """Cleanup test data"""
        await self.db.clinics.delete_many({"id": self.clinic_id})
        await self.db.doctors.delete_many({"id": self.doctor_id})
        await self.db.patients.delete_many({"phone": {"$regex": "^\\+9191"}})
        await self.db.appointments.delete_many({"clinic_id": self.clinic_id})
        await self.db.calendar_blocks.delete_many({"doctor_id": self.doctor_id})
        self.client.close()
        print("\n✅ Test cleanup complete")
    
    async def run_test(self, test_num: int, command: str, expected_intent: str, description: str):
        """Run a single test"""
        print(f"\n{'='*80}")
        print(f"TEST #{test_num}: {description}")
        print(f"{'='*80}")
        print(f"📝 Command: \"{command}\"")
        
        try:
            # Parse command
            parsed = await self.command_service.parse_command(command)
            
            # Check intent
            actual_intent = parsed.get("intent")
            intent_match = actual_intent == expected_intent
            
            print(f"\n🔍 Parsed Output:")
            print(json.dumps(parsed, indent=2))
            
            print(f"\n✓ Intent Detection: {'✅ PASS' if intent_match else '❌ FAIL'}")
            print(f"  Expected: {expected_intent}")
            print(f"  Actual: {actual_intent}")
            
            # Execute command
            print(f"\n⚙️  Executing command...")
            response = await self.command_executor.execute(parsed, self.clinic_id, self.doctor_phone, self.db)
            
            print(f"\n💬 Response:")
            print(f"  {response}")
            
            # Record result
            self.test_results.append({
                "test": test_num,
                "description": description,
                "command": command,
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "passed": intent_match,
                "response": response
            })
            
            return intent_match
        
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            self.test_results.append({
                "test": test_num,
                "description": description,
                "command": command,
                "expected_intent": expected_intent,
                "passed": False,
                "error": str(e)
            })
            return False
    
    async def run_all_tests(self):
        """Run all 15+ test cases"""
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        next_friday = (datetime.now() + timedelta(days=(4 - datetime.now().weekday()) % 7 + 7)).strftime("%Y-%m-%d")
        
        # Test 1: Calendar Block with Time Range
        await self.run_test(
            1,
            "Block tomorrow 10 to 1 surgery",
            "create_calendar_block",
            "Calendar block with time range"
        )
        
        # Test 2: Calendar Block - Afternoon
        await self.run_test(
            2,
            "Block tomorrow afternoon",
            "create_calendar_block",
            "Calendar block with relative time"
        )
        
        # Test 3: Calendar Block - Specific reason
        await self.run_test(
            3,
            "Block Friday 2 to 4 pm for training",
            "create_calendar_block",
            "Calendar block with specific reason"
        )
        
        # Test 4: Set Vacation - Date range
        await self.run_test(
            4,
            "Vacation 5 June to 12 June",
            "set_vacation",
            "Vacation with date range"
        )
        
        # Test 5: Set Vacation - Alternative phrasing
        await self.run_test(
            5,
            "I'm on leave next Monday to Friday",
            "set_vacation",
            "Vacation with relative dates"
        )
        
        # Test 6: Create Appointment
        await self.run_test(
            6,
            "Schedule Ramesh Friday 5 pm",
            "create_appointment",
            "Create appointment with patient name, day, time"
        )
        
        # Test 7: Create Appointment - Tomorrow
        await self.run_test(
            7,
            "Put Neha on tomorrow 11 am",
            "create_appointment",
            "Create appointment - tomorrow"
        )
        
        # Test 8: Create Appointment - Full sentence
        await self.run_test(
            8,
            "Book an appointment for Priya on Monday at 3 pm",
            "create_appointment",
            "Create appointment - full sentence"
        )
        
        # Test 9: Cancel Appointment by Patient
        await self.run_test(
            9,
            "Cancel Neha tomorrow",
            "cancel_appointment",
            "Cancel appointment by patient name and date"
        )
        
        # Test 10: Cancel Appointment by Date
        await self.run_test(
            10,
            "Cancel all appointments on Friday",
            "cancel_appointment",
            "Cancel all appointments on specific date"
        )
        
        # Test 11: List Appointments
        await self.run_test(
            11,
            "Show tomorrow appointments",
            "list_appointments",
            "List appointments for tomorrow"
        )
        
        # Test 12: List Appointments - Today
        await self.run_test(
            12,
            "What's my schedule today",
            "list_appointments",
            "List today's schedule"
        )
        
        # Test 13: List Appointments - Specific day
        await self.run_test(
            13,
            "Show me Friday's appointments",
            "list_appointments",
            "List appointments for specific day"
        )
        
        # Test 14: Bulk Reschedule
        await self.run_test(
            14,
            "Move all morning patients to next Monday",
            "bulk_reschedule",
            "Bulk reschedule morning appointments"
        )
        
        # Test 15: Bulk Reschedule - Afternoon
        await self.run_test(
            15,
            "Shift everyone after lunch to Wednesday",
            "bulk_reschedule",
            "Bulk reschedule afternoon appointments"
        )
        
        # Test 16: Unavailability
        await self.run_test(
            16,
            "I'm unavailable this afternoon",
            "create_calendar_block",
            "Unavailability for time period"
        )
        
        # Test 17: Complex scheduling
        await self.run_test(
            17,
            "Schedule a follow-up for Amit in 2 weeks",
            "create_appointment",
            "Schedule appointment with relative future date"
        )
        
        # Test 18: Reschedule specific appointment
        await self.run_test(
            18,
            "Reschedule Ramesh from Friday to next Monday same time",
            "reschedule_appointment",
            "Reschedule specific patient appointment"
        )
    
    async def print_summary(self):
        """Print test summary"""
        print(f"\n\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}\n")
        
        passed = sum(1 for r in self.test_results if r.get("passed", False))
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {total - passed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        if total - passed > 0:
            print("Failed Tests:")
            for r in self.test_results:
                if not r.get("passed", False):
                    print(f"  - Test #{r['test']}: {r['description']}")
                    print(f"    Expected: {r['expected_intent']}, Got: {r.get('actual_intent', 'ERROR')}")
        
        print(f"\n{'='*80}\n")

async def main():
    tester = DoctorCommandTester()
    
    try:
        await tester.setup()
        await tester.run_all_tests()
        await tester.print_summary()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DOCTOR NATURAL LANGUAGE COMMAND ENGINE - TEST SUITE")
    print("="*80 + "\n")
    asyncio.run(main())
