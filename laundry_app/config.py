"""
Configuration module - loads environment variables
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Placeholder values that must never be accepted as a real signing key. Flask
# signs session cookies with SECRET_KEY, so anything guessable (an empty value
# or the literal that used to ship in this file) lets anyone forge an admin
# session. These are treated as "unset" -- see app.resolve_secret_key.
INSECURE_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "your-secret-key",
        "your-super-secret-key-change-in-production",
    }
)


class Config:
    """Application configuration"""

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///laundry.db")

    # Security
    #
    # No default: Flask signs session cookies with this key, so falling back to
    # a value baked into public source code would let anyone forge a session
    # (including an admin one). When it is unset ``os.getenv`` returns ``None``;
    # ``app.resolve_secret_key`` then fails closed at startup unless DEBUG is on.
    SECRET_KEY = os.getenv("SECRET_KEY")

    # App settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
