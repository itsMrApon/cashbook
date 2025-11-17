import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Database configuration - prefer DATABASE_URL but test connection first
    database_url = os.environ.get("DATABASE_URL")
    use_sqlite = False
    
    if database_url and 'postgres' in database_url.lower():
        # Test PostgreSQL connection before committing to it
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
            
            # Connection successful, use PostgreSQL
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }
            logging.info("Using PostgreSQL database")
        except Exception as e:
            # PostgreSQL connection failed, fall back to SQLite
            logging.warning(f"PostgreSQL connection test failed: {str(e)}")
            logging.info("Falling back to SQLite database")
            use_sqlite = True
    else:
        # No DATABASE_URL or not PostgreSQL
        use_sqlite = True
    
    if use_sqlite:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cashbook.db"
        if not database_url:
            logging.info("No DATABASE_URL found, using SQLite database")
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # File upload configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Initialize extensions (only once)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        # Import models to ensure they are created
        import models
        db.create_all()
        
        # Create default admin user if none exists
        from models import User, Role
        from werkzeug.security import generate_password_hash
        
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
            
        # Create default categories if none exist
        from models import Category
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
    
    return app

# Create the app instance
app = create_app()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))
