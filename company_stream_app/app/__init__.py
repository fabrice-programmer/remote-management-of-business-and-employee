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

    return app
