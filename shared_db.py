# shared_db.py - WebExtract Pro Database Models
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    """User model for WebExtract Pro authentication"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    sessions = db.relationship('ScrapingSession', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

class ScrapingSession(db.Model):
    """Model to track all scraping sessions in WebExtract Pro"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    worker_type = db.Column(db.String(50), nullable=False)  # 'kilimall' or 'jumia'
    task_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    search_query = db.Column(db.String(200))
    category_url = db.Column(db.Text)
    pages_scraped = db.Column(db.Integer, default=0)
    products_found = db.Column(db.Integer, default=0)
    products_data = db.Column(db.Text)  # JSON string of scraped products
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    progress = db.Column(db.Integer, default=0)  # 0-100 percentage
    message = db.Column(db.String(200))  # Current status message
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'worker_type': self.worker_type,
            'task_id': self.task_id,
            'status': self.status,
            'search_query': self.search_query,
            'category_url': self.category_url,
            'pages_scraped': self.pages_scraped,
            'products_found': self.products_found,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'progress': self.progress,
            'message': self.message
        }

class DatabaseManager:
    """Database initialization and management for WebExtract Pro"""
    
    @staticmethod
    def init_app(app):
        """Initialize database with Flask app"""
        # Database configuration
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webextract_pro.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize extensions
        db.init_app(app)
        bcrypt.init_app(app)
        
        # Create tables and admin user
        with app.app_context():
            db.create_all()
            DatabaseManager.create_admin_user()
    
    @staticmethod
    def create_admin_user():
        """Create default admin user if doesn't exist"""
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
    
    @staticmethod
    def get_user_stats(user_id):
        """Get statistics for a specific user"""
        sessions = ScrapingSession.query.filter_by(user_id=user_id).all()
        
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == 'completed'])
        failed_sessions = len([s for s in sessions if s.status == 'failed'])
        total_products = sum(s.products_found for s in sessions if s.products_found)
        
        # Group by worker type
        kilimall_sessions = [s for s in sessions if s.worker_type == 'kilimall']
        jumia_sessions = [s for s in sessions if s.worker_type == 'jumia']
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'failed_sessions': failed_sessions,
            'success_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            'total_products': total_products,
            'kilimall': {
                'sessions': len(kilimall_sessions),
                'products': sum(s.products_found for s in kilimall_sessions if s.products_found)
            },
            'jumia': {
                'sessions': len(jumia_sessions),
                'products': sum(s.products_found for s in jumia_sessions if s.products_found)
            }
        }
    
    @staticmethod
    def get_system_stats():
        """Get system-wide statistics for admin dashboard"""
        total_users = User.query.count()
        total_sessions = ScrapingSession.query.count()
        completed_sessions = ScrapingSession.query.filter_by(status='completed').count()
        total_products = db.session.query(db.func.sum(ScrapingSession.products_found)).scalar() or 0
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_sessions = ScrapingSession.query.filter(ScrapingSession.started_at >= week_ago).count()
        
        return {
            'total_users': total_users,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'success_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            'total_products': total_products,
            'recent_activity': recent_sessions
        }
    
    @staticmethod
    def get_recent_sessions(user_id=None, limit=10):
        """Get recent scraping sessions"""
        query = ScrapingSession.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        return query.order_by(ScrapingSession.started_at.desc()).limit(limit).all()