from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from config import Config
import os
from sqlalchemy import MetaData

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
bcrypt = Bcrypt()
login_manager = LoginManager()
socketio = SocketIO()
migrate = Migrate()

login_manager.login_view = 'routes.login'


def create_app():
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)
    flask_app.config['UPLOAD_FOLDER'] = os.path.join(flask_app.instance_path, flask_app.config['UPLOAD_FOLDER'])
    os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(flask_app)
    bcrypt.init_app(flask_app)
    login_manager.init_app(flask_app)
    socketio.init_app(flask_app)
    migrate.init_app(flask_app, db, render_as_batch=True)

    # Dev safeguard: if DB is missing new tables (e.g., Attendance), create them.
    # This avoids runtime crashes like: "no such table: attendance".
    with flask_app.app_context():
        # Using relative imports ensures we don't accidentally pull in the 'app' 
        # package namespace into the local scope of this function.
        from . import models
        db.create_all()

    # Explicitly import User for the user_loader
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from .routes import routes
    # Import crud_routes to ensure all admin/CRUD routes are attached to the blueprint
    from . import crud_routes
    flask_app.register_blueprint(routes)

    return flask_app
