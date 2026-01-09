"""
Authentication routes for login, registration, and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db, User, Admin
from ..schemas import (
    LoginRequest,
    LoginResponse,
    RegisterAdminRequest,
    RegisterAdminResponse,
    VerifyTokenResponse,
)
from ..utils import (
    hash_password,
    verify_password,
    create_access_token,
    extract_user_from_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =====================================================
# LOGIN ENDPOINT
# =====================================================


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token

    - **username**: Student ID (e.g., STU001) or Admin username
    - **password**: User password
    - **user_type**: Either 'student' or 'admin'

    Returns:
        LoginResponse: JWT access token and user information
    """

    if credentials.user_type == "student":
        # Student login - find by student_id
        user = db.query(User).filter(User.student_id == credentials.username).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid student ID or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # Check password if student has password_hash set
        if user.password_hash:
            if not verify_password(credentials.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid student ID or password",
                )
        # Otherwise, allow login with just student_id (legacy behavior)

        # Create access token
        access_token = create_access_token(
            data={
                "user_id": user.id,
                "username": user.student_id,
                "user_type": "student",
            }
        )

        return LoginResponse(
            access_token=access_token,
            user_type="student",
            user_id=user.id,
            username=user.student_id,
        )

    elif credentials.user_type == "admin":
        # Admin login - find by username
        admin = (
            db.query(Admin).filter(Admin.username == credentials.username).first()
        )

        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # Verify password
        if not verify_password(credentials.password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Create access token
        access_token = create_access_token(
            data={
                "user_id": admin.id,
                "username": admin.username,
                "user_type": "admin",
            }
        )

        return LoginResponse(
            access_token=access_token,
            user_type="admin",
            user_id=admin.id,
            username=admin.username,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user type. Must be 'student' or 'admin'",
        )


# =====================================================
# REGISTER ADMIN ENDPOINT
# =====================================================


@router.post("/register", response_model=RegisterAdminResponse)
def register_admin(
    admin_data: RegisterAdminRequest, db: Session = Depends(get_db)
):
    """
    Register a new admin user

    - **username**: Admin username (min 3 characters)
    - **password**: Admin password (min 8 characters)
    - **email**: Optional admin email

    Returns:
        RegisterAdminResponse: Created admin information
    """

    # Check if username already exists
    existing_admin = (
        db.query(Admin).filter(Admin.username == admin_data.username).first()
    )
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{admin_data.username}' already exists",
        )

    # Check if email already exists (if provided)
    if admin_data.email:
        existing_email = (
            db.query(Admin).filter(Admin.email == admin_data.email).first()
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{admin_data.email}' already registered",
            )

    # Hash the password
    hashed_password = hash_password(admin_data.password)

    # Create new admin
    new_admin = Admin(
        username=admin_data.username,
        email=admin_data.email,
        password_hash=hashed_password,
        role="admin",
        is_active=True,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return RegisterAdminResponse(
        message="Admin registered successfully",
        admin_id=new_admin.id,
        username=new_admin.username,
    )


# =====================================================
# VERIFY TOKEN ENDPOINT
# =====================================================


@router.get("/verify", response_model=VerifyTokenResponse)
def verify_token(token: str):
    """
    Verify JWT token and return user information

    - **token**: JWT access token

    Returns:
        VerifyTokenResponse: Token validity and user information
    """

    user_info = extract_user_from_token(token)

    if not user_info or not user_info.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return VerifyTokenResponse(
        valid=True,
        user_id=user_info["user_id"],
        username=user_info["username"],
        user_type=user_info["user_type"],
    )


# =====================================================
# LOGOUT ENDPOINT (Optional - client-side token removal)
# =====================================================


@router.post("/logout")
def logout():
    """
    Logout endpoint (client should remove token)

    Note: Since JWT is stateless, actual logout is handled client-side
    by removing the token from storage
    """
    return {"success": True, "message": "Logged out successfully"}


# =====================================================
# EXPORTS
# =====================================================

__all__ = ["router"]
