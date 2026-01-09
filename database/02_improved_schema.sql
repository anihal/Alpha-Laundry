-- =====================================================
-- Alpha Laundry Management System - Improved Schema
-- =====================================================
-- This schema includes proper constraints, indexes,
-- timestamps, and validation for production use.
-- =====================================================

-- Enable UUID extension for better ID generation (optional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS TABLE (combines students and basic user info)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255), -- Optional: for student login
    remaining_quota INTEGER DEFAULT 30 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_remaining_quota CHECK (remaining_quota >= 0),
    CONSTRAINT chk_student_id_format CHECK (student_id ~ '^STU[0-9]{3,}$')
);

-- =====================================================
-- SUBSCRIPTIONS TABLE (for tracking subscription plans)
-- =====================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_type VARCHAR(50) NOT NULL DEFAULT 'basic', -- basic, premium, unlimited
    quota_limit INTEGER NOT NULL DEFAULT 30,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys
    CONSTRAINT fk_subscription_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Constraints
    CONSTRAINT chk_plan_type CHECK (plan_type IN ('basic', 'premium', 'unlimited')),
    CONSTRAINT chk_quota_limit CHECK (quota_limit > 0),
    CONSTRAINT chk_date_range CHECK (end_date IS NULL OR end_date >= start_date)
);

-- =====================================================
-- LAUNDRY_JOBS TABLE (renamed from laundry_requests)
-- =====================================================
CREATE TABLE IF NOT EXISTS laundry_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    student_id VARCHAR(20) NOT NULL, -- Denormalized for faster queries
    num_clothes INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'submitted' NOT NULL,
    priority VARCHAR(10) DEFAULT 'normal',
    notes TEXT,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_date TIMESTAMP,
    completed_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys
    CONSTRAINT fk_laundry_job_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    -- Constraints
    CONSTRAINT chk_num_clothes CHECK (num_clothes > 0 AND num_clothes <= 50),
    CONSTRAINT chk_status CHECK (status IN ('submitted', 'processing', 'completed', 'cancelled')),
    CONSTRAINT chk_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    CONSTRAINT chk_dates CHECK (
        (started_date IS NULL OR started_date >= submission_date) AND
        (completed_date IS NULL OR completed_date >= submission_date)
    )
);

-- =====================================================
-- ADMINS TABLE (enhanced with roles)
-- =====================================================
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT chk_role CHECK (role IN ('admin', 'super_admin', 'operator'))
);

-- =====================================================
-- AUDIT_LOG TABLE (for tracking important changes)
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- =====================================================
-- INDEXES for optimized queries
-- =====================================================

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_student_id ON users(student_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Subscriptions table indexes
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_dates ON subscriptions(start_date, end_date);

-- Laundry jobs table indexes
CREATE INDEX IF NOT EXISTS idx_laundry_jobs_user_id ON laundry_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_laundry_jobs_student_id ON laundry_jobs(student_id);
CREATE INDEX IF NOT EXISTS idx_laundry_jobs_status ON laundry_jobs(status);
CREATE INDEX IF NOT EXISTS idx_laundry_jobs_submission_date ON laundry_jobs(submission_date DESC);
CREATE INDEX IF NOT EXISTS idx_laundry_jobs_status_date ON laundry_jobs(status, submission_date DESC);

-- Admins table indexes
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit_log(changed_at DESC);

-- =====================================================
-- FUNCTIONS for automatic timestamp updates
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS for automatic timestamp updates
-- =====================================================
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_laundry_jobs_updated_at ON laundry_jobs;
CREATE TRIGGER update_laundry_jobs_updated_at
    BEFORE UPDATE ON laundry_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_admins_updated_at ON admins;
CREATE TRIGGER update_admins_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- VIEWS for common queries
-- =====================================================

-- View: Active jobs with user information
CREATE OR REPLACE VIEW active_jobs_view AS
SELECT
    lj.id,
    lj.user_id,
    u.student_id,
    u.name AS student_name,
    lj.num_clothes,
    lj.status,
    lj.priority,
    lj.submission_date,
    lj.started_date,
    lj.completed_date,
    u.remaining_quota
FROM laundry_jobs lj
JOIN users u ON lj.user_id = u.id
WHERE lj.status IN ('submitted', 'processing')
ORDER BY lj.priority DESC, lj.submission_date ASC;

-- View: User subscription status
CREATE OR REPLACE VIEW user_subscription_status AS
SELECT
    u.id AS user_id,
    u.student_id,
    u.name,
    u.remaining_quota,
    s.plan_type,
    s.quota_limit,
    s.start_date,
    s.end_date,
    s.is_active AS subscription_active
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.is_active = TRUE;

-- =====================================================
-- COMMENTS for documentation
-- =====================================================
COMMENT ON TABLE users IS 'Stores user/student information and quota tracking';
COMMENT ON TABLE subscriptions IS 'Manages subscription plans and quota limits';
COMMENT ON TABLE laundry_jobs IS 'Tracks all laundry service requests from submission to completion';
COMMENT ON TABLE admins IS 'Stores admin user credentials and access control';
COMMENT ON TABLE audit_log IS 'Audit trail for tracking changes to critical tables';

COMMENT ON COLUMN users.remaining_quota IS 'Number of clothes remaining in current subscription period';
COMMENT ON COLUMN laundry_jobs.student_id IS 'Denormalized field for faster queries without joins';
COMMENT ON COLUMN laundry_jobs.status IS 'Job status: submitted, processing, completed, cancelled';
