"""
Security utilities for password hashing and JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt

from ..config import settings


# =====================================================
# PASSWORD HASHING
# =====================================================

# Create password hashing context using bcrypt
pwd_context = CryptContext(
    schemes=settings.PWD_CONTEXT_SCHEMES,
    deprecated="auto",
    bcrypt__rounds=settings.PWD_BCRYPT_ROUNDS,
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt

    Args:
        password: Plain text password

    Returns:
        str: Hashed password

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> print(hashed)
        $2b$12$...
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        bool: True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_strength(password: str) -> Dict[str, Any]:
    """
    Analyze password strength

    Args:
        password: Password to analyze

    Returns:
        dict: Password strength analysis

    Example:
        >>> analysis = get_password_strength("MyP@ssw0rd123")
        >>> print(analysis)
        {'length': 13, 'has_upper': True, 'has_lower': True, ...}
    """
    return {
        "length": len(password),
        "has_upper": any(c.isupper() for c in password),
        "has_lower": any(c.islower() for c in password),
        "has_digit": any(c.isdigit() for c in password),
        "has_special": any(not c.isalnum() for c in password),
        "is_strong": (
            len(password) >= 8
            and any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
        ),
    }


# =====================================================
# JWT TOKEN MANAGEMENT
# =====================================================


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token (e.g., user_id, username)
        expires_delta: Optional custom expiration time

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "student001"})
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token

    Args:
        token: JWT token to decode

    Returns:
        dict: Decoded token data if valid, None otherwise

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> decoded = decode_access_token(token)
        >>> print(decoded["user_id"])
        1
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> bool:
    """
    Verify if a JWT token is valid

    Args:
        token: JWT token to verify

    Returns:
        bool: True if token is valid, False otherwise

    Example:
        >>> token = create_access_token({"user_id": 1})
        >>> verify_token(token)
        True
    """
    payload = decode_access_token(token)
    return payload is not None


def extract_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from JWT token

    Args:
        token: JWT token

    Returns:
        dict: User information if valid, None otherwise

    Example:
        >>> token = create_access_token({"user_id": 1, "username": "STU001"})
        >>> user_info = extract_user_from_token(token)
        >>> print(user_info["username"])
        STU001
    """
    payload = decode_access_token(token)
    if payload:
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "user_type": payload.get("user_type"),
        }
    return None


# =====================================================
# UTILITY FUNCTIONS
# =====================================================


def generate_temporary_password(length: int = 12) -> str:
    """
    Generate a secure temporary password

    Args:
        length: Password length (default: 12)

    Returns:
        str: Generated password

    Example:
        >>> password = generate_temporary_password()
        >>> print(len(password))
        12
    """
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(length))

    # Ensure password has at least one of each required character type
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.islower() for c in password):
        password = password[:-2] + secrets.choice(string.ascii_lowercase) + password[-1]
    if not any(c.isdigit() for c in password):
        password = password[:-3] + secrets.choice(string.digits) + password[-2:]

    return password


def is_password_compromised(password: str) -> bool:
    """
    Check if password is in common password list (basic implementation)

    Args:
        password: Password to check

    Returns:
        bool: True if password is common/weak

    Example:
        >>> is_password_compromised("password123")
        True
        >>> is_password_compromised("x9$mK2pL@qR5")
        False
    """
    common_passwords = {
        "password",
        "123456",
        "password123",
        "admin",
        "admin123",
        "letmein",
        "welcome",
        "monkey",
        "1234567890",
        "qwerty",
    }
    return password.lower() in common_passwords


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "pwd_context",
    "hash_password",
    "verify_password",
    "get_password_strength",
    "create_access_token",
    "decode_access_token",
    "verify_token",
    "extract_user_from_token",
    "generate_temporary_password",
    "is_password_compromised",
]
