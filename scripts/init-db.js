#!/usr/bin/env node

/**
 * Database Initialization Script
 *
 * This script initializes the database with:
 * 1. Schema (tables, indexes, constraints)
 * 2. Optional seed data for development
 *
 * Usage:
 *   node scripts/init-db.js              # Schema only
 *   node scripts/init-db.js --seed       # Schema + seed data
 */

require('dotenv').config({ path: require('path').join(__dirname, '../backend/.env') });
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

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

async function initializeDatabase() {
  const client = await pool.connect();

  try {
    console.log('🔧 Initializing Alpha Laundry database...\n');

    // Run schema
    console.log('📋 Creating tables and indexes...');
    const schemaPath = path.join(__dirname, '../backend/database/schema.sql');
    const schemaContent = fs.readFileSync(schemaPath, 'utf8');
    await client.query(schemaContent);
    console.log('✓ Schema created successfully\n');

    // Check if seed flag is present
    const shouldSeed = process.argv.includes('--seed');

    if (shouldSeed) {
      console.log('🌱 Seeding development data...');
      const seedPath = path.join(__dirname, '../backend/database/seeds/dev-data.sql');
      const seedContent = fs.readFileSync(seedPath, 'utf8');
      await client.query(seedContent);
      console.log('✓ Seed data inserted successfully\n');
      console.log('📝 Default credentials:');
      console.log('   Admin - username: admin, password: admin123');
      console.log('   Students - IDs: STU001, STU002, STU003, STU004, STUDENT001\n');
    }

    console.log('✅ Database initialization complete!');
  } catch (error) {
    console.error('❌ Error initializing database:', error.message);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

initializeDatabase();
