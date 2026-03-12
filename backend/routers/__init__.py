from .webhook import router as webhook_router
from .doctors import router as doctors_router
from .patients import router as patients_router
from .appointments import router as appointments_router
from .health import router as health_router

__all__ = [
    "webhook_router",
    "doctors_router",
    "patients_router",
    "appointments_router",
    "health_router",
]
