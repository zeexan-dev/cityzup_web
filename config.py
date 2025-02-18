import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database_online_copy.db')

SECRET_KEY = 'R&4Lw$G2zP@8Bf9sQ#T3yMkD'
UPLOAD_FOLDER = 'project/static/uploads'