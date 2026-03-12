from fastapi import APIRouter
from database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
    """Health check endpoint"""
    try:
        db = get_database()
        await db.command("ping")
        return {
            "status": "healthy",
            "database": "connected",
            "service": "WhatsUpDoc API"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
