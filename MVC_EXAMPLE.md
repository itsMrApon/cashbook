# MVC Pattern Explanation for Django Interview

## What is MVC?

**MVC (Model-View-Controller)** is an architectural pattern that separates an application into three main components:

1. **Model (M)** - Data layer: Handles data, business logic, database operations
2. **View (V)** - Presentation layer: What the user sees (HTML templates)
3. **Controller (C)** - Logic layer: Handles user input, processes requests, coordinates between Model and View

## Django vs Flask MVC Mapping

### Django uses MVT (Model-View-Template):

- **Model** = Same as MVC (data layer)
- **View** = Controller in MVC (handles logic)
- **Template** = View in MVC (presentation)

### Flask (this project) uses MVC:

- **Model** = `app/models.py` (database models)
- **View** = `app/templates/` (HTML templates)
- **Controller** = `app/routes.py` (route handlers)

## Simple MVC Example

```python
# ============================================
# MODEL (models.py) - Data Layer
# ============================================
# Step 1: Define the data structure
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))

    def __repr__(self):
        return f'<User {self.name}>'

# ============================================
# CONTROLLER (routes.py) - Logic Layer
# ============================================
# Step 2: Handle user requests and business logic
@app.route('/users')
def list_users():
    # Step 2a: Get data from Model
    users = User.query.all()  # MODEL interaction

    # Step 2b: Process/format data (business logic)
    user_list = [{'name': u.name, 'email': u.email} for u in users]

    # Step 2c: Pass data to View
    return render_template('users.html', users=user_list)  # VIEW interaction

@app.route('/users/add', methods=['POST'])
def add_user():
    # Step 2a: Get data from request
    name = request.form.get('name')
    email = request.form.get('email')

    # Step 2b: Create Model instance
    new_user = User(name=name, email=email)  # MODEL interaction

    # Step 2c: Save to database
    db.session.add(new_user)
    db.session.commit()

    # Step 2d: Redirect to View
    return redirect(url_for('list_users'))

# ============================================
# VIEW (templates/users.html) - Presentation Layer
# ============================================
# Step 3: Display data to user
"""
<!DOCTYPE html>
<html>
<body>
    <h1>Users</h1>
    <ul>
        {% for user in users %}  {# Data from Controller #}
            <li>{{ user.name }} - {{ user.email }}</li>
        {% endfor %}
    </ul>
</body>
</html>
"""

# ============================================
# FLOW DIAGRAM
# ============================================
# User Request → Controller → Model → Database
#                                      ↓
# User Response ← View ← Controller ← Model
```

## Key Points for Interview:

1. **Separation of Concerns**: Each component has a specific responsibility
2. **Model**: Never directly renders HTML, only handles data
3. **View**: Never contains business logic, only displays data
4. **Controller**: Coordinates between Model and View, handles HTTP requests
5. **Benefits**: Easier to test, maintain, and scale
