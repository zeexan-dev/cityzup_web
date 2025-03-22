import uuid
from flask import (
    Blueprint,
    render_template,
    jsonify,
    redirect,
    session,
    url_for,
    request,
    current_app,
)
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
from project.project_utils import PointsUtils
import base64
from .models import (
    AlertClose,
    AlertConfirm,
    Guide,
    Zone,
    Road,
    ZonePoint,
    RoadPoint,
    AppUser,
    Alert,
    Equivalent,
    EquivalentRequest,
    MissionAction,
    MissionCampaign,
    MissionActionsCompleted,
    MissionPaparazzi,
    MissionPaparazziCompleted,
)
from . import db
import json
import os

api = Blueprint("api", __name__)

@api.route("/api/mission_paparazzi_completed", methods=["POST"])
def mission_paparazzi_completed():

     # Parse JSON data
    data = request.get_json()

    user_id = data.get("userId")
    missions = data.get("missions", [])  # Get mission list (default to empty list if not present)

    # Validate input
    if not (user_id):
        return jsonify({"status": "error", "message": "Invalid user"})

    # Check if the user exists based on email or mobile number
    user = AppUser.query.filter((AppUser.au_id == user_id)).first()
    if not user:
        return jsonify({"status": "error", "message": "Invalid user"})
    

    total_coins = 0  # Initialize total coins count

    for mission in missions:
        mp_unique_id = mission.get("mp_unique_id")
        photo_base64 = mission.get("photo")
        coins = mission.get("coins", 0)
        mission_text = mission.get("text", "")

        # Decode Base64 image
        if photo_base64:
            try:
                photo_data = base64.b64decode(photo_base64)
                # Save the image to a unique folder for each user
                folder = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], "mission_paparazzi"
                )
                os.makedirs(folder, exist_ok=True)

                # Generate a unique filename
                image_fileName = f"missionpap_{mp_unique_id}_{user_id}_{uuid.uuid4()}.jpg"
                image_filePath = os.path.join(folder, image_fileName)

                with open(image_filePath, "wb") as f:
                    f.write(photo_data)
            except Exception as e:
                return jsonify({"status": "error", "message": f"Failed to save image: {str(e)}"}), 500

        # Accumulate total coins
        total_coins += coins

        # Insert mission record into the database
        mission_completed = MissionPaparazziCompleted(
            au_id=user_id,
            mp_unique_id=mp_unique_id,
            mpc_coins=coins,
            mpc_text=mission_text,
            mpc_photo_path=image_fileName if photo_base64 else None,  # Save path if photo exists
        )
        db.session.add(mission_completed)

    # Commit all mission records to the database
    db.session.commit()

    # Successful authentication
    if total_coins == 0:
        return jsonify(
            {"status": "error", "message": f"Mission campaign ended. 0 coins granted"}
        )
    # Successful authentication
    return jsonify({"status": "ok", "message": f"{total_coins} Mission Coins Granted"})


@api.route("/api/get_mission_paparazzi", methods=["GET"])
def get_mission_paparazzi():
    try:
        # Check the status of the mission_paparazzi campaign
        mission_paparazzi_campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Paparazzi"
        ).first()

        # If the campaign is inactive, return an empty list
        if (
            mission_paparazzi_campaign is None
            or not mission_paparazzi_campaign.mc_status
        ):
            return jsonify(
                {
                    "status": "error",
                    "mission_paparazzi": [],
                    "total_coins": 0,  # Total coins is 0 since no paparazzi missions are available
                    "msg": "Mission Paparazzi not available",
                }
            )

        # Fetch all mission paparazzi entries from the database
        mission_paparazzi = MissionPaparazzi.query.all()

        # Prepare a list to store mission paparazzi data
        mission_paparazzi_data = []

        # Initialize a variable to store the total coins
        total_coins = 0

        # Convert each mission paparazzi object to a dictionary and calculate total coins
        for paparazzi in mission_paparazzi:
            paparazzi_data = {
                "mp_id": paparazzi.mp_id,
                "mp_unique_id": paparazzi.mp_unique_id,
                "mp_text": paparazzi.mp_text,
                "mp_lat": paparazzi.mp_lat,
                "mp_lng": paparazzi.mp_lng,
                "mp_radius": paparazzi.mp_radius,
                "mp_coins": paparazzi.mp_coins,
                "mp_created_at": paparazzi.mp_created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),  # Format the creation timestamp
            }
            mission_paparazzi_data.append(paparazzi_data)

            # Add the coins of the current paparazzi mission to the total coins
            total_coins += paparazzi.mp_coins

        # Return the mission paparazzi data and the total coins
        return jsonify(
            {
                "status": "ok",
                "mission_paparazzi": mission_paparazzi_data,
                "total_coins": total_coins,  # Include total coins in the response
                "msg": "",
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@api.route("/api/mission_action_completed", methods=["POST"])
def mission_action_completed():
    # Get data from the request
    user_id = request.form.get("user_id")

    # Validate input
    if not (user_id):
        return jsonify({"status": "error", "message": "Invalid user"})

    # Check if the user exists based on email or mobile number
    user = AppUser.query.filter((AppUser.au_id == user_id)).first()

    if not user:
        return jsonify({"status": "error", "message": "Invalid user"})

    # Calculate the total coins from all mission actions
    total_coins = db.session.query(db.func.sum(MissionAction.ma_coins)).scalar() or 0

    # Insert a record into MissionActionsCompleted
    mission_completed = MissionActionsCompleted(au_id=user_id, total_coins=total_coins)
    db.session.add(mission_completed)
    db.session.commit()

    # Successful authentication
    if total_coins == 0:
        return jsonify(
            {"status": "error", "message": f"Mission campaign ended. 0 coins granted"}
        )
    # Successful authentication
    return jsonify({"status": "ok", "message": f"{total_coins} Mission Coins Granted"})


@api.route("/api/get_mission_actions", methods=["GET"])
def get_mission_actions():
    try:
        # Check the status of the mission_action campaign
        mission_action_campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Action"
        ).first()

        # If the campaign is inactive, return an empty list
        if mission_action_campaign is None or not mission_action_campaign.mc_status:
            return jsonify(
                {
                    "status": "ok",
                    "mission_actions": [],
                    "total_coins": 0,  # Total coins is 0 since no actions are available
                    "msg": "Mission Action not available",
                }
            )

        # Fetch all mission actions from the database
        mission_actions = MissionAction.query.all()

        # Prepare a list to store mission action data
        mission_actions_data = []

        # Initialize a variable to store the total coins
        total_coins = 0

        # Convert each mission action object to a dictionary and calculate total coins
        for action in mission_actions:
            action_data = {
                "ma_id": action.ma_id,  # Action ID
                "ma_unique_id": action.ma_unique_id,  # Action ID
                "ma_text": action.ma_text,  # Action text
                "ma_url": action.ma_url,  # Action URL
                "ma_coins": action.ma_coins,  # Coins for the action
                "ma_created_at": action.ma_created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),  # Format the creation timestamp
            }
            mission_actions_data.append(action_data)

            # Add the coins of the current action to the total coins
            total_coins += action.ma_coins

        # Return the mission actions and the total coins
        return jsonify(
            {
                "status": "ok",
                "mission_actions": mission_actions_data,
                "total_coins": total_coins,  # Include total coins in the response
                "msg": "",
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@api.route("/api/submit_equivalent_request", methods=["POST"])
def submit_equivalent_request():
    try:
        data = request.get_json()
        app_user_id = data.get("app_user_id")
        eq_id = data.get("eq_id")

        # Check if the AppUser exists
        app_user = AppUser.query.get(app_user_id)
        if not app_user:
            return jsonify({"status": "error", "message": "App User not found"})

        # Check if the Equivalent exists
        equivalent = Equivalent.query.get(eq_id)
        if not equivalent:
            return jsonify({"status": "error", "message": "Equivalent not found"})

        # Calculate total user points
        total_user_points = PointsUtils.calculate_user_points(app_user_id)

        # Check if user has enough points
        if total_user_points < equivalent.eq_coins:
            return jsonify({"status": "warning", "message": "Insufficient points"})

        # Create a new EquivalentRequest
        equivalent_request = EquivalentRequest(
            eq_id=eq_id, au_id=app_user_id, eqr_number_of_coins=equivalent.eq_coins
        )
        db.session.add(equivalent_request)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Request submitted successfully"})
    except Exception as e:
        print(e)
        return jsonify(
            {"status": "error", "message": "Failed to submit equivalent request"}
        )


@api.route("/api/get_equivalents", methods=["GET"])
def get_equivalents():
    try:
        # Fetch all equivalents from the database
        equivalents = Equivalent.query.all()

        # Prepare a list to store equivalent data
        equivalents_data = []

        # Convert each equivalent object to a dictionary
        for equivalent in equivalents:
            equivalent_data = {
                "eq_id": equivalent.eq_id,  # Adjust field names based on your model
                "eq_name": equivalent.eq_name,
                "eq_coins": equivalent.eq_coins,
                "eq_picture": equivalent.eq_picture,
                # Add more fields as needed
            }
            equivalents_data.append(equivalent_data)

        return jsonify({"status": "ok", "equivalents": equivalents_data})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@api.route("/api/get_zones_and_roads", methods=["GET"])
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
            zone_centeroid = {"lat": zone.z_centroid_lat, "lng": zone.z_centroid_lng}

            # Retrieve the coordinates for the current zone
            zone_coordinates = ZonePoint.query.filter_by(z_id=zone_id).all()

            # Convert the coordinates to a list of dictionaries
            zone_coordinates_list = [
                {"lat": coord.zp_lat, "lng": coord.zp_lng} for coord in zone_coordinates
            ]

            # Add the zone name and coordinates to the list
            zone_data = {
                "zone_id": zone_id,
                "zone_name": zone_name,
                "coordinates": zone_coordinates_list,
                "centeroid": zone_centeroid,
            }
            all_zones_coordinates.append(zone_data)

        # Loop through each road
        for road in all_roads:
            road_id = road.r_id
            road_name = road.r_name

            # Retrieve the coordinates for the current road
            road_coordinates = RoadPoint.query.filter_by(r_id=road_id).all()

            # Convert the coordinates to a list of dictionaries
            road_coordinates_list = [
                {"lat": coord.rp_lat, "lng": coord.rp_lng} for coord in road_coordinates
            ]

            # Add the road name and coordinates to the list
            road_data = {
                "road_id": road_id,
                "road_name": road_name,
                "coordinates": road_coordinates_list,
            }
            all_roads_coordinates.append(road_data)

        return jsonify(
            {
                "status": "ok",
                "zones": all_zones_coordinates,
                "roads": all_roads_coordinates,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route("/api/signup", methods=["POST"])
def signup():
    # Get data from the request
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    mobile_number = request.form.get("mobile_number")
    password = request.form.get("password")

    # Validate input
    if not (full_name and email and mobile_number and password):
        return jsonify({"status": "error", "message": "Incomplete data provided"})

    # Check if the user already exists
    if (
        AppUser.query.filter_by(au_email=email).first()
        or AppUser.query.filter_by(au_mobile_number=mobile_number).first()
    ):
        return jsonify(
            {
                "status": "error",
                "message": "User with email or mobile number already exists",
            }
        )

    # Create a new user
    new_user = AppUser(
        au_full_name=full_name,
        au_email=email,
        au_mobile_number=mobile_number,
        au_photo="",
    )
    new_user.set_password(password)

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "ok", "message": "Signup Successful"})


@api.route("/api/signin", methods=["POST"])
def signin():
    # Get data from the request
    email_or_mobile = request.form.get("email_or_mobile")
    password = request.form.get("password")

    # Validate input
    if not (email_or_mobile and password):
        return jsonify(
            {
                "status": "error",
                "message": "Incomplete data provided",
                "user_id": "",
                "user_full_name": "",
            }
        )

    # Check if the user exists based on email or mobile number
    user = AppUser.query.filter(
        (AppUser.au_email == email_or_mobile)
        | (AppUser.au_mobile_number == email_or_mobile)
    ).first()

    if not user or not user.check_password(password):
        return jsonify(
            {
                "status": "error",
                "message": "Invalid email/mobile number or password",
                "user_id": "",
                "user_full_name": "",
            }
        )

    # Successful authentication
    return jsonify(
        {
            "status": "ok",
            "message": "Signin Successful",
            "user_id": user.au_id,
            "user_full_name": user.au_full_name,
        }
    )


@api.route("/api/update_profie_image", methods=["POST"])
def updateProfileImage():
    # Get data from the request
    data = request.get_json()

    response_data = {"status": "", "message": "", "user": {}}

    # Validate input
    required_fields = ["auid", "photo"]
    if not all(field in data for field in required_fields):
        response_data["status"] = "error"
        response_data["message"] = "Incomplete data provided"
        return jsonify(response_data)

    # Check if the user exists based on au_id
    user = AppUser.query.get(data["auid"])
    if not user:
        response_data["status"] = "error"
        response_data["message"] = "Invalid user ID"
        return jsonify(response_data)

    # Decode the base64-encoded image string
    image_data = base64.b64decode(data["photo"])

    # Save the image to a unique folder for each user
    user_folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"], str(user.au_id), "profile_images"
    )
    os.makedirs(user_folder, exist_ok=True)

    # Generate a unique filename
    image_fileName = f"captured_image_{uuid.uuid4()}.jpg"
    image_filePath = os.path.join(user_folder, image_fileName)

    with open(image_filePath, "wb") as f:
        f.write(image_data)

    # Update the user's profile image path in the database
    user.au_photo = image_fileName
    # Commit the changes to the database
    db.session.commit()

    response_data["status"] = "ok"
    response_data["message"] = "Profile Image Updated"
    response_data["user"] = {
        "user_id": user.au_id,
        "full_name": user.au_full_name,
        "email": user.au_email,
        "mobile_number": user.au_mobile_number,
        "profile_photo": image_fileName,
    }

    return jsonify(response_data)


@api.route("/api/add_alert_confirm", methods=["POST"])
def add_alert_confirm():
    try:
        # Get data from the request
        data = request.get_json()

        # Validate input
        required_fields = ["au_id", "a_id"]
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Incomplete data provided"})

        # Get data from the request
        au_id = int(data["au_id"])
        a_id = int(data["a_id"])

        # Check if the AppUser exists
        app_user = AppUser.query.get(au_id)
        if not app_user:
            return jsonify({"status": "error", "message": "App User not found"})

        # Check if the Alert exists
        alert = Alert.query.get(a_id)
        if not alert:
            return jsonify({"status": "error", "message": "Alert not found"})

        # Check if the alert is already closed
        if AlertClose.query.filter_by(a_id=a_id).first():
            return jsonify({"status": "warning", "message": "Alert already closed"})

        # Check if au_id is already present for a_id
        if AlertConfirm.query.filter_by(au_id=au_id, a_id=a_id).first():
            return jsonify(
                {"status": "warning", "message": "Alert already confirmed by this user"}
            )

        # find the points to be granted to user for confirming the alert
        zone = alert.zone
        # Fetch the associated city/guide for the zone
        guide = zone.guide
        # Calculate the total coins for the city/guide
        coins_to_be_granted = guide.g_coins_for_confirm_alert

        # Insert data into AlertConfirm table
        alert_confirm = AlertConfirm(
            au_id=au_id, a_id=a_id, acn_points=coins_to_be_granted
        )
        db.session.add(alert_confirm)
        db.session.commit()

        return jsonify(
            {
                "status": "ok",
                "message": "Alert confirmation added successfully",
                "coins_granted": coins_to_be_granted,
            }
        )
    except Exception as e:
        print(e)
        return jsonify(
            {"status": "error", "message": "Failed to add alert confirmation"}
        )


@api.route("/api/add_alert_close", methods=["POST"])
def add_alert_close():
    try:
        # Get data from the request
        data = request.get_json()

        # Validate input
        required_fields = ["au_id", "a_id"]
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Incomplete data provided"})

        # Get data from the request
        au_id = int(data["au_id"])
        a_id = int(data["a_id"])

        # Check if the AppUser exists
        app_user = AppUser.query.get(au_id)
        if not app_user:
            return jsonify({"status": "error", "message": "App User not found"})

        # Check if the Alert exists
        alert = Alert.query.get(a_id)
        if not alert:
            return jsonify({"status": "error", "message": "Alert not found"})

        # Check if any user has already closed the alert for the given a_id
        if AlertClose.query.filter_by(a_id=a_id).first():
            return jsonify({"status": "warning", "message": "Alert already closed"})

        # find the points to be granted to user for confirming the alert
        zone = alert.zone
        # Fetch the associated city/guide for the zone
        guide = zone.guide
        # Calculate the total coins for the city/guide
        coins_to_be_granted = guide.g_coins_for_close_alert

        # Insert data into AlertClose table
        alert_close = AlertClose(au_id=au_id, a_id=a_id, acl_points=coins_to_be_granted)
        db.session.add(alert_close)
        db.session.commit()

        return jsonify(
            {
                "status": "ok",
                "message": "Alert closure added successfully",
                "coins_granted": coins_to_be_granted,
            }
        )
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": "Failed to add alert closure"})


@api.route("/api/addalert", methods=["POST"])
def addalert():
    # Get data from the request
    data = request.get_json()

    # Validate input
    required_fields = [
        "a_category",
        "a_message",
        "a_latitude",
        "a_longitude",
        "au_id",
        "a_photo",
        "z_id",
    ]
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "message": "Incomplete data provided"})

    # Check if the user exists based on au_id
    user = AppUser.query.get(data["au_id"])
    if not user:
        return jsonify({"status": "error", "message": "Invalid user ID"})

    # Decode the base64-encoded image string
    image_data = base64.b64decode(data["a_photo"])

    # Save the image to a unique folder for each user
    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(user.au_id))
    os.makedirs(user_folder, exist_ok=True)

    # Generate a unique filename
    image_fileName = f"captured_image_{uuid.uuid4()}.jpg"
    image_filePath = os.path.join(user_folder, image_fileName)

    with open(image_filePath, "wb") as f:
        f.write(image_data)

    # Fetch the zone based on zone_id
    zone = Zone.query.get(data["z_id"])
    if not zone:
        return jsonify({"status": "error", "message": "Invalid zone ID"})

    # Fetch the associated city/guide for the zone
    guide = zone.guide

    # Calculate the total coins for the city/guide
    coins_to_be_granted = guide.g_coins_for_first_alert

    # Create a new alert
    new_alert = Alert(
        a_category=data["a_category"],
        a_photo=image_fileName,  # Save the filename in the database
        a_message=data["a_message"],
        a_latitude=data["a_latitude"],
        a_longitude=data["a_longitude"],
        a_points=coins_to_be_granted,
        z_id=data["z_id"],  # Add z_id
        app_user=user,
    )

    # Add the new alert to the database
    db.session.add(new_alert)
    db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "message": "Alert created successfully",
            "alert_id": str(new_alert.a_id),
            "coins_granted": coins_to_be_granted,
        }
    )


@api.route("/api/getalerts", methods=["GET"])
def get_alerts():
    # Fetch all alerts from the database
    alerts = Alert.query.all()

    # Prepare a list to store alert data
    alerts_data = []

    # Convert each alert object to a dictionary
    for alert in alerts:
        alert_data = {
            "a_id": alert.a_id,
            "a_category": alert.a_category,
            "a_message": alert.a_message,
            "a_latitude": alert.a_latitude,
            "a_longitude": alert.a_longitude,
            "a_photo": alert.a_photo,
            "au_id": alert.app_user.au_id,  # Assuming you want to include user ID in the response
            "z_id": alert.z_id,
            # 'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),  # Include timestamp if needed
        }
        alerts_data.append(alert_data)

    return jsonify({"status": "ok", "alerts": alerts_data})


@api.route("/api/get_app_data", methods=["POST"])
def get_app_data():
    data = request.json  # Assuming you send a JSON payload in the request
    user_id = data.get("user_id")

    response_data = {
        "status": "",
        "message": "",
        "app_user_points": 0,
        "user": {},
        "cities": {},
    }

    # Retrieve the user from the database
    user = AppUser.query.get(user_id)

    if user:
        # Calculate points
        total_user_points = PointsUtils.calculate_user_points(user_id)

        # Fetch all guides
        guides = Guide.query.all()
        for guide in guides:
            # Get guide settings if available
            city_coins = {
                "first_alert": guide.g_coins_for_first_alert,
                "confirm_alert": guide.g_coins_for_confirm_alert,
                "final_alert": guide.g_coins_for_close_alert,
            }
            response_data["cities"][guide.g_title] = city_coins

        # Return the required data as JSON
        response_data["status"] = "ok"
        response_data["message"] = "User data retrieved successfully"
        response_data["app_user_points"] = total_user_points
        response_data["user"] = {
            "user_id": user.au_id,
            "full_name": user.au_full_name,
            "email": user.au_email,
            "mobile_number": user.au_mobile_number,
            "profile_photo": user.au_photo,
        }

        return jsonify(response_data)
    else:
        response_data["status"] = "logout"
        response_data["message"] = "User not found"
        return jsonify(response_data)
