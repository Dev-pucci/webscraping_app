# jumia_worker.py - WebExtract Pro Worker (Fixed API Compatibility)
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
import os
import sys
import uuid

# Fix path to find shared_db.py (go up 2 directories from workers/jumia/)
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
app.config['SECRET_KEY'] = 'webextract-pro-jumia-worker-2025'
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
JumiaScraper = None

try:
    # Import your JumiaScraper class
    from jumia_scraper import JumiaScraper
    SCRAPER_AVAILABLE = True
    print("[OK] JumiaScraper class imported successfully")
    print("[OK] Your trained requests-based scraper is ready")
except ImportError as e:
    print(f"[WARN] Could not import JumiaScraper: {e}")
    print("[WARN] Make sure jumia_scraper.py is in the workers/jumia/ directory")

# Active tasks storage
active_tasks = {}
task_history = []

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
                    # Convert products to JSON string
                    if isinstance(products_data, list):
                        session.products_data = json.dumps(products_data)
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
    """Serve your existing index.html exactly as it is"""
    try:
        return send_from_directory(current_dir, 'index.html')
    except FileNotFoundError:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Jumia Worker - WebExtract Pro</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #dc2626; color: white; padding: 20px; }}
                .error {{ background: #ff4444; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .info {{ background: #ff8800; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>[JUMIA] Jumia Worker - WebExtract Pro</h1>
            <div class="error">
                <h3>Frontend File Missing</h3>
                <p><strong>index.html</strong> not found in workers/jumia/ directory.</p>
                <p>Please ensure your frontend file is in the correct location.</p>
            </div>
            <div class="info">
                <h3>Worker Status</h3>
                <p>[OK] Jumia Worker is running on port 5000</p>
                <p>{'[OK] JumiaScraper loaded' if SCRAPER_AVAILABLE else '[ERROR] JumiaScraper not found'}</p>
                <p>📊 <a href="/api/health" style="color: #ffff88;">Health Check</a></p>
            </div>
            <p><a href="http://127.0.0.1:8000/dashboard" style="color: #ffff88;">← Back to Dashboard</a></p>
        </body>
        </html>
        """

# Serve all static files from the current directory
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files like CSS, JS, images"""
    return send_from_directory(current_dir, filename)

@app.route('/<path:filename>')
def serve_files(filename):
    """Serve any file from the jumia directory (for compatibility)"""
    try:
        # Only serve safe file types
        safe_extensions = ['.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.json']
        if any(filename.lower().endswith(ext) for ext in safe_extensions):
            return send_from_directory(current_dir, filename)
        else:
            return jsonify({'error': 'File type not allowed'}), 403
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'jumia-worker',
        'platform': 'webextract-pro',
        'scraper_available': SCRAPER_AVAILABLE,
        'scraper_type': 'Requests-based JumiaScraper' if SCRAPER_AVAILABLE else 'Not available',
        'database_available': SHARED_DB_AVAILABLE,
        'frontend_available': os.path.exists(os.path.join(current_dir, 'index.html')),
        'mode': 'integrated' if SCRAPER_AVAILABLE else 'api-only'
    })

@app.route('/api/scrape', methods=['POST'])
def scrape_products():
    """Main scraping endpoint - matches frontend API calls"""
    try:
        if not SCRAPER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'JumiaScraper not available. Please ensure jumia_scraper.py is in the correct directory.'
            }), 500
        
        data = request.get_json()
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        
        # Extract parameters matching frontend expectations
        search_query = data.get('search', '')
        category_url = data.get('categoryUrl', '')
        max_pages = data.get('pages', 3)
        
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
            worker_type='jumia',
            task_id=task_id,
            search_query=search_query,
            category_url=category_url
        )
        
        # Initialize task
        task_data = {
            'task_id': task_id,
            'status': 'running',
            'progress': 0,
            'products': [],
            'message': 'Initializing scraper...',
            'started_at': datetime.utcnow().isoformat(),
            'search_query': search_query,
            'category_url': category_url,
            'max_pages': max_pages,
            'mode': scrape_mode,
            'task_type': f"Jumia {scrape_mode}",
            'product_count': 0
        }
        
        active_tasks[task_id] = task_data
        task_history.append(task_data)
        
        # Start scraping in background thread
        thread = threading.Thread(
            target=run_jumia_scraper,
            args=(task_id, search_query, category_url, max_pages, scrape_mode)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'started',
            'message': 'Scraping task started successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """Get task status - matches frontend polling endpoint"""
    try:
        if task_id in active_tasks:
            task = active_tasks[task_id]
            
            # Calculate duration if task is completed
            duration = None
            if task.get('completed_at') and task.get('started_at'):
                start = datetime.fromisoformat(task['started_at'])
                end = datetime.fromisoformat(task['completed_at'])
                duration_seconds = (end - start).total_seconds()
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                duration = f"{minutes}m {seconds}s"
            
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
                'task_type': task.get('task_type', 'Jumia scrape'),
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
        return jsonify({
            'task_id': task_id,
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/tasks')
def get_all_tasks():
    """Get all tasks for the tasks tab"""
    try:
        # Return tasks from history (most recent first)
        tasks_list = []
        for task in reversed(task_history[-50:]):  # Last 50 tasks
            task_data = {
                'task_id': task['task_id'],
                'status': task['status'],
                'task_type': task.get('task_type', 'Jumia scrape'),
                'started_at': task['started_at'],
                'completed_at': task.get('completed_at'),
                'product_count': len(task.get('products', [])),
                'search_query': task.get('search_query', ''),
                'category_url': task.get('category_url', ''),
                'max_pages': task.get('max_pages', 0)
            }
            
            # Add duration if completed
            if task.get('completed_at') and task.get('started_at'):
                start = datetime.fromisoformat(task['started_at'])
                end = datetime.fromisoformat(task['completed_at'])
                duration_seconds = (end - start).total_seconds()
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                task_data['duration'] = f"{minutes}m {seconds}s"
            
            # Add error if failed
            if task['status'] == 'failed':
                task_data['error'] = task.get('error', 'Unknown error')
            
            tasks_list.append(task_data)
        
        return jsonify({
            'tasks': tasks_list,
            'total': len(tasks_list)
        })
    except Exception as e:
        return jsonify({
            'tasks': [],
            'total': 0,
            'error': str(e)
        }), 500

@app.route('/api/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    """Stop a running scraping task"""
    try:
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'stopped'
            active_tasks[task_id]['message'] = 'Task stopped by user'
            active_tasks[task_id]['completed_at'] = datetime.utcnow().isoformat()
            
        return jsonify({
            'success': True,
            'message': 'Task stopped successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get statistics for the dashboard"""
    try:
        total_tasks = len(task_history)
        completed_tasks = len([t for t in task_history if t['status'] == 'completed'])
        total_products = sum(len(t.get('products', [])) for t in task_history)
        
        return jsonify({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'total_products_scraped': total_products,
            'active_tasks': len([t for t in active_tasks.values() if t['status'] == 'running']),
            'scraper_type': 'Requests-based JumiaScraper'
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

def run_jumia_scraper(task_id, search_query, category_url, max_pages, scrape_mode):
    """Run your existing JumiaScraper with proper integration"""
    try:
        def update_progress(progress, message, products=None):
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
                                'name': product.name,
                                'price': product.price,
                                'original_price': product.original_price,
                                'discount': product.discount,
                                'rating': product.rating,
                                'reviews_count': product.reviews_count,
                                'image_url': product.image_url,
                                'product_url': product.product_url,
                                'brand': product.brand,
                                'category': product.category,
                                'shipping_info': getattr(product, 'shipping_info', 'N/A'),
                                'badges': getattr(product, 'badges', [])
                            }
                            products_dict.append(product_dict)
                        else:
                            products_dict.append(product)
                    
                    active_tasks[task_id]['products'] = products_dict
                    active_tasks[task_id]['product_count'] = len(products_dict)
                    
                    # Update task history as well
                    for task in task_history:
                        if task['task_id'] == task_id:
                            task['products'] = products_dict
                            task['product_count'] = len(products_dict)
                            break
            
            # UPDATE DATABASE
            update_scraping_session_safe(
                task_id,
                progress=progress,
                message=message,
                products_found=len(products) if products else 0
            )
        
        update_progress(5, "Setting up HTTP session...")
        
        # Initialize your JumiaScraper
        scraper = JumiaScraper(delay_range=(1, 3))
        
        update_progress(10, "HTTP session initialized, starting scraping...")
        
        all_products = []
        
        if scrape_mode == 'category' and category_url:
            update_progress(15, f"Scraping category: {category_url}")
            
            # Use your scrape_category method
            products = scraper.scrape_category(category_url, max_pages)
            
            if products:
                all_products.extend(products)
                update_progress(90, f"Category scraping completed", products)
            else:
                update_progress(90, "No products found in category")
                
        else:
            update_progress(15, f"Searching for: {search_query}")
            
            # Use your search_products method
            products = scraper.search_products(search_query, max_pages)
            
            if products:
                all_products.extend(products)
                update_progress(90, f"Search completed", products)
            else:
                update_progress(90, "No products found")
        
        update_progress(95, "Processing results...")
        
        # Final update
        update_progress(
            100, 
            f"Scraping completed! Found {len(all_products)} products",
            all_products
        )
        
        # Mark task as completed in database
        complete_scraping_session_safe(task_id, all_products, 'completed')
        
        # Mark task as completed
        if task_id in active_tasks and active_tasks[task_id]['status'] != 'stopped':
            active_tasks[task_id]['status'] = 'completed'
            active_tasks[task_id]['completed_at'] = datetime.utcnow().isoformat()
            
            # Update task history
            for task in task_history:
                if task['task_id'] == task_id:
                    task['status'] = 'completed'
                    task['completed_at'] = active_tasks[task_id]['completed_at']
                    break
        
        # Clean up active task from memory after 2 hours (keep in history)
        threading.Timer(7200, lambda: active_tasks.pop(task_id, None)).start()
        
    except Exception as e:
        # Handle errors in database
        complete_scraping_session_safe(task_id, [], 'failed', str(e))
        
        # Handle errors
        error_msg = str(e)
        
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
        
        print(f"Error in scraping task {task_id}: {error_msg}")

# Legacy endpoints for compatibility
@app.route('/api/run_scraper', methods=['POST'])
def run_scraper():
    """Legacy endpoint - redirects to main scrape endpoint"""
    return scrape_products()

@app.route('/api/task_status/<task_id>')
def get_task_status_legacy(task_id):
    """Legacy endpoint"""
    return get_task_status(task_id)

@app.route('/api/scrape/<task_id>/status')
def get_task_status_alt(task_id):
    """Alternative endpoint for compatibility"""
    return get_task_status(task_id)

@app.route('/api/scrape/<task_id>/stop', methods=['POST'])
def stop_task_alt(task_id):
    """Alternative endpoint for compatibility"""
    return stop_task(task_id)

@app.route('/api/get_results/<task_id>')
def get_results(task_id):
    """Get results of a completed scraping task"""
    try:
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
                    'mode': task.get('mode', 'search')
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
    print("[JUMIA] Starting Jumia Worker for WebExtract Pro...")
    print("[SERVER] Worker URL: http://127.0.0.1:5000")
    print("[FRONTEND] Frontend: index.html")
    print("[CONNECT] Connect via: WebExtract Pro Dashboard")
    
    # Check components
    if SCRAPER_AVAILABLE:
        print("[OK] Your existing JumiaScraper class is loaded and ready")
        print("[OK] Requests-based scraper with BeautifulSoup parsing")
        print("[OK] Supports both search and category scraping")
        print("[OK] Fast and efficient HTTP-based scraping")
    else:
        print("[WARN] JumiaScraper not found - make sure jumia_scraper.py is in workers/jumia/")
    
    if SHARED_DB_AVAILABLE:
        print("[OK] Database integration enabled")
    else:
        print("[WARN] Running in standalone mode (no database)")
    
    frontend_path = os.path.join(current_dir, 'index.html')
    if os.path.exists(frontend_path):
        print("[OK] index.html found")
    else:
        print("[WARN] index.html not found - using fallback interface")
    
    app.run(host='127.0.0.1', port=5000, debug=True)