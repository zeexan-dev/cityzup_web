import uuid
from flask import Blueprint, render_template, jsonify, redirect, session, url_for, request, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
import base64
from .models import AlertClose, AlertConfirm, Guide, Zone, Road, ZonePoint, RoadPoint, AppUser, Alert
from . import db
import json
import os

api = Blueprint('api', __name__)

@api.route('/api/add_alert_confirm', methods=['POST'])
def add_alert_confirm():
    try:
        # Get data from the request
        data = request.get_json()

        # Validate input
        required_fields = ['au_id', 'a_id']
        if not all(field in data for field in required_fields):
            return jsonify({'status': 'error', 'message': 'Incomplete data provided'})
        
        # Get data from the request
        au_id = int(data['au_id'])
        a_id = int(data['a_id'])

        # Check if au_id is already present for a_id
        if AlertConfirm.query.filter_by(au_id=au_id, a_id=a_id).first():
            return jsonify({"status": "warning", "message": "Alert already confirmed by this user"})

        # Insert data into AlertConfirm table
        alert_confirm = AlertConfirm(au_id=au_id, a_id=a_id)
        db.session.add(alert_confirm)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Alert confirmation added successfully"})
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": "Failed to add alert confirmation"}), 500
    
@api.route('/api/add_alert_close', methods=['POST'])
def add_alert_close():
    try:
        # Get data from the request
        data = request.get_json()

        # Validate input
        required_fields = ['au_id', 'a_id']
        if not all(field in data for field in required_fields):
            return jsonify({'status': 'error', 'message': 'Incomplete data provided'})
        
        # Get data from the request
        au_id = int(data['au_id'])
        a_id = int(data['a_id'])

        # Check if any user has already closed the alert for the given a_id
        if AlertClose.query.filter_by(a_id=a_id).first():
            return jsonify({"status": "warning", "message": "Alert already closed"})

        # Insert data into AlertClose table
        alert_close = AlertClose(au_id=au_id, a_id=a_id)
        db.session.add(alert_close)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Alert closure added successfully"})
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": "Failed to add alert closure"}), 500
    

@api.route('/api/get_zones_and_roads', methods=['GET'])
def get_zones_and_roads():
    try:
        # Retrieve all zones from the database
        all_zones = Zone.query.all()
        # Initialize a list to store the coordinates of all zones
        all_zones_coordinates = []

         # Retrieve all roads from the database
        all_roads = Road.query.all()
        # Initialize a list to store the coordinates of all roads
        all_roads_coordinates = []

        # Loop through each zone
        for zone in all_zones:
            zone_id = zone.z_id
            zone_name = zone.z_name
            zone_centeroid = {'lat': zone.z_centroid_lat, 'lng': zone.z_centroid_lng}

            # Retrieve the coordinates for the current zone
            zone_coordinates = ZonePoint.query.filter_by(z_id=zone_id).all()

            # Convert the coordinates to a list of dictionaries
            zone_coordinates_list = [{'lat': coord.zp_lat, 'lng': coord.zp_lng} for coord in zone_coordinates]

            # Add the zone name and coordinates to the list
            zone_data = {'zone_id': zone_id, 'zone_name': zone_name, 'coordinates': zone_coordinates_list, 'centeroid': zone_centeroid}
            all_zones_coordinates.append(zone_data)

        # Loop through each road
        for road in all_roads:
            road_id = road.r_id
            road_name = road.r_name

            # Retrieve the coordinates for the current road
            road_coordinates = RoadPoint.query.filter_by(r_id=road_id).all()

            # Convert the coordinates to a list of dictionaries
            road_coordinates_list = [{'lat': coord.rp_lat, 'lng': coord.rp_lng} for coord in road_coordinates]

            # Add the road name and coordinates to the list
            road_data = {'road_id': road_id, 'road_name': road_name, 'coordinates': road_coordinates_list}
            all_roads_coordinates.append(road_data)

        return jsonify({'status': 'ok', 'zones': all_zones_coordinates, 'roads': all_roads_coordinates})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

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
    new_user = AppUser(au_full_name=full_name, au_email=email, au_mobile_number=mobile_number, au_photo='')
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


@api.route('/api/update_profie_image', methods=['POST'])
def updateProfileImage():
    # Get data from the request
    data = request.get_json()
    
    response_data = {'status':'', 'message':'', 'user': {}}

    # Validate input
    required_fields = ['auid', 'photo']
    if not all(field in data for field in required_fields):
        response_data['status'] = 'error'
        response_data['message'] = 'Incomplete data provided'
        return jsonify(response_data)
    
    # Check if the user exists based on au_id
    user = AppUser.query.get(data['auid'])
    if not user:
        response_data['status'] = 'error'
        response_data['message'] = 'Invalid user ID'
        return jsonify(response_data)
    
    # Decode the base64-encoded image string
    image_data = base64.b64decode(data['photo'])

    # Save the image to a unique folder for each user
    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user.au_id), 'profile_images')
    os.makedirs(user_folder, exist_ok=True)
    
    # Generate a unique filename
    image_fileName = f"captured_image_{uuid.uuid4()}.jpg"
    image_filePath = os.path.join(user_folder, image_fileName)
    
    with open(image_filePath, 'wb') as f:
        f.write(image_data)

     # Update the user's profile image path in the database
    user.au_photo = image_fileName
    # Commit the changes to the database
    db.session.commit()

    response_data['status'] = 'ok'
    response_data['message'] = 'Profile Image Updated'
    response_data['user'] = {
            'user_id': user.au_id,
            'full_name': user.au_full_name,
            'email': user.au_email,
            'mobile_number': user.au_mobile_number,
            'profile_photo': image_fileName
        }

    return jsonify(response_data)

@api.route('/api/addalert', methods=['POST'])
def addalert():
    # Get data from the request
    data = request.get_json()

    # Validate input
    required_fields = ['a_category', 'a_message', 'a_latitude', 'a_longitude', 'au_id', 'a_photo', 'z_id']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Incomplete data provided'})

    # Check if the user exists based on au_id
    user = AppUser.query.get(data['au_id'])
    if not user:
        return jsonify({'status': 'error', 'message': 'Invalid user ID'})

    # Decode the base64-encoded image string
    image_data = base64.b64decode(data['a_photo'])

    # Save the image to a unique folder for each user
    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(user.au_id))
    os.makedirs(user_folder, exist_ok=True)
    
    # Generate a unique filename
    image_fileName = f"captured_image_{uuid.uuid4()}.jpg"
    image_filePath = os.path.join(user_folder, image_fileName)
    
    with open(image_filePath, 'wb') as f:
        f.write(image_data)

    # Fetch the zone based on zone_id
    zone = Zone.query.get(data['z_id'])
    if not zone:
        return jsonify({'status': 'error', 'message': 'Invalid zone ID'})
    
     # Fetch the associated city/guide for the zone
    guide = zone.guide

    # Calculate the total coins for the city/guide
    coins_to_be_granted = guide.g_coins_for_first_alert

    # Create a new alert
    new_alert = Alert(
        a_category=data['a_category'],
        a_photo=image_fileName,  # Save the filename in the database
        a_message=data['a_message'],
        a_latitude=data['a_latitude'],
        a_longitude=data['a_longitude'],
        a_points = coins_to_be_granted,
        z_id=data['z_id'],  # Add z_id
        app_user=user
    )

    # Add the new alert to the database
    db.session.add(new_alert)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': 'Alert created successfully', 'alert_id': str(new_alert.a_id), 'coins_granted':coins_to_be_granted})

@api.route('/api/getalerts', methods=['GET'])
def get_alerts():
    # Fetch all alerts from the database
    alerts = Alert.query.all()

    # Prepare a list to store alert data
    alerts_data = []

    # Convert each alert object to a dictionary
    for alert in alerts:
        alert_data = {
            'a_id': alert.a_id,
            'a_category': alert.a_category,
            'a_message': alert.a_message,
            'a_latitude': alert.a_latitude,
            'a_longitude': alert.a_longitude,
            'a_photo': alert.a_photo,
            'au_id': alert.app_user.au_id,  # Assuming you want to include user ID in the response
            # 'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),  # Include timestamp if needed
        }
        alerts_data.append(alert_data)

    return jsonify({'status': 'ok', 'alerts': alerts_data})

@api.route('/api/get_app_data', methods=['POST'])
def get_app_data():
    data = request.json  # Assuming you send a JSON payload in the request
    user_id = data.get('user_id')

    response_data = {'status':'', 'message':'', 'app_user_points': 0, 'user': {}, 'cities': {}}

    # Retrieve the user from the database
    user = AppUser.query.get(user_id)

    if user:
        # Calculate points dynamically (for example, based on 100 points per alert)
         # Calculate points dynamically based on the associated guide's settings for each alert
        points_for_alerts = 0
        points_for_confirmation = 0
        points_for_close = 0

        # Fetch all alerts for the user
        alerts = Alert.query.filter_by(au_id=user_id).all()
        for alert in alerts:
            # Add points based on the alert's points
            points_for_alerts += alert.a_points

        total_user_points = points_for_alerts + points_for_confirmation + points_for_close

        # Fetch all guides
        guides = Guide.query.all()
        for guide in guides:
            # Get guide settings if available
            city_coins = {
                'first_alert': guide.g_coins_for_first_alert,
                'confirm_alert': guide.g_coins_for_confirm_alert,
                'final_alert': guide.g_coins_for_close_alert
            }
            response_data['cities'][guide.g_title] = city_coins

        # Return the required data as JSON
        response_data['status'] = 'ok'
        response_data['message'] = 'User data retrieved successfully'
        response_data['app_user_points'] = total_user_points
        response_data['user'] = {
            'user_id': user.au_id,
            'full_name': user.au_full_name,
            'email': user.au_email,
            'mobile_number': user.au_mobile_number,
            'profile_photo': user.au_photo
        }

        return jsonify(response_data)
    else:
        response_data['status'] = 'logout'
        response_data['message'] = 'User not found'
        return jsonify(response_data)