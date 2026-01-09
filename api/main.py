"""
Main FastAPI application for Alpha Laundry Management System
"""

import sys
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database import engine, Base, check_database_connection
from .routes import auth_router, student_router, admin_router

# =====================================================
# APPLICATION INITIALIZATION
# =====================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RESTful API for managing laundry services with user subscriptions and job tracking",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# =====================================================
# CORS MIDDLEWARE
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# =====================================================
# CUSTOM ERROR HANDLERS
# =====================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "detail": "The request contains invalid data",
            "errors": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle SQLAlchemy database errors
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Database Error",
            "detail": "An error occurred while processing your request",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all other unhandled exceptions
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


# =====================================================
# STARTUP AND SHUTDOWN EVENTS
# =====================================================


@app.on_event("startup")
async def startup_event():
    """
    Actions to perform on application startup
    """
    print("=" * 60)
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)

    # Check database connection
    print("🔌 Checking database connection...")
    if check_database_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed!")
        sys.exit(1)

    # Create tables if they don't exist
    print("📊 Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")

    print("=" * 60)
    print(f"📡 API server running on http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API documentation: http://{settings.HOST}:{settings.PORT}/api/docs")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Actions to perform on application shutdown
    """
    print("\n" + "=" * 60)
    print("🛑 Shutting down Alpha Laundry Management System...")
    print("=" * 60)


# =====================================================
# ROUTERS
# =====================================================

# Include authentication routes
app.include_router(auth_router, prefix=settings.API_PREFIX)

# Include student routes
app.include_router(student_router, prefix=settings.API_PREFIX)

# Include admin routes
app.include_router(admin_router, prefix=settings.API_PREFIX)


# =====================================================
# HEALTH CHECK AND ROOT ENDPOINTS
# =====================================================


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    db_connected = check_database_connection()

    return {
        "status": "healthy" if db_connected else "unhealthy",
        "database": "connected" if db_connected else "disconnected",
        "version": settings.APP_VERSION,
    }


@app.get("/api")
async def api_info():
    """
    API information endpoint
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "auth": f"{settings.API_PREFIX}/auth",
            "student": f"{settings.API_PREFIX}/student",
            "admin": f"{settings.API_PREFIX}/admin",
        },
        "documentation": {
            "swagger": "/api/docs",
            "redoc": "/api/redoc",
            "openapi": "/api/openapi.json",
        },
    }


# =====================================================
# APPLICATION ENTRY POINT
# =====================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
    )
