"""
===========================================
CONTROLLER LAYER - MVC ARCHITECTURE
===========================================
This file contains all route handlers (the "C" in MVC).

CONTROLLER RESPONSIBILITIES:
- Handle HTTP requests (GET, POST, etc.)
- Process user input and validate data
- Coordinate between Model and View
- Execute business logic
- Return responses (render templates or JSON)

In Django terms: This is equivalent to views.py in a Django app.
Flask routes = Django views (both are Controllers in MVC)
"""

# ===========================================
# STEP 1: Import required libraries
# ===========================================
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session, abort, send_from_directory, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import or_, and_, func, desc
from app import db  # Database instance
from app.models import User, Role, Transaction, Category, Tag, Receipt, SpendingLimit, AuditLog, transaction_tags  # MODEL layer
from app.forms import (LoginForm, RegistrationForm, TransactionForm, CategoryForm, SpendingLimitForm, 
                  ReportForm, SearchForm, ProfileForm, ChangePasswordForm, UserForm)  # Form validation
from app.utils import (save_uploaded_file, delete_file, format_currency, parse_tags, 
                  generate_pdf_report, generate_excel_report, log_audit_action, 
                  get_dashboard_stats, backup_database)  # Helper functions
from io import BytesIO

# ===========================================
# STEP 2: Create Blueprint (Organize Routes)
# ===========================================
# Blueprints are Flask's way to organize routes (like Django's URL patterns)
# This groups all routes under the 'main' blueprint
main = Blueprint('main', __name__)

# ===========================================
# STEP 3: Context Processor (Make functions available in templates)
# ===========================================
# This makes utility functions available in all templates (VIEW layer)
@main.context_processor
def utility_processor():
    """Make utility functions available in templates"""
    return dict(
        format_currency=format_currency,
        len=len,
        str=str,
        int=int,
        enumerate=enumerate
    )

# ===========================================
# STEP 4: Homepage Route (GET request)
# ===========================================
# MVC FLOW: User Request → Controller → Model → View → Response
@main.route('/')
def index():
    """
    Homepage route - demonstrates basic MVC flow
    
    Step 4a: Receive HTTP GET request from user
    Step 4b: Check if user is authenticated (Controller logic)
    Step 4c: Redirect to dashboard if logged in, or show landing page
    Step 4d: Render template (VIEW layer) and return HTML response
    """
    # Controller logic: Check authentication status
    if current_user.is_authenticated:
        # Redirect to dashboard (another Controller route)
        return redirect(url_for('main.dashboard'))
    # Render VIEW (template) - returns HTML to user
    return render_template('index.html')

# ===========================================
# STEP 5: Login Route (GET and POST requests)
# ===========================================
# This demonstrates full MVC cycle with form handling
@main.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route - Full MVC example
    
    GET REQUEST FLOW:
    Step 5a: User visits /login (GET request)
    Step 5b: Controller creates form instance
    Step 5c: Controller renders VIEW (login.html template) with form
    Step 5d: VIEW displays login form to user
    
    POST REQUEST FLOW:
    Step 5e: User submits login form (POST request)
    Step 5f: Controller validates form data
    Step 5g: Controller queries MODEL (User.query) to find user
    Step 5h: Controller checks password (business logic)
    Step 5i: Controller logs user in (session management)
    Step 5j: Controller queries MODEL (log_audit_action) to log action
    Step 5k: Controller redirects to dashboard (or renders error VIEW)
    """
    # Step 5a: Check if already logged in (Controller logic)
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Step 5b: Create form instance (form validation)
    form = LoginForm()
    
    # Step 5c: Handle form submission (POST request)
    if form.validate_on_submit():
        # Step 5d: Query MODEL layer - find user by username
        user = User.query.filter_by(username=form.username.data).first()
        
        # Step 5e: Controller business logic - verify password
        if user and check_password_hash(user.password_hash, form.password.data):
            # Step 5f: Controller business logic - check if user is active
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                # Render VIEW with error message
                return render_template('login.html', form=form)
            
            # Step 5g: Controller - log user in (session management)
            login_user(user, remember=form.remember_me.data)
            
            # Step 5h: Query MODEL layer - log audit action
            log_audit_action(user.id, 'login')
            
            # Step 5i: Controller - determine redirect destination
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            
            # Step 5j: Controller - redirect to dashboard
            return redirect(next_page)
        
        # Step 5k: Controller - show error message
        flash('Invalid username or password', 'error')
    
    # Step 5l: Render VIEW (template) - display login form
    return render_template('login.html', form=form)

# ===========================================
# STEP 6: Logout Route
# ===========================================
@main.route('/logout')
@login_required  # Decorator ensures user must be logged in
def logout():
    """
    User logout route
    
    Step 6a: User clicks logout link (GET request)
    Step 6b: Controller queries MODEL to log action
    Step 6c: Controller logs user out (session management)
    Step 6d: Controller redirects to homepage
    """
    # Query MODEL layer - log audit action
    log_audit_action(current_user.id, 'logout')
    # Controller - log user out
    logout_user()
    flash('You have been logged out.', 'info')
    # Controller - redirect to homepage
    return redirect(url_for('main.index'))

# ===========================================
# STEP 7: Dashboard Route (Read Operation)
# ===========================================
# Demonstrates MVC: Controller → Model → View
@main.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard route - Read operation example
    
    MVC FLOW:
    Step 7a: User requests /dashboard (GET request)
    Step 7b: Controller checks permissions (business logic)
    Step 7c: Controller queries MODEL (get_dashboard_stats) for data
    Step 7d: Controller queries MODEL (User.spending_limits) for alerts
    Step 7e: Controller processes data (business logic)
    Step 7f: Controller passes data to VIEW (template)
    Step 7g: VIEW renders HTML with data
    """
    # Step 7a: Query MODEL layer - get dashboard statistics
    # This function queries Transaction model and returns stats
    stats = get_dashboard_stats(current_user)
    
    # Step 7b: Controller business logic - get spending limit alerts
    spending_alerts = []
    if current_user.has_permission('read'):
        # Step 7c: Access MODEL relationship (User.spending_limits)
        for limit in current_user.spending_limits:
            # Step 7d: Call MODEL method (is_exceeded) - business logic in Model
            if limit.is_active and limit.is_exceeded():
                # Step 7e: Controller processes data
                spending_alerts.append({
                    'limit': limit,
                    'spent': limit.get_spent_amount(),  # MODEL method call
                    'percentage': (limit.get_spent_amount() / limit.amount) * 100
                })
    
    # Step 7f: Controller passes data to VIEW (template)
    # Template receives: stats, spending_alerts
    return render_template('dashboard.html', stats=stats, spending_alerts=spending_alerts)

# ===========================================
# STEP 8: List Transactions Route (Read Operation)
# ===========================================
# Demonstrates complex querying and filtering
@main.route('/transactions')
@login_required
def transactions():
    """
    List transactions route - Complex read operation
    
    MVC FLOW:
    Step 8a: User requests /transactions (GET request)
    Step 8b: Controller checks permissions
    Step 8c: Controller gets query parameters (pagination, filters)
    Step 8d: Controller queries MODEL (Transaction.query)
    Step 8e: Controller applies filters (business logic)
    Step 8f: Controller paginates results
    Step 8g: Controller passes data to VIEW
    """
    # Step 8a: Controller - check permissions (business logic)
    if not current_user.has_permission('read'):
        abort(403)
    
    # Step 8b: Controller - get pagination parameters from request
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Step 8c: Query MODEL layer - start with base query
    query = Transaction.query
    
    # Step 8d: Controller business logic - filter by user if not admin
    if not current_user.has_permission('manage_users'):
        query = query.filter(Transaction.user_id == current_user.id)
    
    # Step 8e: Controller - handle search and filters
    search_form = SearchForm()
    if request.method == 'GET' and request.args:
        search_form.process(request.args)
        
        # Step 8f: Controller - apply search filter (business logic)
        if search_form.search_term.data:
            search_term = f"%{search_form.search_term.data}%"
            query = query.filter(or_(
                Transaction.description.ilike(search_term),
                Transaction.notes.ilike(search_term),
                Transaction.party.ilike(search_term)
            ))
        
        # Step 8g: Controller - apply category filter
        if search_form.category_id.data and search_form.category_id.data != 0:
            query = query.filter(Transaction.category_id == search_form.category_id.data)
        
        # Step 8h: Controller - apply type filter
        if search_form.type.data:
            query = query.filter(Transaction.type == search_form.type.data)
        
        # Step 8i: Controller - apply date filters
        if search_form.start_date.data:
            query = query.filter(Transaction.transaction_date >= search_form.start_date.data)
        
        if search_form.end_date.data:
            query = query.filter(Transaction.transaction_date <= search_form.end_date.data)
    
    # Step 8j: Controller - order results (business logic)
    query = query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
    
    # Step 8k: Controller - paginate results
    transactions_page = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Step 8l: Controller passes data to VIEW (template)
    return render_template('transactions.html', 
                         transactions=transactions_page.items,
                         pagination=transactions_page,
                         search_form=search_form)

# ===========================================
# STEP 9: Add Transaction Route (Create Operation)
# ===========================================
# Demonstrates full CREATE operation in MVC
@main.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """
    Add new transaction route - Create operation example
    
    GET REQUEST FLOW:
    Step 9a: User visits /transactions/add (GET request)
    Step 9b: Controller creates form instance
    Step 9c: Controller renders VIEW (form template)
    
    POST REQUEST FLOW:
    Step 9d: User submits form (POST request)
    Step 9e: Controller validates form data
    Step 9f: Controller creates MODEL instance (Transaction)
    Step 9g: Controller sets MODEL attributes from form data
    Step 9h: Controller saves MODEL to database
    Step 9i: Controller creates related MODEL instances (Tag, Receipt)
    Step 9j: Controller queries MODEL (log_audit_action)
    Step 9k: Controller redirects to list view
    """
    # Step 9a: Controller - check permissions
    if not current_user.has_permission('create'):
        abort(403)
    
    # Step 9b: Controller - create form instance
    form = TransactionForm()
    
    # Step 9c: Handle form submission (POST request)
    if form.validate_on_submit():
        # Step 9d: Create MODEL instance (Transaction)
        transaction = Transaction()
        
        # Step 9e: Controller - set MODEL attributes from form data
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.notes = form.notes.data
        transaction.party = form.party.data
        transaction.transaction_date = form.transaction_date.data
        transaction.user_id = current_user.id
        transaction.category_id = form.category_id.data
        
        # Step 9f: Controller - add MODEL to database session
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID without committing
        
        # Step 9g: Controller business logic - handle tags
        if form.tags.data:
            tag_names = parse_tags(form.tags.data)
            for tag_name in tag_names:
                # Step 9h: Query MODEL layer - find or create tag
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    # Step 9i: Create MODEL instance (Tag)
                    tag = Tag()
                    tag.name = tag_name
                    db.session.add(tag)
                # Step 9j: Controller - associate tag with transaction
                transaction.tags.append(tag)
        
        # Step 9k: Controller business logic - handle receipt upload
        if form.receipts.data:
            filename = save_uploaded_file(form.receipts.data)
            if filename:
                # Step 9l: Create MODEL instance (Receipt)
                receipt = Receipt()
                receipt.filename = filename
                receipt.original_filename = form.receipts.data.filename
                receipt.file_size = len(form.receipts.data.read())
                receipt.mime_type = form.receipts.data.mimetype
                receipt.transaction_id = transaction.id
                db.session.add(receipt)
        
        # Step 9m: Controller - commit all changes to database
        db.session.commit()
        
        # Step 9n: Query MODEL layer - log audit action
        log_audit_action(current_user.id, 'create_transaction', 'transactions', transaction.id)
        
        # Step 9o: Controller - show success message
        flash('Transaction added successfully.', 'success')
        
        # Step 9p: Controller - redirect to list view
        return redirect(url_for('main.transactions'))
    
    # Step 9q: Render VIEW (template) - display form
    return render_template('add_transaction.html', form=form)

# ===========================================
# STEP 10: Edit Transaction Route (Update Operation)
# ===========================================
@main.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """
    Edit transaction route - Update operation example
    
    GET REQUEST FLOW:
    Step 10a: User visits /transactions/1/edit (GET request)
    Step 10b: Controller queries MODEL (Transaction.query.get)
    Step 10c: Controller checks permissions
    Step 10d: Controller creates form with MODEL data
    Step 10e: Controller renders VIEW (edit form)
    
    POST REQUEST FLOW:
    Step 10f: User submits form (POST request)
    Step 10g: Controller validates form data
    Step 10h: Controller updates MODEL attributes
    Step 10i: Controller saves MODEL to database
    Step 10j: Controller redirects to list view
    """
    # Step 10a: Query MODEL layer - get transaction by ID
    transaction = Transaction.query.get_or_404(id)
    
    # Step 10b: Controller - check permissions (business logic)
    if not current_user.has_permission('update'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    # Step 10c: Controller - create form with MODEL data
    form = TransactionForm(obj=transaction)
    
    # Step 10d: Handle GET request - pre-populate form
    if request.method == 'GET':
        # Step 10e: Controller - get tags from MODEL relationship
        form.tags.data = ', '.join([tag.name for tag in transaction.tags])
    
    # Step 10f: Handle POST request - update transaction
    if form.validate_on_submit():
        # Step 10g: Controller - save old values for audit log
        old_values = {
            'type': transaction.type,
            'amount': str(transaction.amount),
            'description': transaction.description,
            'category_id': transaction.category_id
        }
        
        # Step 10h: Controller - update MODEL attributes
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.notes = form.notes.data
        transaction.party = form.party.data
        transaction.transaction_date = form.transaction_date.data
        transaction.category_id = form.category_id.data
        transaction.updated_at = datetime.utcnow()
        
        # Step 10i: Controller business logic - update tags
        transaction.tags.clear()
        if form.tags.data:
            tag_names = parse_tags(form.tags.data)
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag()
                    tag.name = tag_name
                    db.session.add(tag)
                transaction.tags.append(tag)
        
        # Step 10j: Controller business logic - handle new receipt
        if form.receipts.data:
            filename = save_uploaded_file(form.receipts.data)
            if filename:
                receipt = Receipt()
                receipt.filename = filename
                receipt.original_filename = form.receipts.data.filename
                receipt.file_size = len(form.receipts.data.read())
                receipt.mime_type = form.receipts.data.mimetype
                receipt.transaction_id = transaction.id
                db.session.add(receipt)
        
        # Step 10k: Controller - save new values for audit log
        new_values = {
            'type': transaction.type,
            'amount': str(transaction.amount),
            'description': transaction.description,
            'category_id': transaction.category_id
        }
        
        # Step 10l: Controller - commit changes to database
        db.session.commit()
        
        # Step 10m: Query MODEL layer - log audit action
        log_audit_action(current_user.id, 'update_transaction', 'transactions', transaction.id, old_values, new_values)
        
        # Step 10n: Controller - show success message
        flash('Transaction updated successfully.', 'success')
        
        # Step 10o: Controller - redirect to list view
        return redirect(url_for('main.transactions'))
    
    # Step 10p: Render VIEW (template) - display edit form
    return render_template('edit_transaction.html', form=form, transaction=transaction)

# ===========================================
# STEP 11: Delete Transaction Route (Delete Operation)
# ===========================================
@main.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete_transaction(id):
    """
    Delete transaction route - Delete operation example
    
    MVC FLOW:
    Step 11a: User submits delete form (POST request)
    Step 11b: Controller queries MODEL (Transaction.query.get)
    Step 11c: Controller checks permissions
    Step 11d: Controller deletes related MODEL instances (Receipts)
    Step 11e: Controller deletes MODEL instance
    Step 11f: Controller commits to database
    Step 11g: Controller queries MODEL (log_audit_action)
    Step 11h: Controller redirects to list view
    """
    # Step 11a: Query MODEL layer - get transaction by ID
    transaction = Transaction.query.get_or_404(id)
    
    # Step 11b: Controller - check permissions
    if not current_user.has_permission('delete'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    # Step 11c: Controller business logic - delete associated receipts
    for receipt in transaction.receipts:
        delete_file(receipt.filename)  # Delete file from filesystem
    
    # Step 11d: Controller - delete MODEL instance
    db.session.delete(transaction)
    
    # Step 11e: Controller - commit deletion to database
    db.session.commit()
    
    # Step 11f: Query MODEL layer - log audit action
    log_audit_action(current_user.id, 'delete_transaction', 'transactions', id)
    
    # Step 11g: Controller - show success message
    flash('Transaction deleted successfully.', 'success')
    
    # Step 11h: Controller - redirect to list view
    return redirect(url_for('main.transactions'))

# ===========================================
# STEP 12: Reports Route (Complex Read Operation)
# ===========================================
@main.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    """
    Generate reports route - Complex read operation
    
    MVC FLOW:
    Step 12a: User requests /reports (GET) or submits form (POST)
    Step 12b: Controller validates form data
    Step 12c: Controller queries MODEL (Transaction.query) with filters
    Step 12d: Controller processes data (business logic)
    Step 12e: Controller generates report (PDF/Excel)
    Step 12f: Controller returns file to user
    """
    # Step 12a: Controller - check permissions
    if not current_user.has_permission('reports'):
        abort(403)
    
    # Step 12b: Controller - create form instance
    form = ReportForm()
    
    # Step 12c: Handle form submission
    if form.validate_on_submit():
        # Step 12d: Query MODEL layer - start with base query
        query = Transaction.query
        
        # Step 12e: Controller business logic - apply user filter
        if form.user_id.data and form.user_id.data != 0:
            if current_user.has_permission('manage_users'):
                query = query.filter(Transaction.user_id == form.user_id.data)
            else:
                query = query.filter(Transaction.user_id == current_user.id)
        elif not current_user.has_permission('manage_users'):
            query = query.filter(Transaction.user_id == current_user.id)
        
        # Step 12f: Controller - apply date range filter
        query = query.filter(
            Transaction.transaction_date >= form.start_date.data,
            Transaction.transaction_date <= form.end_date.data
        )
        
        # Step 12g: Controller - apply category filter
        if form.category_id.data and form.category_id.data != 0:
            query = query.filter(Transaction.category_id == form.category_id.data)
        
        # Step 12h: Controller - apply type filter
        if form.type.data:
            query = query.filter(Transaction.type == form.type.data)
        
        # Step 12i: Controller - get all matching transactions
        transactions = query.order_by(Transaction.transaction_date.desc()).all()
        
        # Step 12j: Controller - generate report title
        title = f"Financial Report - {form.start_date.data} to {form.end_date.data}"
        
        # Step 12k: Controller business logic - generate PDF or Excel
        if form.format.data == 'pdf':
            buffer = generate_pdf_report(transactions, title)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mimetype='application/pdf'
            )
        else:  # Excel
            buffer = generate_excel_report(transactions, title)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
    
    # Step 12l: Render VIEW (template) - display report form
    return render_template('reports.html', form=form)

# ===========================================
# STEP 13: Additional Routes (Users, Profile, Settings, etc.)
# ===========================================
# These follow the same MVC pattern as above

@main.route('/users')
@login_required
def users():
    """List users - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    # Query MODEL layer
    users = User.query.order_by(User.username).all()
    # Render VIEW
    return render_template('users.html', users=users)

@main.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Register new user - only for admins"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create MODEL instance
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.password_hash = generate_password_hash(form.password.data)
        user.role_id = form.role_id.data
        user.is_active = True
        
        # Save MODEL to database
        db.session.add(user)
        db.session.commit()
        
        # Log audit action
        log_audit_action(current_user.id, 'create_user', 'users', user.id)
        flash(f'User {user.username} has been registered successfully.', 'success')
        return redirect(url_for('main.users'))
    
    return render_template('register.html', form=form)

@main.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit user - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    # Query MODEL layer
    user = User.query.get_or_404(id)
    form = UserForm(user=user, obj=user)
    
    if form.validate_on_submit():
        old_values = {
            'username': user.username,
            'email': user.email,
            'role_id': user.role_id,
            'is_active': user.is_active
        }
        
        # Update MODEL attributes
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        new_values = {
            'username': user.username,
            'email': user.email,
            'role_id': user.role_id,
            'is_active': user.is_active
        }
        
        # Commit changes
        db.session.commit()
        log_audit_action(current_user.id, 'update_user', 'users', user.id, old_values, new_values)
        
        flash('User updated successfully.', 'success')
        return redirect(url_for('main.users'))
    
    return render_template('register.html', form=form, user=user)

@main.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    """Delete user - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    # Query MODEL layer
    user = User.query.get_or_404(id)
    
    # Controller business logic - prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('main.users'))
    
    # Update MODEL (deactivate instead of delete)
    user.is_active = False
    db.session.commit()
    
    log_audit_action(current_user.id, 'deactivate_user', 'users', user.id)
    flash('User deactivated successfully.', 'success')
    return redirect(url_for('main.users'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        # Update MODEL attributes
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        
        # Commit changes
        db.session.commit()
        log_audit_action(current_user.id, 'update_profile')
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html', form=form)

@main.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Controller business logic - verify current password
        if check_password_hash(current_user.password_hash, form.current_password.data):
            # Update MODEL attribute
            current_user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            
            log_audit_action(current_user.id, 'change_password')
            flash('Password changed successfully.', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('Current password is incorrect.', 'error')
    
    return render_template('profile.html', password_form=form)

@main.route('/settings')
@login_required
def settings():
    """Application settings"""
    # Query MODEL layer
    categories = Category.query.order_by(Category.name).all()
    spending_limits = SpendingLimit.query.filter_by(user_id=current_user.id).all()
    
    # Render VIEW
    return render_template('settings.html', categories=categories, spending_limits=spending_limits)

@main.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """Add new category"""
    if not current_user.has_permission('create'):
        abort(403)
    
    form = CategoryForm()
    if form.validate_on_submit():
        # Create MODEL instance
        category = Category()
        category.name = form.name.data
        category.description = form.description.data
        category.color = form.color.data or '#007bff'
        
        # Save to database
        db.session.add(category)
        db.session.commit()
        
        log_audit_action(current_user.id, 'create_category', 'categories', category.id)
        flash('Category added successfully.', 'success')
    
    return redirect(url_for('main.settings'))

@main.route('/spending-limits/add', methods=['POST'])
@login_required
def add_spending_limit():
    """Add spending limit"""
    form = SpendingLimitForm()
    if form.validate_on_submit():
        category_id = form.category_id.data if form.category_id.data != 0 else None
        
        # Create MODEL instance
        spending_limit = SpendingLimit()
        spending_limit.type = form.type.data
        spending_limit.amount = form.amount.data
        spending_limit.category_id = category_id
        spending_limit.is_active = form.is_active.data
        spending_limit.user_id = current_user.id
        
        # Save to database
        db.session.add(spending_limit)
        db.session.commit()
        
        log_audit_action(current_user.id, 'create_spending_limit', 'spending_limits', spending_limit.id)
        flash('Spending limit added successfully.', 'success')
    
    return redirect(url_for('main.settings'))

@main.route('/backup')
@login_required
def backup():
    """Download database backup - admin only"""
    if not current_user.has_permission('backup'):
        abort(403)
    
    # Query MODEL layer - get all data
    backup_data = backup_database()
    buffer = BytesIO(backup_data.encode('utf-8'))
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"cashbook_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mimetype='application/json'
    )

@main.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/receipts/<int:receipt_id>/delete', methods=['POST'])
@login_required
def delete_receipt(receipt_id):
    """Delete receipt"""
    # Query MODEL layer
    receipt = Receipt.query.get_or_404(receipt_id)
    transaction = receipt.transaction
    
    # Controller - check permissions
    if not current_user.has_permission('update'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    # Controller business logic - delete file
    delete_file(receipt.filename)
    
    # Delete MODEL instance
    db.session.delete(receipt)
    db.session.commit()
    
    log_audit_action(current_user.id, 'delete_receipt', 'receipts', receipt_id)
    flash('Receipt deleted successfully.', 'success')
    return redirect(url_for('main.edit_transaction', id=transaction.id))

# ===========================================
# STEP 14: API Endpoints (JSON Responses)
# ===========================================
# These return JSON instead of HTML (for AJAX requests)

@main.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """Get dashboard statistics - API endpoint"""
    # Query MODEL layer
    stats = get_dashboard_stats(current_user)
    # Return JSON (no VIEW template)
    return jsonify(stats)

@main.route('/api/spending-check/<int:category_id>')
@login_required
def api_spending_check(category_id):
    """Check spending limits for category - API endpoint"""
    # Query MODEL layer
    limits = SpendingLimit.query.filter_by(
        user_id=current_user.id,
        category_id=category_id if category_id != 0 else None,
        is_active=True
    ).all()
    
    # Controller business logic - process data
    alerts = []
    for limit in limits:
        spent = limit.get_spent_amount()  # MODEL method call
        if spent > limit.amount * 0.8:  # 80% threshold
            alerts.append({
                'type': limit.type,
                'limit': float(limit.amount),
                'spent': float(spent),
                'percentage': (spent / limit.amount) * 100,
                'exceeded': spent > limit.amount
            })
    
    # Return JSON (no VIEW template)
    return jsonify(alerts)

# Error handlers are registered in app/__init__.py
