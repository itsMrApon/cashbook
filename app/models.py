"""
===========================================
MODEL LAYER - MVC ARCHITECTURE
===========================================
This file contains all database models (the "M" in MVC).

MODEL RESPONSIBILITIES:
- Define database schema (tables, columns, relationships)
- Handle data validation rules
- Contain business logic related to data
- Provide methods to interact with database

In Django terms: This is equivalent to models.py in a Django app.
"""

# ===========================================
# STEP 1: Import required libraries
# ===========================================
from datetime import datetime, date
from flask_login import UserMixin  # Provides user authentication methods
from sqlalchemy import func
from app import db  # Database instance from app/__init__.py

# ===========================================
# STEP 2: Define Role Model (Many-to-One with User)
# ===========================================
# This represents user roles (Admin, Manager, Viewer)
# In MVC: This is the MODEL - defines data structure
class Role(db.Model):
    # Step 2a: Define table name in database
    __tablename__ = 'roles'
    
    # Step 2b: Define columns (fields) in the table
    id = db.Column(db.Integer, primary_key=True)  # Primary key
    name = db.Column(db.String(50), unique=True, nullable=False)  # Role name
    description = db.Column(db.Text)  # Role description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp
    
    # Step 2c: Define relationship (one Role can have many Users)
    # This creates a reverse relationship: role.users to get all users with this role
    users = db.relationship('User', backref='role', lazy=True)

# ===========================================
# STEP 3: Define User Model (Core Model)
# ===========================================
# This represents users in the system
# In MVC: This is the MODEL - defines user data structure
class User(UserMixin, db.Model):
    # Step 3a: Define table name
    __tablename__ = 'users'
    
    # Step 3b: Define user fields (columns in database)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Hashed password, never store plain text
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    _is_active = db.Column('is_active', db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Step 3c: Define foreign key (User belongs to a Role)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # Step 3d: Define relationships (one User can have many Transactions)
    # These create reverse relationships for easy data access
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    spending_limits = db.relationship('SpendingLimit', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Step 3e: Property methods (business logic in Model)
    @property
    def is_active(self):
        """Required by Flask-Login UserMixin"""
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value
    
    # Step 3f: Business logic method (Model layer responsibility)
    def get_full_name(self):
        """Return user's full name or username"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    # Step 3g: Permission checking method (business logic)
    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        role_permissions = {
            'Admin': ['create', 'read', 'update', 'delete', 'manage_users', 'reports', 'backup'],
            'Manager': ['create', 'read', 'update', 'delete', 'reports'],
            'Viewer': ['read', 'reports']
        }
        return permission in role_permissions.get(self.role.name, [])

# ===========================================
# STEP 4: Define Category Model
# ===========================================
# Categories for transactions (Food, Transportation, etc.)
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Hex color code for UI
    is_system = db.Column(db.Boolean, default=False)  # System categories cannot be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship: one Category can have many Transactions
    transactions = db.relationship('Transaction', backref='category', lazy=True)

# ===========================================
# STEP 5: Define Tag Model
# ===========================================
# Tags for categorizing transactions (Many-to-Many with Transaction)
class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===========================================
# STEP 6: Association Table (Many-to-Many Relationship)
# ===========================================
# This table links Transactions and Tags (many-to-many relationship)
# One transaction can have many tags, one tag can be on many transactions
transaction_tags = db.Table('transaction_tags',
    db.Column('transaction_id', db.Integer, db.ForeignKey('transactions.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# ===========================================
# STEP 7: Define Transaction Model (Core Business Model)
# ===========================================
# This is the main model - represents income/expense transactions
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    # Step 7a: Define transaction fields
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # Decimal with 2 decimal places
    description = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    party = db.Column(db.String(200))  # Person/organization involved
    transaction_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Step 7b: Foreign keys (Transaction belongs to User and Category)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Step 7c: Relationships
    # Many-to-many with Tags (through association table)
    tags = db.relationship('Tag', secondary=transaction_tags, lazy='subquery',
                          backref=db.backref('transactions', lazy=True))
    # One-to-many with Receipts (one Transaction can have many Receipts)
    receipts = db.relationship('Receipt', backref='transaction', lazy=True, cascade='all, delete-orphan')

# ===========================================
# STEP 8: Define Receipt Model
# ===========================================
# Stores uploaded receipt files for transactions
class Receipt(db.Model):
    __tablename__ = 'receipts'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Stored filename
    original_filename = db.Column(db.String(255), nullable=False)  # Original filename
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))  # File type (image/png, application/pdf, etc.)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key: Receipt belongs to a Transaction
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)

# ===========================================
# STEP 9: Define SpendingLimit Model
# ===========================================
# Spending limits for users (daily/monthly limits)
class SpendingLimit(db.Model):
    __tablename__ = 'spending_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'daily' or 'monthly'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # Optional: limit per category
    
    # Step 9a: Business logic methods (Model layer responsibility)
    def get_period_start(self):
        """Get the start date for the current period"""
        today = date.today()
        if self.type == 'daily':
            return today
        elif self.type == 'monthly':
            return today.replace(day=1)
        return today
    
    def get_spent_amount(self):
        """Get amount spent in current period (queries Transaction model)"""
        period_start = self.get_period_start()
        query = Transaction.query.filter(
            Transaction.user_id == self.user_id,
            Transaction.type == 'expense',
            Transaction.transaction_date >= period_start
        )
        
        if self.category_id:
            query = query.filter(Transaction.category_id == self.category_id)
            
        result = query.with_entities(func.sum(Transaction.amount)).scalar()
        return result or 0
    
    def is_exceeded(self):
        """Check if spending limit is exceeded"""
        return self.get_spent_amount() > self.amount

# ===========================================
# STEP 10: Define SystemSetting Model
# ===========================================
# Key-value store for system settings
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ===========================================
# STEP 11: Define AuditLog Model
# ===========================================
# Logs all user actions for security and compliance
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)  # 'login', 'create_transaction', etc.
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship: AuditLog belongs to a User
    user = db.relationship('User', backref='audit_logs')
