import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

class ConversationStateManager:
    """Manage multi-turn conversation state for patients"""
    
    def __init__(self, db):
        self.db = db
    
    async def get_state(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state for patient"""
        try:
            state = await self.db.conversation_states.find_one({
                "patient_id": patient_id,
                "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
            }, {"_id": 0})
            
            if state:
                logger.info(f"Found active state for patient {patient_id}: {state['state_type']}")
            
            return state
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return None
    
    async def set_state(self, patient_id: str, state_type: str, data: Dict[str, Any], ttl_minutes: int = 10) -> bool:
        """Set conversation state for patient"""
        try:
            from datetime import timedelta
            
            # Clear existing states for this patient
            await self.db.conversation_states.delete_many({"patient_id": patient_id})
            
            # Create new state
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            state_doc = {
                "id": str(uuid.uuid4()),
                "patient_id": patient_id,
                "state_type": state_type,
                "data": data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
            await self.db.conversation_states.insert_one(state_doc)
            logger.info(f"Set state for patient {patient_id}: {state_type}")
            return True
        
        except Exception as e:
            logger.error(f"Error setting conversation state: {e}")
            return False
    
    async def clear_state(self, patient_id: str):
        """Clear conversation state for patient"""
        try:
            await self.db.conversation_states.delete_many({"patient_id": patient_id})
            logger.info(f"Cleared state for patient {patient_id}")
        except Exception as e:
            logger.error(f"Error clearing conversation state: {e}")
    
    async def cleanup_expired(self):
        """Remove expired conversation states"""
        try:
            result = await self.db.conversation_states.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}
            })
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired conversation states")
        except Exception as e:
            logger.error(f"Error cleaning up expired states: {e}")
