# Alpha Laundry - Modern Flask Application

A clean, modular Python web application for laundry management built with Flask, SQLAlchemy, and Tailwind CSS.

## Project Structure

```
laundry_app/
├── app.py              # Entry point (initializes the app)
├── config.py           # Loads environment variables
├── models.py           # SQLAlchemy database models
├── routes.py           # URL endpoints and business logic
├── .env                # Secret variables (DATABASE_URL, SECRET_KEY)
├── requirements.txt    # Python dependencies
├── static/
│   └── style.css       # Custom styles
└── templates/
    ├── base.html       # Main layout with Tailwind CSS
    ├── login.html      # Student login page
    ├── admin_login.html # Admin login page
    ├── dashboard.html  # Student dashboard
    └── admin.html      # Admin dashboard
```

## Features

- **Student Portal**: Login to view remaining clothes quota, submit laundry requests, and track request history
- **Admin Dashboard**: View all active/completed jobs, update job statuses, see statistics
- **Modern UI**: Clean, responsive design using Tailwind CSS
- **Secure**: Password hashing, session management, externalized configuration

## Quick Start

### 1. Create Virtual Environment

```bash
cd laundry_app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Edit the `.env` file to customize your settings:

```env
DATABASE_URL=sqlite:///laundry.db
SECRET_KEY=  # generate: python -c "import secrets; print(secrets.token_hex(32))"
DEBUG=True
```

`SECRET_KEY` signs the session cookies and has **no in-code default**. The app
fails to start when it is missing, blank, or a known placeholder, so a
forgeable session key can never ship. With `DEBUG=True` (local development
only) a random ephemeral key is generated per process instead, so you can run
without setting one; sessions simply reset on restart.

### 4. Run the Application

```bash
python app.py
```

The application will:
1. Create the SQLite database (`laundry.db`)
2. Initialize sample data (students and admin)
3. Start the server at `http://localhost:5000`

## Demo Credentials

### Student Login
- **Student ID**: `STU001`
- **Password**: `password123`

### Admin Login
- **Username**: `admin`
- **Password**: `admin123`

## Database Schema

### Students Table
| Column          | Type         | Description                    |
|-----------------|--------------|--------------------------------|
| id              | Integer (PK) | Auto-increment ID              |
| student_id      | String(20)   | Unique student identifier      |
| name            | String(100)  | Student name                   |
| password_hash   | String(255)  | Hashed password                |
| remaining_quota | Integer      | Clothes remaining (default: 30)|
| created_at      | DateTime     | Account creation timestamp     |

### Laundry Requests Table
| Column          | Type         | Description                    |
|-----------------|--------------|--------------------------------|
| id              | Integer (PK) | Auto-increment ID              |
| student_id      | String(20)   | Foreign key to students        |
| num_clothes     | Integer      | Number of clothes              |
| status          | String(20)   | submitted/processing/completed/cancelled |
| submission_date | DateTime     | Request timestamp              |
| completed_date  | DateTime     | Completion timestamp           |

### Admins Table
| Column          | Type         | Description                    |
|-----------------|--------------|--------------------------------|
| id              | Integer (PK) | Auto-increment ID              |
| username        | String(50)   | Unique admin username          |
| password_hash   | String(255)  | Hashed password                |
| created_at      | DateTime     | Account creation timestamp     |

## API Endpoints

| Method | Endpoint                      | Description                |
|--------|-------------------------------|----------------------------|
| GET    | `/`                           | Landing page (login)       |
| GET/POST | `/login`                    | Student login              |
| GET/POST | `/admin/login`              | Admin login                |
| GET    | `/logout`                     | Logout                     |
| GET    | `/student/dashboard`          | Student dashboard          |
| POST   | `/student/submit`             | Submit laundry request     |
| GET    | `/admin/dashboard`            | Admin dashboard            |
| POST   | `/admin/update-status/<id>`   | Update job status          |

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Generate a strong `SECRET_KEY` (required -- with `DEBUG=False` the app will
   refuse to start without one):
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```
3. Use a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
   ```
4. For PostgreSQL, update `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://user:password@localhost/laundry_db
   ```

## License

MIT License
