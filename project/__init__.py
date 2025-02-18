import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
# from flask_cors import CORS
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    # CORS(app)
    app.config.from_pyfile('../config.py')
    db.init_app(app)

    #login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # Ensure the 'equivalents' folder exists
    equivalents_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'equivalents')
    os.makedirs(equivalents_folder, exist_ok=True)

    migrate = Migrate(app, db)  # Make sure Migrate is initialized

    return app