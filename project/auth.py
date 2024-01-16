from flask import Blueprint, render_template, jsonify, redirect, session, url_for, request
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import timedelta

from . import db

auth = Blueprint('auth', __name__)

# The login page is the racine of the application
@auth.route("/login")
def login():
    # Check if the user is already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    message = request.args.get('message')
    return render_template('login.html', message=message)

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = 'remember_me' in request.form  # Check if the checkbox is selected

    # Assuming your user model has a method for processing login
    user = User.query.filter_by(u_username=username).first()

    if not user or not check_password_hash(user.u_password, password):
        # Login failed, redirect back to the login page with a message in the URL
        return render_template('login.html', message='Invalid Login Credentials')
    else:
        login_user(user, remember=remember_me, duration=timedelta(days=2))

        return redirect(url_for('main.home'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))