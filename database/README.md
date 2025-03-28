# Database Setup

This directory contains the database migrations and setup scripts for the Alpha Laundry Management System.

## Prerequisites

- PostgreSQL 12 or higher
- psql command-line tool

## Setup Instructions

1. Create the database:
   ```bash
   createdb alpha_laundry
   ```

2. Run the migrations:
   ```bash
   psql -d alpha_laundry -f 01_create_tables.sql
   ```

## Database Schema

The database consists of three main tables:

1. `students` - Stores student information and their laundry quota
2. `laundry_requests` - Tracks all laundry requests
3. `admins` - Stores admin user credentials

## Indexes

The following indexes have been created for optimal query performance:

- `idx_laundry_requests_student_id` - For quick lookups of requests by student
- `idx_laundry_requests_status` - For filtering requests by status
- `idx_students_student_id` - For quick student lookups

## Backup and Restore

To backup the database:
```bash
pg_dump alpha_laundry > backup.sql
```

To restore from backup:
```bash
psql alpha_laundry < backup.sql
``` 