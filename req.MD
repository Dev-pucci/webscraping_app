# Kenya Scraper Hub - Setup Instructions

## Overview
A comprehensive web scraping platform that manages Jumia and Kilimall scrapers with user authentication, task management, and real-time monitoring.

## Architecture
```
Kenya Scraper Hub (Port 8000) - Parent App with Auth
├── Kilimall Scraper Worker (Port 5001)
└── Jumia Scraper Worker (Port 5000)
```

## Requirements

### Python Dependencies
Create a `requirements.txt` file:

```txt
Flask==2.3.3
Flask-CORS==4.0.0
Flask-SQLAlchemy==3.0.5
Flask-Bcrypt==1.0.1
Flask-JWT-Extended==4.5.2
requests==2.31.0
beautifulsoup4==4.12.2
selenium==4.15.0
webdriver-manager==4.0.1
python-dotenv==1.0.0
gunicorn==21.2.0
```

### System Requirements
- Python 3.8+
- Chrome browser (for Selenium)
- SQLite (or PostgreSQL for production)

## Installation Steps

### 1. Clone and Setup Environment
```bash
# Create project directory
mkdir kenya-scraper-hub
cd kenya-scraper-hub

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Project Structure
```
kenya-scraper-hub/
├── parent_app.py              # Main authentication server
├── workers/
│   ├── kilimall/
│   │   ├── kilimall_api_server.py    # Kilimall worker
│   │   ├── kilimall_scraper.py       # Kilimall scraper
│   │   └── index.html                # Kilimall interface
│   └── jumia/
│       ├── app.py                    # Jumia worker  
│       ├── jumia_scraper.py          # Jumia scraper
│       └── index.html                # Jumia interface
├── frontend/
│   └── index.html                    # Parent app interface
├── requirements.txt
├── .env
└── README.md
```

### 3. Environment Configuration
Create a `.env` file:

```env
# Parent App Configuration
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
DATABASE_URL=sqlite:///scraper_hub.db

# Production Database (Optional)
# DATABASE_URL=postgresql://username:password@localhost/scraper_hub

# Worker Configuration
KILIMALL_WORKER_PORT=5001
JUMIA_WORKER_PORT=5000
PARENT_APP_PORT=8000

# Security
FLASK_ENV=development
CORS_ORIGINS=*
```

### 4. Database Setup
```bash
# The database will be created automatically on first run
# Or manually initialize:
python -c "
from parent_app import app, db
with app.app_context():
    db.create_all()
    print('Database created successfully!')
"
```

## Running the Application

### Method 1: Manual Start (Development)
Open 3 separate terminals:

```bash
# Terminal 1: Start Parent App
python parent_app.py
# Runs on http://127.0.0.1:8000

# Terminal 2: Start Kilimall Worker
cd workers/kilimall
python kilimall_api_server.py
# Runs on http://127.0.0.1:5001

# Terminal 3: Start Jumia Worker  
cd workers/jumia
python app.py
# Runs on http://127.0.0.1:5000
```

### Method 2: Using Process Manager (Recommended)
Create a `start_all.py` script:

```python
import subprocess
import time
import os

def start_service(name, command, cwd=None):
    print(f"Starting {name}...")
    process = subprocess.Popen(
        command, 
        shell=True, 
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # Give service time to start
    return process

if __name__ == "__main__":
    services = []
    
    try:
        # Start parent app
        services.append(start_service(
            "Parent App", 
            "python parent_app.py"
        ))
        
        # Start Kilimall worker
        services.append(start_service(
            "Kilimall Worker", 
            "python kilimall_api_server.py",
            cwd="workers/kilimall"
        ))
        
        # Start Jumia worker
        services.append(start_service(
            "Jumia Worker", 
            "python app.py",
            cwd="workers/jumia"
        ))
        
        print("\n✅ All services started successfully!")
        print("🌐 Access the app at: http://127.0.0.1:8000")
        print("\nPress Ctrl+C to stop all services")
        
        # Keep script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        for service in services:
            service.terminate()
        print("✅ All services stopped")
```

Run with: `python start_all.py`

## Usage Instructions

### 1. First Time Setup
1. Open http://127.0.0.1:8000
2. Click "Sign Up" to create an account
3. Fill in your details and register
4. You'll be automatically logged in

### 2. Using the Scrapers
1. **Dashboard Overview**: See all available scrapers and their status
2. **Kilimall Scraper**: Click "Open Scraper" to launch Kilimall worker
3. **Jumia Scraper**: Click "Open Scraper" to launch Jumia worker
4. **Monitor Progress**: Real-time task tracking and statistics
5. **Download Data**: Export results as JSON or CSV

### 3. Admin Features
- Default admin: `admin@scraperhub.com` / `admin123`
- View all users and sessions
- System-wide statistics
- Worker health monitoring

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/profile` - Get user profile

### Workers
- `GET /api/workers` - Get all worker status
- `GET /api/workers/<worker_id>/stats` - Get worker statistics

### Sessions
- `GET /api/sessions` - Get user sessions
- `POST /api/sessions` - Create new session
- `PUT /api/sessions/<id>` - Update session

### Admin (Requires admin privileges)
- `GET /api/admin/users` - Get all users
- `GET /api/admin/sessions` - Get all sessions
- `GET /api/admin/stats` - Get system statistics

## Production Deployment

### 1. Environment Setup
```bash
# Use production database
export DATABASE_URL=postgresql://user:password@localhost/scraper_hub

# Set secure keys
export SECRET_KEY=your-production-secret-key
export JWT_SECRET_KEY=your-production-jwt-key
export FLASK_ENV=production
```

### 2. Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Start parent app
gunicorn -w 4 -b 0.0.0.0:8000 parent_app:app

# Start workers
gunicorn -w 2 -b 0.0.0.0:5001 workers.kilimall.kilimall_api_server:app
gunicorn -w 2 -b 0.0.0.0:5000 workers.jumia.app:app
```

### 3. Using Docker (Optional)
Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000 5000 5001

CMD ["python", "start_all.py"]
```

### 4. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /kilimall/ {
        proxy_pass http://127.0.0.1:5001/;
    }
    
    location /jumia/ {
        proxy_pass http://127.0.0.1:5000/;
    }
}
```

## Security Considerations

### 1. Change Default Credentials
- Update admin password
- Use strong SECRET_KEY and JWT_SECRET_KEY
- Enable HTTPS in production

### 2. Database Security
- Use PostgreSQL in production
- Enable database authentication
- Regular backups

### 3. Rate Limiting
Add rate limiting to prevent abuse:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill process on port
   lsof -ti:8000 | xargs kill -9
   ```

2. **Database Connection Error**
   ```bash
   # Reset database
   rm scraper_hub.db
   python parent_app.py
   ```

3. **Worker Not Responding**
   - Check if worker services are running
   - Verify ports are not blocked by firewall
   - Check worker logs for errors

4. **Authentication Issues**
   - Clear browser localStorage
   - Verify JWT_SECRET_KEY is consistent
   - Check token expiration

### Logs and Monitoring
- Parent app logs: Console output
- Worker logs: Check individual worker consoles
- Database queries: Enable SQLAlchemy logging

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Features

### ✅ Implemented
- User authentication (register/login)
- Worker management and monitoring
- Real-time task tracking
- Statistics dashboard
- Admin panel
- Data export (JSON/CSV)
- Responsive UI
- Error handling

### 🚀 Future Enhancements
- Email notifications
- Scheduled scraping
- Data visualization charts
- API rate limiting
- User roles and permissions
- Advanced filtering
- Export to databases
- Webhook integrations

## Support

For issues and questions:
1. Check logs for error details
2. Verify all services are running
3. Check network connectivity
4. Review configuration files

## License
This project is for educational and personal use.