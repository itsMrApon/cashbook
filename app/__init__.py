"""
===========================================
FLASK APPLICATION FACTORY - MVC SETUP
===========================================
This file sets up the Flask application using the Application Factory pattern.
It initializes all components needed for the MVC architecture.

MVC COMPONENTS IN THIS FILE:
- Step 1-3: Initialize database (Model layer support)
- Step 4-6: Configure application settings
- Step 7-9: Register blueprints (Controller layer)
- Step 10: Error handlers (Controller layer)
"""

# ===========================================
# STEP 1: Import required libraries
# ===========================================
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy  # ORM for Model layer
from flask_login import LoginManager     # Authentication support
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# ===========================================
# STEP 2: Define base class for SQLAlchemy models
# ===========================================
# This is used by all Model classes (app/models.py)
class Base(DeclarativeBase):
    pass

# ===========================================
# STEP 3: Initialize Flask extensions
# ===========================================
# These are initialized here but configured in create_app()
# - db: Database ORM (Model layer support)
# - login_manager: User authentication (Controller layer support)
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# ===========================================
# STEP 4: Application Factory Function
# ===========================================
# This function creates and configures the Flask app instance
# This is the Flask equivalent of Django's settings.py
def create_app():
    # Step 4a: Create Flask application instance
    app = Flask(__name__)
    
    # Step 4b: Configure application secret key (for sessions/cookies)
    # REQUIRED: Set SESSION_SECRET environment variable in Vercel
    app.secret_key = os.environ.get("SESSION_SECRET") or "dev-secret-key-change-in-production"
    if not os.environ.get("SESSION_SECRET"):
        logging.warning("SESSION_SECRET not set! Using default (not secure for production)")
    
    # Step 4c: Configure proxy settings (for production behind reverse proxy)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # ===========================================
    # STEP 5: Database Configuration (Model Layer Setup)
    # ===========================================
    # Step 5a: Check for PostgreSQL database URL
    database_url = os.environ.get("DATABASE_URL")
    use_sqlite = False
    
    if database_url and 'postgres' in database_url.lower():
        # Step 5b: Test PostgreSQL connection before committing
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            # Parse the DATABASE_URL to extract connection parameters
            parsed = urlparse(database_url)
            test_conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:] if parsed.path else 'postgres'
            )
            test_conn.close()
            
            # Step 5c: Connection successful, use PostgreSQL
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }
            logging.info("Using PostgreSQL database")
        except Exception as e:
            # Step 5d: PostgreSQL connection failed, fall back to SQLite
            logging.warning(f"PostgreSQL connection test failed: {str(e)}")
            logging.info("Falling back to SQLite database")
            use_sqlite = True
    else:
        # Step 5e: No DATABASE_URL or not PostgreSQL
        use_sqlite = True
    
    # Step 5f: Configure SQLite as fallback/default database
    if use_sqlite:
        # On Vercel, use /tmp directory for SQLite (writable filesystem)
        # In production, you should use PostgreSQL instead
        if os.environ.get("VERCEL"):
            db_path = "/tmp/cashbook.db"
        else:
            db_path = "cashbook.db"
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        if not database_url:
            logging.info("No DATABASE_URL found, using SQLite database")
    
    # Step 5g: Disable SQLAlchemy modification tracking (performance)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # ===========================================
    # STEP 6: Application Configuration
    # ===========================================
    # Step 6a: File upload configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    # On Vercel, use /tmp directory (writable filesystem)
    # In production, consider using cloud storage (S3, etc.)
    if os.environ.get("VERCEL"):
        app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    else:
        app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    
    # Step 6b: Initialize extensions with app instance
    db.init_app(app)  # Connect database to app
    login_manager.init_app(app)  # Connect login manager to app
    
    # Step 6c: Configure login manager settings
    login_manager.login_view = 'main.login'  # Redirect to login if not authenticated
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Step 6d: Create upload directory if it doesn't exist
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except Exception as e:
        logging.warning(f"Could not create upload directory: {str(e)}")
    
    # ===========================================
    # STEP 7: Database Initialization (Model Layer)
    # ===========================================
    # Step 7a: Create application context (required for database operations)
    with app.app_context():
        # Step 7b: Import models to register them with SQLAlchemy
        from app import models
        
        # Step 7c: Create all database tables based on Model definitions
        # This reads app/models.py and creates tables for User, Transaction, etc.
        db.create_all()
        
        # Step 7d: Seed database with initial data (Roles)
        from app.models import User, Role
        from werkzeug.security import generate_password_hash
        
        # Step 7e: Create default roles if none exist
        if not Role.query.first():
            admin_role = Role()
            admin_role.name = 'Admin'
            admin_role.description = 'Full system access'
            
            manager_role = Role()
            manager_role.name = 'Manager'
            manager_role.description = 'Add/view transactions, manage expenses, generate reports'
            
            viewer_role = Role()
            viewer_role.name = 'Viewer'
            viewer_role.description = 'Read-only access to data and reports'
            
            db.session.add(admin_role)
            db.session.add(manager_role)
            db.session.add(viewer_role)
            db.session.commit()
        
        # Step 7f: Create default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            admin_role = Role.query.filter_by(name='Admin').first()
            admin_user = User()
            admin_user.username = 'admin'
            admin_user.email = 'admin@cashbook.com'
            admin_user.password_hash = generate_password_hash('admin123')
            admin_user.role_id = admin_role.id
            admin_user.is_active = True
            db.session.add(admin_user)
            db.session.commit()
            logging.info("Default admin user created: admin/admin123")
        
        # Step 7g: Create default categories if none exist
        from app.models import Category
        if not Category.query.first():
            default_categories = [
                {'name': 'Food & Dining', 'color': '#FF6B6B', 'is_system': True},
                {'name': 'Transportation', 'color': '#4ECDC4', 'is_system': True},
                {'name': 'Shopping', 'color': '#45B7D1', 'is_system': True},
                {'name': 'Entertainment', 'color': '#96CEB4', 'is_system': True},
                {'name': 'Bills & Utilities', 'color': '#FECA57', 'is_system': True},
                {'name': 'Healthcare', 'color': '#FF9FF3', 'is_system': True},
                {'name': 'Salary', 'color': '#54A0FF', 'is_system': True},
                {'name': 'Investment', 'color': '#5F27CD', 'is_system': True},
                {'name': 'Other', 'color': '#999999', 'is_system': True}
            ]
            
            for cat_data in default_categories:
                category = Category()
                category.name = cat_data['name']
                category.color = cat_data['color']
                category.is_system = cat_data['is_system']
                db.session.add(category)
            
            db.session.commit()
    
    # ===========================================
    # STEP 8: Register Blueprints (Controller Layer)
    # ===========================================
    # Step 8a: Import the main blueprint (contains all routes/controllers)
    # Blueprints are Flask's way of organizing routes (like Django's urls.py)
    from app.routes import main as main_blueprint
    
    # Step 8b: Register the blueprint with the app
    # This connects all routes in app/routes.py to the Flask app
    app.register_blueprint(main_blueprint)
    
    # ===========================================
    # STEP 9: Register Error Handlers (Controller Layer)
    # ===========================================
    # These handle HTTP error responses
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        from flask import render_template
        return render_template('errors/500.html'), 500
    
    # Step 9a: Return configured app instance
    return app

# ===========================================
# STEP 10: User Loader Function (Authentication)
# ===========================================
# This function is called by Flask-Login to load a user from the database
# It's part of the authentication system (Controller layer support)
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
