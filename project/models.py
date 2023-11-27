from . import db, login_manager
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin


class AppUser(db.Model):
    au_id = db.Column(db.Integer, primary_key=True)
    au_full_name = db.Column(db.String(100), nullable=False)
    au_email = db.Column(db.String(120), unique=True, nullable=False)
    au_mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    au_password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.au_password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.au_password_hash, password)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    u_username = db.Column(db.String(80), unique=True, nullable=False)
    u_password = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Guide(db.Model):
    g_id = db.Column(db.Integer, primary_key=True)
    g_title = db.Column(db.String(255), nullable=False)
    g_title_alb = db.Column(db.String(255), nullable=True)

class Zone(db.Model):
    z_id = db.Column(db.Integer, primary_key=True)
    z_name = db.Column(db.String(255), nullable=False)
    g_id = db.Column(db.Integer, db.ForeignKey('guide.g_id'), nullable=False)
    guide = db.relationship('Guide', backref=db.backref('zones', lazy=True))
    zone_points = db.relationship('ZonePoint', backref=db.backref('zones', lazy=True), cascade='all, delete-orphan')

class ZonePoint(db.Model):
    zp_id = db.Column(db.Integer, primary_key=True)
    zp_lat = db.Column(db.Float, nullable=False)
    zp_lng = db.Column(db.Float, nullable=False)
    z_id = db.Column(db.Integer, db.ForeignKey('zone.z_id'), nullable=False)
    zone = db.relationship('Zone', backref=db.backref('points', lazy=True))

class Road(db.Model):
    r_id = db.Column(db.Integer, primary_key=True)
    r_name = db.Column(db.String(255), nullable=False)
    g_id = db.Column(db.Integer, db.ForeignKey('guide.g_id'), nullable=False)
    guide = db.relationship('Guide', backref=db.backref('roads', lazy=True))
    road_points = db.relationship('RoadPoint', backref=db.backref('roads', lazy=True), cascade='all, delete-orphan')

class RoadPoint(db.Model):
    rp_id = db.Column(db.Integer, primary_key=True)
    rp_lat = db.Column(db.Float, nullable=False)
    rp_lng = db.Column(db.Float, nullable=False)
    r_id = db.Column(db.Integer, db.ForeignKey('road.r_id'), nullable=False)
    road = db.relationship('Road', backref=db.backref('points', lazy=True))
    


# generate a default user
def insert_default_user(*args, **kwargs):
    default_user = User(u_username='admin', u_password=generate_password_hash('admin', method='pbkdf2:sha256'))
    db.session.add(default_user)
    db.session.commit()