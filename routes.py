import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session, abort
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import or_, and_, func, desc
from app import app, db
from models import User, Role, Transaction, Category, Tag, Receipt, SpendingLimit, AuditLog, transaction_tags
from forms import (LoginForm, RegistrationForm, TransactionForm, CategoryForm, SpendingLimitForm, 
                  ReportForm, SearchForm, ProfileForm, ChangePasswordForm, UserForm)
from utils import (save_uploaded_file, delete_file, format_currency, parse_tags, 
                  generate_pdf_report, generate_excel_report, log_audit_action, 
                  get_dashboard_stats, backup_database)
from io import BytesIO

@app.context_processor
def utility_processor():
    """Make utility functions available in templates"""
    return dict(
        format_currency=format_currency,
        len=len,
        str=str,
        int=int,
        enumerate=enumerate
    )

@app.route('/')
def index():
    """Homepage - redirect to dashboard if logged in, otherwise show landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return render_template('login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            log_audit_action(user.id, 'login')
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    log_audit_action(current_user.id, 'logout')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Register new user - only for admins"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.password_hash = generate_password_hash(form.password.data)
        user.role_id = form.role_id.data
        user.is_active = True
        
        db.session.add(user)
        db.session.commit()
        
        log_audit_action(current_user.id, 'create_user', 'users', user.id)
        flash(f'User {user.username} has been registered successfully.', 'success')
        return redirect(url_for('users'))
    
    return render_template('register.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    stats = get_dashboard_stats(current_user)
    
    # Get spending limit alerts
    spending_alerts = []
    if current_user.has_permission('read'):
        for limit in current_user.spending_limits:
            if limit.is_active and limit.is_exceeded():
                spending_alerts.append({
                    'limit': limit,
                    'spent': limit.get_spent_amount(),
                    'percentage': (limit.get_spent_amount() / limit.amount) * 100
                })
    
    return render_template('dashboard.html', stats=stats, spending_alerts=spending_alerts)

@app.route('/transactions')
@login_required
def transactions():
    """List transactions with search and filter"""
    if not current_user.has_permission('read'):
        abort(403)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query
    query = Transaction.query
    if not current_user.has_permission('manage_users'):
        query = query.filter(Transaction.user_id == current_user.id)
    
    # Search and filters
    search_form = SearchForm()
    if request.method == 'GET' and request.args:
        search_form.process(request.args)
        
        if search_form.search_term.data:
            search_term = f"%{search_form.search_term.data}%"
            query = query.filter(or_(
                Transaction.description.ilike(search_term),
                Transaction.notes.ilike(search_term),
                Transaction.party.ilike(search_term)
            ))
        
        if search_form.category_id.data and search_form.category_id.data != 0:
            query = query.filter(Transaction.category_id == search_form.category_id.data)
        
        if search_form.type.data:
            query = query.filter(Transaction.type == search_form.type.data)
        
        if search_form.start_date.data:
            query = query.filter(Transaction.transaction_date >= search_form.start_date.data)
        
        if search_form.end_date.data:
            query = query.filter(Transaction.transaction_date <= search_form.end_date.data)
    
    # Order by date descending
    query = query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
    
    # Paginate
    transactions_page = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('transactions.html', 
                         transactions=transactions_page.items,
                         pagination=transactions_page,
                         search_form=search_form)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """Add new transaction"""
    if not current_user.has_permission('create'):
        abort(403)
    
    form = TransactionForm()
    if form.validate_on_submit():
        # Create transaction
        transaction = Transaction()
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.notes = form.notes.data
        transaction.party = form.party.data
        transaction.transaction_date = form.transaction_date.data
        transaction.user_id = current_user.id
        transaction.category_id = form.category_id.data
        
        db.session.add(transaction)
        db.session.flush()  # To get the transaction ID
        
        # Handle tags
        if form.tags.data:
            tag_names = parse_tags(form.tags.data)
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag()
                    tag.name = tag_name
                    db.session.add(tag)
                transaction.tags.append(tag)
        
        # Handle receipt upload
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
        
        db.session.commit()
        log_audit_action(current_user.id, 'create_transaction', 'transactions', transaction.id)
        
        flash('Transaction added successfully.', 'success')
        return redirect(url_for('transactions'))
    
    return render_template('add_transaction.html', form=form)

@app.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """Edit transaction"""
    transaction = Transaction.query.get_or_404(id)
    
    # Permission check
    if not current_user.has_permission('update'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    form = TransactionForm(obj=transaction)
    
    if request.method == 'GET':
        # Pre-populate tags
        form.tags.data = ', '.join([tag.name for tag in transaction.tags])
    
    if form.validate_on_submit():
        old_values = {
            'type': transaction.type,
            'amount': str(transaction.amount),
            'description': transaction.description,
            'category_id': transaction.category_id
        }
        
        # Update transaction
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.notes = form.notes.data
        transaction.party = form.party.data
        transaction.transaction_date = form.transaction_date.data
        transaction.category_id = form.category_id.data
        transaction.updated_at = datetime.utcnow()
        
        # Update tags
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
        
        # Handle new receipt upload
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
        
        new_values = {
            'type': transaction.type,
            'amount': str(transaction.amount),
            'description': transaction.description,
            'category_id': transaction.category_id
        }
        
        db.session.commit()
        log_audit_action(current_user.id, 'update_transaction', 'transactions', transaction.id, old_values, new_values)
        
        flash('Transaction updated successfully.', 'success')
        return redirect(url_for('transactions'))
    
    return render_template('edit_transaction.html', form=form, transaction=transaction)

@app.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete_transaction(id):
    """Delete transaction"""
    transaction = Transaction.query.get_or_404(id)
    
    # Permission check
    if not current_user.has_permission('delete'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    # Delete associated receipts
    for receipt in transaction.receipts:
        delete_file(receipt.filename)
    
    db.session.delete(transaction)
    db.session.commit()
    
    log_audit_action(current_user.id, 'delete_transaction', 'transactions', id)
    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('transactions'))

@app.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    """Generate and download reports"""
    if not current_user.has_permission('reports'):
        abort(403)
    
    form = ReportForm()
    if form.validate_on_submit():
        # Build query
        query = Transaction.query
        
        # User filter
        if form.user_id.data and form.user_id.data != 0:
            if current_user.has_permission('manage_users'):
                query = query.filter(Transaction.user_id == form.user_id.data)
            else:
                query = query.filter(Transaction.user_id == current_user.id)
        elif not current_user.has_permission('manage_users'):
            query = query.filter(Transaction.user_id == current_user.id)
        
        # Date range
        query = query.filter(
            Transaction.transaction_date >= form.start_date.data,
            Transaction.transaction_date <= form.end_date.data
        )
        
        # Category filter
        if form.category_id.data and form.category_id.data != 0:
            query = query.filter(Transaction.category_id == form.category_id.data)
        
        # Type filter
        if form.type.data:
            query = query.filter(Transaction.type == form.type.data)
        
        # Order by date
        transactions = query.order_by(Transaction.transaction_date.desc()).all()
        
        # Generate report
        title = f"Financial Report - {form.start_date.data} to {form.end_date.data}"
        
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
    
    return render_template('reports.html', form=form)

@app.route('/users')
@login_required
def users():
    """List users - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    users = User.query.order_by(User.username).all()
    return render_template('users.html', users=users)

@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit user - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    user = User.query.get_or_404(id)
    form = UserForm(user=user, obj=user)
    
    if form.validate_on_submit():
        old_values = {
            'username': user.username,
            'email': user.email,
            'role_id': user.role_id,
            'is_active': user.is_active
        }
        
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
        
        db.session.commit()
        log_audit_action(current_user.id, 'update_user', 'users', user.id, old_values, new_values)
        
        flash('User updated successfully.', 'success')
        return redirect(url_for('users'))
    
    return render_template('register.html', form=form, user=user)

@app.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    """Delete user - admin only"""
    if not current_user.has_permission('manage_users'):
        abort(403)
    
    user = User.query.get_or_404(id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('users'))
    
    # Don't actually delete, just deactivate
    user.is_active = False
    db.session.commit()
    
    log_audit_action(current_user.id, 'deactivate_user', 'users', user.id)
    flash('User deactivated successfully.', 'success')
    return redirect(url_for('users'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile"""
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        
        db.session.commit()
        log_audit_action(current_user.id, 'update_profile')
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form)

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if check_password_hash(current_user.password_hash, form.current_password.data):
            current_user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            
            log_audit_action(current_user.id, 'change_password')
            flash('Password changed successfully.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Current password is incorrect.', 'error')
    
    return render_template('profile.html', password_form=form)

@app.route('/settings')
@login_required
def settings():
    """Application settings"""
    # Categories
    categories = Category.query.order_by(Category.name).all()
    
    # Spending limits for current user
    spending_limits = SpendingLimit.query.filter_by(user_id=current_user.id).all()
    
    return render_template('settings.html', categories=categories, spending_limits=spending_limits)

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """Add new category"""
    if not current_user.has_permission('create'):
        abort(403)
    
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category()
        category.name = form.name.data
        category.description = form.description.data
        category.color = form.color.data or '#007bff'
        
        db.session.add(category)
        db.session.commit()
        
        log_audit_action(current_user.id, 'create_category', 'categories', category.id)
        flash('Category added successfully.', 'success')
    
    return redirect(url_for('settings'))

@app.route('/spending-limits/add', methods=['POST'])
@login_required
def add_spending_limit():
    """Add spending limit"""
    form = SpendingLimitForm()
    if form.validate_on_submit():
        category_id = form.category_id.data if form.category_id.data != 0 else None
        
        spending_limit = SpendingLimit()
        spending_limit.type = form.type.data
        spending_limit.amount = form.amount.data
        spending_limit.category_id = category_id
        spending_limit.is_active = form.is_active.data
        spending_limit.user_id = current_user.id
        
        db.session.add(spending_limit)
        db.session.commit()
        
        log_audit_action(current_user.id, 'create_spending_limit', 'spending_limits', spending_limit.id)
        flash('Spending limit added successfully.', 'success')
    
    return redirect(url_for('settings'))

@app.route('/backup')
@login_required
def backup():
    """Download database backup - admin only"""
    if not current_user.has_permission('backup'):
        abort(403)
    
    backup_data = backup_database()
    buffer = BytesIO(backup_data.encode('utf-8'))
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"cashbook_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mimetype='application/json'
    )

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/receipts/<int:receipt_id>/delete', methods=['POST'])
@login_required
def delete_receipt(receipt_id):
    """Delete receipt"""
    receipt = Receipt.query.get_or_404(receipt_id)
    transaction = receipt.transaction
    
    # Permission check
    if not current_user.has_permission('update'):
        abort(403)
    if not current_user.has_permission('manage_users') and transaction.user_id != current_user.id:
        abort(403)
    
    # Delete file
    delete_file(receipt.filename)
    
    # Delete record
    db.session.delete(receipt)
    db.session.commit()
    
    log_audit_action(current_user.id, 'delete_receipt', 'receipts', receipt_id)
    flash('Receipt deleted successfully.', 'success')
    return redirect(url_for('edit_transaction', id=transaction.id))

# API endpoints for AJAX requests
@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """Get dashboard statistics"""
    stats = get_dashboard_stats(current_user)
    return jsonify(stats)

@app.route('/api/spending-check/<int:category_id>')
@login_required
def api_spending_check(category_id):
    """Check spending limits for category"""
    limits = SpendingLimit.query.filter_by(
        user_id=current_user.id,
        category_id=category_id if category_id != 0 else None,
        is_active=True
    ).all()
    
    alerts = []
    for limit in limits:
        spent = limit.get_spent_amount()
        if spent > limit.amount * 0.8:  # 80% threshold
            alerts.append({
                'type': limit.type,
                'limit': float(limit.amount),
                'spent': float(spent),
                'percentage': (spent / limit.amount) * 100,
                'exceeded': spent > limit.amount
            })
    
    return jsonify(alerts)

# Error handlers
@app.errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

