# MVC Pattern - Step-by-Step Guide for Django Interview

## Overview
This document explains the MVC (Model-View-Controller) pattern implemented in this Flask project, which is similar to Django's MVT (Model-View-Template) pattern.

---

## What is MVC?

**MVC** separates an application into three interconnected components:

1. **Model (M)** - Data layer: Database models, data validation, business logic
2. **View (V)** - Presentation layer: HTML templates, what users see
3. **Controller (C)** - Logic layer: Handles requests, processes data, coordinates Model and View

---

## Project Structure Mapping

```
CashBookManager/
├── app/
│   ├── __init__.py      → Application setup (Step 1-10)
│   ├── models.py         → MODEL layer (Step 1-11)
│   ├── routes.py         → CONTROLLER layer (Step 1-14)
│   ├── forms.py          → Form validation (supports Controller)
│   ├── utils.py          → Helper functions (supports Controller)
│   ├── templates/        → VIEW layer (HTML files)
│   └── static/           → Static files (CSS, JS)
└── main.py               → Application entry point
```

---

## Step-by-Step MVC Flow

### Example: Adding a Transaction

#### **STEP 1: User Request (Browser)**
```
User clicks "Add Transaction" button
→ Browser sends HTTP GET request to /transactions/add
```

#### **STEP 2: Controller Receives Request** (`app/routes.py`)
```python
@main.route('/transactions/add', methods=['GET', 'POST'])
def add_transaction():
    # Step 2a: Controller checks permissions (business logic)
    if not current_user.has_permission('create'):
        abort(403)
    
    # Step 2b: Controller creates form instance
    form = TransactionForm()
```

#### **STEP 3: Controller Renders View** (`app/routes.py`)
```python
    # Step 3a: For GET request, render template (VIEW layer)
    return render_template('add_transaction.html', form=form)
```

#### **STEP 4: View Displays Form** (`app/templates/add_transaction.html`)
```html
<!-- VIEW layer - HTML template -->
<form method="POST">
    <input name="amount" type="number">
    <input name="description" type="text">
    <button type="submit">Save</button>
</form>
```

#### **STEP 5: User Submits Form**
```
User fills form and clicks "Save"
→ Browser sends HTTP POST request to /transactions/add
```

#### **STEP 6: Controller Validates Data** (`app/routes.py`)
```python
    if form.validate_on_submit():
        # Step 6a: Form validation passed
```

#### **STEP 7: Controller Creates Model Instance** (`app/routes.py`)
```python
        # Step 7a: Create MODEL instance
        transaction = Transaction()
        
        # Step 7b: Set MODEL attributes from form data
        transaction.type = form.type.data
        transaction.amount = form.amount.data
        transaction.description = form.description.data
        transaction.user_id = current_user.id
```

#### **STEP 8: Controller Saves to Database** (`app/routes.py`)
```python
        # Step 8a: Add MODEL to database session
        db.session.add(transaction)
        
        # Step 8b: Commit to database
        db.session.commit()
```

#### **STEP 9: Controller Redirects** (`app/routes.py`)
```python
        # Step 9a: Show success message
        flash('Transaction added successfully.', 'success')
        
        # Step 9b: Redirect to list view
        return redirect(url_for('main.transactions'))
```

#### **STEP 10: Controller Renders List View** (`app/routes.py`)
```python
@main.route('/transactions')
def transactions():
    # Step 10a: Query MODEL layer
    query = Transaction.query
    
    # Step 10b: Apply filters (business logic)
    if not current_user.has_permission('manage_users'):
        query = query.filter(Transaction.user_id == current_user.id)
    
    # Step 10c: Get paginated results
    transactions_page = query.paginate(page=page, per_page=20)
    
    # Step 10d: Render VIEW with data
    return render_template('transactions.html', 
                         transactions=transactions_page.items)
```

---

## Key MVC Concepts for Interview

### 1. **Separation of Concerns**
- **Model**: Never renders HTML, only handles data
- **View**: Never contains business logic, only displays data
- **Controller**: Coordinates between Model and View

### 2. **Model Layer** (`app/models.py`)
```python
class Transaction(db.Model):
    # Defines database structure
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12, 2))
    
    # Business logic methods
    def calculate_total(self):
        return self.amount * 1.1  # Add tax
```

**Responsibilities:**
- Define database schema
- Data validation rules
- Business logic related to data
- Relationships between models

### 3. **Controller Layer** (`app/routes.py`)
```python
@main.route('/transactions/add', methods=['POST'])
def add_transaction():
    # 1. Receive request
    # 2. Validate input
    # 3. Query/update Model
    # 4. Process business logic
    # 5. Render View or redirect
```

**Responsibilities:**
- Handle HTTP requests
- Validate user input
- Query/update Model layer
- Execute business logic
- Render templates or return JSON

### 4. **View Layer** (`app/templates/`)
```html
<!-- templates/transactions.html -->
{% for transaction in transactions %}
    <div>{{ transaction.amount }}</div>
{% endfor %}
```

**Responsibilities:**
- Display data to user
- HTML structure and styling
- Form rendering
- No business logic

---

## Django vs Flask MVC Comparison

| Component | Django | Flask (This Project) |
|-----------|--------|---------------------|
| **Model** | `models.py` | `app/models.py` |
| **View** | `views.py` (Controller) | `app/routes.py` (Controller) |
| **Template** | `templates/` | `app/templates/` |
| **URLs** | `urls.py` | `@route` decorators |

**Note:** Django uses MVT (Model-View-Template) where:
- **View** = Controller in MVC (handles logic)
- **Template** = View in MVC (presentation)

---

## Common MVC Patterns in This Project

### Pattern 1: CRUD Operations

#### **CREATE** (Add Transaction)
```
User → Controller → Model → Database → Controller → View
```

#### **READ** (List Transactions)
```
User → Controller → Model → Database → Controller → View
```

#### **UPDATE** (Edit Transaction)
```
User → Controller → Model → Database → Controller → View
```

#### **DELETE** (Delete Transaction)
```
User → Controller → Model → Database → Controller → View
```

### Pattern 2: Authentication Flow
```
1. User submits login form (POST)
2. Controller validates credentials
3. Controller queries User Model
4. Controller creates session
5. Controller redirects to dashboard
6. Controller queries Transaction Model for stats
7. Controller renders dashboard View
```

---

## Interview Talking Points

1. **"Explain MVC in this project"**
   - Models (`models.py`) define data structure
   - Controllers (`routes.py`) handle requests and logic
   - Views (`templates/`) display data to users

2. **"How does data flow?"**
   - User request → Controller → Model → Database
   - Database → Model → Controller → View → User

3. **"Where is business logic?"**
   - Model methods (e.g., `is_exceeded()`)
   - Controller functions (e.g., permission checks)
   - Utility functions (`utils.py`)

4. **"How is MVC different from Django?"**
   - Django uses MVT (Model-View-Template)
   - Flask routes = Django views (both are Controllers)
   - Same separation of concerns, different naming

5. **"Benefits of MVC?"**
   - Separation of concerns
   - Easier testing
   - Better maintainability
   - Code reusability

---

## File-by-File Breakdown

### `app/__init__.py` (Steps 1-10)
- Sets up Flask application
- Configures database (Model layer support)
- Registers blueprints (Controller layer)
- Initializes extensions

### `app/models.py` (Steps 1-11)
- Defines all database models
- Contains business logic methods
- Defines relationships between models

### `app/routes.py` (Steps 1-14)
- Contains all route handlers (Controllers)
- Handles HTTP requests
- Coordinates Model and View
- Implements CRUD operations

### `app/templates/` (View Layer)
- HTML templates
- Jinja2 templating
- Displays data from Controller
- No business logic

---

## Quick Reference

**Model Layer:**
- File: `app/models.py`
- Purpose: Data structure, database schema
- Example: `Transaction`, `User`, `Category`

**Controller Layer:**
- File: `app/routes.py`
- Purpose: Handle requests, process logic
- Example: `@main.route('/transactions')`

**View Layer:**
- Directory: `app/templates/`
- Purpose: Display data, HTML templates
- Example: `transactions.html`, `dashboard.html`

---

## Practice Questions

1. **Where would you add a new feature to calculate transaction totals?**
   - Answer: Model layer (`models.py`) - add method to Transaction model

2. **Where would you add a new route to export data?**
   - Answer: Controller layer (`routes.py`) - add new route handler

3. **Where would you change how transactions are displayed?**
   - Answer: View layer (`templates/transactions.html`) - modify HTML template

4. **How does authentication work in MVC?**
   - Answer: Controller checks credentials, queries User Model, creates session, redirects

5. **What happens when a user deletes a transaction?**
   - Answer: Controller receives request → queries Transaction Model → deletes from database → redirects to list view

