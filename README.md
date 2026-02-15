# Alpha Laundry

A web-based laundry management system built for college/university campuses. Students can log in to submit laundry requests and track their clothing quota, while admins manage and monitor all laundry jobs from a centralized dashboard.

Built with Flask, SQLAlchemy, and Tailwind CSS.

## How It Works

**Students** are assigned a monthly clothing quota (default: 30 items). They log in with their student ID, submit laundry requests by specifying how many clothes they want washed, and can view their request history and remaining quota from their dashboard.

**Admins** have a separate login and dashboard where they can see all active and completed laundry jobs, update job statuses (submitted → processing → completed), and view statistics like total students and job counts by status.

## Tech Stack

- **Backend**: Python 3, Flask, Flask-SQLAlchemy
- **Database**: SQLite (swappable to PostgreSQL for production)
- **Frontend**: Jinja2 templates, Tailwind CSS
- **Auth**: Session-based with Werkzeug password hashing

## Project Structure

```
laundry_app/
├── app.py              # App factory and database initialization
├── config.py           # Environment variable configuration
├── models.py           # SQLAlchemy models (Student, LaundryRequest, Admin)
├── routes.py           # All route blueprints and business logic
├── requirements.txt    # Python dependencies
├── static/
│   └── style.css       # Custom styles
└── templates/
    ├── base.html       # Base layout with Tailwind CSS
    ├── login.html      # Student login
    ├── admin_login.html# Admin login
    ├── dashboard.html  # Student dashboard
    └── admin.html      # Admin dashboard
```

## Getting Started

```bash
cd laundry_app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The app starts at `http://localhost:5001`. On first run, it creates the SQLite database and seeds it with sample data.

## Demo Credentials

| Role    | Username/ID | Password      |
|---------|-------------|---------------|
| Student | `STU001`    | `password123` |
| Student | `STU002`    | `password123` |
| Admin   | `admin`     | `admin123`    |

## Routes

| Method   | Endpoint                    | Description              |
|----------|-----------------------------|--------------------------|
| GET      | `/`                         | Landing page (login)     |
| GET/POST | `/login`                    | Student login            |
| GET/POST | `/admin/login`              | Admin login              |
| GET      | `/logout`                   | Logout                   |
| GET      | `/student/dashboard`        | Student dashboard        |
| POST     | `/student/submit`           | Submit laundry request   |
| GET      | `/admin/dashboard`          | Admin dashboard          |
| POST     | `/admin/update-status/<id>` | Update job status        |

## Configuration

Create a `.env` file inside `laundry_app/`:

```env
DATABASE_URL=sqlite:///laundry.db
SECRET_KEY=your-secret-key
DEBUG=True
```

For production, set `DEBUG=False`, use a strong `SECRET_KEY`, and swap to PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/laundry_db
```

## License

MIT
