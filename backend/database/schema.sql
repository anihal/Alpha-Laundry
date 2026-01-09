-- =============================================================================
-- ALPHA LAUNDRY DATABASE SCHEMA
-- =============================================================================
-- This file contains the database schema for the Alpha Laundry application
-- Run this file to create all necessary tables and indexes
-- =============================================================================

-- Create students table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    remaining_quota INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create laundry_requests table
CREATE TABLE IF NOT EXISTS laundry_requests (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) REFERENCES students(student_id) ON DELETE CASCADE,
    num_clothes INTEGER NOT NULL CHECK (num_clothes > 0),
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN ('submitted', 'processing', 'completed', 'cancelled')),
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_date TIMESTAMP
);

-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_laundry_requests_student_id ON laundry_requests(student_id);
CREATE INDEX IF NOT EXISTS idx_laundry_requests_status ON laundry_requests(status);
CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);

-- Add comments to tables for documentation
COMMENT ON TABLE students IS 'Stores student information and laundry quota';
COMMENT ON TABLE laundry_requests IS 'Tracks all laundry service requests';
COMMENT ON TABLE admins IS 'Stores admin user credentials';

COMMENT ON COLUMN students.remaining_quota IS 'Number of free clothes remaining (default: 30)';
COMMENT ON COLUMN laundry_requests.status IS 'Request status: submitted, processing, completed, or cancelled';
