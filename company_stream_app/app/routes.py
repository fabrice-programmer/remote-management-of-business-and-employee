from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from . import bcrypt, db
from .forms import LoginForm, RegisterForm
from .models import Attendance, ChatMessage, CompanyUpdate, DailyStat, Department, DirectMessage, EmployeeTask, HomepageMedia, Notification, ReportDocument, User
import os
from datetime import datetime, date
from urllib.parse import urlparse, urljoin
from uuid import uuid4

routes = Blueprint('routes', __name__)
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'webm', 'avi'}
ADMIN_ROLES = {'admin', 'manager'}
def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS


def store_uploaded_document(document):
    original_filename = secure_filename(document.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f'{uuid4().hex}.{extension}'
    document.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename))
    return original_filename, stored_filename

def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()


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
        return [dept.name for dept in Department.query.order_by(Department.name.asc()).all()]
    except Exception:
        return []


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
# Homepage Media Management
# =====================
@routes.route('/home-media')
@login_required
def home_media():
    require_admin()
    assets = HomepageMedia.query.order_by(HomepageMedia.asset_type, HomepageMedia.order).all()
    return render_template('home_media_list.html', assets=assets)


@routes.route('/home-media/create', methods=['GET', 'POST'])
@login_required
def create_home_media():
    require_admin()
    if request.method == 'POST':
        asset_type = request.form.get('asset_type', 'feature').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        order = request.form.get('order', 0, type=int)
        media = request.files.get('media')

        if not media or media.filename == '':
            flash('Please select an image or video file to upload.', 'danger')
            return render_template('home_media_form.html', asset=None, action='Create')

        if not allowed_document(media.filename):
            flash('Unsupported file type. Please upload an image or video.', 'danger')
            return render_template('home_media_form.html', asset=None, action='Create')

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
            order=order
        )
        db.session.add(asset)
        db.session.commit()
        flash('Homepage media asset created successfully.', 'success')
        return redirect(url_for('routes.home_media'))

    return render_template('home_media_form.html', asset=None, action='Create')


@routes.route('/home-media/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_home_media(asset_id):
    require_admin()
    asset = HomepageMedia.query.get_or_404(asset_id)

    if request.method == 'POST':
        asset.asset_type = request.form.get('asset_type', 'feature').strip()
        asset.title = request.form.get('title', '').strip()
        asset.description = request.form.get('description', '').strip()
        asset.order = request.form.get('order', 0, type=int)

        media = request.files.get('media')
        if media and media.filename:
            if not allowed_document(media.filename):
                flash('Unsupported file type. Please upload an image or video.', 'danger')
                return render_template('home_media_form.html', asset=asset, action='Edit')

            original_filename, stored_filename = store_uploaded_document(media)
            extension = original_filename.rsplit('.', 1)[1].lower()
            asset.media_type = 'video' if extension in {'mp4', 'mov', 'webm', 'avi'} else 'image'
            asset.original_filename = original_filename
            asset.stored_filename = stored_filename

        db.session.commit()
        flash('Homepage media asset updated successfully.', 'success')
        return redirect(url_for('routes.home_media'))

    return render_template('home_media_form.html', asset=asset, action='Edit')


@routes.route('/home-media/<int:asset_id>/delete', methods=['POST'])
@login_required
def delete_home_media(asset_id):
    require_admin()
    asset = HomepageMedia.query.get_or_404(asset_id)

    # Delete the file from disk
    if asset.stored_filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], asset.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting homepage media file: {e}")

    db.session.delete(asset)
    db.session.commit()
    flash('Homepage media asset deleted successfully.', 'success')
    return redirect(url_for('routes.home_media'))


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
            provided_code = form.employee_code.data.strip() if form.employee_code.data else ""
            
            # Verify against the user's specific code OR the global company secret
            company_secret = current_app.config.get('COMPANY_ACCESS_CODE', 'fab1')
            
            if provided_code == company_secret or provided_code == user.employee_code:
                login_user(user)
                flash('You are logged in.', 'success')
                next_page = request.args.get('next')
                if is_safe_redirect(next_page):
                    return redirect(next_page)
                return redirect(url_for('routes.dashboard'))
            else:
                flash('Invalid access code.', 'danger')
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))

    form = RegisterForm()

    if form.validate_on_submit():
        # Security check: verify the company access code
        if form.employee_code.data.strip() != current_app.config.get('COMPANY_ACCESS_CODE', 'fab1'):
            flash('Invalid company access code. Please contact your administrator.', 'danger')
            return render_template('register.html', form=form)

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
            password=hashed_password,
            employee_code=form.employee_code.data.strip()
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
    # Initialize defaults to prevent crashes if tables are missing
    attendance = None
    unread_notifications = 0
    updates, reports, messages, direct_messages = [], [], [], []
    employees_count = 0
    visible_reports_query = None
    today = date.today()

    try:
        if is_admin():
            visible_reports_query = ReportDocument.query
            employees_count = User.query.count()
        else:
            visible_reports_query = ReportDocument.query.filter(
                (ReportDocument.sender_id == current_user.id) |
                (ReportDocument.recipient_id == current_user.id)
            )
            employees_count = 1
    except Exception:
        employees_count = 1

    stats = {
        'employees': employees_count,
        'reports': 0,
        'received': 0,
        'departments': len(department_names()),
        'unread_notifications': 0
    }

    try:
        attendance = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        stats['unread_notifications'] = unread_notifications
        if visible_reports_query:
            stats['reports'] = visible_reports_query.count()
            reports = visible_reports_query.order_by(ReportDocument.created_at.desc()).limit(5).all()
            
        stats['received'] = ReportDocument.query.filter_by(recipient_id=current_user.id).count()
        updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(5).all()
        messages = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(4).all()
        direct_messages = DirectMessage.query.filter_by(recipient_id=current_user.id).order_by(DirectMessage.created_at.desc()).limit(5).all()
    except Exception:
        # Silently fail for missing tables in dev; allows dashboard to load
        pass

    now_date = date.today()
    return render_template('dashboard.html', stats=stats, updates=updates, reports=reports, messages=messages, direct_messages=direct_messages, is_admin=is_admin(), attendance=attendance, now_date=now_date)


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
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template('manager_dashboard.html', stats=stats, updates=updates, departments=departments, employees=employees, is_admin=is_admin())


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
    department_list = department_names()
    
    return render_template('chat.html', messages=messages, departments=department_list, active_department=active_department)


@routes.route('/departments')
@login_required
def departments():
    require_admin()
    department_stats = []
    db_departments = Department.query.order_by(Department.name.asc()).all()

    for department in db_departments:
        employee_count = User.query.filter_by(department=department.name).count()
        employees = User.query.filter_by(department=department.name).order_by(User.username.asc()).limit(4).all()
        report_count = ReportDocument.query.filter(ReportDocument.message.ilike(f"%{department.name}%")).count()
        message_count = ChatMessage.query.filter_by(department=department.name).count()
        update_count = CompanyUpdate.query.filter_by(department=department.name).count()
        
        department_stats.append({
            'id': department.id,
            'name': department.name,
            'manager': department.manager,
            'summary': department.summary,
            'status': department.status,
            'employees': employee_count,
            'employee_preview': employees,
            'reports': report_count,
            'messages': message_count,
            'updates': update_count
        })

    return render_template('departments.html', departments=department_stats, department_list=department_names(), users=User.query.order_by(User.username.asc()).all())

@routes.route('/departments/<department_name>')
@login_required
def department_detail(department_name):
    require_admin()
    
    department = Department.query.filter_by(name=department_name).first()
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
    employee_code = request.form.get('employee_code', '').strip() or current_app.config.get('COMPANY_ACCESS_CODE', 'fab1')
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
        'employee code': employee_code,
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
        employee_code=employee_code,
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
            return redirect(request.referrer or url_for('routes.dashboard'))
    else:
        user_id = request.form.get('target_user_id', type=int)
        user = db.session.get(User, user_id) if user_id else None
        if user:
            recipients = [user]

    if not recipients:
        flash('Please select a valid recipient or department.', 'danger')
        return redirect(request.referrer or url_for('routes.dashboard'))

    # File Handling
    if document and document.filename:
        if not allowed_document(document.filename):
            flash('This work file type is not allowed.', 'danger')
            return redirect(request.referrer or url_for('routes.dashboard'))
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
        create_notification(recipient.id, f"You have been assigned a new task: {title}")

    db.session.commit()
    flash(f'Task assigned to {len(recipients)} recipient(s).', 'success')
    return redirect(request.referrer or url_for('routes.dashboard'))


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
    create_notification(employee.id, f"New direct message from {current_user.username}")
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
# ATTENDANCE & NOTIFICATIONS
# =====================

@routes.route('/attendance/check-in', methods=['POST'])
@login_required
def check_in():
    today = date.today()
    existing = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    if not existing:
        entry = Attendance(user_id=current_user.id)
        db.session.add(entry)
        db.session.commit()
        flash('Checked in for today.', 'success')
    return redirect(url_for('routes.dashboard'))

@routes.route('/attendance/check-out', methods=['POST'])
@login_required
def check_out():
    today = date.today()
    entry = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    if entry and not entry.check_out:
        entry.check_out = datetime.utcnow()
        db.session.commit()
        flash('Checked out successfully.', 'info')
    return redirect(url_for('routes.dashboard'))

@routes.route('/admin/attendance')
@login_required
def attendance_records():
    """Admin view of all attendance records with filtering."""
    require_admin()
    
    # Parse filters
    selected_date_str = request.args.get('date', '')
    selected_status = request.args.get('status', '')
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date() if selected_date_str else date.today()
    except (ValueError, TypeError):
        selected_date = date.today()
    
    selected_date_str = selected_date.isoformat()
    
    # Query attendance records for the selected date
    query = Attendance.query.filter(Attendance.date == selected_date)
    if selected_status and selected_status != 'absent':
        query = query.filter(Attendance.status == selected_status)
    
    attendance_entries = query.order_by(Attendance.check_in.asc()).all()
    
    # Build record list
    records = []
    present_user_ids = set()
    for entry in attendance_entries:
        present_user_ids.add(entry.user_id)
        records.append({
            'username': entry.user.username,
            'full_name': entry.user.full_name or entry.user.username,
            'department': entry.user.department,
            'position': entry.user.position,
            'check_in': entry.check_in.strftime('%H:%M') if entry.check_in else '--',
            'check_out': entry.check_out.strftime('%H:%M') if entry.check_out else '--',
            'status': entry.status
        })
    
    # Count stats
    total_employees = User.query.count()
    present_count = Attendance.query.filter(
        Attendance.date == selected_date,
        Attendance.status.in_(['present', 'late', 'half-day'])
    ).count()
    late_count = Attendance.query.filter(Attendance.date == selected_date, Attendance.status == 'late').count()
    absent_count = total_employees - present_count
    
    # If filtering by absent status, show only absent employees
    if selected_status == 'absent':
        present_user_ids_for_absent = set()
        all_entries = Attendance.query.filter(Attendance.date == selected_date).all()
        for entry in all_entries:
            present_user_ids_for_absent.add(entry.user_id)
        absent_employees = User.query.filter(~User.id.in_(present_user_ids_for_absent)).order_by(User.department.asc(), User.username.asc()).all()
        records = []
        for emp in absent_employees:
            records.append({
                'username': emp.username,
                'full_name': emp.full_name or emp.username,
                'department': emp.department,
                'position': emp.position,
                'check_in': '--',
                'check_out': '--',
                'status': 'absent'
            })
    else:
        # Find absent employees
        absent_employees = User.query.filter(~User.id.in_(present_user_ids)).order_by(User.department.asc(), User.username.asc()).all()
    
    absent_list = []
    for emp in absent_employees:
        absent_list.append({
            'username': emp.username,
            'full_name': emp.full_name or emp.username,
            'department': emp.department,
            'position': emp.position
        })
    
    stats = {
        'total': total_employees,
        'present': present_count,
        'late': late_count,
        'absent': absent_count
    }
    
    return render_template(
        'attendance_records.html',
        records=records,
        absent_employees=absent_list,
        stats=stats,
        selected_date=selected_date_str,
        selected_status=selected_status
    )

@routes.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark all as read when viewing
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifications)

# =====================
# ANALYTICS
# =====================

@routes.route('/admin/analytics')
@login_required
def analytics():
    require_admin()
    
    total_tasks = EmployeeTask.query.count()
    completed_tasks = EmployeeTask.query.filter_by(status='Done').count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    dept_counts = {}
    for dept in department_names():
        count = User.query.filter_by(department=dept).count()
        dept_counts[dept] = count
        
    analytics_data = {
        'task_stats': {
            'total': total_tasks,
            'completed': completed_tasks,
            'rate': round(completion_rate, 1)
        },
        'department_distribution': dept_counts,
        'total_reports': ReportDocument.query.count()
    }
    return render_template('analytics.html', data=analytics_data)


# =====================
# DASHBOARD STATISTICS API
# =====================

@routes.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """JSON endpoint for dashboard statistics data."""
    today = date.today()
    total_employees = User.query.count()
    
    # Attendance for today
    present_today = Attendance.query.filter(
        Attendance.date == today,
        Attendance.status.in_(['present', 'late', 'half-day'])
    ).count()
    late_today = Attendance.query.filter(Attendance.date == today, Attendance.status == 'late').count()
    absent_today = total_employees - present_today
    
    # Tasks overview
    total_tasks = EmployeeTask.query.count()
    todo_tasks = EmployeeTask.query.filter_by(status='To Do').count()
    in_progress_tasks = EmployeeTask.query.filter_by(status='In Progress').count()
    done_tasks = EmployeeTask.query.filter_by(status='Done').count()
    
    # Reports count
    total_reports = ReportDocument.query.count()
    
    # Chat & Messages
    chat_count = ChatMessage.query.count()
    
    # Department distribution
    dept_data = []
    for dept_name in department_names():
        emp_count = User.query.filter_by(department=dept_name).count()
        dept_data.append({
            'name': dept_name,
            'employees': emp_count
        })
    
    # Recent activity (combined log)
    recent_activity = []
    
    # Recent reports
    recent_reports = ReportDocument.query.order_by(ReportDocument.created_at.desc()).limit(5).all()
    for r in recent_reports:
        recent_activity.append({
            'type': 'report',
            'title': r.title,
            'description': f"Report by {r.sender.username if r.sender else 'System'} → {r.recipient.username}",
            'time': r.created_at.isoformat(),
            'date_str': r.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Recent updates
    recent_updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(5).all()
    for u in recent_updates:
        recent_activity.append({
            'type': 'update',
            'title': u.title,
            'description': f"Announcement by {u.author.username} for {u.department}",
            'time': u.created_at.isoformat(),
            'date_str': u.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Recent tasks
    recent_tasks = EmployeeTask.query.order_by(EmployeeTask.created_at.desc()).limit(5).all()
    for t in recent_tasks:
        recent_activity.append({
            'type': 'task',
            'title': t.title,
            'description': f"Task for {t.employee.username} - {t.status}",
            'time': t.created_at.isoformat(),
            'date_str': t.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Recent chat
    recent_chats = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(5).all()
    for c in recent_chats:
        recent_activity.append({
            'type': 'chat',
            'title': c.department,
            'description': f"{c.user.username}: {c.body[:80]}..." if len(c.body) > 80 else f"{c.user.username}: {c.body}",
            'time': c.created_at.isoformat(),
            'date_str': c.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # Sort activity by time (newest first)
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    recent_activity = recent_activity[:15]
    
    # Daily stat for today
    daily_stat = DailyStat.query.filter_by(date=today).first()
    if not daily_stat:
        daily_stat = DailyStat.record_today()
    
    # Get last 7 days stats for trend
    from datetime import timedelta
    last_7_days = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        stat = DailyStat.query.filter_by(date=day).first()
        if stat:
            last_7_days.append({
                'date': day.isoformat(),
                'date_label': day.strftime('%a %d'),
                'performance_score': stat.performance_score,
                'present_count': stat.present_count,
                'absent_count': stat.absent_count,
                'tasks_created': stat.tasks_created,
                'tasks_completed': stat.tasks_completed,
                'reports_sent': stat.reports_sent
            })
        else:
            # Compute on the fly if not recorded yet
            computed = DailyStat.compute_for(day)
            last_7_days.append({
                'date': day.isoformat(),
                'date_label': day.strftime('%a %d'),
                'performance_score': computed.performance_score,
                'present_count': computed.present_count,
                'absent_count': computed.absent_count,
                'tasks_created': computed.tasks_created,
                'tasks_completed': computed.tasks_completed,
                'reports_sent': computed.reports_sent
            })
    
    # Attendance list for today (who's in)
    attendance_list = []
    today_records = Attendance.query.filter(
        Attendance.date == today,
        Attendance.status.in_(['present', 'late', 'half-day'])
    ).order_by(Attendance.check_in.asc()).all()
    for rec in today_records:
        attendance_list.append({
            'user_id': rec.user_id,
            'username': rec.user.username,
            'full_name': rec.user.full_name or rec.user.username,
            'department': rec.user.department or 'N/A',
            'position': rec.user.position or 'N/A',
            'check_in': rec.check_in.strftime('%H:%M') if rec.check_in else '--',
            'check_out': rec.check_out.strftime('%H:%M') if rec.check_out else '--',
            'status': rec.status
        })
    
    return jsonify({
        'today': {
            'date': today.isoformat(),
            'total_employees': total_employees,
            'present': present_today,
            'late': late_today,
            'absent': absent_today,
            'total_tasks': total_tasks,
            'todo_tasks': todo_tasks,
            'in_progress_tasks': in_progress_tasks,
            'done_tasks': done_tasks,
            'total_reports': total_reports,
            'chat_messages': chat_count,
            'daily_stat': {
                'performance_score': daily_stat.performance_score,
                'tasks_created': daily_stat.tasks_created,
                'tasks_completed': daily_stat.tasks_completed,
                'reports_sent': daily_stat.reports_sent,
                'messages_sent': daily_stat.messages_sent,
                'chat_messages': daily_stat.chat_messages,
                'updates_published': daily_stat.updates_published
            }
        },
        'department_distribution': dept_data,
        'last_7_days': last_7_days,
        'recent_activity': recent_activity,
        'attendance_list': attendance_list
    })


@routes.route('/api/dashboard/stats-by-date')
@login_required
def api_dashboard_stats_by_date():
    """JSON endpoint for statistics on a specific date."""
    require_admin()
    target_date_str = request.args.get('date', '')
    
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
    
    # Get or compute DailyStat for that date
    stat = DailyStat.query.filter_by(date=target_date).first()
    if not stat:
        stat = DailyStat.compute_for(target_date)
    
    # Attendance records for that date
    attendance_records = []
    day_records = Attendance.query.filter(
        Attendance.date == target_date,
        Attendance.status.in_(['present', 'late', 'half-day'])
    ).order_by(Attendance.check_in.asc()).all()
    
    for rec in day_records:
        attendance_records.append({
            'user_id': rec.user_id,
            'username': rec.user.username,
            'department': rec.user.department or 'N/A',
            'position': rec.user.position or 'N/A',
            'check_in': rec.check_in.strftime('%H:%M') if rec.check_in else '--',
            'check_out': rec.check_out.strftime('%H:%M') if rec.check_out else '--',
            'status': rec.status
        })
    
    # Activities on that date
    activities = []
    
    day_reports = ReportDocument.query.filter(
        db.func.date(ReportDocument.created_at) == target_date
    ).order_by(ReportDocument.created_at.desc()).all()
    for r in day_reports:
        activities.append({
            'type': 'report',
            'title': r.title,
            'description': f"Report by {r.sender.username if r.sender else 'System'} → {r.recipient.username}",
            'time': r.created_at.strftime('%H:%M')
        })
    
    day_updates = CompanyUpdate.query.filter(
        db.func.date(CompanyUpdate.created_at) == target_date
    ).order_by(CompanyUpdate.created_at.desc()).all()
    for u in day_updates:
        activities.append({
            'type': 'update',
            'title': u.title,
            'description': f"By {u.author.username} for {u.department}",
            'time': u.created_at.strftime('%H:%M')
        })
    
    day_tasks = EmployeeTask.query.filter(
        db.func.date(EmployeeTask.created_at) == target_date
    ).order_by(EmployeeTask.created_at.desc()).all()
    for t in day_tasks:
        activities.append({
            'type': 'task',
            'title': t.title,
            'description': f"For {t.employee.username} - {t.status}",
            'time': t.created_at.strftime('%H:%M')
        })
    
    day_chats = ChatMessage.query.filter(
        db.func.date(ChatMessage.created_at) == target_date
    ).order_by(ChatMessage.created_at.desc()).all()
    for c in day_chats:
        activities.append({
            'type': 'chat',
            'title': c.department,
            'description': f"{c.user.username}: {c.body[:80]}..." if len(c.body) > 80 else f"{c.user.username}: {c.body}",
            'time': c.created_at.strftime('%H:%M')
        })
    
    day_messages = DirectMessage.query.filter(
        db.func.date(DirectMessage.created_at) == target_date
    ).order_by(DirectMessage.created_at.desc()).all()
    for m in day_messages:
        activities.append({
            'type': 'message',
            'title': 'Direct Message',
            'description': f"From {m.sender.username} to {m.recipient.username}",
            'time': m.created_at.strftime('%H:%M')
        })
    
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    # Who was absent that day
    absent_users = []
    if stat:
        present_ids = [r.user_id for r in day_records]
        all_users = User.query.all()
        for u in all_users:
            if u.id not in present_ids:
                absent_users.append({
                    'user_id': u.id,
                    'username': u.username,
                    'full_name': u.full_name or u.username,
                    'department': u.department or 'N/A'
                })
    
    return jsonify({
        'date': target_date.isoformat(),
        'stat': {
            'total_employees': stat.total_employees,
            'present_count': stat.present_count,
            'late_count': stat.late_count,
            'absent_count': stat.absent_count,
            'tasks_created': stat.tasks_created,
            'tasks_completed': stat.tasks_completed,
            'reports_sent': stat.reports_sent,
            'messages_sent': stat.messages_sent,
            'chat_messages': stat.chat_messages,
            'updates_published': stat.updates_published,
            'performance_score': stat.performance_score
        },
        'attendance': attendance_records,
        'absent_users': absent_users,
        'activities': activities
    })


@routes.route('/api/dashboard/record-today', methods=['POST'])
@login_required
def api_record_today():
    """Trigger recording of today's daily stats."""
    require_admin()
    try:
        stat = DailyStat.record_today()
        return jsonify({'success': True, 'date': stat.date.isoformat(), 'performance_score': stat.performance_score})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
