from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from app import bcrypt, db
from app.forms import LoginForm, RegisterForm
from app.models import ChatMessage, CompanyUpdate, Department, DirectMessage, EmployeeTask, HomepageMedia, ReportDocument, User
import os
from urllib.parse import urlparse, urljoin
from uuid import uuid4

routes = Blueprint('routes', __name__)
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'mp4', 'mov', 'webm', 'avi'}
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


@routes.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


def is_safe_redirect(target):
    if not target:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {'http', 'https'} and host_url.netloc == redirect_url.netloc


def department_names():
    try:
        names = [dept.name for dept in Department.query.order_by(Department.name.asc()).all()]
        if names:
            return names
    except Exception:
        pass
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

def get_homepage_defaults():
    return {
        'hero_image': 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=1400',
        'feature_images': [
            {
                'src': 'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&q=80&w=600',
                'alt': 'Modern Office',
                'title': 'Modern Workflows',
                'description': 'A platform built to keep departments aligned and productive.'
            },
            {
                'src': 'https://images.unsplash.com/photo-1522071823991-b9671f30d46f?auto=format&fit=crop&q=80&w=600',
                'alt': 'Collaboration',
                'title': 'Team Collaboration',
                'description': 'Department chat keeps everyone connected on shared priorities.'
            },
            {
                'src': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&q=80&w=600',
                'alt': 'Data Analytics',
                'title': 'Insights & Reporting',
                'description': 'Upload, assign, and review reports from a single location.'
            }
        ]
    }


# =====================
# Home Page
# =====================
@routes.route('/')
def home():
    hero_media = HomepageMedia.query.filter_by(asset_type='hero').order_by(HomepageMedia.order.asc()).first()
    feature_media = HomepageMedia.query.filter_by(asset_type='feature').order_by(HomepageMedia.order.asc()).limit(3).all()
    defaults = get_homepage_defaults()
    return render_template(
        'index.html',
        hero_media=hero_media,
        feature_media=feature_media,
        homepage_defaults=defaults
    )


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
        'departments': len(department_names())
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
    try:
        db_departments = Department.query.order_by(Department.name.asc()).all()
    except Exception:
        db_departments = []
    department_list = db_departments if db_departments else DEPARTMENTS
    return render_template('manager_dashboard.html', stats=stats, updates=updates, departments=department_list, employees=employees, is_admin=is_admin())


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
        media = request.files.get('media')

        if not body and not media:
            flash('Please enter a message or upload media before sending.', 'danger')
            return redirect(url_for('routes.chat'))

        original_filename = None
        stored_filename = None
        media_type = 'file'

        if media and media.filename:
            if not allowed_document(media.filename):
                flash('Unsupported file type. Supported files include images and videos.', 'danger')
                return redirect(url_for('routes.chat', department=department))

            original_filename, stored_filename = store_uploaded_document(media)
            extension = original_filename.rsplit('.', 1)[1].lower()
            media_type = 'video' if extension in {'mp4', 'mov', 'webm', 'avi'} else 'image' if extension in {'png', 'jpg', 'jpeg', 'gif'} else 'file'

        message = ChatMessage(
            department=department,
            body=body,
            user_id=current_user.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            media_type=media_type
        )
        db.session.add(message)
        db.session.commit()
        flash('Message sent.', 'success')
        return redirect(url_for('routes.chat', department=department))

    active_department = request.args.get('department', 'General')
    messages = ChatMessage.query.filter_by(department=active_department).order_by(ChatMessage.created_at.asc()).all()

    try:
        department_objects = Department.query.order_by(Department.name.asc()).all()
    except Exception:
        department_objects = []
    department_list = [d.name for d in department_objects] if department_objects else [department['name'] for department in DEPARTMENTS]
    return render_template('chat.html', messages=messages, departments=department_list, active_department=active_department)


@routes.route('/departments')
@login_required
def departments():
    require_admin()
    department_stats = []

    try:
        db_departments = Department.query.order_by(Department.name.asc()).all()
    except Exception:
        db_departments = []
    department_source = db_departments if db_departments else DEPARTMENTS

    for department in department_source:
        dept_name = department.name if hasattr(department, 'name') else department['name']
        employee_count = User.query.filter_by(department=dept_name).count()
        employees = User.query.filter_by(department=dept_name).order_by(User.username.asc()).limit(4).all()
        report_count = ReportDocument.query.filter(ReportDocument.message.ilike(f"%{dept_name}%")).count()
        message_count = ChatMessage.query.filter_by(department=dept_name).count()
        update_count = CompanyUpdate.query.filter_by(department=dept_name).count()
        department_stats.append({
            'id': department.id if hasattr(department, 'id') else None,
            'name': dept_name,
            'lead': department.lead if hasattr(department, 'lead') else department['lead'],
            'summary': department.summary if hasattr(department, 'summary') else department['summary'],
            'status': department.status if hasattr(department, 'status') else department['status'],
            'employees': employee_count,
            'employee_preview': employees,
            'reports': report_count,
            'messages': message_count,
            'updates': update_count
        })

    return render_template('departments.html', departments=department_stats)

@routes.route('/departments/<department_name>')
@login_required
def department_detail(department_name):
    require_admin()
    
    department = Department.query.filter_by(name=department_name).first()
    if not department:
        department = next((d for d in DEPARTMENTS if d['name'] == department_name), None)
        if not department:
            abort(404)
    
    employees = User.query.filter_by(department=department_name).order_by(User.username.asc()).all()
    
    all_users = User.query.order_by(User.department.asc(), User.username.asc()).all()
    
    employee_details = []
    for emp in employees:
        stats = {
            'sent_reports': ReportDocument.query.filter_by(sender_id=emp.id).count(),
            'received_reports': ReportDocument.query.filter_by(recipient_id=emp.id).count(),
            'open_tasks': EmployeeTask.query.filter(
                EmployeeTask.employee_id == emp.id,
                EmployeeTask.status != 'Done'
            ).count(),
            'completed_tasks': EmployeeTask.query.filter_by(employee_id=emp.id, status='Done').count()
        }
        employee_details.append({
            'user': emp,
            'stats': stats,
            'tasks': EmployeeTask.query.filter_by(employee_id=emp.id).order_by(EmployeeTask.created_at.desc()).limit(3).all()
        })
    
    return render_template(
        'department_detail.html',
        department=department,
        employee_details=employee_details,
        all_users=all_users,
        department_list=department_names()
    )


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
    return redirect(url_for('routes.department_detail', department_name=department))


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
    
    all_users = User.query.order_by(User.department.asc(), User.username.asc()).all()
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
        is_admin=is_admin(),
        all_users=all_users,
        department_list=department_names()
    )


@routes.route('/tasks/assign-global', methods=['POST'])
@login_required
def assign_global_task():
    require_admin()
    
    assignment_type = request.form.get('assignment_type')  # 'individual' or 'department'
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Normal').strip() or 'Normal'
    due_date = request.form.get('due_date', '').strip()
    document = request.files.get('document')
    
    original_filename = None
    stored_filename = None

    if not title:
        flash('Please enter a task title.', 'danger')
        return redirect(request.referrer or url_for('routes.dashboard'))

    # Handle Recipients
    recipients = []
    if assignment_type == 'department':
        dept_name = request.form.get('target_department')
        recipients = User.query.filter_by(department=dept_name).all()
        if not recipients:
            flash(f'No employees found in the {dept_name} department.', 'warning')
            return redirect(request.referrer)
    else:
        user_id = request.form.get('target_user_id', type=int)
        user = User.query.get(user_id)
        if user:
            recipients = [user]

    if not recipients:
        flash('Please select a valid recipient or department.', 'danger')
        return redirect(request.referrer)

    # File Handling
    if document and document.filename:
        if not allowed_document(document.filename):
            flash('This work file type is not allowed.', 'danger')
            return redirect(request.referrer)
        original_filename, stored_filename = store_uploaded_document(document)

    for recipient in recipients:
        task = EmployeeTask(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            original_filename=original_filename,
            stored_filename=stored_filename,
            employee_id=recipient.id,
            assigned_by_id=current_user.id
        )
        db.session.add(task)

    db.session.commit()
    flash(f'Task assigned to {len(recipients)} recipient(s).', 'success')
    return redirect(request.referrer)


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
    # Sort by department first, then username to allow grouping in the template
    users = User.query.filter(User.id != current_user.id).order_by(User.department.asc(), User.username.asc()).all()

    reports = ReportDocument.query.order_by(ReportDocument.created_at.desc()).all()

    # Identify employees who have not sent any reports
    from sqlalchemy import not_
    sent_sender_ids = db.session.query(ReportDocument.sender_id).filter(ReportDocument.sender_id.isnot(None)).distinct()
    missing_users = User.query.filter(
        User.role == 'employee',
        not_(User.id.in_(sent_sender_ids))
    ).order_by(User.department.asc(), User.username.asc()).all()

    return render_template('reports.html', reports=reports, users=users, missing_users=missing_users)


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


# =====================
# COMPREHENSIVE CRUD OPERATIONS
# =====================

# =====================
# DEPARTMENT CRUD
# =====================
@routes.route('/admin/departments/create', methods=['GET', 'POST'])
@login_required
def create_department():
    require_admin()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        lead = request.form.get('lead', '').strip()
        summary = request.form.get('summary', '').strip()
        status = request.form.get('status', 'Active').strip()

        if not name:
            flash('Department name is required.', 'danger')
            return redirect(url_for('routes.create_department'))

        if Department.query.filter_by(name=name).first():
            flash('A department with this name already exists.', 'danger')
            return redirect(url_for('routes.create_department'))

        department = Department(
            name=name,
            lead=lead,
            summary=summary,
            status=status
        )
        db.session.add(department)
        db.session.commit()
        flash(f'Department "{name}" created successfully.', 'success')
        return redirect(url_for('routes.departments'))

    return render_template('department_form.html', department=None, action='Create')


@routes.route('/admin/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_department(dept_id):
    require_admin()
    department = Department.query.get_or_404(dept_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        lead = request.form.get('lead', '').strip()
        summary = request.form.get('summary', '').strip()
        status = request.form.get('status', 'Active').strip()

        if not name:
            flash('Department name is required.', 'danger')
            return redirect(url_for('routes.edit_department', dept_id=dept_id))

        # Check if name is taken by another department
        existing = Department.query.filter_by(name=name).filter(Department.id != dept_id).first()
        if existing:
            flash('A department with this name already exists.', 'danger')
            return redirect(url_for('routes.edit_department', dept_id=dept_id))

        department.name = name
        department.lead = lead
        department.summary = summary
        department.status = status
        db.session.commit()
        flash(f'Department "{name}" updated successfully.', 'success')
        return redirect(url_for('routes.departments'))

    return render_template('department_form.html', department=department, action='Edit')


@routes.route('/admin/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
def delete_department(dept_id):
    require_admin()
    department = Department.query.get_or_404(dept_id)

    # Check if department has employees
    employee_count = User.query.filter_by(department=department.name).count()
    if employee_count > 0:
        flash(f'Cannot delete department with {employee_count} employee(s). Move employees to another department first.', 'danger')
        return redirect(url_for('routes.departments'))

    dept_name = department.name
    db.session.delete(department)
    db.session.commit()
    flash(f'Department "{dept_name}" deleted successfully.', 'success')
    return redirect(url_for('routes.departments'))


# =====================
# HOMEPAGE MEDIA CRUD
# =====================
@routes.route('/admin/home-media')
@login_required
def home_media():
    require_admin()
    assets = HomepageMedia.query.order_by(HomepageMedia.asset_type.asc(), HomepageMedia.order.asc()).all()
    return render_template('home_media_list.html', assets=assets)


@routes.route('/admin/home-media/create', methods=['GET', 'POST'])
@login_required
def create_home_media():
    require_admin()

    if request.method == 'POST':
        asset_type = request.form.get('asset_type', 'feature').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        order = request.form.get('order', '0').strip() or '0'
        media = request.files.get('media')

        if not media or media.filename == '':
            flash('Please upload an image or video file for the homepage asset.', 'danger')
            return redirect(url_for('routes.create_home_media'))

        if not allowed_document(media.filename):
            flash('Unsupported file type. Supported files include images and video formats.', 'danger')
            return redirect(url_for('routes.create_home_media'))

        original_filename, stored_filename = store_uploaded_document(media)
        extension = original_filename.rsplit('.', 1)[1].lower()
        media_type = 'video' if extension in {'mp4', 'mov', 'webm', 'avi'} else 'image'

        asset = HomepageMedia(
            asset_type=asset_type,
            title=title,
            description=description,
            media_type=media_type,
            original_filename=original_filename,
            stored_filename=stored_filename,
            order=int(order)
        )

        db.session.add(asset)
        db.session.commit()
        flash('Homepage media asset saved successfully.', 'success')
        return redirect(url_for('routes.home_media'))

    return render_template('home_media_form.html', asset=None, action='Create')


@routes.route('/admin/home-media/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_home_media(asset_id):
    require_admin()
    asset = HomepageMedia.query.get_or_404(asset_id)

    if request.method == 'POST':
        asset.asset_type = request.form.get('asset_type', asset.asset_type).strip()
        asset.title = request.form.get('title', asset.title).strip()
        asset.description = request.form.get('description', asset.description).strip()
        order = request.form.get('order', str(asset.order)).strip() or '0'
        asset.order = int(order)

        media = request.files.get('media')
        if media and media.filename:
            if not allowed_document(media.filename):
                flash('Unsupported file type. Supported files include images and video formats.', 'danger')
                return redirect(url_for('routes.edit_home_media', asset_id=asset_id))

            original_filename, stored_filename = store_uploaded_document(media)
            try:
                existing_path = os.path.join(current_app.config['UPLOAD_FOLDER'], asset.stored_filename)
                if os.path.exists(existing_path):
                    os.remove(existing_path)
            except Exception:
                pass

            extension = original_filename.rsplit('.', 1)[1].lower()
            asset.media_type = 'video' if extension in {'mp4', 'mov', 'webm', 'avi'} else 'image'
            asset.original_filename = original_filename
            asset.stored_filename = stored_filename

        db.session.commit()
        flash('Homepage media asset updated successfully.', 'success')
        return redirect(url_for('routes.home_media'))

    return render_template('home_media_form.html', asset=asset, action='Edit')


@routes.route('/admin/home-media/<int:asset_id>/delete', methods=['POST'])
@login_required
def delete_home_media(asset_id):
    require_admin()
    asset = HomepageMedia.query.get_or_404(asset_id)

    try:
        existing_path = os.path.join(current_app.config['UPLOAD_FOLDER'], asset.stored_filename)
        if os.path.exists(existing_path):
            os.remove(existing_path)
    except Exception:
        pass

    db.session.delete(asset)
    db.session.commit()
    flash('Homepage media asset deleted successfully.', 'success')
    return redirect(url_for('routes.home_media'))


# =====================
# EMPLOYEE CRUD
# =====================
@routes.route('/admin/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        position = request.form.get('position', '').strip()
        hire_date = request.form.get('hire_date', '').strip()
        role = request.form.get('role', 'employee').strip()

        if not full_name or not email or not department or not position:
            flash('Please complete all required fields.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        # Check if email is taken by another user
        if email != employee.email and User.query.filter_by(email=email).first():
            flash('That email is already in use.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        if department not in department_names():
            flash('Invalid department selected.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        employee.full_name = full_name
        employee.email = email
        employee.phone = phone
        employee.department = department
        employee.position = position
        employee.hire_date = hire_date
        employee.role = role
        db.session.commit()
        flash(f'{full_name} updated successfully.', 'success')
        return redirect(url_for('routes.employee_detail', employee_id=employee_id))

    return render_template('employee_form.html', employee=employee, action='Edit', department_list=department_names())


@routes.route('/admin/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
def delete_employee(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)
    employee_name = employee.full_name or employee.username

    # Check for related data
    task_count = EmployeeTask.query.filter_by(employee_id=employee_id).count()
    report_count = ReportDocument.query.filter_by(sender_id=employee_id).count()
    message_count = DirectMessage.query.filter(
        (DirectMessage.sender_id == employee_id) | (DirectMessage.recipient_id == employee_id)
    ).count()

    if task_count > 0 or report_count > 0 or message_count > 0:
        flash(f'Cannot delete employee with associated tasks, reports, or messages. Please remove these first.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee_id))

    db.session.delete(employee)
    db.session.commit()
    flash(f'Employee "{employee_name}" deleted successfully.', 'success')
    return redirect(url_for('routes.departments'))


# =====================
# TASK CRUD
# =====================
@routes.route('/admin/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    require_admin()
    task = EmployeeTask.query.get_or_404(task_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Normal').strip()
        status = request.form.get('status', 'To Do').strip()
        due_date = request.form.get('due_date', '').strip()

        if not title:
            flash('Task title is required.', 'danger')
            return redirect(url_for('routes.edit_task', task_id=task_id))

        task.title = title
        task.description = description
        task.priority = priority
        task.status = status
        task.due_date = due_date
        db.session.commit()
        flash(f'Task "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.employee_detail', employee_id=task.employee_id))

    return render_template('task_form.html', task=task, action='Edit')


@routes.route('/admin/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    require_admin()
    task = EmployeeTask.query.get_or_404(task_id)
    task_title = task.title
    employee_id = task.employee_id

    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{task_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee_id))


# =====================
# REPORT CRUD
# =====================
@routes.route('/admin/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    require_admin()
    report = ReportDocument.query.get_or_404(report_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        status = request.form.get('status', 'Sent').strip()

        if not title:
            flash('Report title is required.', 'danger')
            return redirect(url_for('routes.edit_report', report_id=report_id))

        report.title = title
        report.message = message
        report.status = status
        db.session.commit()
        flash(f'Report "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.reports'))

    return render_template('report_form.html', report=report, action='Edit')


@routes.route('/admin/reports/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    require_admin()
    report = ReportDocument.query.get_or_404(report_id)
    report_title = report.title

    # Delete file if exists
    if report.stored_filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], report.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    db.session.delete(report)
    db.session.commit()
    flash(f'Report "{report_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.reports'))


# =====================
# COMPANY UPDATE CRUD
# =====================
@routes.route('/admin/updates/<int:update_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_update(update_id):
    require_admin()
    update = CompanyUpdate.query.get_or_404(update_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        department = request.form.get('department', 'Company-wide').strip() or 'Company-wide'

        if not title or not body:
            flash('Please enter both a title and update details.', 'danger')
            return redirect(url_for('routes.edit_update', update_id=update_id))

        update.title = title
        update.body = body
        update.department = department
        db.session.commit()
        flash(f'Update "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.manager_dashboard'))

    return render_template('update_form.html', update=update, action='Edit', department_list=department_names())


@routes.route('/admin/updates/<int:update_id>/delete', methods=['POST'])
@login_required
def delete_update(update_id):
    require_admin()
    update = CompanyUpdate.query.get_or_404(update_id)
    update_title = update.title

    db.session.delete(update)
    db.session.commit()
    flash(f'Update "{update_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.manager_dashboard'))


# =====================
# CHAT MESSAGE DELETE
# =====================
@routes.route('/admin/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_chat_message(message_id):
    require_admin()
    message = ChatMessage.query.get_or_404(message_id)
    department = message.department

    db.session.delete(message)
    db.session.commit()
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('routes.chat', department=department))


# =====================
# DIRECT MESSAGE DELETE
# =====================
@routes.route('/admin/direct-messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_direct_message(message_id):
    require_admin()
    message = DirectMessage.query.get_or_404(message_id)

    # Delete attached file if exists
    if message.stored_filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], message.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    sender_id = message.sender_id
    db.session.delete(message)
    db.session.commit()
    flash('Direct message deleted successfully.', 'success')
    return redirect(request.referrer or url_for('routes.dashboard'))
