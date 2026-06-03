from app import db
from flask_login import UserMixin
from datetime import datetime


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    lead = db.Column(db.String(120), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Department {self.name}>'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='employee')
    full_name = db.Column(db.String(120), nullable=True)
    employee_number = db.Column(db.String(40), unique=True, nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    department = db.Column(db.String(80), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    hire_date = db.Column(db.String(20), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'


class ReportDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default='Sent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_reports')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_reports')

    def __repr__(self):
        return f'<ReportDocument {self.title}>'


class CompanyUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(80), default='Company-wide')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='company_updates')

    def __repr__(self):
        return f'<CompanyUpdate {self.title}>'


class HomepageMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_type = db.Column(db.String(50), nullable=False, default='feature')
    title = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(20), nullable=False, default='image')
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<HomepageMedia {self.asset_type} {self.id}>'


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(80), default='General')
    body = db.Column(db.Text, nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)
    media_type = db.Column(db.String(20), nullable=True, default='file')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='chat_messages')

    def __repr__(self):
        return f'<ChatMessage {self.department}>'


class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_direct_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_direct_messages')

    def __repr__(self):
        return f'<DirectMessage {self.sender_id}->{self.recipient_id}>'


class EmployeeTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='To Do')
    priority = db.Column(db.String(20), default='Normal')
    due_date = db.Column(db.String(20), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    stored_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    employee = db.relationship('User', foreign_keys=[employee_id], backref='assigned_tasks')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='created_tasks')

    def __repr__(self):
        return f'<EmployeeTask {self.title}>'
