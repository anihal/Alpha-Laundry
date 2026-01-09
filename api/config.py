"""
Configuration module for Alpha Laundry Management System
Handles environment variables and application settings
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # Application Settings
    APP_NAME: str = "Alpha Laundry Management System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "alpha_laundry"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "your_password"
    DB_ECHO: bool = False  # Set to True for SQL query logging

    # Database Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # JWT Configuration
    JWT_SECRET_KEY: str = "your_jwt_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # Password Hashing Settings
    PWD_CONTEXT_SCHEMES: list = ["bcrypt"]
    PWD_BCRYPT_ROUNDS: int = 12

    # Pagination Settings
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Business Logic Settings
    DEFAULT_QUOTA: int = 30
    MAX_CLOTHES_PER_REQUEST: int = 50
    MIN_CLOTHES_PER_REQUEST: int = 1

    # Rate Limiting (optional, for future implementation)
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def database_url(self) -> str:
        """
        Construct PostgreSQL database URL for SQLAlchemy
        """
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def async_database_url(self) -> str:
        """
        Construct async PostgreSQL database URL for SQLAlchemy
        """
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Returns:
        Settings: Application settings singleton
    """
    return Settings()


# Create a global settings instance
settings = get_settings()


# Database connection string for direct usage
DATABASE_URL = settings.database_url
ASYNC_DATABASE_URL = settings.async_database_url


# Environment check helpers
def is_development() -> bool:
    """Check if running in development mode"""
    return os.getenv("NODE_ENV", "development") == "development"


def is_production() -> bool:
    """Check if running in production mode"""
    return os.getenv("NODE_ENV", "development") == "production"


def is_testing() -> bool:
    """Check if running in test mode"""
    return os.getenv("NODE_ENV", "development") == "test"


# Export commonly used settings
__all__ = [
    "settings",
    "get_settings",
    "Settings",
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
    "is_development",
    "is_production",
    "is_testing",
]
