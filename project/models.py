from . import db, login_manager
from datetime import datetime

from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin


class AppUser(db.Model):
    au_id = db.Column(db.Integer, primary_key=True)
    au_full_name = db.Column(db.String(100), nullable=False)
    au_email = db.Column(db.String(120), unique=True, nullable=False)
    au_mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    au_password_hash = db.Column(db.String(128), nullable=False)
    au_photo = db.Column(db.String(255), nullable=True)

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


class MissionMCQ(db.Model):
    q_id = db.Column(db.Integer, primary_key=True)
    q_question = db.Column(db.String(255), nullable=False)  # Question text
    q_option_1 = db.Column(db.String(255), nullable=False)  # Option 1
    q_option_2 = db.Column(db.String(255), nullable=False)  # Option 2
    q_option_3 = db.Column(db.String(255), nullable=False)  # Option 3
    q_option_4 = db.Column(db.String(255), nullable=False)  # Option 4
    q_correct_option = db.Column(db.Integer, nullable=False)  # Index of correct option (1, 2, 3, or 4)
    q_coins = db.Column(db.Integer, nullable=False)  # Coins for the quiz
    q_created_at = db.Column(db.DateTime, default=db.func.now())  # Timestamp for when the quiz is created

class MissionAction(db.Model):
    ma_id = db.Column(db.Integer, primary_key=True)
    ma_text = db.Column(db.String(255), nullable=False)  # Action text
    ma_url =  db.Column(db.String(255), nullable=False) # Action URL
    ma_coins = db.Column(db.Integer, nullable=False)  # Coins for the Action
    ma_created_at = db.Column(db.DateTime, default=db.func.now())  # Timestamp for when the quiz is created

class Equivalent(db.Model):    
    eq_id = db.Column(db.Integer, primary_key=True)
    eq_name = db.Column(db.String(255), nullable=False)
    eq_coins = db.Column(db.Integer, nullable=False)
    eq_picture = db.Column(db.String(255), nullable=True)

class EquivalentRequest(db.Model):
    eqr_id = db.Column(db.Integer, primary_key=True)
    eq_id = db.Column(db.Integer, db.ForeignKey('equivalent.eq_id'), nullable=False)
    au_id = db.Column(db.Integer, db.ForeignKey('app_user.au_id'), nullable=False)
    eqr_number_of_coins = db.Column(db.Integer, nullable=False)
    eqr_accepted = db.Column(db.Integer, nullable=False, default=0)

    equivalent = db.relationship('Equivalent', backref=db.backref('equivalent_requests', lazy=True))
    app_user = db.relationship('AppUser', backref=db.backref('equivalent_requests', lazy=True))


class Guide(db.Model):
    g_id = db.Column(db.Integer, primary_key=True)
    g_title = db.Column(db.String(255), nullable=False)
    g_coins_for_first_alert = db.Column(db.Integer, nullable=False)
    g_coins_for_confirm_alert = db.Column(db.Integer, nullable=False)
    g_coins_for_close_alert = db.Column(db.Integer, nullable=False)


class Zone(db.Model):
    z_id = db.Column(db.Integer, primary_key=True)
    z_name = db.Column(db.String(255), nullable=False)
    z_centroid_lat = db.Column(db.Float)
    z_centroid_lng = db.Column(db.Float)
    g_id = db.Column(db.Integer, db.ForeignKey('guide.g_id'), nullable=False)
    guide = db.relationship('Guide', backref=db.backref('zones', lazy=True))
    zone_points = db.relationship('ZonePoint', backref=db.backref('zones', lazy=True), cascade='all, delete-orphan')
    # Relationship with alerts
    zone_alerts = db.relationship('Alert', backref='zones', lazy=True)

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

class Alert(db.Model):
    a_id = db.Column(db.Integer, primary_key=True)
    a_category = db.Column(db.String(255), nullable=False)
    a_photo = db.Column(db.String(255)) 
    a_message = db.Column(db.String(255), nullable=False)
    a_latitude = db.Column(db.Float, nullable=False)
    a_longitude = db.Column(db.Float, nullable=False)
    a_points = db.Column(db.Integer, nullable=False)
    
    # Relationship with Zone
    z_id = db.Column(db.Integer, db.ForeignKey('zone.z_id'), nullable=False)
    zone = db.relationship('Zone', backref=db.backref('alerts', lazy=True))

    # Foreign key relationship with AppUser
    au_id = db.Column(db.Integer, db.ForeignKey('app_user.au_id'), nullable=False)
    app_user = db.relationship('AppUser', backref=db.backref('alerts', lazy=True))
   
class AlertConfirm(db.Model):
    acn_id = db.Column(db.Integer, primary_key=True)
    acn_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    acn_points = db.Column(db.Integer, nullable=False)

    # Foreign key relationship with AppUser
    au_id = db.Column(db.Integer, db.ForeignKey('app_user.au_id'), nullable=False)
    app_user = db.relationship('AppUser', backref=db.backref('confirmations', lazy=True))

    # Foreign key relationship with Alert
    a_id = db.Column(db.Integer, db.ForeignKey('alert.a_id'), nullable=False)
    alert = db.relationship('Alert', backref=db.backref('confirmations', lazy=True))

class AlertClose(db.Model):
    acl_id = db.Column(db.Integer, primary_key=True)
    acl_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    acl_points = db.Column(db.Integer, nullable=False)


    # Foreign key relationship with AppUser
    au_id = db.Column(db.Integer, db.ForeignKey('app_user.au_id'), nullable=False)
    app_user = db.relationship('AppUser', backref=db.backref('closures', lazy=True))

    # Foreign key relationship with Alert
    a_id = db.Column(db.Integer, db.ForeignKey('alert.a_id'), nullable=False)
    alert = db.relationship('Alert', backref=db.backref('closures', uselist=False))
    


# generate a default user
def insert_default_user(*args, **kwargs):
    default_user = User(u_username='admin', u_password=generate_password_hash('admin', method='pbkdf2:sha256'))
    db.session.add(default_user)
    db.session.commit()