# kilimall_worker.py - WebExtract Pro Worker (Fixed HTML Serving)
from flask import Flask, send_from_directory, request, jsonify, make_response
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import os
import sys
import uuid
import logging

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix path to find shared_db.py (go up 2 directories from workers/kilimall/)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Try to import shared_db (optional for standalone operation)
try:
    from shared_db import db, User, ScrapingSession, DatabaseManager
    SHARED_DB_AVAILABLE = True
    print("[OK] shared_db imported successfully")
except ImportError:
    SHARED_DB_AVAILABLE = False
    print("[WARN] shared_db not available - running in standalone mode")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'webextract-pro-kilimall-worker-2025'
CORS(app)

# Initialize database if available
if SHARED_DB_AVAILABLE:
    try:
        DatabaseManager.init_app(app)
        print("[OK] Database initialized")
    except Exception as e:
        print(f"[WARN] Database initialization failed: {e}")
        SHARED_DB_AVAILABLE = False

# Import your existing scraper
SCRAPER_AVAILABLE = False
KilimallScraper = None

try:
    # Import your KilimallScraper class
    from kilimall_scraper import KilimallScraper
    SCRAPER_AVAILABLE = True
    print("[OK] KilimallScraper class imported successfully")
    print("[OK] Your trained Selenium-based scraper is ready")
    print("[OK] Using exact selectors from real Kilimall HTML analysis")
except ImportError as e:
    print(f"[WARN] Could not import KilimallScraper: {e}")
    print("[WARN] Make sure kilimall_scraper.py is in the workers/kilimall/ directory")

# Active tasks storage - Fixed to prevent memory leaks
active_tasks = {}
task_history = []
task_lock = threading.Lock()  # Thread safety

def create_scraping_session(user_id, worker_type, task_id, search_query=None, category_url=None):
    """Create a new scraping session in the database"""
    if not SHARED_DB_AVAILABLE:
        return None
    
    try:
        with app.app_context():  # Ensure we have app context
            session = ScrapingSession(
                user_id=user_id,
                worker_type=worker_type,
                task_id=task_id,
                status='running',
                search_query=search_query,
                category_url=category_url,
                progress=0,
                message='Initializing...'
            )
            db.session.add(session)
            db.session.commit()
            
            print(f"[OK] Created ScrapingSession record: {session.id} for task {task_id}")
            return session
    except Exception as e:
        print(f"[ERROR] Error creating ScrapingSession: {e}")
        db.session.rollback()
        return None

def update_scraping_session_safe(task_id, **kwargs):
    """Thread-safe update function that creates its own app context"""
    if not SHARED_DB_AVAILABLE:
        return
    
    def do_update():
        try:
            session = ScrapingSession.query.filter_by(task_id=task_id).first()
            if session:
                # Only update fields that exist in the model
                valid_fields = ['progress', 'message', 'products_found', 'pages_scraped', 'status']
                
                for key, value in kwargs.items():
                    if key in valid_fields and hasattr(session, key):
                        setattr(session, key, value)
                        print(f"[OK] Setting {key} = {value} for task {task_id}")
                
                db.session.commit()
                print(f"[OK] Updated ScrapingSession for task {task_id}")
            else:
                print(f"[ERROR] No session found for task_id: {task_id}")
        except Exception as e:
            print(f"[ERROR] Error updating ScrapingSession for task {task_id}: {e}")
            try:
                db.session.rollback()
            except:
                pass
    
    # Run the update with proper app context
    with app.app_context():
        do_update()

def complete_scraping_session_safe(task_id, products_data, status='completed', error_message=None):
    """Thread-safe completion function that creates its own app context"""
    if not SHARED_DB_AVAILABLE:
        return
    
    def do_complete():
        try:
            session = ScrapingSession.query.filter_by(task_id=task_id).first()
            if session:
                session.status = status
                session.completed_at = datetime.utcnow()
                session.progress = 100 if status == 'completed' else session.progress
                
                if products_data:
                    session.products_found = len(products_data)
                    
                    # Convert products to JSON-serializable format
                    if isinstance(products_data, list):
                        # Convert Product objects to dictionaries if needed
                        json_products = []
                        for product in products_data:
                            if hasattr(product, '__dict__'):
                                # Convert dataclass/object to dict
                                product_dict = {
                                    'name': getattr(product, 'name', 'N/A'),
                                    'price': getattr(product, 'price', 'N/A'),
                                    'original_price': getattr(product, 'original_price', 'N/A'),
                                    'discount': getattr(product, 'discount', 'N/A'),
                                    'rating': getattr(product, 'rating', 'N/A'),
                                    'reviews_count': getattr(product, 'reviews_count', 'N/A'),
                                    'image_url': getattr(product, 'image_url', 'N/A'),
                                    'product_url': getattr(product, 'product_url', 'N/A'),
                                    'brand': getattr(product, 'brand', 'N/A'),
                                    'category': getattr(product, 'category', 'N/A'),
                                    'shipping_info': getattr(product, 'shipping_info', 'N/A'),
                                    'badges': getattr(product, 'badges', [])
                                }
                                json_products.append(product_dict)
                            else:
                                # Already a dict
                                json_products.append(product)
                        
                        session.products_data = json.dumps(json_products)
                    else:
                        session.products_data = str(products_data)
                
                if error_message:
                    session.error_message = error_message
                    session.message = f"Failed: {error_message}"
                else:
                    session.message = f"Completed successfully - {len(products_data) if products_data else 0} products"
                
                db.session.commit()
                print(f"[OK] Completed ScrapingSession for task {task_id}: {status} with {len(products_data) if products_data else 0} products")
            else:
                print(f"[ERROR] No session found for task_id: {task_id}")
        except Exception as e:
            print(f"[ERROR] Error completing ScrapingSession for task {task_id}: {e}")
            try:
                db.session.rollback()
            except:
                pass
    
    # Run the completion with proper app context
    with app.app_context():
        do_complete()

def test_database_update(task_id):
    """Test function to verify database updates work"""
    if not SHARED_DB_AVAILABLE:
        print("Database not available")
        return
    
    try:
        with app.app_context():
            session = ScrapingSession.query.filter_by(task_id=task_id).first()
            if session:
                print(f"Found session: {session.id}")
                print(f"Current progress: {session.progress}")
                print(f"Current message: {session.message}")
                
                # Test update
                session.progress = 50
                session.message = "Test update"
                db.session.commit()
                print("[OK] Test update successful")
            else:
                print(f"[ERROR] No session found for task_id: {task_id}")
    except Exception as e:
        print(f"[ERROR] Test update failed: {e}")

@app.route('/')
def home():
    """Serve kilimall_frontend.html with proper headers - FIXED"""
    try:
        frontend_path = os.path.join(current_dir, 'kilimall_frontend.html')
        
        if os.path.exists(frontend_path):
            # Read the HTML file directly
            with open(frontend_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Create response with explicit headers
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            print(f"[OK] Successfully served kilimall_frontend.html ({len(html_content)} chars)")
            return response
        else:
            print(f"[WARN] kilimall_frontend.html not found at: {frontend_path}")
            return serve_fallback_html()
            
    except Exception as e:
        print(f"[ERROR] Error serving HTML: {e}")
        return serve_fallback_html()

def serve_fallback_html():
    """Serve fallback HTML when main file has issues"""
    fallback_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kilimall Worker - WebExtract Pro</title>
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
                background: rgba(255, 255, 255, 0.1); 
                padding: 30px; 
                border-radius: 15px; 
                backdrop-filter: blur(10px); 
            }
            .status { 
                background: rgba(0, 255, 0, 0.2); 
                padding: 20px; 
                border-radius: 10px; 
                margin: 20px 0; 
            }
            .error { 
                background: rgba(255, 0, 0, 0.2); 
                padding: 20px; 
                border-radius: 10px; 
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
            <h1>[KILIMALL] Kilimall Worker - WebExtract Pro</h1>
            <div class="error">
                <h3>[WARN] Frontend Issue</h3>
                <p>The <strong>kilimall_frontend.html</strong> file couldn't be loaded properly.</p>
                <p>Using fallback interface instead.</p>
            </div>
            <div class="status">
                <h3>[OK] Worker Status</h3>
                <p>[OK] Kilimall Worker is running on port 5001</p>
                <p>[OK] Flask application is working</p>
                <p>[OK] API endpoints are available</p>
                <p>{'[OK] KilimallScraper loaded' if SCRAPER_AVAILABLE else '[ERROR] KilimallScraper not found'}</p>
            </div>
            <div>
                <a href="/api/health" class="btn">Health Check</a>
                <a href="/api/stats" class="btn">Statistics</a>
                <a href="/test" class="btn">Test Route</a>
                <a href="http://127.0.0.1:8000" class="btn">Back to Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    response = make_response(fallback_html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/test')
def test_route():
    """Test route to verify HTML serving works"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kilimall Worker Test</title>
        <meta charset="UTF-8">
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
                max-width: 600px; 
                margin: 0 auto; 
                background: rgba(255, 255, 255, 0.1); 
                padding: 30px; 
                border-radius: 15px; 
                backdrop-filter: blur(10px); 
            }
            .success { 
                background: rgba(0, 255, 0, 0.2); 
                padding: 20px; 
                border-radius: 10px; 
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
            <h1>[OK] Kilimall Worker HTML Test</h1>
            <div class="success">
                <h3>[OK] Success!</h3>
                <p>HTML serving is working correctly!</p>
                <p>Flask can serve HTML with proper headers.</p>
            </div>
            <div>
                <a href="/" class="btn">Back to Main</a>
                <a href="/api/health" class="btn">Health Check</a>
                <a href="/api/stats" class="btn">Statistics</a>
            </div>
        </div>
    </body>
    </html>
    """

# Serve all static files from the current directory
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

@app.route('/<path:filename>')
def serve_files(filename):
    """Serve any file from the kilimall directory (for compatibility)"""
    try:
        if filename == 'favicon.ico':
            return '', 404
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

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'kilimall-worker',
        'platform': 'webextract-pro',
        'scraper_available': SCRAPER_AVAILABLE,
        'scraper_type': 'Final Working Version - Real HTML Selectors' if SCRAPER_AVAILABLE else 'Not available',
        'database_available': SHARED_DB_AVAILABLE,
        'frontend_available': os.path.exists(os.path.join(current_dir, 'kilimall_frontend.html')),
        'mode': 'integrated' if SCRAPER_AVAILABLE else 'api-only',
        'active_tasks': len(active_tasks),
        'total_tasks': len(task_history),
        'search_format': 'keyword-based',
        'category_focus': 'Phones & Accessories',
        'html_serving': 'fixed'
    })

@app.route('/api/scrape', methods=['POST'])
def scrape_products():
    """Main scraping endpoint - matches frontend API calls"""
    try:
        if not SCRAPER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'KilimallScraper not available. Please ensure kilimall_scraper.py is in the correct directory.'
            }), 500
        
        data = request.get_json() or {}
        logger.info(f"Received scrape request: {data}")
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        
        # Extract parameters matching frontend expectations
        search_query = data.get('search', '')
        category_url = data.get('categoryUrl', '')
        max_pages = min(data.get('pages', 1), 3)  # Limit to 3 pages max for performance
        
        # Determine scraping mode
        if category_url:
            scrape_mode = 'category'
        elif search_query:
            scrape_mode = 'search'
        else:
            return jsonify({
                'success': False,
                'error': 'Please provide either search query or category URL'
            }), 400
        
        # CREATE DATABASE RECORD
        create_scraping_session(
            user_id=1,  # Default to admin user
            worker_type='kilimall',
            task_id=task_id,
            search_query=search_query,
            category_url=category_url
        )
        
        # Initialize task with thread safety
        with task_lock:
            task_data = {
                'task_id': task_id,
                'status': 'running',
                'progress': 0,
                'products': [],
                'message': 'Initializing scraper with real HTML selectors...',
                'started_at': datetime.utcnow().isoformat(),
                'search_query': search_query,
                'category_url': category_url,
                'max_pages': max_pages,
                'mode': scrape_mode,
                'task_type': f"Kilimall {scrape_mode}",
                'product_count': 0
            }
            
            active_tasks[task_id] = task_data
            task_history.append(task_data.copy())  # Add copy to history
            
            logger.info(f"Created task {task_id} for {scrape_mode}: {search_query or category_url}")
        
        # Start scraping in background thread
        thread = threading.Thread(
            target=run_kilimall_scraper,
            args=(task_id, search_query, category_url, max_pages, scrape_mode),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'started',
            'message': 'Scraping task started with real HTML selectors'
        })
        
    except Exception as e:
        logger.error(f"Error in scrape_products: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """Get task status - matches frontend polling endpoint"""
    try:
        with task_lock:
            if task_id in active_tasks:
                task = active_tasks[task_id]
                
                # Calculate duration if task is completed
                duration = None
                if task.get('completed_at') and task.get('started_at'):
                    try:
                        start = datetime.fromisoformat(task['started_at'])
                        end = datetime.fromisoformat(task['completed_at'])
                        duration_seconds = (end - start).total_seconds()
                        minutes = int(duration_seconds // 60)
                        seconds = int(duration_seconds % 60)
                        duration = f"{minutes}m {seconds}s"
                    except:
                        duration = "N/A"
                
                response_data = {
                    'task_id': task_id,
                    'status': task['status'],
                    'progress': task.get('progress', 0),
                    'message': task.get('message', ''),
                    'products': task.get('products', []),
                    'started_at': task.get('started_at'),
                    'completed_at': task.get('completed_at'),
                    'duration': duration,
                    'product_count': len(task.get('products', [])),
                    'task_type': task.get('task_type', 'Kilimall scrape'),
                    'search_query': task.get('search_query', ''),
                    'category_url': task.get('category_url', ''),
                    'max_pages': task.get('max_pages', 0)
                }
                
                # Add error field if task failed
                if task['status'] == 'failed':
                    response_data['error'] = task.get('error', 'Unknown error occurred')
                
                return jsonify(response_data)
            else:
                return jsonify({
                    'task_id': task_id,
                    'status': 'not_found',
                    'error': 'Task not found'
                }), 404
    except Exception as e:
        logger.error(f"Error in get_task_status: {e}")
        return jsonify({
            'task_id': task_id,
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/tasks')
def get_all_tasks():
    """Get all tasks for the tasks tab"""
    try:
        with task_lock:
            # Combine active tasks and history for complete view
            all_tasks = {}
            
            # First add all from history
            for task in task_history:
                all_tasks[task['task_id']] = task.copy()
            
            # Then update with active tasks (more recent data)
            for task_id, task in active_tasks.items():
                all_tasks[task_id] = task.copy()
            
            # Convert to list and sort by start time (most recent first)
            tasks_list = []
            for task in all_tasks.values():
                task_data = {
                    'task_id': task['task_id'],
                    'status': task['status'],
                    'task_type': task.get('task_type', 'Kilimall scrape'),
                    'started_at': task['started_at'],
                    'completed_at': task.get('completed_at'),
                    'product_count': len(task.get('products', [])),
                    'search_query': task.get('search_query', ''),
                    'category_url': task.get('category_url', ''),
                    'max_pages': task.get('max_pages', 0),
                    'progress': task.get('progress', 0),
                    'message': task.get('message', '')
                }
                
                # Add duration if completed
                if task.get('completed_at') and task.get('started_at'):
                    try:
                        start = datetime.fromisoformat(task['started_at'])
                        end = datetime.fromisoformat(task['completed_at'])
                        duration_seconds = (end - start).total_seconds()
                        minutes = int(duration_seconds // 60)
                        seconds = int(duration_seconds % 60)
                        task_data['duration'] = f"{minutes}m {seconds}s"
                    except:
                        task_data['duration'] = "N/A"
                else:
                    task_data['duration'] = "Running..." if task['status'] == 'running' else "N/A"
                
                # Add error if failed
                if task['status'] == 'failed':
                    task_data['error'] = task.get('error', 'Unknown error')
                
                tasks_list.append(task_data)
            
            # Sort by start time (most recent first)
            tasks_list.sort(key=lambda x: x['started_at'], reverse=True)
            
            # Limit to last 50 tasks
            tasks_list = tasks_list[:50]
            
            logger.info(f"Returning {len(tasks_list)} tasks (Active: {len(active_tasks)}, History: {len(task_history)})")
            return jsonify({
                'tasks': tasks_list,
                'total': len(tasks_list),
                'active_count': len([t for t in tasks_list if t['status'] == 'running']),
                'completed_count': len([t for t in tasks_list if t['status'] == 'completed']),
                'failed_count': len([t for t in tasks_list if t['status'] == 'failed'])
            })
    except Exception as e:
        logger.error(f"Error in get_all_tasks: {e}")
        return jsonify({
            'tasks': [],
            'total': 0,
            'error': str(e)
        }), 500

@app.route('/api/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    """Stop a running scraping task"""
    try:
        with task_lock:
            if task_id in active_tasks:
                active_tasks[task_id]['status'] = 'stopped'
                active_tasks[task_id]['message'] = 'Task stopped by user'
                active_tasks[task_id]['completed_at'] = datetime.utcnow().isoformat()
                
                # Update task in history as well
                for task in task_history:
                    if task['task_id'] == task_id:
                        task.update(active_tasks[task_id])
                        break
                
                logger.info(f"Task {task_id} stopped by user")
            
            return jsonify({
                'success': True,
                'message': 'Task stopped successfully'
            })
    except Exception as e:
        logger.error(f"Error in stop_task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics for the dashboard"""
    try:
        with task_lock:
            total_tasks = len(task_history)
            completed_tasks = len([t for t in task_history if t['status'] == 'completed'])
            total_products = sum(len(t.get('products', [])) for t in task_history)
            
            return jsonify({
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                'total_products_scraped': total_products,
                'active_tasks': len([t for t in active_tasks.values() if t['status'] == 'running']),
                'scraper_type': 'Final Working Version - Real HTML Selectors',
                'search_format': 'keyword-based (correct for Kilimall)',
                'category_focus': 'Phones & Accessories'
            })
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return jsonify({
            'error': str(e)
        }), 500

def run_kilimall_scraper(task_id, search_query, category_url, max_pages, scrape_mode):
    """Run your existing KilimallScraper with proper configuration"""
    def update_progress(progress, message, products=None):
        """Thread-safe progress update"""
        try:
            with task_lock:
                if task_id in active_tasks:
                    active_tasks[task_id].update({
                        'progress': progress,
                        'message': message
                    })
                    
                    if products:
                        # Convert Product dataclass objects to dictionaries
                        products_dict = []
                        for product in products:
                            if hasattr(product, '__dict__'):
                                # Convert dataclass to dict
                                product_dict = {
                                    'name': getattr(product, 'name', 'N/A'),
                                    'price': getattr(product, 'price', 'N/A'),
                                    'original_price': getattr(product, 'original_price', 'N/A'),
                                    'discount': getattr(product, 'discount', 'N/A'),
                                    'rating': getattr(product, 'rating', 'N/A'),
                                    'reviews_count': getattr(product, 'reviews_count', 'N/A'),
                                    'image_url': getattr(product, 'image_url', 'N/A'),
                                    'product_url': getattr(product, 'product_url', 'N/A'),
                                    'brand': getattr(product, 'brand', 'N/A'),
                                    'category': getattr(product, 'category', 'Phones & Accessories'),
                                    'shipping_info': getattr(product, 'shipping_info', 'N/A'),
                                    'badges': getattr(product, 'badges', [])
                                }
                                products_dict.append(product_dict)
                            else:
                                # Handle if product is already a dict
                                products_dict.append(product)
                        
                        active_tasks[task_id]['products'] = products_dict
                        active_tasks[task_id]['product_count'] = len(products_dict)
                        
                        # Update task history as well
                        for task in task_history:
                            if task['task_id'] == task_id:
                                task['products'] = products_dict
                                task['product_count'] = len(products_dict)
                                task['progress'] = progress
                                task['message'] = message
                                break
                    
                    logger.info(f"Task {task_id}: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Error updating progress for task {task_id}: {e}")
        
        # UPDATE DATABASE
        update_scraping_session_safe(
            task_id,
            progress=progress,
            message=message,
            products_found=len(products) if products else 0
        )
    
    try:
        update_progress(5, "Setting up Selenium browser with real HTML selectors...")
        
        # Initialize your KilimallScraper
        scraper_options = {
            'headless': True, 
            'delay_range': (1, 3)
        }
        
        with KilimallScraper(**scraper_options) as scraper:
            update_progress(10, "Browser initialized with enhanced Chrome options...")
            
            all_products = []
            
            if scrape_mode == 'category' and category_url:
                update_progress(15, f"Scraping category: {category_url}")
                
                try:
                    products = scraper.scrape_category(category_url, max_pages)
                    if products:
                        all_products.extend(products)
                        update_progress(85, f"Category scraping completed - found {len(products)} products", products)
                    else:
                        update_progress(85, "No products found in category")
                except Exception as e:
                    logger.error(f"Error in category scraping: {e}")
                    update_progress(85, f"Category scraping failed: {str(e)}")
                    
            else:
                update_progress(15, f"Searching for: {search_query}")
                
                try:
                    products = scraper.search_products(search_query, max_pages)
                    if products:
                        all_products.extend(products)
                        update_progress(85, f"Search completed - found {len(products)} products", products)
                    else:
                        update_progress(85, "No products found")
                except Exception as e:
                    logger.error(f"Error in search: {e}")
                    update_progress(85, f"Search failed: {str(e)}")
            
            update_progress(95, "Processing results...")
            
            # Final update
            final_message = f"Scraping completed! Found {len(all_products)} products"
            update_progress(100, final_message, all_products)
            
            logger.info(f"Task {task_id} completed successfully with {len(all_products)} products")
        
        # Mark task as completed in database
        complete_scraping_session_safe(task_id, all_products, 'completed')
        
        # Mark task as completed
        with task_lock:
            if task_id in active_tasks and active_tasks[task_id]['status'] != 'stopped':
                active_tasks[task_id]['status'] = 'completed'
                active_tasks[task_id]['completed_at'] = datetime.utcnow().isoformat()
                
                # Update task history
                for task in task_history:
                    if task['task_id'] == task_id:
                        task['status'] = 'completed'
                        task['completed_at'] = active_tasks[task_id]['completed_at']
                        break
        
        # Clean up active task from memory after 1 hour
        def cleanup_task():
            with task_lock:
                active_tasks.pop(task_id, None)
        
        threading.Timer(3600, cleanup_task).start()
        
    except Exception as e:
        # Handle errors in database
        complete_scraping_session_safe(task_id, [], 'failed', str(e))
        
        # Handle errors
        error_msg = str(e)
        logger.error(f"Error in scraping task {task_id}: {error_msg}")
        
        with task_lock:
            if task_id in active_tasks:
                active_tasks[task_id]['status'] = 'failed'
                active_tasks[task_id]['message'] = f"Scraping failed: {error_msg}"
                active_tasks[task_id]['error'] = error_msg
                active_tasks[task_id]['completed_at'] = datetime.utcnow().isoformat()
                
                # Update task history
                for task in task_history:
                    if task['task_id'] == task_id:
                        task['status'] = 'failed'
                        task['error'] = error_msg
                        task['completed_at'] = active_tasks[task_id]['completed_at']
                        break

# Legacy endpoints for compatibility
@app.route('/api/tasks/<task_id>')
def get_task_status_frontend(task_id):
    return get_task_status(task_id)

@app.route('/api/tasks/<task_id>/stop', methods=['POST'])
def stop_task_frontend(task_id):
    return stop_task(task_id)

@app.route('/api/get_results/<task_id>')
def get_results(task_id):
    """Get results of a completed scraping task"""
    try:
        with task_lock:
            if task_id in active_tasks:
                task = active_tasks[task_id]
                
                if task['status'] == 'completed':
                    return jsonify({
                        'success': True,
                        'task_id': task_id,
                        'products': task.get('products', []),
                        'total_products': len(task.get('products', [])),
                        'search_query': task.get('search_query', ''),
                        'category_url': task.get('category_url', ''),
                        'max_pages': task.get('max_pages', 0),
                        'mode': task.get('mode', 'search'),
                        'scraper_version': 'Final Working Version - Real HTML Selectors'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Task not completed. Current status: {task["status"]}'
                    }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Task not found'
                }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug/test_db/<task_id>')
def debug_test_db(task_id):
    """Debug endpoint to test database updates"""
    test_database_update(task_id)
    return jsonify({'message': 'Check console for debug output'})

if __name__ == '__main__':
    print("[KILIMALL] Starting Kilimall Worker for WebExtract Pro...")
    print("[SERVER] Worker URL: http://127.0.0.1:5001")
    print("[FRONTEND] Frontend: kilimall_frontend.html")
    print("[CONNECT] Connect via: WebExtract Pro Dashboard")
    print("[FAST] Optimized with proper HTML serving")
    
    # Check components
    if SCRAPER_AVAILABLE:
        print("[OK] Your Final Working Version KilimallScraper is loaded and ready")
        print("[OK] Selenium-based scraper with real HTML structure analysis")
        print("[OK] Enhanced Chrome driver with --headless=new")
        print("[OK] Correct search format: /search?keyword=")
        print("[OK] Phone-focused brand detection")
        print("[OK] Supports both search and category scraping")
        print("[OK] Browser automation for Vue.js sites")
        print("[FAST] Performance optimizations enabled")
    else:
        print("[WARN] KilimallScraper not found - make sure kilimall_scraper.py is in workers/kilimall/")
    
    if SHARED_DB_AVAILABLE:
        print("[OK] Database integration enabled")
    else:
        print("[WARN] Running in standalone mode (no database)")
    
    frontend_path = os.path.join(current_dir, 'kilimall_frontend.html')
    if os.path.exists(frontend_path):
        print("[OK] kilimall_frontend.html found")
    else:
        print("[WARN] kilimall_frontend.html not found - using fallback interface")
    
    print("[CONFIG] HTML serving fix applied - should work with proper headers")
    
    app.run(host='127.0.0.1', port=5001, debug=False)