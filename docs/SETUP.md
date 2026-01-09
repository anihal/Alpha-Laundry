# Alpha Laundry - Detailed Setup Guide

This guide provides comprehensive instructions for setting up the Alpha Laundry Management System for development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Node.js** (v16 or higher)
   ```bash
   node --version  # Should be >= 16.0.0
   npm --version   # Should be >= 8.0.0
   ```
   Download from: https://nodejs.org/

2. **PostgreSQL** (v12 or higher)
   ```bash
   psql --version  # Should be >= 12.0
   ```
   Download from: https://www.postgresql.org/download/

3. **Git**
   ```bash
   git --version
   ```
   Download from: https://git-scm.com/downloads

### Optional Tools

- **pgAdmin** - GUI for PostgreSQL management
- **Postman** - API testing
- **VSCode** - Recommended code editor

---

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/alpha-laundry.git
cd alpha-laundry
```

### 2. Install Dependencies

The project uses a monorepo structure with separate frontend and backend packages.

```bash
# Install root dependencies (Cypress, testing tools, scripts)
npm install

# Install backend dependencies
cd backend
npm install
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Environment Configuration

### Backend Configuration

1. **Create backend environment file:**
   ```bash
   cp backend/.env.example backend/.env
   ```

2. **Edit `backend/.env`** with your configuration:
   ```env
   # Server Configuration
   PORT=3001
   NODE_ENV=development

   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=alpha_laundry
   DB_USER=postgres
   DB_PASSWORD=your_password_here

   # JWT Authentication
   # IMPORTANT: Generate a strong secret (min 32 characters)
   # Run: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   JWT_SECRET=your_generated_secret_here
   JWT_EXPIRES_IN=24h

   # API Configuration
   API_PREFIX=/api
   CORS_ORIGIN=http://localhost:3000
   ```

### Frontend Configuration

1. **Create frontend environment file:**
   ```bash
   cp frontend/.env.example frontend/.env.local
   ```

2. **Edit `frontend/.env.local`** if needed:
   ```env
   # API Configuration
   REACT_APP_API_URL=http://localhost:3001/api

   # App Metadata
   REACT_APP_NAME=Alpha Laundry
   REACT_APP_VERSION=1.0.0
   ```

   **Note:** For local development, the defaults usually work fine.

---

## Database Setup

### Option 1: Quick Setup (Recommended for Development)

This initializes the database with schema and sample data:

```bash
# 1. Create PostgreSQL database
createdb alpha_laundry

# 2. Initialize with schema and seed data
npm run db:seed
```

**Default test accounts will be created:**
- Admin: `admin` / `admin123`
- Students: `STU001`, `STU002`, `STU003`, `STU004`, `STUDENT001`

### Option 2: Production Setup

For production, initialize only the schema without sample data:

```bash
# 1. Create PostgreSQL database
createdb alpha_laundry

# 2. Initialize schema only (no seed data)
npm run db:init
```

You'll need to manually create admin accounts.

### Manual Database Setup

If you prefer manual setup:

```bash
# 1. Create database
createdb alpha_laundry

# 2. Run schema
psql -d alpha_laundry -f backend/database/schema.sql

# 3. (Optional) Add seed data
psql -d alpha_laundry -f backend/database/seeds/dev-data.sql
```

### Database Reset

To completely reset the database (⚠️ **WARNING: Deletes all data!**):

```bash
npm run db:reset
```

---

## Running the Application

### Option 1: Concurrent Mode (Recommended)

Start both frontend and backend with a single command:

```bash
npm run dev
```

This runs:
- Backend on http://localhost:3001
- Frontend on http://localhost:3000

### Option 2: Separate Terminals

**Terminal 1 - Backend:**
```bash
cd backend
npm run dev
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### Verify Installation

1. **Backend Health Check:**
   Visit: http://localhost:3001/health

   Expected response:
   ```json
   {
     "status": "ok",
     "environment": "development"
   }
   ```

2. **Frontend:**
   Visit: http://localhost:3000

   You should see the login page.

3. **Test Login:**
   - Try logging in with admin credentials: `admin` / `admin123`
   - Or student ID: `STU001`

---

## Testing

### Backend Tests

```bash
cd backend
npm test
```

### Frontend Tests

```bash
cd frontend
npm test
```

### End-to-End Tests (Cypress)

```bash
# Run tests in headless mode
npm run test:e2e

# Open Cypress UI for interactive testing
npm run test:e2e:dev
```

---

## Production Deployment

### Environment Preparation

1. **Set production environment variables:**
   ```env
   NODE_ENV=production
   PORT=3001

   # Use strong, unique values
   DB_PASSWORD=strong_production_password
   JWT_SECRET=long_random_secret_at_least_32_characters

   # Update CORS to your production frontend URL
   CORS_ORIGIN=https://your-production-domain.com
   ```

2. **Build applications:**
   ```bash
   # Build both frontend and backend
   npm run build

   # Or individually:
   npm run build:backend
   npm run build:frontend
   ```

### Database Migration

For production, only run schema initialization (no seed data):

```bash
# On production server
createdb alpha_laundry
npm run db:init
```

### Security Checklist

- [ ] Strong, unique `JWT_SECRET` (min 32 characters)
- [ ] Strong database password
- [ ] `NODE_ENV=production` set
- [ ] CORS restricted to production domain
- [ ] SSL/TLS enabled for database connections
- [ ] Environment files not committed to Git
- [ ] Regular database backups configured

---

## Troubleshooting

### Common Issues

#### 1. "Cannot connect to database"

**Symptoms:**
```
Error connecting to the database: ECONNREFUSED
```

**Solutions:**
- Verify PostgreSQL is running: `pg_isready`
- Check database credentials in `backend/.env`
- Ensure database exists: `psql -l | grep alpha_laundry`
- Check PostgreSQL is listening: `psql -h localhost -U postgres`

#### 2. "Missing required environment variables"

**Symptoms:**
```
Missing required environment variables: JWT_SECRET
```

**Solutions:**
- Ensure `backend/.env` file exists
- Copy from template: `cp backend/.env.example backend/.env`
- Fill in all required values

#### 3. "Port 3000 or 3001 already in use"

**Solutions:**
```bash
# Find process using port
lsof -i :3000
lsof -i :3001

# Kill process
kill -9 <PID>
```

Or change ports in environment files.

#### 4. "Authentication failed" / "Invalid token"

**Solutions:**
- Clear browser localStorage
- Verify `JWT_SECRET` is set and consistent
- Check token expiration in `backend/.env`

#### 5. Frontend can't reach backend API

**Solutions:**
- Verify backend is running on port 3001
- Check `REACT_APP_API_URL` in `frontend/.env.local`
- Verify CORS settings in `backend/.env`
- Check browser console for CORS errors

### Getting Help

If issues persist:

1. Check the [GitHub Issues](https://github.com/yourusername/alpha-laundry/issues)
2. Review application logs
3. Enable debug logging:
   ```env
   NODE_ENV=development
   DEBUG=*
   ```

---

## Additional Resources

- **Database README:** `backend/database/README.md`
- **API Documentation:** `docs/api.yaml`
- **Main README:** `README.md`

---

## Development Tips

### Useful Scripts

```bash
# Database operations
npm run db:init      # Initialize schema
npm run db:seed      # Initialize with sample data
npm run db:reset     # Reset database (careful!)

# Development
npm run dev          # Run both servers
npm run backend      # Backend only
npm run frontend     # Frontend only

# Building
npm run build        # Build both
npm run build:backend
npm run build:frontend

# Testing
npm test             # Run all tests
npm run test:backend
npm run test:frontend
npm run test:e2e
```

### Hot Reload

Both frontend and backend support hot reloading:
- Frontend: React Fast Refresh (automatic)
- Backend: ts-node-dev watches for changes

### Database Management

```bash
# Connect to database
psql -d alpha_laundry

# View tables
\dt

# Describe table
\d students

# View data
SELECT * FROM students;
```

---

**Happy Coding! 🚀**
