from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename
from app import bcrypt, db
from app.forms import LoginForm, RegisterForm
from app.models import ChatMessage, CompanyUpdate, ReportDocument, User
import os
from urllib.parse import urlparse, urljoin
from uuid import uuid4

routes = Blueprint('routes', __name__)
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg'}
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


def is_safe_redirect(target):
    if not target:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in {'http', 'https'} and host_url.netloc == redirect_url.netloc

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
    visible_reports = ReportDocument.query.filter(
        (ReportDocument.sender_id == current_user.id) |
        (ReportDocument.recipient_id == current_user.id)
    )

    stats = {
        'employees': User.query.count(),
        'reports': visible_reports.count(),
        'received': ReportDocument.query.filter_by(recipient_id=current_user.id).count(),
        'departments': len(DEPARTMENTS)
    }
    updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(5).all()
    reports = visible_reports.order_by(ReportDocument.created_at.desc()).limit(5).all()
    messages = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(4).all()
    return render_template('dashboard.html', stats=stats, updates=updates, reports=reports, messages=messages)


@routes.route('/manager-dashboard')
@login_required
def manager_dashboard():
    stats = {
        'employees': User.query.count(),
        'reports': ReportDocument.query.count(),
        'updates': CompanyUpdate.query.count(),
        'messages': ChatMessage.query.count()
    }
    updates = CompanyUpdate.query.order_by(CompanyUpdate.created_at.desc()).limit(8).all()
    return render_template('manager_dashboard.html', stats=stats, updates=updates, departments=DEPARTMENTS)


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
    department_stats = []

    for department in DEPARTMENTS:
        report_count = ReportDocument.query.filter(ReportDocument.message.ilike(f"%{department['name']}%")).count()
        message_count = ChatMessage.query.filter_by(department=department['name']).count()
        update_count = CompanyUpdate.query.filter_by(department=department['name']).count()
        department_stats.append({
            **department,
            'reports': report_count,
            'messages': message_count,
            'updates': update_count
        })

    return render_template('departments.html', departments=department_stats)


@routes.route('/reports')
@login_required
def reports():
    users = User.query.filter(User.id != current_user.id).order_by(User.username.asc()).all()

    if current_user.role == 'manager':
        reports = ReportDocument.query.order_by(ReportDocument.created_at.desc()).all()
    else:
        reports = ReportDocument.query.filter(
            (ReportDocument.sender_id == current_user.id) |
            (ReportDocument.recipient_id == current_user.id)
        ).order_by(ReportDocument.created_at.desc()).all()

    return render_template('reports.html', reports=reports, users=users)


@routes.route('/reports/upload', methods=['POST'])
@login_required
def upload_report():
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

    original_filename = secure_filename(document.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f'{uuid4().hex}.{extension}'
    document.save(os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename))

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
    if not can_download and current_user.role != 'manager':
        abort(403)

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        report.stored_filename,
        as_attachment=True,
        download_name=report.original_filename
    )
