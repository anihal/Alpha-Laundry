# Alpha Laundry Management System - Python Backend API

A modern, production-ready RESTful API built with FastAPI, SQLAlchemy, and PostgreSQL for managing laundry services, user subscriptions, and job tracking.

## 🎯 Features

### ✅ Database Schema
- **Properly designed schema** with primary keys, foreign keys, and indexes
- **Users table** with quota tracking and subscription management
- **Subscriptions table** for managing different service plans
- **Laundry Jobs table** with status tracking and timestamps
- **Admins table** with role-based access control
- **Audit logging** capabilities
- **Database triggers** for automatic timestamp updates
- **Check constraints** for data validation

### 🔐 Security
- **Password hashing** using bcrypt (12 rounds)
- **JWT authentication** for secure API access
- **Role-based access control** (Student vs Admin)
- **Password strength validation**
- **SQL injection protection** via SQLAlchemy ORM

### 📊 API Features
- **RESTful endpoints** for all operations
- **Pydantic validation** for all inputs
- **Proper error handling** with detailed error messages
- **CORS support** for frontend integration
- **Pagination** for list endpoints
- **Filtering and sorting** capabilities
- **Transaction handling** for data integrity

### 🎨 Code Quality
- **Type hints** throughout the codebase
- **Comprehensive documentation** with docstrings
- **Modular architecture** with clean separation of concerns
- **Configuration management** via environment variables
- **Database connection pooling** for performance

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- pip or poetry

### Installation

1. **Install dependencies:**
```bash
cd api
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. **Set up the database:**

Run the improved schema:
```bash
psql -U postgres -d alpha_laundry -f ../database/02_improved_schema.sql
```

Or use the SQLAlchemy models (they will auto-create on startup):
```python
from api.database import create_tables
create_tables()
```

4. **Run the application:**
```bash
# Development mode with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

5. **Access the API:**
- API Documentation: http://localhost:8000/api/docs
- Alternative Docs: http://localhost:8000/api/redoc
- Health Check: http://localhost:8000/health

## 📚 API Endpoints

### Authentication
- `POST /api/auth/login` - Login (student or admin)
- `POST /api/auth/register` - Register new admin
- `GET /api/auth/verify` - Verify JWT token
- `POST /api/auth/logout` - Logout (client-side)

### Student Endpoints
- `GET /api/student/dashboard` - Get student dashboard
- `POST /api/student/submit` - Submit laundry request (with quota decrement)
- `GET /api/student/history` - Get laundry history (paginated)
- `GET /api/student/job/{job_id}` - Get specific job details

### Admin Endpoints
- `GET /api/admin/dashboard` - Get admin dashboard
- `PATCH /api/admin/update-status` - Update job status
- `GET /api/admin/analytics` - Get analytics and statistics
- `GET /api/admin/jobs` - Get all jobs with filters

## 🔧 Configuration

All configuration is managed via environment variables in `.env` file:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alpha_laundry
DB_USER=postgres
DB_PASSWORD=your_password

# JWT
JWT_SECRET_KEY=your_secret_key_here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Server
HOST=0.0.0.0
PORT=8000
```

## 📊 Database Schema

### Users Table
- Primary key: `id` (SERIAL)
- Unique: `student_id`, `email`
- Constraints: `remaining_quota >= 0`, student_id format validation
- Indexes: student_id, email, is_active

### Laundry Jobs Table
- Primary key: `id` (SERIAL)
- Foreign key: `user_id` → users(id)
- Constraints: num_clothes (1-50), valid status, date validation
- Indexes: user_id, student_id, status, submission_date

### Subscriptions Table
- Primary key: `id` (SERIAL)
- Foreign key: `user_id` → users(id) ON DELETE CASCADE
- Constraints: valid plan_type, quota_limit > 0, date range validation
- Indexes: user_id, is_active, dates

### Admins Table
- Primary key: `id` (SERIAL)
- Unique: `username`, `email`
- Constraints: username length >= 3, valid role
- Indexes: username, is_active

## 🎯 Key Features Implementation

### Remaining Clothes Logic
The `/api/student/submit` endpoint implements **atomic transaction handling** for quota management:

```python
# Transaction ensures atomicity
db.begin_nested()

# Create job
new_job = LaundryJob(...)
db.add(new_job)

# Decrement quota atomically
student.remaining_quota -= num_clothes

# Commit both operations together
db.commit()
```

### Password Hashing
All passwords are hashed using bcrypt with 12 rounds:

```python
from api.utils import hash_password, verify_password

hashed = hash_password("user_password")
is_valid = verify_password("user_password", hashed)
```

### JWT Authentication
Secure token-based authentication:

```python
from api.utils import create_access_token

token = create_access_token({
    "user_id": user.id,
    "username": user.student_id,
    "user_type": "student"
})
```

## 🧪 Testing

Example API calls:

### Login as Student
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "STU001",
    "password": "password",
    "user_type": "student"
  }'
```

### Submit Laundry Request
```bash
curl -X POST http://localhost:8000/api/student/submit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "num_clothes": 5,
    "notes": "Urgent cleaning needed",
    "priority": "high"
  }'
```

### Admin Update Status
```bash
curl -X PATCH http://localhost:8000/api/admin/update-status \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": 1,
    "status": "processing"
  }'
```

## 📁 Project Structure

```
api/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application entry point
├── config.py            # Configuration and settings
├── database.py          # SQLAlchemy models and DB setup
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── README.md            # This file
├── routes/              # API route handlers
│   ├── __init__.py
│   ├── auth.py          # Authentication endpoints
│   ├── student.py       # Student endpoints
│   └── admin.py         # Admin endpoints
├── schemas/             # Pydantic validation schemas
│   ├── __init__.py
│   ├── base.py          # Base schemas
│   ├── user.py          # User schemas
│   ├── admin.py         # Admin schemas
│   ├── laundry_job.py   # Laundry job schemas
│   ├── subscription.py  # Subscription schemas
│   └── auth.py          # Auth schemas
└── utils/               # Utility functions
    ├── __init__.py
    └── security.py      # Password hashing, JWT, etc.
```

## 🔒 Security Best Practices

1. ✅ **Never commit `.env` file** - Use `.env.example` as template
2. ✅ **Use strong JWT secret** - Generate with `openssl rand -hex 32`
3. ✅ **Enable HTTPS in production** - Use reverse proxy (nginx)
4. ✅ **Validate all inputs** - Pydantic schemas enforce validation
5. ✅ **Use connection pooling** - Configured in database.py
6. ✅ **Hash all passwords** - bcrypt with 12 rounds
7. ✅ **Implement rate limiting** - Optional, can be added

## 🚀 Deployment

### Production Deployment

1. **Set production environment:**
```bash
export NODE_ENV=production
export DEBUG=False
```

2. **Run with Gunicorn:**
```bash
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

3. **Or use Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📈 Performance

- **Connection pooling**: 10 connections, 20 max overflow
- **Query optimization**: Indexed columns for common queries
- **Pagination**: Default 20 items per page, max 100
- **Caching**: Settings cached with `@lru_cache`

## 🤝 Contributing

1. Follow PEP 8 style guide
2. Add type hints to all functions
3. Write docstrings for public APIs
4. Update tests for new features

## 📝 License

Copyright © 2024 Alpha Laundry Team

---

**Built with ❤️ using FastAPI, SQLAlchemy, and PostgreSQL**
