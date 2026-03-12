#!/usr/bin/env python3
"""
Mock WhatsApp Conversation Simulator
Simulates WhatsApp conversations for testing without real WhatsApp API
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from routers.webhook import process_incoming_message
from database import Database
import uuid
from datetime import datetime, timezone

class MockWhatsAppSimulator:
    def __init__(self):
        self.client = None
        self.db = None
    
    async def setup(self):
        """Setup database connection"""
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.DB_NAME]
        Database.db = self.db
        print("✅ Connected to database\n")
    
    async def cleanup(self):
        """Cleanup"""
        if self.client:
            self.client.close()
    
    async def send_message(self, phone: str, message: str):
        """Simulate sending a WhatsApp message"""
        print(f"\n{'='*80}")
        print(f"📱 From: {phone}")
        print(f"💬 Message: \"{message}\"")
        print(f"{'='*80}\n")
        
        # Create mock WhatsApp message structure
        whatsapp_message = {
            "from": phone,
            "id": f"mock_{uuid.uuid4().hex[:8]}",
            "text": {
                "body": message
            },
            "timestamp": str(int(datetime.now().timestamp()))
        }
        
        # Process through webhook handler
        try:
            await process_incoming_message(whatsapp_message, {})
            await asyncio.sleep(0.5)  # Small delay for processing
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    async def run_scenario(self, scenario_name: str, messages: list):
        """Run a conversation scenario"""
        print(f"\n{'='*80}")
        print(f"🎬 SCENARIO: {scenario_name}")
        print(f"{'='*80}\n")
        
        for phone, message, delay in messages:
            await self.send_message(phone, message)
            if delay:
                print(f"⏳ Waiting {delay}s...\n")
                await asyncio.sleep(delay)
        
        print(f"\n{'='*80}")
        print(f"✅ SCENARIO COMPLETE: {scenario_name}")
        print(f"{'='*80}\n")

async def main():
    simulator = MockWhatsAppSimulator()
    
    try:
        await simulator.setup()
        
        # Get test numbers from database or use defaults
        doctor_phone = "+919123456789"
        patient_phone = "+919999888877"
        
        # Scenario 1: Patient Booking Flow (English)
        await simulator.run_scenario(
            "Patient Booking Flow - English",
            [
                (patient_phone, "Can I come tomorrow?", 2),
                (patient_phone, "2", 2),
            ]
        )
        
        # Scenario 2: Patient Booking Flow (Hindi)
        await simulator.run_scenario(
            "Patient Booking Flow - Hindi",
            [
                (patient_phone, "Kal appointment mil sakti hai?", 2),
                (patient_phone, "1", 2),
            ]
        )
        
        # Scenario 3: Patient Check Appointment
        await simulator.run_scenario(
            "Check Appointment",
            [
                (patient_phone, "When is my next appointment?", 2),
            ]
        )
        
        # Scenario 4: Patient Escalation (Hindi)
        await simulator.run_scenario(
            "Emergency Escalation - Hindi",
            [
                (patient_phone, "Mera dard bohot zyada hai", 2),
            ]
        )
        
        # Scenario 5: Doctor Block Calendar
        await simulator.run_scenario(
            "Doctor Block Calendar",
            [
                (doctor_phone, "Block tomorrow 10 to 1 surgery", 2),
            ]
        )
        
        # Scenario 6: Doctor Vacation
        await simulator.run_scenario(
            "Doctor Set Vacation",
            [
                (doctor_phone, "Vacation 20 March to 25 March", 2),
            ]
        )
        
        # Scenario 7: Doctor Schedule Appointment
        await simulator.run_scenario(
            "Doctor Schedule Appointment",
            [
                (doctor_phone, "Schedule Priya Monday 3 pm", 2),
            ]
        )
        
        # Scenario 8: Doctor List Appointments
        await simulator.run_scenario(
            "Doctor List Appointments",
            [
                (doctor_phone, "Show tomorrow appointments", 2),
            ]
        )
        
        # Scenario 9: Patient Cancel
        await simulator.run_scenario(
            "Patient Cancel Appointment",
            [
                (patient_phone, "Cancel my appointment", 2),
            ]
        )
        
        # Scenario 10: Multilingual Mix
        await simulator.run_scenario(
            "Multilingual - Hinglish",
            [
                (patient_phone, "Mujhe appointment chahiye next Friday ko", 2),
                (patient_phone, "3", 2),
            ]
        )
        
        print("\n" + "="*80)
        print("🎉 ALL SCENARIOS COMPLETED")
        print("="*80 + "\n")
        
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🤖 MOCK WHATSAPP CONVERSATION SIMULATOR")
    print("="*80 + "\n")
    asyncio.run(main())
