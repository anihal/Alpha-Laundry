-- =============================================================================
-- ALPHA LAUNDRY - DEVELOPMENT SEED DATA
-- =============================================================================
-- This file contains sample data for local development and testing
-- WARNING: This will clear all existing data!
-- =============================================================================

-- Clear existing data (use with caution!)
TRUNCATE TABLE laundry_requests CASCADE;
TRUNCATE TABLE students CASCADE;
TRUNCATE TABLE admins CASCADE;

-- Insert test admin user
-- Default password: 'admin123' (hashed with bcrypt)
INSERT INTO admins (username, password_hash) VALUES
('admin', '$2b$10$AZqMm6qUwOOf6SX/maTfIOUml6LbGKVXaPe5hkct.XtmxxHXMcJP.');

-- Insert test students
INSERT INTO students (student_id, name, remaining_quota) VALUES
('STU001', 'Nihal', 30),
('STU002', 'Kapish', 30),
('STU003', 'Pavan', 30),
('STU004', 'Steve', 30),
('STUDENT001', 'Test Student', 25);

-- Insert sample laundry requests
INSERT INTO laundry_requests (student_id, num_clothes, status, submission_date) VALUES
('STU001', 5, 'submitted', NOW() - INTERVAL '2 days'),
('STU001', 3, 'completed', NOW() - INTERVAL '5 days'),
('STU002', 4, 'processing', NOW() - INTERVAL '1 day'),
('STU002', 6, 'completed', NOW() - INTERVAL '6 days'),
('STU003', 8, 'submitted', NOW() - INTERVAL '12 hours'),
('STU003', 2, 'completed', NOW() - INTERVAL '4 days'),
('STU004', 5, 'processing', NOW() - INTERVAL '1 day'),
('STU004', 4, 'submitted', NOW() - INTERVAL '3 hours'),
('STUDENT001', 5, 'completed', NOW() - INTERVAL '7 days');

-- =============================================================================
-- NOTES
-- =============================================================================
-- Default admin credentials for testing:
--   Username: admin
--   Password: admin123
--
-- Test student IDs: STU001, STU002, STU003, STU004, STUDENT001
-- =============================================================================
