from flask import Blueprint, render_template, jsonify, redirect, session, url_for, request
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
import base64
from .models import Guide, Zone, Road, ZonePoint, RoadPoint, AppUser, Alert
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
        return jsonify({'status': 'error', 'message': 'Incomplete data provided', 'user_id': '', 'user_full_name':''})

    # Check if the user exists based on email or mobile number
    user = AppUser.query.filter((AppUser.au_email == email_or_mobile) | (AppUser.au_mobile_number == email_or_mobile)).first()

    if not user or not user.check_password(password):
        return jsonify({'status': 'error', 'message': 'Invalid email/mobile number or password', 'user_id':'', 'user_full_name':''})

    # Successful authentication
    return jsonify({'status': 'ok', 'message': 'Signin Successful', 'user_id': user.au_id, 'user_full_name': user.au_full_name })


@api.route('/api/addalert', methods=['POST'])
def addalert():
    # Get data from the request
    data = request.get_json()

    # Validate input
    required_fields = ['a_category', 'a_message', 'a_latitude', 'a_longitude', 'au_id', 'a_photo']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Incomplete data provided'})

    # Check if the user exists based on au_id
    user = AppUser.query.get(data['au_id'])
    if not user:
        return jsonify({'status': 'error', 'message': 'Invalid user ID'})

    # Decode the base64-encoded image string
    image_data = base64.b64decode(data['a_photo'])
    
    # Save the image to a file
    image_filename = 'captured_image.jpg'  # You can generate a unique filename
    with open(image_filename, 'wb') as f:
        f.write(image_data)

    # Create a new alert
    new_alert = Alert(
        a_category=data['a_category'],
        a_photo=image_filename,  # Save the filename in the database
        a_message=data['a_message'],
        a_latitude=data['a_latitude'],
        a_longitude=data['a_longitude'],
        app_user=user
    )

    # Add the new alert to the database
    db.session.add(new_alert)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': 'Alert created successfully'})