import logging
from typing import List

logger = logging.getLogger(__name__)

class EscalationService:
    """Service for detecting urgent/clinical messages that need escalation"""
    
    def __init__(self):
        self.urgent_keywords = [
            # English
            "pain", "severe", "emergency", "urgent", "bleeding", "swelling",
            "fever", "infection", "broken", "fracture", "accident", "injury",
            "can't breathe", "chest pain", "unconscious", "allergic",
            
            # Hindi
            "dard", "\u0926\u0930\u094d\u0926", "sujan", "\u0938\u0942\u091c\u0928", "khoon", "\u0916\u0942\u0928",
            "turant", "\u0924\u0941\u0930\u0902\u0924", "bukhar", "\u092c\u0941\u0916\u093e\u0930",
            
            # Hinglish
            "bohot dard", "bahut pain", "emergency hai",
            
            # Punjabi
            "dukh", "jaldi", "khatra",
            
            # Tamil
            "vali", "\u0bb5\u0bb2\u0bbf", "emergency",
            
            # Telugu
            "noppi", "\u0c28\u0c4a\u0c2a\u0c4d\u0c2a\u0c3f", "emergency",
            
            # Medical
            "prescription", "medicine", "tablet", "dawa", "\u0926\u0935\u093e",
            "injection", "surgery", "operation"
        ]
    
    def detect_escalation(self, message: str) -> bool:
        """Check if message contains urgent/clinical keywords"""
        message_lower = message.lower()
        
        for keyword in self.urgent_keywords:
            if keyword.lower() in message_lower:
                logger.warning(f"Escalation keyword detected: {keyword} in message: {message}")
                return True
        
        return False
    
    def get_escalation_keywords(self) -> List[str]:
        """Return list of escalation keywords"""
        return self.urgent_keywords
