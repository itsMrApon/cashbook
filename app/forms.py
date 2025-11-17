from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, DecimalField, SelectField, DateField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError, EqualTo
from app.models import User, Category, Role
from datetime import date

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.role_id.choices = [(role.id, role.name) for role in Role.query.all()]
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists. Please choose a different one.')

class TransactionForm(FlaskForm):
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    amount = DecimalField('Amount', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=500)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    party = StringField('Party (Person/Organization)', validators=[Optional(), Length(max=200)])
    transaction_date = DateField('Date', validators=[DataRequired()], default=date.today)
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    receipts = FileField('Receipt', validators=[Optional(), FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Only PDF and image files allowed!')])
    submit = SubmitField('Save Transaction')
    
    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(cat.id, cat.name) for cat in Category.query.order_by(Category.name).all()]

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    color = StringField('Color', validators=[Optional()], default='#007bff')
    submit = SubmitField('Save Category')

class SpendingLimitForm(FlaskForm):
    type = SelectField('Period', choices=[('daily', 'Daily'), ('monthly', 'Monthly')], validators=[DataRequired()])
    amount = DecimalField('Limit Amount', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    category_id = SelectField('Category (Optional)', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Limit')
    
    def __init__(self, *args, **kwargs):
        super(SpendingLimitForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'All Categories')] + [(cat.id, cat.name) for cat in Category.query.order_by(Category.name).all()]

class ReportForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    type = SelectField('Type', choices=[('', 'All'), ('income', 'Income'), ('expense', 'Expense')], validators=[Optional()])
    format = SelectField('Format', choices=[('pdf', 'PDF'), ('excel', 'Excel')], validators=[DataRequired()])
    submit = SubmitField('Generate Report')
    
    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(0, 'All Users')] + [(user.id, user.get_full_name()) for user in User.query.filter_by(is_active=True).order_by(User.username).all()]
        self.category_id.choices = [(0, 'All Categories')] + [(cat.id, cat.name) for cat in Category.query.order_by(Category.name).all()]

class SearchForm(FlaskForm):
    search_term = StringField('Search', validators=[Optional()], render_kw={"placeholder": "Search transactions..."})
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    type = SelectField('Type', choices=[('', 'All'), ('income', 'Income'), ('expense', 'Expense')], validators=[Optional()])
    start_date = DateField('From Date', validators=[Optional()])
    end_date = DateField('To Date', validators=[Optional()])
    submit = SubmitField('Search')
    
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'All Categories')] + [(cat.id, cat.name) for cat in Category.query.order_by(Category.name).all()]

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    password = PasswordField('Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Save User')
    
    def __init__(self, user=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.role_id.choices = [(role.id, role.name) for role in Role.query.all()]
        self._user = user
    
    def validate_username(self, username):
        if self._user and self._user.username == username.data:
            return
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        if self._user and self._user.email == email.data:
            return
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists. Please choose a different one.')
