require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const app = express();
const port = process.env.PORT || 3001;

// Database configuration
const pool = new Pool({
  user: 'postgres',
  password: 'password',
  host: 'localhost',
  port: 5432,
  database: 'alpha_laundry'
});

// Middleware
app.use(cors());
app.use(express.json());

// Authentication middleware
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ message: 'No token provided' });
  }

  jwt.verify(token, 'your_jwt_secret_key', (err, user) => {
    if (err) {
      return res.status(403).json({ message: 'Invalid token' });
    }
    req.user = user;
    next();
  });
};

// Test route
app.get('/', (req, res) => {
  res.json({ message: 'Welcome to Alpha Laundry API' });
});

// Test database connection
app.get('/api/test-db', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW()');
    res.json({ success: true, timestamp: result.rows[0].now });
  } catch (error) {
    console.error('Database connection error:', error);
    res.status(500).json({ success: false, error: 'Database connection failed' });
  }
});

// Login endpoint
app.post('/api/auth/login', async (req, res) => {
  console.log('Login request received:', req.body);
  const { username, password, role } = req.body;

  try {
    let user;
    if (role === 'student') {
      console.log('Attempting student login with ID:', username);
      const result = await pool.query(
        'SELECT * FROM students WHERE student_id = $1',
        [username]
      );
      console.log('Student query result:', result.rows);
      if (result.rows.length > 0) {
        user = { ...result.rows[0], role: 'student' };
      } else {
        return res.status(401).json({ message: 'Invalid student ID' });
      }
    } else {
      console.log('Attempting admin login with username:', username);
      const result = await pool.query(
        'SELECT * FROM admins WHERE username = $1',
        [username]
      );
      console.log('Admin query result:', result.rows);
      if (result.rows.length > 0) {
        const admin = result.rows[0];
        const validPassword = await bcrypt.compare(password, admin.password_hash);
        console.log('Password validation result:', validPassword);
        if (!validPassword) {
          return res.status(401).json({ message: 'Invalid password' });
        }
        user = { ...admin, role: 'admin' };
      } else {
        return res.status(401).json({ message: 'Invalid username' });
      }
    }

    // Generate JWT token
    const token = jwt.sign(
      { 
        id: user.id, 
        username: role === 'student' ? user.student_id : user.username,
        role: user.role 
      },
      'your_jwt_secret_key',
      { expiresIn: '24h' }
    );

    console.log('Login successful, sending response');
    res.json({
      token,
      user: {
        id: user.id,
        username: role === 'student' ? user.student_id : user.username,
        role: user.role,
        name: user.name
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Admin Routes
app.get('/api/admin/dashboard', authenticateToken, async (req, res) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({ message: 'Access denied' });
  }

  try {
    // Get all laundry requests with student information
    const result = await pool.query(`
      SELECT lr.*, s.name as student_name, s.remaining_quota
      FROM laundry_requests lr
      JOIN students s ON lr.student_id = s.student_id
      ORDER BY lr.submission_date DESC
    `);

    res.json({
      requests: result.rows,
      totalRequests: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching admin dashboard:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Update request status endpoint
app.patch('/api/admin/requests/:id', authenticateToken, async (req, res) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({ message: 'Access denied' });
  }

  const { id } = req.params;
  const { status } = req.body;

  try {
    const result = await pool.query(
      'UPDATE laundry_requests SET status = $1 WHERE id = $2 RETURNING *',
      [status, id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Request not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating request:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Get admin analytics
app.get('/api/admin/analytics', authenticateToken, async (req, res) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({ message: 'Access denied' });
  }

  try {
    // Get total requests by status
    const statusResult = await pool.query(`
      SELECT status, COUNT(*) as count
      FROM laundry_requests
      GROUP BY status
    `);

    // Get total students and average quota
    const studentStats = await pool.query(`
      SELECT 
        COUNT(*) as total_students,
        AVG(remaining_quota) as avg_quota
      FROM students
    `);

    res.json({
      requestsByStatus: statusResult.rows,
      studentStats: studentStats.rows[0]
    });
  } catch (error) {
    console.error('Error fetching analytics:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Start server
app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
}); 