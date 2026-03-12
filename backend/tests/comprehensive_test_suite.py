#!/usr/bin/env python3
"""
Comprehensive Test Suite for WhatsUpDoc MVP
Tests all major flows with multilingual support
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from services.doctor_command_service import DoctorCommandService
from services.patient_intent_service import PatientIntentService
from services.escalation_service import EscalationService
from routers.webhook import detect_sender_role, process_incoming_message
from database import Database
import uuid
from datetime import datetime, timezone

class ComprehensiveTestSuite:
    def __init__(self):
        self.doctor_service = DoctorCommandService()
        self.patient_service = PatientIntentService()
        self.escalation_service = EscalationService()
        self.client = None
        self.db = None
        self.results = []
    
    async def setup(self):
        """Setup test environment"""
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.DB_NAME]
        Database.db = self.db
        print("✅ Test environment ready\n")
    
    async def cleanup(self):
        """Cleanup"""
        if self.client:
            self.client.close()
    
    def record_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.results.append({
            "category": category,
            "test": test_name,
            "passed": passed,
            "details": details
        })
    
    async def test_language_detection(self):
        """Test language detection across multiple languages"""
        print("\n" + "="*80)
        print("TEST CATEGORY: Language Detection")
        print("="*80 + "\n")
        
        test_cases = [
            ("Can I come tomorrow?", "en", "English"),
            ("Kal appointment mil sakti hai?", "hi", "Hindi"),
            ("Mujhe doctor se milna hai", "hi", "Hindi"),
            ("Doctor ji Friday nu time mil sakda?", "pa", "Punjabi"),
            ("Enakku naalai appointment venum", "ta", "Tamil"),
            ("నాకు రేపు అపాయింట్మెంట్ కావాలి", "te", "Telugu"),
            ("I want appointment kal", "en", "Hinglish")
        ]
        
        for message, expected_lang, language_name in test_cases:
            try:
                parsed = await self.patient_service.parse_intent(message)
                detected = parsed.get("detected_language", "").lower()
                
                # Be flexible with language codes (en, English, etc.)
                passed = expected_lang in detected.lower() or detected.startswith(expected_lang)
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | {language_name:15} | \"{message[:40]}...\"")
                if not passed:
                    print(f"         Expected: {expected_lang}, Got: {detected}")
                
                self.record_result("Language Detection", language_name, passed, detected)
            except Exception as e:
                print(f"❌ ERROR | {language_name:15} | {str(e)[:50]}")
                self.record_result("Language Detection", language_name, False, str(e))
    
    async def test_escalation_detection(self):
        """Test escalation keyword detection"""
        print("\n" + "="*80)
        print("TEST CATEGORY: Escalation Detection")
        print("="*80 + "\n")
        
        test_cases = [
            ("I have severe pain", True, "English - pain"),
            ("Mera dard bohot zyada hai", True, "Hindi - dard"),
            ("Bleeding won't stop", True, "English - bleeding"),
            ("Bohot sujan hai", True, "Hindi - sujan"),
            ("I need appointment tomorrow", False, "Normal booking"),
            ("What are your hours?", False, "General query"),
        ]
        
        for message, should_escalate, test_name in test_cases:
            detected = self.escalation_service.detect_escalation(message)
            passed = detected == should_escalate
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} | {test_name:25} | \"{message[:35]}...\" -> {detected}")
            
            self.record_result("Escalation", test_name, passed)
    
    async def test_sender_role_detection(self):
        """Test doctor vs patient role detection"""
        print("\n" + "="*80)
        print("TEST CATEGORY: Sender Role Detection")
        print("="*80 + "\n")
        
        # Get test phones from database
        clinic = await self.db.clinics.find_one({"is_active": True})
        if not clinic:
            print("⚠️  No clinic found, skipping role detection tests")
            return
        
        doctor = await self.db.doctors.find_one({"clinic_id": clinic["id"]})
        patient = await self.db.patients.find_one({})
        
        test_cases = []
        if doctor:
            test_cases.append((doctor["phone"], "DOCTOR", "Doctor phone"))
        if patient:
            test_cases.append((patient["phone"], "PATIENT", "Patient phone"))
        test_cases.append(("+919999999999", "PATIENT", "Unknown phone (default)"))
        
        for phone, expected_role, test_name in test_cases:
            try:
                detected_role = await detect_sender_role(self.db, phone, clinic["id"])
                passed = detected_role.value.upper() == expected_role
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | {test_name:25} | {phone} -> {detected_role.value}")
                
                self.record_result("Role Detection", test_name, passed)
            except Exception as e:
                print(f"❌ ERROR | {test_name:25} | {str(e)[:50]}")
                self.record_result("Role Detection", test_name, False)
    
    async def test_doctor_command_parsing(self):
        """Test doctor command natural language parsing"""
        print("\n" + "="*80)
        print("TEST CATEGORY: Doctor Command Parsing")
        print("="*80 + "\n")
        
        test_cases = [
            ("Block tomorrow 10 to 1 surgery", "create_calendar_block"),
            ("Vacation 5 June to 12 June", "set_vacation"),
            ("Schedule Ramesh Friday 5 pm", "create_appointment"),
            ("Cancel Neha tomorrow", "cancel_appointment"),
            ("Show tomorrow appointments", "list_appointments"),
            ("Move all morning patients to Monday", "bulk_reschedule"),
        ]
        
        for command, expected_intent in test_cases:
            try:
                parsed = await self.doctor_service.parse_command(command)
                actual_intent = parsed.get("intent")
                passed = actual_intent == expected_intent
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | \"{command[:40]}...\" -> {actual_intent}")
                
                self.record_result("Doctor Parsing", command[:30], passed, actual_intent)
            except Exception as e:
                print(f"❌ ERROR | \"{command[:40]}...\" | {str(e)[:50]}")
                self.record_result("Doctor Parsing", command[:30], False)
    
    async def test_patient_intent_parsing(self):
        """Test patient intent parsing"""
        print("\n" + "="*80)
        print("TEST CATEGORY: Patient Intent Parsing")
        print("="*80 + "\n")
        
        test_cases = [
            ("Can I come tomorrow?", "book_appointment"),
            ("Cancel my appointment", "cancel_appointment"),
            ("When is my next appointment?", "check_appointment"),
            ("Kal appointment mil sakti hai?", "book_appointment"),
            ("Mujhe appointment reschedule karni hai", "reschedule_appointment"),
        ]
        
        for message, expected_intent in test_cases:
            try:
                parsed = await self.patient_service.parse_intent(message)
                actual_intent = parsed.get("intent")
                passed = actual_intent == expected_intent
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{status} | \"{message[:40]}...\" -> {actual_intent}")
                
                self.record_result("Patient Parsing", message[:30], passed, actual_intent)
            except Exception as e:
                print(f"❌ ERROR | \"{message[:40]}...\" | {str(e)[:50]}")
                self.record_result("Patient Parsing", message[:30], False)
    
    def print_summary(self):
        """Print test summary"""
        print("\n\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80 + "\n")
        
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}
            
            if result["passed"]:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        total_passed = 0
        total_failed = 0
        
        for category, stats in categories.items():
            total = stats["passed"] + stats["failed"]
            passed = stats["passed"]
            rate = (passed / total * 100) if total > 0 else 0
            
            print(f"{category:25} | {passed:2}/{total:2} passed ({rate:5.1f}%)")
            
            total_passed += passed
            total_failed += stats["failed"]
        
        print("\n" + "-"*80)
        grand_total = total_passed + total_failed
        overall_rate = (total_passed / grand_total * 100) if grand_total > 0 else 0
        print(f"{'OVERALL':25} | {total_passed:2}/{grand_total:2} passed ({overall_rate:5.1f}%)")
        print("="*80 + "\n")
        
        if total_failed > 0:
            print("❌ Failed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"   - {result['category']}: {result['test']}")
                    if result.get("details"):
                        print(f"     Details: {result['details']}")

async def main():
    suite = ComprehensiveTestSuite()
    
    try:
        await suite.setup()
        
        # Run all test categories
        await suite.test_language_detection()
        await suite.test_escalation_detection()
        await suite.test_sender_role_detection()
        await suite.test_doctor_command_parsing()
        await suite.test_patient_intent_parsing()
        
        # Print summary
        suite.print_summary()
        
    finally:
        await suite.cleanup()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE TEST SUITE - WhatsUpDoc MVP")
    print("="*80)
    asyncio.run(main())
