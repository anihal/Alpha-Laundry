#!/usr/bin/env python3
"""
Startup script for Alpha Laundry Management System API
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False, workers: int = 1):
    """
    Run the FastAPI server using uvicorn

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload (for development)
        workers: Number of worker processes
    """
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info",
    )


def init_database():
    """
    Initialize database tables
    """
    print("🔧 Initializing database...")
    from api.database import create_tables, check_database_connection

    if not check_database_connection():
        print("❌ Cannot connect to database. Please check your configuration.")
        sys.exit(1)

    create_tables()
    print("✅ Database initialized successfully")


def seed_database():
    """
    Seed database with sample data
    """
    print("🌱 Seeding database with sample data...")
    from api.database import SessionLocal, User, Admin, LaundryJob
    from api.utils import hash_password
    from datetime import datetime, timedelta

    db = SessionLocal()

    try:
        # Create admin user
        admin = Admin(
            username="admin",
            password_hash=hash_password("admin123"),
            email="admin@alphalaundry.com",
            role="admin",
        )
        db.add(admin)

        # Create sample students
        students = [
            User(student_id="STU001", name="Nihal", email="nihal@example.com", remaining_quota=30),
            User(student_id="STU002", name="Kapish", email="kapish@example.com", remaining_quota=25),
            User(student_id="STU003", name="Pavan", email="pavan@example.com", remaining_quota=28),
            User(student_id="STU004", name="Steve", email="steve@example.com", remaining_quota=30),
        ]

        for student in students:
            db.add(student)

        db.commit()

        # Create sample laundry jobs
        jobs = [
            LaundryJob(
                user_id=1,
                student_id="STU001",
                num_clothes=5,
                status="submitted",
                submission_date=datetime.utcnow() - timedelta(days=2),
            ),
            LaundryJob(
                user_id=1,
                student_id="STU001",
                num_clothes=3,
                status="completed",
                submission_date=datetime.utcnow() - timedelta(days=5),
                completed_date=datetime.utcnow() - timedelta(days=4),
            ),
            LaundryJob(
                user_id=2,
                student_id="STU002",
                num_clothes=5,
                status="processing",
                submission_date=datetime.utcnow() - timedelta(days=1),
                started_date=datetime.utcnow() - timedelta(hours=12),
            ),
        ]

        for job in jobs:
            db.add(job)

        db.commit()
        print("✅ Database seeded successfully")
        print("\n📝 Sample credentials:")
        print("   Admin: username=admin, password=admin123")
        print("   Student: student_id=STU001 (no password required)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)
    finally:
        db.close()


def main():
    """
    Main entry point
    """
    parser = argparse.ArgumentParser(description="Alpha Laundry Management System API")
    parser.add_argument("command", choices=["run", "init-db", "seed-db"], help="Command to execute")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")

    args = parser.parse_args()

    if args.command == "run":
        run_server(
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
        )
    elif args.command == "init-db":
        init_database()
    elif args.command == "seed-db":
        seed_database()


if __name__ == "__main__":
    main()
