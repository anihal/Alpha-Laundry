# Alpha Laundry - Frontend

A clean, modern web interface for the Alpha Laundry campus laundry management system.

## Features

### 🧺 User Dashboard
- View remaining clothes quota
- See current laundry status (Washing, Ready for Pickup, etc.)
- Submit new laundry requests with priority levels
- View request history with real-time updates
- Auto-refresh every 30 seconds

### 👨‍💼 Admin Dashboard
- View analytics and statistics
- List all active jobs with filtering
- Update job status (Submitted → Processing → Completed)
- Real-time monitoring of operations
- Mobile-responsive interface

### 🔐 Authentication
- Minimalist login page
- Secure JWT token-based authentication
- Automatic token verification
- Separate student and admin access

## Tech Stack

- **Pure HTML5** - No heavy frameworks
- **Tailwind CSS** - Modern, responsive styling via CDN
- **Vanilla JavaScript** - ES6+ modules for clean code
- **Fetch API** - Native browser API for backend communication
- **LocalStorage** - Client-side token management

## Project Structure

```
frontend/
├── index.html                 # Login page (entry point)
├── student-dashboard.html     # Student interface
├── admin-dashboard.html       # Admin interface
├── js/
│   ├── config.js             # API configuration (externalized)
│   ├── api.js                # API service module
│   └── auth.js               # Authentication module
└── README.md                  # This file
```

## Setup & Installation

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- Python backend running (see `/api` directory)
- A local web server (Python's built-in server, Live Server, etc.)

### Quick Start

1. **Start the Backend** (if not already running):
   ```bash
   cd api
   python run.py run --reload
   ```
   Backend will be available at `http://localhost:8000`

2. **Start a Web Server** for the frontend:

   **Option 1: Python HTTP Server**
   ```bash
   cd frontend
   python -m http.server 3000
   ```

   **Option 2: Node.js HTTP Server**
   ```bash
   cd frontend
   npx http-server -p 3000
   ```

   **Option 3: VS Code Live Server**
   - Install the "Live Server" extension
   - Right-click `index.html` → "Open with Live Server"

3. **Open in Browser**:
   ```
   http://localhost:3000/index.html
   ```

## Configuration

### API URL Configuration

The API URL is configured in `/js/config.js`:

```javascript
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : '/api',
    // ... other settings
};
```

**To change the API URL:**

1. **Edit config.js directly**:
   ```javascript
   API_BASE_URL: 'http://your-server.com:8000/api'
   ```

2. **Or use localStorage override** (temporary, for testing):
   ```javascript
   // In browser console:
   localStorage.setItem('api_override', 'http://your-server.com:8000/api')
   ```

### Auto-Refresh Interval

Dashboards auto-refresh every 30 seconds. To change this, edit `config.js`:

```javascript
DASHBOARD_REFRESH_INTERVAL: 30000, // milliseconds (30 seconds)
```

## Usage

### Login Credentials

**Students:**
- Username: `STU001`, `STU002`, `STU003`, `STU004`
- Password: `password` (for demo accounts)

**Admin:**
- Username: `admin`
- Password: `admin123`

### Student Workflow

1. **Login** with student ID (e.g., STU001)
2. **View Dashboard**:
   - Check remaining quota
   - See current request status
   - View request history
3. **Submit Request**:
   - Enter number of clothes (1-50)
   - Select priority (Low, Normal, High, Urgent)
   - Add optional notes
   - Click "Submit Request"
4. **Monitor Status**:
   - Submitted → Processing → Ready for Pickup

### Admin Workflow

1. **Login** with admin credentials
2. **View Analytics**:
   - Total jobs, submitted, processing, completed
   - Total clothes processed
3. **Manage Jobs**:
   - Filter by status (All, Submitted, Processing, Completed)
   - Click "Update" on any job
   - Change status in modal
   - Confirm update
4. **Monitor Operations**:
   - Real-time dashboard updates
   - Click refresh to manually update

## API Integration

### API Endpoints Used

**Authentication:**
- `POST /api/auth/login` - User login
- `GET /api/auth/verify` - Token verification
- `POST /api/auth/logout` - User logout

**Student:**
- `GET /api/student/dashboard?token=...` - Get dashboard data
- `POST /api/student/submit?token=...` - Submit laundry request
- `GET /api/student/history?token=...` - Get request history

**Admin:**
- `GET /api/admin/dashboard?token=...` - Get admin dashboard
- `PATCH /api/admin/update-status?token=...` - Update job status
- `GET /api/admin/analytics?token=...` - Get analytics
- `GET /api/admin/jobs?token=...` - List all jobs

### Authentication Flow

1. User submits credentials to `/api/auth/login`
2. Backend returns JWT token in response
3. Frontend stores token in `localStorage`
4. Token sent in all subsequent requests as query parameter: `?token=<token>`
5. Backend verifies token and processes request

### Error Handling

The API service (`js/api.js`) handles:
- Network errors
- HTTP error responses (400, 401, 403, 404, 500)
- Invalid tokens (redirects to login)
- Validation errors

## Mobile Responsiveness

The interface is fully responsive and optimized for:
- **Desktop** (1024px+) - Full layout with all features
- **Tablet** (768px-1023px) - Adapted grid layouts
- **Mobile** (320px-767px) - Stacked layouts, touch-friendly buttons

### Mobile Features:
- Responsive navigation
- Touch-optimized buttons
- Readable fonts on small screens
- Horizontal scrolling for tables
- Optimized form layouts

## Browser Compatibility

Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Requirements:**
- ES6 modules support
- Fetch API support
- LocalStorage support
- CSS Grid and Flexbox support

## Security Features

- JWT token-based authentication
- Secure token storage in `localStorage`
- Automatic token verification on protected routes
- Session timeout handling
- HTTPS recommended for production

## Deployment

### Production Deployment

1. **Update API URL** in `config.js`:
   ```javascript
   API_BASE_URL: 'https://your-api-server.com/api'
   ```

2. **Deploy Files**:
   - Upload all files to your web server
   - Ensure server is configured to serve static files
   - Configure CORS on backend to allow your domain

3. **Recommended Hosting**:
   - **Netlify** - Drag & drop deployment
   - **Vercel** - Git-based deployment
   - **GitHub Pages** - Free static hosting
   - **AWS S3 + CloudFront** - Enterprise hosting

### Environment-Specific Configuration

For different environments (dev, staging, production), you can:

1. Create separate config files:
   ```
   config.dev.js
   config.staging.js
   config.prod.js
   ```

2. Load appropriate config based on hostname:
   ```javascript
   const hostname = window.location.hostname;
   const configFile = hostname.includes('staging')
       ? './config.staging.js'
       : hostname.includes('localhost')
           ? './config.dev.js'
           : './config.prod.js';
   ```

## Troubleshooting

### "Network error" on login
- ✅ Check backend is running (`http://localhost:8000`)
- ✅ Verify API URL in `config.js`
- ✅ Check browser console for CORS errors
- ✅ Ensure backend CORS allows frontend origin

### "Token invalid" errors
- ✅ Clear localStorage: `localStorage.clear()`
- ✅ Login again to get new token
- ✅ Check token hasn't expired (24hr default)

### Dashboard not loading
- ✅ Check browser console for errors
- ✅ Verify you're logged in with correct user type
- ✅ Check network tab for failed API requests
- ✅ Verify backend database has data (run seed script)

### Styling issues
- ✅ Check internet connection (Tailwind CSS loads from CDN)
- ✅ Clear browser cache
- ✅ Try different browser

## Development

### Code Style

- ES6+ JavaScript modules
- Async/await for API calls
- Functional programming approach
- Clean, readable code with comments

### Best Practices

- ✅ Externalized configuration
- ✅ Modular code organization
- ✅ Error handling and user feedback
- ✅ Loading states and animations
- ✅ Mobile-first responsive design
- ✅ Accessibility considerations

## Future Enhancements

Potential features to add:
- [ ] Dark mode toggle
- [ ] Push notifications for status updates
- [ ] Advanced filtering and search
- [ ] Export reports (PDF, CSV)
- [ ] User profile management
- [ ] Multi-language support
- [ ] Progressive Web App (PWA) features
- [ ] Offline support with service workers

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend API documentation (`/api/README.md`)
3. Check browser console for error messages
4. Verify backend is running and accessible

## License

Part of the Alpha Laundry project.

---

**Version:** 2.0
**Last Updated:** January 2024
**Author:** Alpha Laundry Team
