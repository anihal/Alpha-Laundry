-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS students (
  id SERIAL PRIMARY KEY,
  student_id VARCHAR(20) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  remaining_quota INTEGER DEFAULT 30
);

CREATE TABLE IF NOT EXISTS laundry_requests (
  id SERIAL PRIMARY KEY,
  student_id VARCHAR(20) REFERENCES students(student_id),
  num_clothes INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'submitted',
  submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL
);

-- Clear existing data
TRUNCATE TABLE laundry_requests CASCADE;
TRUNCATE TABLE students CASCADE;
TRUNCATE TABLE admins CASCADE;

-- Insert admin user
INSERT INTO admins (username, password_hash) 
VALUES ('admin', '$2b$10$AZqMm6qUwOOf6SX/maTfIOUml6LbGKVXaPe5hkct.XtmxxHXMcJP.');

-- Insert students
INSERT INTO students (student_id, name, remaining_quota) VALUES
('STU001', 'Nihal', 30),
('STU002', 'Kapish', 30),
('STU003', 'Pavan', 30),
('STU004', 'Steve', 30);

-- Insert sample laundry requests
INSERT INTO laundry_requests (student_id, num_clothes, status, submission_date) VALUES
('STU001', 5, 'submitted', NOW() - INTERVAL '2 days'),
('STU001', 3, 'completed', NOW() - INTERVAL '5 days'),
('STU002', 4, 'processing', NOW() - INTERVAL '1 day'),
('STU002', 6, 'completed', NOW() - INTERVAL '6 days'),
('STU003', 8, 'submitted', NOW() - INTERVAL '12 hours'),
('STU003', 2, 'completed', NOW() - INTERVAL '4 days'),
('STU004', 5, 'processing', NOW() - INTERVAL '1 day'),
('STU004', 4, 'submitted', NOW() - INTERVAL '3 hours'); 