"""
Database models and connection management for Alpha Laundry Management System
Uses SQLAlchemy ORM for type-safe database operations
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

from .config import settings

# Create declarative base
Base = declarative_base()


# =====================================================
# DATABASE ENGINE SETUP
# =====================================================

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =====================================================
# DATABASE MODELS
# =====================================================


class User(Base):
    """
    User/Student model for tracking laundry service users
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))  # Optional for student login
    remaining_quota = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    laundry_jobs = relationship(
        "LaundryJob", back_populates="user", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint("remaining_quota >= 0", name="chk_remaining_quota"),
        CheckConstraint(
            "student_id ~ '^STU[0-9]{3,}$'", name="chk_student_id_format"
        ),
    )

    def __repr__(self):
        return f"<User(id={self.id}, student_id='{self.student_id}', name='{self.name}')>"


class Subscription(Base):
    """
    Subscription model for managing user subscription plans
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String(50), default="basic", nullable=False)
    quota_limit = Column(Integer, default=30, nullable=False)
    start_date = Column(Date, default=datetime.utcnow().date, nullable=False)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('basic', 'premium', 'unlimited')", name="chk_plan_type"
        ),
        CheckConstraint("quota_limit > 0", name="chk_quota_limit"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="chk_date_range"
        ),
        Index("idx_subscriptions_user_id", "user_id"),
        Index("idx_subscriptions_active", "is_active"),
        Index("idx_subscriptions_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan='{self.plan_type}')>"


class LaundryJob(Base):
    """
    Laundry Job model for tracking laundry requests from submission to completion
    """

    __tablename__ = "laundry_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", onupdate="CASCADE"), nullable=False)
    student_id = Column(String(20), nullable=False, index=True)  # Denormalized
    num_clothes = Column(Integer, nullable=False)
    status = Column(String(20), default="submitted", nullable=False, index=True)
    priority = Column(String(10), default="normal")
    notes = Column(Text)
    submission_date = Column(DateTime, default=datetime.utcnow, index=True)
    started_date = Column(DateTime)
    completed_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="laundry_jobs")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "num_clothes > 0 AND num_clothes <= 50", name="chk_num_clothes"
        ),
        CheckConstraint(
            "status IN ('submitted', 'processing', 'completed', 'cancelled')",
            name="chk_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')", name="chk_priority"
        ),
        CheckConstraint(
            "(started_date IS NULL OR started_date >= submission_date) AND "
            "(completed_date IS NULL OR completed_date >= submission_date)",
            name="chk_dates",
        ),
        Index("idx_laundry_jobs_user_id", "user_id"),
        Index("idx_laundry_jobs_student_id", "student_id"),
        Index("idx_laundry_jobs_status", "status"),
        Index("idx_laundry_jobs_submission_date", "submission_date"),
        Index("idx_laundry_jobs_status_date", "status", "submission_date"),
    )

    def __repr__(self):
        return f"<LaundryJob(id={self.id}, student_id='{self.student_id}', status='{self.status}')>"


class Admin(Base):
    """
    Admin user model for system administration
    """

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Table constraints
    __table_args__ = (
        CheckConstraint("LENGTH(username) >= 3", name="chk_username_length"),
        CheckConstraint(
            "role IN ('admin', 'super_admin', 'operator')", name="chk_role"
        ),
    )

    def __repr__(self):
        return f"<Admin(id={self.id}, username='{self.username}', role='{self.role}')>"


# =====================================================
# DATABASE DEPENDENCY
# =====================================================


def get_db() -> Session:
    """
    FastAPI dependency for database sessions

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions

    Example:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =====================================================
# DATABASE INITIALIZATION
# =====================================================


def create_tables():
    """
    Create all database tables
    Only call this in development or during initial setup
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def drop_tables():
    """
    Drop all database tables
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
    print("✓ Database tables dropped")


def reset_database():
    """
    Reset database by dropping and recreating all tables
    WARNING: This will delete all data!
    """
    drop_tables()
    create_tables()
    print("✓ Database reset completed")


# =====================================================
# UTILITY FUNCTIONS
# =====================================================


def check_database_connection() -> bool:
    """
    Check if database connection is working

    Returns:
        bool: True if connection is successful
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information

    Returns:
        dict: Database configuration details
    """
    return {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "database": settings.DB_NAME,
        "user": settings.DB_USER,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
    }


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "User",
    "Subscription",
    "LaundryJob",
    "Admin",
    "get_db",
    "get_db_context",
    "create_tables",
    "drop_tables",
    "reset_database",
    "check_database_connection",
    "get_database_info",
]
