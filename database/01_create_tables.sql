-- Create students table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    remaining_quota INTEGER DEFAULT 30
);

-- Create laundry_requests table
CREATE TABLE laundry_requests (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) REFERENCES students(student_id),
    num_clothes INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'submitted',
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create admins table
CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_laundry_requests_student_id ON laundry_requests(student_id);
CREATE INDEX idx_laundry_requests_status ON laundry_requests(status);
CREATE INDEX idx_students_student_id ON students(student_id); 