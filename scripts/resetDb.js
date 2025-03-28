const { Pool } = require('pg');
const bcrypt = require('bcrypt');

const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'alpha_laundry',
  password: process.env.DB_PASSWORD || 'postgres',
  port: process.env.DB_PORT || 5432,
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