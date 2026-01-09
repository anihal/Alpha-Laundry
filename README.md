# Alpha Laundry - Hostel Laundry Management System

A modern web-based laundry tracking application designed for hostel laundry services. This application helps students track their laundry usage and allows laundry staff to manage requests efficiently.

## Overview

Alpha Laundry is a full-stack web application that streamlines the laundry management process in hostels. Students can track their laundry usage through a personalized dashboard, while laundry staff can manage and process requests through an administrative interface.

### Key Features

- **Student Dashboard**
  - Student authentication using student IDs
  - Track laundry usage and remaining quota (30 free clothes)
  - View laundry status and history
  - Submit new laundry requests

- **Admin Dashboard**
  - Staff authentication and management
  - Process laundry requests
  - Track overall laundry operations
  - Generate reports and analytics

## Tech Stack

- **Frontend**: React.js with TypeScript
- **Backend**: Node.js with Express
- **Database**: PostgreSQL
- **Authentication**: JWT
- **API Documentation**: Swagger/OpenAPI
- **Testing**: Jest and React Testing Library
- **Deployment**: Docker and Docker Compose

## Database Schema

### Tables

1. **students**
   ```sql
   CREATE TABLE students (
     id SERIAL PRIMARY KEY,
     student_id VARCHAR(20) UNIQUE NOT NULL,
     name VARCHAR(100) NOT NULL,
     remaining_quota INTEGER DEFAULT 30
   );
   ```

2. **laundry_requests**
   ```sql
   CREATE TABLE laundry_requests (
     id SERIAL PRIMARY KEY,
     student_id VARCHAR(20) REFERENCES students(student_id),
     num_clothes INTEGER NOT NULL,
     status VARCHAR(20) DEFAULT 'submitted',
     submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. **admins**
   ```sql
   CREATE TABLE admins (
     id SERIAL PRIMARY KEY,
     username VARCHAR(50) UNIQUE NOT NULL,
     password_hash VARCHAR(255) NOT NULL
   );
   ```

## API Endpoints

### Authentication
- `POST /api/login` - Student and admin login
- `POST /api/register` - Admin registration (protected)

### Student Routes
- `GET /api/student/dashboard` - Get student stats and requests
- `POST /api/student/submit` - Submit new laundry request
- `GET /api/student/history` - Get laundry history

### Admin Routes
- `GET /api/admin/dashboard` - Get all requests
- `PATCH /api/admin/update-status` - Update request status
- `GET /api/admin/analytics` - Get usage analytics

## Development Phases

### Phase 1: Project Setup and Database Design
1. Set up development environment
   - Install Node.js, PostgreSQL
   - Initialize backend with `npm init -y`
   - Create React frontend with `npx create-react-app`
   - Initialize Git repository

2. Design and implement database schema
   - Create PostgreSQL tables
   - Set up relationships and constraints
   - Test database connectivity

3. Plan and document API endpoints
   - Define RESTful routes
   - Document request/response formats
   - Set up API testing environment

### Phase 2: Backend Development
1. Set up Express server
   - Install dependencies (express, pg, dotenv, bcrypt, jsonwebtoken)
   - Configure middleware
   - Set up error handling

2. Implement database connectivity
   - Configure PostgreSQL connection
   - Set up environment variables
   - Test database queries

3. Build authentication system
   - Implement JWT-based auth
   - Create protected routes
   - Add input validation

4. Develop API endpoints
   - Implement all planned routes
   - Add business logic
   - Test with Postman

### Phase 3: Frontend Development
1. Set up React application
   - Configure routing
   - Set up state management
   - Install UI dependencies

2. Build student dashboard
   - Create dashboard components
   - Implement quota tracking
   - Add request submission form

3. Build admin dashboard
   - Create admin interface
   - Implement request management
   - Add analytics views

4. Implement authentication UI
   - Create login forms
   - Add protected routes
   - Handle token management

### Phase 4: Integration and Testing
1. Connect frontend and backend
   - Set up API client
   - Implement error handling
   - Add loading states

2. Add validation and security
   - Implement input validation
   - Add SQL injection prevention
   - Set up password hashing

3. Write tests
   - Backend unit tests with Jest
   - Frontend tests with React Testing Library
   - End-to-end testing

4. Polish UI/UX
   - Add responsive design
   - Implement loading states
   - Add user feedback

### Phase 5: Deployment and Finalization
1. Prepare for production
   - Set up production database
   - Configure environment variables
   - Build frontend assets

2. Deploy application
   - Deploy backend to cloud platform
   - Deploy frontend to static hosting
   - Set up monitoring

3. Documentation and feedback
   - Update documentation
   - Create user guides
   - Gather user feedback

## Getting Started

### Prerequisites
- Node.js 16+ and npm
- PostgreSQL 12+
- Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/alpha-laundry.git
   cd alpha-laundry
   ```

2. **Set up the database:**
   ```bash
   # Create PostgreSQL database
   createdb alpha_laundry
   ```

3. **Install dependencies:**
   ```bash
   # Install root dependencies (for testing/scripts)
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

4. **Configure environment variables:**
   ```bash
   # Backend - Copy and edit configuration
   cp backend/.env.example backend/.env
   # Edit backend/.env with your database credentials and JWT secret

   # Frontend - Copy and edit configuration
   cp frontend/.env.example frontend/.env.local
   # Edit frontend/.env.local if needed (defaults should work for local dev)
   ```

5. **Initialize the database:**
   ```bash
   # Option 1: Schema only (production)
   npm run db:init

   # Option 2: Schema + sample data (development - recommended)
   npm run db:seed
   ```

6. **Start the development servers:**
   ```bash
   # Option 1: Start both servers concurrently (recommended)
   npm run dev

   # Option 2: Start servers separately
   # Terminal 1 - Backend
   cd backend && npm run dev

   # Terminal 2 - Frontend
   cd frontend && npm start
   ```

7. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:3001
   - Health check: http://localhost:3001/health

### Default Test Credentials

After running `npm run db:seed`:
- **Admin**: username: `admin`, password: `admin123`
- **Students**: IDs: `STU001`, `STU002`, `STU003`, `STU004`, `STUDENT001`

## Project Structure

```
alpha-laundry/
├── .env.template              # Environment variables template
├── .gitignore
├── README.md
├── package.json               # Root workspace configuration
│
├── frontend/                  # Frontend React application
│   ├── .env.example          # Frontend environment template
│   ├── package.json
│   ├── tsconfig.json
│   ├── public/               # Static files
│   │   └── index.html
│   └── src/
│       ├── api/              # API client and error handling
│       ├── components/       # Reusable React components
│       ├── contexts/         # React Context providers
│       ├── pages/            # Page components (admin, student)
│       ├── theme/            # MUI theme configuration
│       └── index.tsx         # App entry point
│
├── backend/                   # Backend Node.js/Express application
│   ├── .env.example          # Backend environment template
│   ├── package.json
│   ├── tsconfig.json
│   ├── database/             # Database schema and seeds
│   │   ├── schema.sql        # Database tables and indexes
│   │   ├── seeds/
│   │   │   └── dev-data.sql  # Development seed data
│   │   └── README.md
│   └── src/
│       ├── server.ts         # Main entry point
│       ├── config/           # Configuration (env, database)
│       │   ├── env.ts        # Environment config loader
│       │   └── database.ts   # PostgreSQL connection pool
│       ├── controllers/      # Route controllers (auth, admin, student)
│       ├── middleware/       # Custom middleware (auth, error handling)
│       └── routes/           # API route definitions
│
├── scripts/                   # Utility scripts
│   ├── init-db.js            # Database initialization
│   └── resetDb.js            # Database reset utility
│
├── tests/                     # End-to-end tests
│   ├── cypress.config.ts
│   └── e2e/
│       ├── e2e/              # Cypress test specs
│       └── support/          # Cypress support files
│
└── docs/                      # Documentation
    ├── api.yaml              # OpenAPI/Swagger specification
    └── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by Airbnb's architecture and best practices
- Built with modern web technologies for scalability and maintainability 