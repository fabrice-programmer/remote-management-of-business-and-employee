from flask import Blueprint, render_template

routes = Blueprint('routes', __name__)

# =====================
# Home Page
# =====================
@routes.route('/')
def home():
    return render_template('index.html')


# =====================
# Authentication Pages
# =====================
@routes.route('/login')
def login():
    return render_template('login.html')


@routes.route('/register')
def register():
    return render_template('register.html')


# =====================
# Dashboards
# =====================
@routes.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@routes.route('/manager-dashboard')
def manager_dashboard():
    return render_template('manager_dashboard.html')


# =====================
# Company Modules
# =====================
@routes.route('/chat')
def chat():
    return render_template('chat.html')


@routes.route('/departments')
def departments():
    return render_template('departments.html')


@routes.route('/reports')
def reports():
    return render_template('reports.html')