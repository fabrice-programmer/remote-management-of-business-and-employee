from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from app import bcrypt, db
from app.forms import LoginForm, RegisterForm
from app.models import ChatMessage, CompanyUpdate, DirectMessage, EmployeeTask, ReportDocument, User
import os
from urllib.parse import urlparse, urljoin
from uuid import uuid4

routes = Blueprint('routes', __name__)
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg'}
ADMIN_ROLES = {'admin', 'manager'}
DEPARTMENTS = [
    {
        'name': 'Operations',
        'lead': 'Operations Manager',
        'summary': 'Coordinates daily work, tasks, productivity, and company execution.',
        'status': 'Active'
    },
    {
        'name': 'Human Resources',
        'lead': 'HR Lead',
        'summary': 'Manages employee records, onboarding, support, and internal policy updates.',
        'status': 'Active'
    },
    {
        'name': 'Finance',
        'lead': 'Finance Controller',
        'summary': 'Tracks budgets, payments, approvals, and financial reporting.',
        'status': 'Reviewing'
    },
    {
        'name': 'IT Support',
        'lead': 'Systems Admin',
        'summary': 'Maintains business systems, user access, devices, and technical support.',
        'status': 'Active'
    }
]


def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS


def store_uploaded_document(document):
    original_filename = secure_filename(document.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f'{uuid4().hex}.{extension}'
    document.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename))
    return original_filename, stored_filename


def is_safe_redirect(target):
    if not target:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {'http', 'https'} and host_url.netloc == redirect_url.netloc


def department_names():
    return [department['name'] for department in DEPARTMENTS]


def admin_users_query():
    return User.query.filter(User.role.in_(ADMIN_ROLES))


def is_admin(user=None):
    user = user or current_user
    return user.is_authenticated and user.role in ADMIN_ROLES


def require_admin():
    if not is_admin():
        abort(403)


def can_view_employee(employee):
    return is_admin() or current_user.id == employee.id

# =====================
# Home Page
# =====================
@routes.route('/')
def home():
    return render_template('index.html')


# =====================
# Authentication Pages
# =====================
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('You are logged in.', 'success')
            next_page = request.args.get('next')
            if is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for('routes.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))

    form = RegisterForm()

    if form.validate_on_submit():
        username_exists = User.query.filter_by(username=form.username.data).first()
        email_exists = User.query.filter_by(email=form.email.data.lower()).first()

        if username_exists:
            flash('That username is already taken.', 'danger')
            return render_template('register.html', form=form)

        if email_exists:
            flash('That email already has an account.', 'danger')
            return render_template('register.html', form=form)

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()
        flash('Account created. You can now log in.', 'success')
        return redirect(url_for('routes.login'))

    return render_template('register.html', form=form)


@routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You are logged out.', 'info')
    return redirect(url_for('routes.home'))


# =====================
# Dashboards
# =====================
@routes.route('/dashboard')
@login_required
def dashboard():
    if is_admin():
        visible_reports = ReportDocument.query
        employees_count = User.query.count()
    else:
        visible_reports = ReportDocument.query.filter(
            (ReportDocument.sender_id == current_user.id) |
            (ReportDocument.recipient_id == current_user.id)
        )
        employees_count = 1

    stats = {
        'employees': employees_count,
        'reports': visible_reports.count(),
        'received': ReportDocument.query.filter_by(recipient_id=current_user.id).count(),
        'departments': len(DEPARTMENTS)
    }
    updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(5).all()
    reports = visible_reports.order_by(ReportDocument.created_at.desc()).limit(5).all()
    messages = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(4).all()
    direct_messages = DirectMessage.query.filter_by(recipient_id=current_user.id).order_by(DirectMessage.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', stats=stats, updates=updates, reports=reports, messages=messages, direct_messages=direct_messages, is_admin=is_admin())


@routes.route('/manager-dashboard')
@login_required
def manager_dashboard():
    employees = User.query.order_by(User.username.asc()).all() if is_admin() else []
    stats = {
        'employees': User.query.count(),
        'reports': ReportDocument.query.count(),
        'updates': CompanyUpdate.query.count(),
        'messages': ChatMessage.query.count()
    }
    updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(8).all()
    return render_template('manager_dashboard.html', stats=stats, updates=updates, departments=DEPARTMENTS, employees=employees, is_admin=is_admin())


@routes.route('/updates/create', methods=['POST'])
@login_required
def create_update():
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    department = request.form.get('department', 'Company-wide').strip() or 'Company-wide'

    if not title or not body:
        flash('Please enter both a title and update details.', 'danger')
        return redirect(url_for('routes.manager_dashboard'))

    update = CompanyUpdate(
        title=title,
        body=body,
        department=department,
        author_id=current_user.id
    )
    db.session.add(update)
    db.session.commit()
    flash('Company update published.', 'success')
    return redirect(url_for('routes.manager_dashboard'))


# =====================
# Company Modules
# =====================
@routes.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    require_admin()
    if request.method == 'POST':
        body = request.form.get('message', '').strip()
        department = request.form.get('department', 'General').strip() or 'General'

        if not body:
            flash('Please enter a message before sending.', 'danger')
            return redirect(url_for('routes.chat'))

        message = ChatMessage(department=department, body=body, user_id=current_user.id)
        db.session.add(message)
        db.session.commit()
        flash('Message sent.', 'success')
        return redirect(url_for('routes.chat', department=department))

    active_department = request.args.get('department', 'General')
    messages = ChatMessage.query.filter_by(department=active_department).order_by(ChatMessage.created_at.asc()).all()
    return render_template('chat.html', messages=messages, departments=DEPARTMENTS, active_department=active_department)


@routes.route('/departments')
@login_required
def departments():
    require_admin()
    department_stats = []

    for department in DEPARTMENTS:
        employee_count = User.query.filter_by(department=department['name']).count()
        employees = User.query.filter_by(department=department['name']).order_by(User.username.asc()).limit(4).all()
        report_count = ReportDocument.query.filter(ReportDocument.message.ilike(f"%{department['name']}%")).count()
        message_count = ChatMessage.query.filter_by(department=department['name']).count()
        update_count = CompanyUpdate.query.filter_by(department=department['name']).count()
        department_stats.append({
            **department,
            'employees': employee_count,
            'employee_preview': employees,
            'reports': report_count,
            'messages': message_count,
            'updates': update_count
        })

    return render_template('departments.html', departments=department_stats)


@routes.route('/departments/employees/add', methods=['POST'])
@login_required
def add_department_employee():
    require_admin()
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    employee_number = request.form.get('employee_number', '').strip()
    phone = request.form.get('phone', '').strip()
    department = request.form.get('department', '').strip()
    position = request.form.get('position', '').strip()
    hire_date = request.form.get('hire_date', '').strip()
    password = request.form.get('password', '').strip()

    required_fields = {
        'full name': full_name,
        'username': username,
        'email': email,
        'employee number': employee_number,
        'department': department,
        'position': position,
        'password': password
    }
    missing_fields = [label for label, value in required_fields.items() if not value]

    if missing_fields:
        flash(f"Please complete: {', '.join(missing_fields)}.", 'danger')
        return redirect(url_for('routes.departments'))

    if department not in department_names():
        flash('Please choose a valid department.', 'danger')
        return redirect(url_for('routes.departments'))

    if len(password) < 6:
        flash('Employee password must be at least 6 characters.', 'danger')
        return redirect(url_for('routes.departments'))

    if User.query.filter_by(username=username).first():
        flash('That username is already taken.', 'danger')
        return redirect(url_for('routes.departments'))

    if User.query.filter_by(email=email).first():
        flash('That email already has an account.', 'danger')
        return redirect(url_for('routes.departments'))

    if User.query.filter_by(employee_number=employee_number).first():
        flash('That employee number is already in use.', 'danger')
        return redirect(url_for('routes.departments'))

    employee = User(
        full_name=full_name,
        username=username,
        email=email,
        employee_number=employee_number,
        phone=phone,
        department=department,
        position=position,
        hire_date=hire_date,
        role='employee',
        password=bcrypt.generate_password_hash(password).decode('utf-8')
    )

    db.session.add(employee)
    db.session.commit()
    flash(f'{full_name} was added to {department}.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/employees/<int:employee_id>')
@login_required
def employee_detail(employee_id):
    employee = User.query.get_or_404(employee_id)
    if not can_view_employee(employee):
        abort(403)

    sent_reports = ReportDocument.query.filter_by(sender_id=employee.id).order_by(ReportDocument.created_at.desc()).all()
    received_reports = ReportDocument.query.filter_by(recipient_id=employee.id).order_by(ReportDocument.created_at.desc()).all()
    tasks = EmployeeTask.query.filter_by(employee_id=employee.id).order_by(EmployeeTask.created_at.desc()).all()
    direct_messages = DirectMessage.query.filter(
        (DirectMessage.sender_id == employee.id) |
        (DirectMessage.recipient_id == employee.id)
    ).order_by(DirectMessage.created_at.desc()).all()
    admin_users = admin_users_query().filter(User.id != current_user.id).order_by(User.username.asc()).all()

    stats = {
        'sent_reports': len(sent_reports),
        'received_reports': len(received_reports),
        'open_tasks': EmployeeTask.query.filter(
            EmployeeTask.employee_id == employee.id,
            EmployeeTask.status != 'Done'
        ).count(),
        'completed_tasks': EmployeeTask.query.filter_by(employee_id=employee.id, status='Done').count()
    }

    return render_template(
        'employee_detail.html',
        employee=employee,
        sent_reports=sent_reports,
        received_reports=received_reports,
        tasks=tasks,
        direct_messages=direct_messages,
        admin_users=admin_users,
        stats=stats,
        is_admin=is_admin()
    )


@routes.route('/employees/<int:employee_id>/tasks/add', methods=['POST'])
@login_required
def add_employee_task(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Normal').strip() or 'Normal'
    due_date = request.form.get('due_date', '').strip()
    document = request.files.get('document')
    original_filename = None
    stored_filename = None

    if not title:
        flash('Please enter a task title.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if priority not in {'Low', 'Normal', 'High', 'Urgent'}:
        priority = 'Normal'

    if document and document.filename:
        if not allowed_document(document.filename):
            flash('This work file type is not allowed.', 'danger')
            return redirect(url_for('routes.employee_detail', employee_id=employee.id))

        original_filename, stored_filename = store_uploaded_document(document)

    task = EmployeeTask(
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        original_filename=original_filename,
        stored_filename=stored_filename,
        employee_id=employee.id,
        assigned_by_id=current_user.id
    )
    db.session.add(task)
    db.session.commit()
    flash(f'Task assigned to {employee.full_name or employee.username}.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/employees/<int:employee_id>/tasks/<int:task_id>/report', methods=['POST'])
@login_required
def submit_employee_task_report(employee_id, task_id):
    employee = User.query.get_or_404(employee_id)
    task = EmployeeTask.query.filter_by(id=task_id, employee_id=employee.id).first_or_404()
    if current_user.id != employee.id:
        abort(403)

    title = request.form.get('title', '').strip() or f'Finished Report: {task.title}'
    message = request.form.get('message', '').strip()
    document = request.files.get('document')
    recipient = task.assigned_by if task.assigned_by and task.assigned_by.role in ADMIN_ROLES else admin_users_query().first()

    if not recipient:
        flash('No admin account is available to receive this report.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if not document or document.filename == '':
        flash('Please upload the finished report file.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if not allowed_document(document.filename):
        flash('This report file type is not allowed.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    original_filename, stored_filename = store_uploaded_document(document)
    report = ReportDocument(
        title=title,
        message=f'Task: {task.title}\n\n{message}' if message else f'Task: {task.title}',
        original_filename=original_filename,
        stored_filename=stored_filename,
        status='Submitted',
        sender_id=current_user.id,
        recipient_id=recipient.id
    )
    task.status = 'Done'

    db.session.add(report)
    db.session.commit()
    flash(f'Finished report sent to {recipient.username}.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/employees/<int:employee_id>/tasks/<int:task_id>/download')
@login_required
def download_employee_task(employee_id, task_id):
    employee = User.query.get_or_404(employee_id)
    task = EmployeeTask.query.filter_by(id=task_id, employee_id=employee.id).first_or_404()
    if not can_view_employee(employee):
        abort(403)

    if not task.stored_filename or not task.original_filename:
        abort(404)

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        task.stored_filename,
        as_attachment=True,
        download_name=task.original_filename
    )


@routes.route('/employees/<int:employee_id>/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_employee_task_status(employee_id, task_id):
    employee = User.query.get_or_404(employee_id)
    task = EmployeeTask.query.filter_by(id=task_id, employee_id=employee.id).first_or_404()
    if not can_view_employee(employee):
        abort(403)

    status = request.form.get('status', '').strip()

    if status not in {'To Do', 'In Progress', 'Done'}:
        flash('Please choose a valid task status.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    task.status = status
    db.session.commit()
    flash('Task status updated.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/employees/<int:employee_id>/messages/send', methods=['POST'])
@login_required
def send_employee_message(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)
    body = request.form.get('body', '').strip()
    document = request.files.get('document')
    original_filename = None
    stored_filename = None

    if not body and (not document or document.filename == ''):
        flash('Please enter a message or attach a file before sending.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if document and document.filename:
        if not allowed_document(document.filename):
            flash('This message file type is not allowed.', 'danger')
            return redirect(url_for('routes.employee_detail', employee_id=employee.id))

        original_filename, stored_filename = store_uploaded_document(document)

    message = DirectMessage(
        body=body or 'Attached file.',
        original_filename=original_filename,
        stored_filename=stored_filename,
        sender_id=current_user.id,
        recipient_id=employee.id
    )
    db.session.add(message)
    db.session.commit()
    flash(f'Message sent directly to {employee.full_name or employee.username}.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/employees/<int:employee_id>/messages/reply', methods=['POST'])
@login_required
def reply_employee_message(employee_id):
    employee = User.query.get_or_404(employee_id)
    if current_user.id != employee.id:
        abort(403)

    recipient_id = request.form.get('recipient_id', type=int)
    recipient = admin_users_query().filter_by(id=recipient_id).first() if recipient_id else None
    body = request.form.get('body', '').strip()
    document = request.files.get('document')
    original_filename = None
    stored_filename = None

    if not recipient:
        flash('Please choose an admin to receive your reply.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if not body and (not document or document.filename == ''):
        flash('Please enter a reply or attach a file before sending.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee.id))

    if document and document.filename:
        if not allowed_document(document.filename):
            flash('This reply file type is not allowed.', 'danger')
            return redirect(url_for('routes.employee_detail', employee_id=employee.id))

        original_filename, stored_filename = store_uploaded_document(document)

    message = DirectMessage(
        body=body or 'Attached file.',
        original_filename=original_filename,
        stored_filename=stored_filename,
        sender_id=current_user.id,
        recipient_id=recipient.id
    )
    db.session.add(message)
    db.session.commit()
    flash(f'Reply sent to {recipient.username}.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee.id))


@routes.route('/messages/<int:message_id>/download')
@login_required
def download_direct_message(message_id):
    message = DirectMessage.query.get_or_404(message_id)
    can_download = current_user.id in {message.sender_id, message.recipient_id}
    if not can_download and not is_admin():
        abort(403)

    if not message.stored_filename or not message.original_filename:
        abort(404)

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        message.stored_filename,
        as_attachment=True,
        download_name=message.original_filename
    )


@routes.route('/reports')
@login_required
def reports():
    require_admin()
    users = User.query.filter(User.id != current_user.id).order_by(User.username.asc()).all()

    reports = ReportDocument.query.order_by(ReportDocument.created_at.desc()).all()

    return render_template('reports.html', reports=reports, users=users)


@routes.route('/reports/upload', methods=['POST'])
@login_required
def upload_report():
    require_admin()
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    recipient_id = request.form.get('recipient_id', type=int)
    document = request.files.get('document')

    recipient = User.query.get(recipient_id) if recipient_id else None

    if not title:
        flash('Please enter a report title.', 'danger')
        return redirect(url_for('routes.reports'))

    if not recipient:
        flash('Please choose a valid recipient account.', 'danger')
        return redirect(url_for('routes.reports'))

    if not document or document.filename == '':
        flash('Please choose a document to upload.', 'danger')
        return redirect(url_for('routes.reports'))

    if not allowed_document(document.filename):
        flash('This document type is not allowed.', 'danger')
        return redirect(url_for('routes.reports'))

    original_filename, stored_filename = store_uploaded_document(document)

    report = ReportDocument(
        title=title,
        message=message,
        original_filename=original_filename,
        stored_filename=stored_filename,
        sender_id=current_user.id,
        recipient_id=recipient.id
    )

    db.session.add(report)
    db.session.commit()

    flash(f'Document sent to {recipient.username}.', 'success')
    return redirect(url_for('routes.reports'))


@routes.route('/reports/download/<int:report_id>')
@login_required
def download_report(report_id):
    report = ReportDocument.query.get_or_404(report_id)

    can_download = current_user.id in {report.sender_id, report.recipient_id}
    if not can_download and not is_admin():
        abort(403)

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        report.stored_filename,
        as_attachment=True,
        download_name=report.original_filename
    )
