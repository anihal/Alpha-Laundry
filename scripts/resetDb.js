require('dotenv').config({ path: require('path').join(__dirname, '../backend/.env') });
const { Pool } = require('pg');
const bcrypt = require('bcrypt');

// Validate required environment variables
const requiredEnvVars = ['DB_USER', 'DB_HOST', 'DB_NAME', 'DB_PASSWORD'];
const missing = requiredEnvVars.filter(varName => !process.env[varName]);

if (missing.length > 0) {
  console.error(`❌ Missing required environment variables: ${missing.join(', ')}`);
  console.error('Please ensure backend/.env file exists and contains all required values.');
  process.exit(1);
}

const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: parseInt(process.env.DB_PORT || '5432', 10),
});

async function resetDatabase() {
  const client = await pool.connect();
  try {
    // Start transaction
    await client.query('BEGIN');

    // Clear all tables
    await client.query('TRUNCATE TABLE laundry_requests CASCADE');
    await client.query('TRUNCATE TABLE students CASCADE');
    await client.query('TRUNCATE TABLE admins CASCADE');

    // Insert test data
    await client.query(`
      INSERT INTO students (student_id, name, remaining_quota)
      VALUES ('STUDENT001', 'Test Student', 30)
    `);

    // Hash the admin password
    const hashedPassword = await bcrypt.hash('admin123', 10);
    await client.query(`
      INSERT INTO admins (username, password_hash)
      VALUES ('admin', $1)
    `, [hashedPassword]);

    // Commit transaction
    await client.query('COMMIT');
    console.log('Database reset successful');
  } catch (error) {
    // Rollback transaction on error
    await client.query('ROLLBACK');
    console.error('Error resetting database:', error);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

resetDatabase(); 