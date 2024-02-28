from flask import Blueprint, render_template, jsonify, redirect, session, url_for, request
from flask_login import login_user, logout_user, login_required
from .models import Guide, GuideSettings, Zone, Road, ZonePoint, RoadPoint, Alert, AppUser
from . import db
import json
import os

main = Blueprint('main', __name__)

@main.route("/")
@login_required
def home():
    # Query to get all guides with their point counts
    guides = db.session.query(Guide.g_id, Guide.g_title, db.func.count(Zone.z_id).label('point_count')) \
                      .outerjoin(Zone, Zone.g_id == Guide.g_id) \
                      .group_by(Guide.g_id) \
                      .order_by(Guide.g_id.desc()) \
                      .all()

    title = 'Dashboard'
    page_title = 'Recent Cities'
    return render_template('home.html', guides=guides, page_title=page_title, title=title)
# ================================= ALERTS =================================
@main.route("/alerts/")
@login_required
def get_alerts_with_user_info():
    # Query alerts with user information
    alerts_with_user_info = db.session.query(
        Alert,
        AppUser
    ).join(AppUser).all()

    # Extract the relevant information from the query results
    result = []
    for alert, user in alerts_with_user_info:
        result.append({
            'a_id': alert.a_id,
            'a_category': alert.a_category,
            'a_photo': alert.a_photo,
            'a_message': alert.a_message,
            'a_latitude': alert.a_latitude,
            'a_longitude': alert.a_longitude,
            'au_full_name': user.au_full_name,
            'au_email': user.au_email,
            'au_mobile_number': user.au_mobile_number
        })

    # Render the template with the alerts data
    title = 'Alerts'
    page_title = 'Alerts'
    return render_template('alerts.html', alerts=result, page_title=page_title, title=title)

#  ================================ CITIES =================================
@main.route("/cities/")
@login_required
def cities():
    # Query to get all guides with their point counts and settings
    cities = db.session.query(
        Guide.g_id,
        Guide.g_title,
        db.func.count(Zone.z_id).label('point_count'),
        GuideSettings.coins_for_first_alert,
        GuideSettings.coins_for_confirm_alert,
        GuideSettings.coins_for_close_alert
    ) \
        .outerjoin(Zone, Zone.g_id == Guide.g_id) \
        .outerjoin(GuideSettings, GuideSettings.g_id == Guide.g_id) \
        .group_by(Guide.g_id, GuideSettings.coins_for_first_alert, GuideSettings.coins_for_confirm_alert,
                  GuideSettings.coins_for_close_alert) \
        .order_by(Guide.g_id.desc()) \
        .all()

    title = 'Cities'
    page_title = 'Cities'
    return render_template('cities.html', cities=cities, page_title=page_title, title=title)


@main.route("/cities/add", methods=['POST'])
@login_required
def add_city():
    try:
        # Get data from the request
        title = request.form.get('title')

        # Check if the title field is empty
        if not title:
            return jsonify({"status": "warning", "message": "Both titles are required"})

        # Check if the title has at least 3 characters
        elif len(title) < 3:
            return jsonify({"status": "warning", "message": "Title must have at least 3 characters."})

        # Validation passed, insert the guide into the database
        else:
            # Insert the guide into the database
            new_guide = Guide(g_title=title)
            db.session.add(new_guide)
            db.session.commit()

            settings = GuideSettings(coins_for_first_alert=100,
                                         coins_for_confirm_alert=50,
                                         coins_for_close_alert=30,
                                         guide=new_guide)
            db.session.add(settings)
            db.session.commit()

            return jsonify({"status": "ok", "message": "City Added Successfully"})

    except Exception as e:
        # print(e)
        return jsonify({"status": "error", "message": "Cannot add data, please try again"})


@main.route("/cities/edit", methods=['POST'])
@login_required
def edit_city():
    data = request.form
    title = data.get('gtitle')
    gid = data.get('gid')

    # Check if the title field is empty
    if not title:
        return jsonify(status='warning', message='Both titles are required')

    # Check if the title has at least 3 characters
    elif len(title) < 3:
        return jsonify(status='warning', message='Title must have at least 3 characters.')

    # Validation passed, update the guide in the database
    else:
        try:
            # Update the guide in the database
            guide = Guide.query.filter_by(g_id=gid).one()
            guide.g_title = title

            db.session.commit()

            return jsonify(status='ok', message='City Edited Successfully')

        except NoResultFound:
            return jsonify(status='error', message='City not found')

        except Exception as e:
            # Log the error for debugging
            print(e)
            db.session.rollback()

            return jsonify(status='error', message='Cannot edit data, please try again')

@main.route("/cities/delete", methods=['POST'])
@login_required
def delete_city():
    gid = request.form.get('gid')

    # Check if gid is provided
    if not gid:
        return jsonify(status='warning', message='Guide ID is required for deletion')

    try:
        # Find the guide by gid
        guide = Guide.query.filter_by(g_id=gid).one()

        # Delete the guide from the database
        db.session.delete(guide)
        db.session.commit()

        return jsonify(status='ok', message='City Deleted Successfully')

    except NoResultFound:
        return jsonify(status='error', message='City not found')

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status='error', message='Cannot delete data, please try again')
# ================================ CITY SETTINGS =========================
@main.route("/update_city_settings", methods=['POST'])
@login_required
def update_city_settings():
    try:
        # Get data from the request
        first_alert = int(request.form.get('first_alert'))
        confirm_alert = int(request.form.get('confirm_alert'))
        final_alert = int(request.form.get('final_alert'))
        g_id = int(request.form.get('gid'))

        # Check if the title field is empty
        if not first_alert or not confirm_alert or not final_alert :
            return jsonify({"status": "warning", "message": "All fields are required"})

        # Check if the title has at least 3 characters
        elif first_alert < 0 or confirm_alert < 0 or final_alert < 0:
            return jsonify({"status": "warning", "message": "Coins values must be greater than 0"})

        # Validation passed, insert the guide into the database
        else:
            # Insert the guide into the database
            new_settings = GuideSettings(coins_for_first_alert=first_alert,
                                      coins_for_confirm_alert=confirm_alert,
                                      coins_for_close_alert=final_alert,
                                      g_id = g_id)
            db.session.add(new_settings)
            db.session.commit()

            return jsonify({"status": "ok", "message": "Settings Updated Successfully"})

    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": "Cannot add data, please try again"})
#  ================================ USERS =================================
@main.route("/users/")
@login_required
def users():
    
   # Query to get all users
    users = User.query.all()

    title = 'Users'
    page_title = 'Users'
    return render_template('users.html', users=users, page_title=page_title, title=title)

@main.route("/users/add", methods=['POST'])
@login_required
def add_user():
    
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if the fields are present
    if not username or not password:
        return jsonify({'status': 'warning', 'message': 'All fields are required'})

    # Check length requirements
    if len(username) < 5:
        return jsonify({'status': 'warning', 'message': 'Username cannot be less than 5 characters.'})

    if len(password) < 6:
        return jsonify({'status': 'warning', 'message': 'Password cannot be less than 6 characters.'})

    # Hash the password
    hashed_password = hashlib.sha1(password.encode()).hexdigest()

    # Check if the username already exists
    existing_user = User.query.filter_by(u_username=username).first()

    if existing_user:
        return jsonify({'status': 'warning', 'message': 'Username already exists. Choose a different username.'})


    # Create a new user
    new_user = User(u_username=username, u_password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'User Added Successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Cannot add data, please try again'}), 500

#  ========================== ZONES  ===========================
@main.route("/zonesandroads/")
@login_required
def zones_and_roads():
    
    # Query all zones
    zones = Zone.query.join(Guide).order_by(Guide.g_id.desc()).all()

    # Query all roads
    roads = Road.query.join(Guide).order_by(Guide.g_id.desc()).all()

    cities = Guide.query.all()


    title = 'Zones & Roads'
    page_title = 'Zones & Roads'
    return render_template('zones_and_roads.html', zones=zones, roads=roads, cities=cities, page_title=page_title, title=title)

@main.route('/show_zone_points', methods=['POST'])
def show_zone_points():
    zid = request.form.get('zid')
    zone_points = ZonePoint.query.filter_by(z_id=zid).all()

    if zone_points:
        # Convert the SQLAlchemy objects to a list of dictionaries
        result = [{'zp_id': point.zp_id, 'zp_lat': point.zp_lat, 'zp_lng': point.zp_lng, 'z_id': point.z_id} for point in zone_points]
        return jsonify({'status': 'ok', 'data': result})
    
    else:
        return jsonify({'status': 'error', 'message': 'Points not found'})

@main.route('/add_zone', methods=['POST'])
@login_required
def add_zone():
    # Get data from the request
    gid = request.form.get('guide')
    zname = request.form.get('zname')

    # Check if gid is present and valid
    if gid is None or gid == "0":
        return jsonify({'status': 'error', 'message': 'Please select a city'})

    # Check if zname is present and has at least 3 characters
    if zname is None or len(zname) < 3:
        return jsonify({'status': 'error', 'message': 'Zone name must have at least 3 characters'})
    
    # Check if the file is present in the request
    if 'zone_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})

    # Get the uploaded file
    zone_file = request.files['zone_file']

    # Check if the file is empty
    if zone_file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    # Check if the file is allowed
    allowed_extensions = {'json'}
    if '.' not in zone_file.filename or zone_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'status': 'error', 'message': 'Invalid file type'})

    # Set up the path for file upload
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save the uploaded file
    file_path = os.path.join(upload_folder, zone_file.filename)
    zone_file.save(file_path)

    # Check if the file already exists
    if Zone.query.filter_by(z_name=zname).first():
        os.remove(file_path)  # Delete the uploaded file
        return jsonify({'status': 'error', 'message': 'Zone file already exists'})

    # Create a new zone
    new_zone = Zone(z_name=zname, g_id=gid)
    db.session.add(new_zone)
    db.session.commit()

    # Parse the JSON data from the uploaded file
    with open(file_path, 'r') as json_file:
        try:
            json_data = json.load(json_file)
            coordinates = json_data['coordinates']
            zone_id = new_zone.z_id

            # Initialize an array to store the data to be inserted into zone_points table
            zone_points_data = []

            for coord in coordinates:
                zp_lat = coord[1]
                zp_lng = coord[0]

                # Add the data to the array for insertion
                zone_points_data.append({
                    'zp_lat': zp_lat,
                    'zp_lng': zp_lng,
                    'z_id': zone_id,
                })

            # Insert the data into the zone_points table
            db.session.bulk_insert_mappings(ZonePoint, zone_points_data)
            db.session.commit()

            return jsonify({'status': 'ok', 'message': 'Zone and Zone Points Added Successfully'})

        except json.JSONDecodeError:
            # Delete the zone if JSON decoding fails
            db.session.delete(new_zone)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({'status': 'error', 'message': 'Invalid JSON file'})
        except Exception as e:
            # Delete the zone if an exception occurs
            db.session.delete(new_zone)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({'status': 'error', 'message': str(e)}), 500

@main.route('/delete_zone', methods=['POST'])
@login_required
def delete_zone():
    zid = request.form.get('zid')

    # Check if gid is provided
    if not zid:
        return jsonify(status='warning', message='Zone ID is required for deletion')

    try:
        # Find the guide by gid
        zone = Zone.query.filter_by(z_id=zid).one()

        # Delete the guide from the database
        db.session.delete(zone)
        db.session.commit()

        return jsonify(status='ok', message='Zone Deleted Successfully')

    except NoResultFound:
        return jsonify(status='error', message='Zone not found')

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status='error', message='Cannot delete data, please try again')
    

# ============================ ROADS =======================
@main.route('/show_road_points', methods=['POST'])
def show_road_points():
    rid = request.form.get('rid')
    road_points = RoadPoint.query.filter_by(r_id=rid).all()

    if road_points:
        # Convert the SQLAlchemy objects to a list of dictionaries
        result = [{'rp_id': point.rp_id, 'rp_lat': point.rp_lat, 'rp_lng': point.rp_lng, 'r_id': point.r_id} for point in road_points]
        return jsonify({'status': 'ok', 'data': result})
    
    else:
        return jsonify({'status': 'error', 'message': 'Points not found'})


@main.route('/add_road', methods=['POST'])
@login_required
def add_road():
    # Get data from the request
    gid = request.form.get('guide')
    rname = request.form.get('rname')

    # Check if gid is present and valid
    if gid is None or gid == "0":
        return jsonify({'status': 'error', 'message': 'Please select a city'})

    # Check if zname is present and has at least 3 characters
    if rname is None or len(rname) < 3:
        return jsonify({'status': 'error', 'message': 'Road name must have at least 3 characters'})
    
    # Check if the file is present in the request
    if 'road_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})

    # Get the uploaded file
    road_file = request.files['road_file']

    # Check if the file is empty
    if road_file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    # Check if the file is allowed
    allowed_extensions = {'json'}
    if '.' not in road_file.filename or road_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'status': 'error', 'message': 'Invalid file type'})

    # Set up the path for file upload
    upload_folder = 'uploads'
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save the uploaded file
    file_path = os.path.join(upload_folder, road_file.filename)
    road_file.save(file_path)

    # Check if the file already exists
    if Road.query.filter_by(r_name=rname).first():
        os.remove(file_path)  # Delete the uploaded file
        return jsonify({'status': 'error', 'message': 'Road file already exists'})

    # Create a new road
    new_road = Road(r_name=rname, g_id=gid)
    db.session.add(new_road)
    db.session.commit()

    # Parse the JSON data from the uploaded file
    with open(file_path, 'r') as json_file:
        try:
            json_data = json.load(json_file)
            coordinates = json_data['coordinates']
            road_id = new_road.r_id

            # Initialize an array to store the data to be inserted into zone_points table
            road_points_data = []

            for coord in coordinates:
                rp_lat = coord[1]
                rp_lng = coord[0]

                # Add the data to the array for insertion
                road_points_data.append({
                    'rp_lat': rp_lat,
                    'rp_lng': rp_lng,
                    'r_id': road_id,
                })

            # Insert the data into the zone_points table
            db.session.bulk_insert_mappings(RoadPoint, road_points_data)
            db.session.commit()

            return jsonify({'status': 'ok', 'message': 'Road and Road Points Added Successfully'})

        except json.JSONDecodeError:
            # Delete the zone if JSON decoding fails
            db.session.delete(new_road)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({'status': 'error', 'message': 'Invalid JSON file'})
        except Exception as e:
            # Delete the zone if an exception occurs
            db.session.delete(new_road)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({'status': 'error', 'message': str(e)})


@main.route('/delete_road', methods=['POST'])
@login_required
def delete_road():
    rid = request.form.get('rid')

    # Check if gid is provided
    if not rid:
        return jsonify(status='warning', message='Road ID is required for deletion')

    try:
        # Find the guide by gid
        road = Road.query.filter_by(r_id=rid).one()

        # Delete the guide from the database
        db.session.delete(road)
        db.session.commit()

        return jsonify(status='ok', message='Road Deleted Successfully')

    except NoResultFound:
        return jsonify(status='error', message='Road not found')

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status='error', message='Cannot delete data, please try again')
