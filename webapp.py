# webapp.py - WebExtract Pro Main Application (Fixed Version)
from flask import Flask, send_from_directory, request, jsonify, redirect, url_for, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from datetime import datetime, timedelta
import requests
import json
import os
from shared_db import db, User, ScrapingSession, DatabaseManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'webextract-pro-secret-key-2025'
app.config['JWT_SECRET_KEY'] = 'webextract-pro-jwt-secret-2025'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize extensions
CORS(app)
jwt = JWTManager(app)
DatabaseManager.init_app(app)

# Get current directory for serving files
current_dir = os.path.dirname(os.path.abspath(__file__))

# Worker configurations
WORKERS = {
    'kilimall': {
        'name': 'Kilimall Scraper',
        'description': 'Extract products from Kilimall Kenya',
        'port': 5001,
        'url': 'http://127.0.0.1:5001',
        'icon': '🛒'
    },
    'jumia': {
        'name': 'Jumia Scraper', 
        'description': 'Extract products from Jumia Kenya',
        'port': 5000,
        'url': 'http://127.0.0.1:5000',
        'icon': '🛍️'
    }
}

# Initialize database tables and admin user (Fixed for modern Flask)
@app.before_request
def initialize_database():
    """Initialize database on first request instead of before_first_request"""
    if not hasattr(app, 'db_initialized'):
        with app.app_context():
            db.create_all()
            # Create admin user if doesn't exist
            admin = User.query.filter_by(email='admin@webextract-pro.com').first()
            if not admin:
                admin = User(
                    name='WebExtract Pro Admin',
                    email='admin@webextract-pro.com'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("[OK] Admin user created: admin@webextract-pro.com / admin123")
        app.db_initialized = True

@app.route('/')
def home():
    """Serve your existing webextract-pro.html with proper headers"""
    try:
        # Check if the file exists first
        frontend_path = os.path.join(current_dir, 'webextract-pro.html')
        if not os.path.exists(frontend_path):
            print(f"[ERROR] webextract-pro.html not found at: {frontend_path}")
            raise FileNotFoundError("Frontend file not found")
        
        # Create response with proper headers
        response = make_response(send_from_directory(current_dir, 'webextract-pro.html'))
        
        # Set explicit headers to ensure proper content type
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"[OK] Serving webextract-pro.html from: {frontend_path}")
        return response
        
    except FileNotFoundError:
        print("[WARN] webextract-pro.html not found - serving fallback interface")
        # Fallback if webextract-pro.html doesn't exist
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebExtract Pro - File Missing</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 20px; 
                    min-height: 100vh; 
                    margin: 0; 
                }
                .container { 
                    max-width: 800px; 
                    margin: 0 auto; 
                    text-align: center; 
                    padding-top: 100px; 
                }
                .error { 
                    background: rgba(255, 68, 68, 0.8); 
                    padding: 30px; 
                    border-radius: 15px; 
                    margin: 20px 0; 
                }
                .info { 
                    background: rgba(68, 68, 255, 0.8); 
                    padding: 30px; 
                    border-radius: 15px; 
                    margin: 20px 0; 
                }
                .btn { 
                    display: inline-block; 
                    padding: 12px 24px; 
                    background: rgba(255, 255, 255, 0.2); 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    margin: 10px; 
                    transition: all 0.3s; 
                }
                .btn:hover { 
                    background: rgba(255, 255, 255, 0.3); 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>[START] WebExtract Pro</h1>
                <div class="error">
                    <h3>Frontend File Missing</h3>
                    <p><strong>webextract-pro.html</strong> not found in the root directory.</p>
                    <p>Please ensure your frontend file is in the correct location.</p>
                    <p>Current directory: <code>""" + current_dir + """</code></p>
                </div>
                <div class="info">
                    <h3>System Status</h3>
                    <p>[OK] WebExtract Pro backend is running on port 8000</p>
                    <p>🔗 API endpoints are available</p>
                    <p>[DATABASE] Database is operational</p>
                </div>
                <div>
                    <a href="/api/health" class="btn">Health Check</a>
                    <a href="/api/workers/health" class="btn">Worker Status</a>
                    <a href="http://127.0.0.1:5001" class="btn">Kilimall Worker</a>
                    <a href="http://127.0.0.1:5000" class="btn">Jumia Worker</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        response = make_response(fallback_html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

# Debug route to check file existence
@app.route('/debug/files')
def debug_files():
    """Debug route to check what files exist"""
    files_in_directory = os.listdir(current_dir)
    return jsonify({
        'current_directory': current_dir,
        'files_in_directory': files_in_directory,
        'webextract_pro_html_exists': os.path.exists(os.path.join(current_dir, 'webextract-pro.html')),
        'webextract_pro_html_path': os.path.join(current_dir, 'webextract-pro.html')
    })

# Test route to verify HTML serving
@app.route('/test')
def test():
    """Test route to verify HTML serving works"""
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Flask HTML Test</h1>
        <p>If you see this, Flask is serving HTML correctly!</p>
        <p>Current time: """ + str(datetime.now()) + """</p>
    </body>
    </html>
    """
    response = make_response(test_html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

# Serve static files (CSS, JS, images) from the current directory
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files like CSS, JS, images"""
    try:
        response = make_response(send_from_directory(current_dir, filename))
        
        # Set appropriate content type based on file extension
        if filename.endswith('.css'):
            response.headers['Content-Type'] = 'text/css'
        elif filename.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'
        elif filename.endswith('.json'):
            response.headers['Content-Type'] = 'application/json'
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            response.headers['Content-Type'] = 'image/' + filename.split('.')[-1]
        elif filename.endswith('.svg'):
            response.headers['Content-Type'] = 'image/svg+xml'
        
        return response
    except FileNotFoundError:
        return jsonify({'error': 'Static file not found'}), 404

# Also serve files directly from root for compatibility
@app.route('/<path:filename>')
def serve_files(filename):
    """Serve any file from the root directory for compatibility"""
    try:
        # Only serve safe file types
        safe_extensions = ['.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.json']
        if any(filename.lower().endswith(ext) for ext in safe_extensions):
            response = make_response(send_from_directory(current_dir, filename))
            
            # Set appropriate content type
            if filename.endswith('.html'):
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
            elif filename.endswith('.css'):
                response.headers['Content-Type'] = 'text/css'
            elif filename.endswith('.js'):
                response.headers['Content-Type'] = 'application/javascript'
            elif filename.endswith('.json'):
                response.headers['Content-Type'] = 'application/json'
            
            return response
        else:
            return jsonify({'error': 'File type not allowed'}), 403
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

# Keep the dashboard route for backward compatibility
@app.route('/dashboard')
def dashboard():
    """Redirect to main page (since your HTML handles routing)"""
    return redirect('/')

# API Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'All fields are required'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        user = User(name=data['name'], email=data['email'])
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'token': access_token,  # Alternative field name for compatibility
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if user and user.check_password(data['password']):
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            access_token = create_access_token(identity=user.id)
            
            return jsonify({
                'success': True,
                'access_token': access_token,
                'token': access_token,  # Alternative field name for compatibility
                'user': user.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/stats')
@jwt_required()
def dashboard_stats():
    """Get dashboard statistics for current user"""
    try:
        user_id = get_jwt_identity()
        stats = DatabaseManager.get_user_stats(user_id)
        recent_sessions = DatabaseManager.get_recent_sessions(user_id, limit=5)
        
        stats['recent_sessions'] = [session.to_dict() for session in recent_sessions]
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/workers/health')
def worker_health():
    """Check health of all worker services"""
    health_status = {}
    
    for worker_name, worker_config in WORKERS.items():
        try:
            response = requests.get(f"{worker_config['url']}/api/health", timeout=5)
            health_status[worker_name] = {
                'status': 'online' if response.status_code == 200 else 'offline',
                'url': worker_config['url'],
                'data': response.json() if response.status_code == 200 else None
            }
        except Exception:
            health_status[worker_name] = {
                'status': 'offline',
                'url': worker_config['url'],
                'data': None
            }
    
    return jsonify(health_status)

@app.route('/api/workers/stats')
def worker_stats():
    """Get statistics from all workers"""
    worker_stats = {}
    
    for worker_name, worker_config in WORKERS.items():
        try:
            response = requests.get(f"{worker_config['url']}/api/stats", timeout=5)
            if response.status_code == 200:
                worker_stats[worker_name] = response.json()
            else:
                worker_stats[worker_name] = {'error': 'Worker not responding'}
        except Exception:
            worker_stats[worker_name] = {'error': 'Worker offline'}
    
    return jsonify(worker_stats)

@app.route('/api/admin/stats')
@jwt_required()
def admin_stats():
    """Get system-wide statistics (admin only)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Check if user is admin
        if user.email != 'admin@webextract-pro.com':
            return jsonify({'error': 'Admin access required'}), 403
        
        stats = DatabaseManager.get_system_stats()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/create', methods=['POST'])
@jwt_required()
def create_session():
    """Create a new scraping session"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        session = ScrapingSession(
            user_id=user_id,
            worker_type=data['worker_type'],
            task_id=data['task_id'],
            search_query=data.get('search_query'),
            category_url=data.get('category_url'),
            status='running'
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({'success': True, 'session_id': session.id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions/update', methods=['POST'])
@jwt_required()
def update_session():
    """Update scraping session progress"""
    try:
        data = request.get_json()
        session = ScrapingSession.query.filter_by(task_id=data['task_id']).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Update session fields
        for field in ['status', 'progress', 'message', 'products_found', 'products_data', 'pages_scraped', 'error_message']:
            if field in data:
                setattr(session, field, data[field])
        
        if data.get('status') in ['completed', 'failed']:
            session.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Additional API endpoints for compatibility with your frontend
@app.route('/api/health')
def health_check():
    """Main health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'webextract-pro-main',
        'platform': 'webextract-pro',
        'database_available': True,
        'frontend_available': os.path.exists(os.path.join(current_dir, 'webextract-pro.html')),
        'workers': WORKERS
    })

@app.route('/api/status')
def get_status():
    """General status endpoint"""
    try:
        # Fix: Don't call worker_health() function recursively
        total_users = User.query.count()
        
        return jsonify({
            'service': 'webextract-pro-main',
            'status': 'online',
            'total_users': total_users,
            'version': '1.0.0',
            'platform': 'webextract-pro'
        })
    except Exception as e:
        return jsonify({
            'service': 'webextract-pro-main',
            'status': 'online',
            'error': str(e)
        }), 500

# CORS preflight handling
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'message': 'OK'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

if __name__ == '__main__':
    print("[START] Starting WebExtract Pro...")
    print("[DASHBOARD] Dashboard: http://127.0.0.1:8000")
    print("[FRONTEND] Frontend: webextract-pro.html")
    print("[ADMIN] Admin Login: admin@webextract-pro.com / admin123")
    print("[DATABASE] Database: webextract_pro.db")
    
    # Check if frontend file exists
    frontend_path = os.path.join(current_dir, 'webextract-pro.html')
    if os.path.exists(frontend_path):
        print("[OK] webextract-pro.html found")
    else:
        print("[WARN] webextract-pro.html not found - using fallback interface")
    
    # Print debug info
    print(f"[FOLDER] Current directory: {current_dir}")
    print(f"[FILES] Files in directory: {os.listdir(current_dir)}")
    
    app.run(host='127.0.0.1', port=8000, debug=True)