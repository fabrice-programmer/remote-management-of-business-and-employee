from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config
import os
from sqlalchemy import inspect, text

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
socketio = SocketIO()

login_manager.login_view = 'routes.login'


def ensure_user_profile_columns():
    if db.engine.dialect.name != 'sqlite':
        return

    inspector = inspect(db.engine)
    if 'user' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('user')}
    profile_columns = {
        'full_name': 'VARCHAR(120)',
        'employee_number': 'VARCHAR(40)',
        'phone': 'VARCHAR(40)',
        'department': 'VARCHAR(80)',
        'position': 'VARCHAR(100)',
        'hire_date': 'VARCHAR(20)'
    }

    with db.engine.begin() as connection:
        for column_name, column_type in profile_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f'ALTER TABLE user ADD COLUMN {column_name} {column_type}'))


def ensure_employee_task_attachment_columns():
    if db.engine.dialect.name != 'sqlite':
        return

    inspector = inspect(db.engine)
    if 'employee_task' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('employee_task')}
    attachment_columns = {
        'original_filename': 'VARCHAR(255)',
        'stored_filename': 'VARCHAR(255)'
    }

    with db.engine.begin() as connection:
        for column_name, column_type in attachment_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f'ALTER TABLE employee_task ADD COLUMN {column_name} {column_type}'))


def ensure_chat_message_attachment_columns():
    if db.engine.dialect.name != 'sqlite':
        return

    inspector = inspect(db.engine)
    if 'chat_message' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('chat_message')}
    attachment_columns = {
        'original_filename': 'VARCHAR(255)',
        'stored_filename': 'VARCHAR(255)',
        'media_type': 'VARCHAR(20)'
    }

    with db.engine.begin() as connection:
        for column_name, column_type in attachment_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f'ALTER TABLE chat_message ADD COLUMN {column_name} {column_type}'))


def ensure_direct_message_attachment_columns():
    if db.engine.dialect.name != 'sqlite':
        return

    inspector = inspect(db.engine)
    if 'direct_message' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('direct_message')}
    attachment_columns = {
        'original_filename': 'VARCHAR(255)',
        'stored_filename': 'VARCHAR(255)'
    }

    with db.engine.begin() as connection:
        for column_name, column_type in attachment_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f'ALTER TABLE direct_message ADD COLUMN {column_name} {column_type}'))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import routes
    app.register_blueprint(routes)

    with app.app_context():
        db.create_all()
        ensure_user_profile_columns()
        ensure_employee_task_attachment_columns()
        ensure_chat_message_attachment_columns()
        ensure_direct_message_attachment_columns()

    return app
