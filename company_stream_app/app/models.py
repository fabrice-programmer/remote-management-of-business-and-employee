from . import db
from flask_login import UserMixin
from datetime import datetime


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_department')

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
    employee_code = db.Column(db.String(40), nullable=True)
   
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


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    status = db.Column(db.String(20), default='present')  # present, late, absent, half-day
    
    user = db.relationship('User', backref='attendance_records')


class DailyStat(db.Model):
    """Tracks daily business performance statistics."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False, default=lambda: datetime.utcnow().date())
    
    # Attendance stats
    total_employees = db.Column(db.Integer, default=0)
    present_count = db.Column(db.Integer, default=0)
    late_count = db.Column(db.Integer, default=0)
    absent_count = db.Column(db.Integer, default=0)
    
    # Task stats
    tasks_created = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    
    # Report stats
    reports_sent = db.Column(db.Integer, default=0)
    
    # Message stats
    messages_sent = db.Column(db.Integer, default=0)
    chat_messages = db.Column(db.Integer, default=0)
    
    # Company updates
    updates_published = db.Column(db.Integer, default=0)
    
    # Revenue / performance (placeholder - can be extended)
    performance_score = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DailyStat {self.date}>'
    
    @staticmethod
    def compute_for(target_date):
        """Compute and return a DailyStat for the given date (without saving)."""
        from . import db
        
        total_emp = User.query.count()
        present = Attendance.query.filter(
            Attendance.date == target_date,
            Attendance.status.in_(['present', 'late', 'half-day'])
        ).count()
        late = Attendance.query.filter(
            Attendance.date == target_date,
            Attendance.status == 'late'
        ).count()
        
        tasks_created = EmployeeTask.query.filter(
            db.func.date(EmployeeTask.created_at) == target_date
        ).count()
        tasks_completed = EmployeeTask.query.filter(
            EmployeeTask.status == 'Done',
            db.func.date(EmployeeTask.created_at) == target_date
        ).count()
        
        reports_sent = ReportDocument.query.filter(
            db.func.date(ReportDocument.created_at) == target_date
        ).count()
        
        chat_msgs = ChatMessage.query.filter(
            db.func.date(ChatMessage.created_at) == target_date
        ).count()
        
        direct_msgs = DirectMessage.query.filter(
            db.func.date(DirectMessage.created_at) == target_date
        ).count()
        
        updates = CompanyUpdate.query.filter(
            db.func.date(CompanyUpdate.created_at) == target_date
        ).count()
        
        # Performance score: weighted composite metric (0-100)
        score = 0.0
        if total_emp > 0:
            score += (present / total_emp) * 30  # attendance weight 30%
        score += min((tasks_completed / max(tasks_created, 1)) * 20, 20)  # tasks 20%
        score += min((reports_sent / max(total_emp, 1)) * 20, 20)  # reports 20%
        score += min((updates / max(total_emp, 1)) * 30, 30)  # updates 30%
        score = round(min(score, 100), 1)
        
        stat = DailyStat(
            date=target_date,
            total_employees=total_emp,
            present_count=present,
            late_count=late,
            absent_count=max(0, total_emp - present),
            tasks_created=tasks_created,
            tasks_completed=tasks_completed,
            reports_sent=reports_sent,
            messages_sent=direct_msgs,
            chat_messages=chat_msgs,
            updates_published=updates,
            performance_score=score
        )
        return stat
    
    @staticmethod
    def record_today():
        """Compute and save today's DailyStat."""
        from . import db
        today = datetime.utcnow().date()
        stat = DailyStat.compute_for(today)
        stat.date = today
        
        existing = DailyStat.query.filter_by(date=today).first()
        if existing:
            # Update existing
            existing.total_employees = stat.total_employees
            existing.present_count = stat.present_count
            existing.late_count = stat.late_count
            existing.absent_count = stat.absent_count
            existing.tasks_created = stat.tasks_created
            existing.tasks_completed = stat.tasks_completed
            existing.reports_sent = stat.reports_sent
            existing.messages_sent = stat.messages_sent
            existing.chat_messages = stat.chat_messages
            existing.updates_published = stat.updates_published
            existing.performance_score = stat.performance_score
            db.session.commit()
            return existing
        else:
            db.session.add(stat)
            db.session.commit()
            return stat
