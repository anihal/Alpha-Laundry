"""
Configuration module - loads environment variables
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///laundry.db")

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # App settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
