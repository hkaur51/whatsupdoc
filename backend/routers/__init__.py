from .webhook import router as webhook_router
from .doctors import router as doctors_router
from .patients import router as patients_router
from .appointments import router as appointments_router
from .health import router as health_router
from .chat import router as chat_router
from .auth import router as auth_router

__all__ = [
    "webhook_router",
    "doctors_router",
    "patients_router",
    "appointments_router",
    "health_router",
    "chat_router",
    "auth_router",
]
