from flask import Blueprint, render_template, jsonify, redirect, session, url_for, request
from flask_login import login_user, logout_user, login_required
from .models import Guide, Zone, Road, ZonePoint, RoadPoint, AppUser
from . import db
import json
import os

api = Blueprint('api', __name__)

    
@api.route('/api/signup', methods=['POST'])
def signup():
    # Get data from the request
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    mobile_number = request.form.get('mobile_number')
    password = request.form.get('password')

    # Validate input
    if not (full_name and email and mobile_number and password ):
        return jsonify({'status': 'error','message': 'Incomplete data provided'})

    # Check if the user already exists
    if AppUser.query.filter_by(au_email=email).first() or AppUser.query.filter_by(au_mobile_number=mobile_number).first():
        return jsonify({'status': 'error','message': 'User with email or mobile number already exists'})

    # Create a new user
    new_user = AppUser(au_full_name=full_name, au_email=email, au_mobile_number=mobile_number)
    new_user.set_password(password)

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'status': 'ok','message': 'Signup Successful'})

@api.route('/api/signin', methods=['POST'])
def signin():
    # Get data from the request
    email_or_mobile = request.form.get('email_or_mobile')
    password = request.form.get('password')

    # Validate input
    if not (email_or_mobile and password):
        return jsonify({'status': 'error', 'message': 'Incomplete data provided', 'user_id': ''})

    # Check if the user exists based on email or mobile number
    user = AppUser.query.filter((AppUser.au_email == email_or_mobile) | (AppUser.au_mobile_number == email_or_mobile)).first()

    if not user or not user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Invalid email/mobile number or password', 'user_id':''})

    # Successful authentication
    return jsonify({'status': 'ok', 'message': 'Signin Successful', 'user_id': user.au_id })
