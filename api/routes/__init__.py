"""
API Routes for Alpha Laundry Management System
"""

from .auth import router as auth_router
from .student import router as student_router
from .admin import router as admin_router

__all__ = ["auth_router", "student_router", "admin_router"]
