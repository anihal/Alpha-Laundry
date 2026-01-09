# Database Setup

This directory contains the database schema and seed data for the Alpha Laundry Management System.

## Directory Structure

```
backend/database/
├── schema.sql          # Database schema (tables, indexes, constraints)
├── seeds/
│   └── dev-data.sql   # Development seed data
└── README.md          # This file
```

## Prerequisites

- PostgreSQL 12 or higher
- psql command-line tool or pg_admin

## Quick Start

### Option 1: Using the initialization script (Recommended)

```bash
# 1. Ensure backend/.env file exists with database credentials
cp backend/.env.example backend/.env
# Edit backend/.env with your database configuration

# 2. Create the database
createdb alpha_laundry

# 3. Initialize schema only
node scripts/init-db.js

# 4. Or initialize with seed data for development
node scripts/init-db.js --seed
```

### Option 2: Manual setup with psql

```bash
# 1. Create the database
createdb alpha_laundry

# 2. Run schema
psql -d alpha_laundry -f backend/database/schema.sql

# 3. (Optional) Add seed data for development
psql -d alpha_laundry -f backend/database/seeds/dev-data.sql
```

## Database Schema

The database consists of three main tables:

### 1. `students`
Stores student information and their laundry quota.

| Column           | Type         | Description                      |
|------------------|--------------|----------------------------------|
| id               | SERIAL       | Primary key                      |
| student_id       | VARCHAR(20)  | Unique student identifier        |
| name             | VARCHAR(100) | Student name                     |
| remaining_quota  | INTEGER      | Free clothes remaining (max 30)  |
| created_at       | TIMESTAMP    | Record creation timestamp        |

### 2. `laundry_requests`
Tracks all laundry service requests.

| Column          | Type         | Description                           |
|-----------------|--------------|---------------------------------------|
| id              | SERIAL       | Primary key                           |
| student_id      | VARCHAR(20)  | Foreign key to students               |
| num_clothes     | INTEGER      | Number of clothes in request          |
| status          | VARCHAR(20)  | submitted, processing, completed, cancelled |
| submission_date | TIMESTAMP    | When request was submitted            |
| completed_date  | TIMESTAMP    | When request was completed            |

### 3. `admins`
Stores admin user credentials.

| Column        | Type         | Description                  |
|---------------|--------------|------------------------------|
| id            | SERIAL       | Primary key                  |
| username      | VARCHAR(50)  | Unique admin username        |
| password_hash | VARCHAR(255) | Bcrypt hashed password       |
| created_at    | TIMESTAMP    | Record creation timestamp    |

## Indexes

The following indexes are created for optimal query performance:

- `idx_laundry_requests_student_id` - Quick lookups of requests by student
- `idx_laundry_requests_status` - Filter requests by status
- `idx_students_student_id` - Quick student lookups
- `idx_admins_username` - Admin authentication

## Development Seed Data

When using `--seed` flag, the following test data is loaded:

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Test Students:**
- STU001, STU002, STU003, STU004, STUDENT001

## Database Operations

### Reset Database

To completely reset and reseed the database:

```bash
node scripts/resetDb.js
```

**Warning:** This will delete all existing data!

### Backup and Restore

To backup the database:
```bash
pg_dump alpha_laundry > backup_$(date +%Y%m%d_%H%M%S).sql
```

To restore from backup:
```bash
psql alpha_laundry < backup_YYYYMMDD_HHMMSS.sql
```

### View Current Schema

```bash
psql -d alpha_laundry -c "\dt"  # List tables
psql -d alpha_laundry -c "\di"  # List indexes
psql -d alpha_laundry -c "\d students"  # Describe table
```

## Troubleshooting

### Connection Issues

If you encounter connection errors:
1. Verify PostgreSQL is running: `pg_isready`
2. Check credentials in `backend/.env`
3. Ensure database exists: `psql -l | grep alpha_laundry`

### Permission Issues

If you get permission errors:
```bash
# Grant privileges to your database user
psql -d alpha_laundry -c "GRANT ALL PRIVILEGES ON DATABASE alpha_laundry TO your_user;"
```

## Production Considerations

For production deployments:

1. **Never use seed data** - Use init-db.js without --seed flag
2. **Strong passwords** - Create admin accounts with strong passwords
3. **Regular backups** - Set up automated database backups
4. **Connection pooling** - Ensure proper pool configuration
5. **SSL/TLS** - Enable SSL for database connections
