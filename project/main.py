from flask import (
    Blueprint,
    current_app,
    render_template,
    jsonify,
    redirect,
    session,
    url_for,
    request,
    flash,
)
from flask_login import login_user, logout_user, login_required
import uuid
from project.project_utils import FileUtils
from .models import (
    Equivalent,
    Guide,
    MissionPaparazziCompleted,
    Zone,
    Road,
    ZonePoint,
    RoadPoint,
    Alert,
    AppUser,
    EquivalentRequest,
    MissionMCQ,
    MissionAction,
    MissionCampaign,
    MissionActionsCompleted,
    MissionPaparazzi,
)
from . import db
import json
import os
from PIL import Image
from werkzeug.utils import secure_filename
from shapely.geometry import Polygon
from shapely.ops import cascaded_union
from sqlalchemy.orm.exc import NoResultFound

main = Blueprint("main", __name__)


@main.route("/")
@login_required
def home():
    # Query to get all guides with their point counts
    guides = (
        db.session.query(
            Guide.g_id, Guide.g_title, db.func.count(Zone.z_id).label("point_count")
        )
        .outerjoin(Zone, Zone.g_id == Guide.g_id)
        .group_by(Guide.g_id)
        .order_by(Guide.g_id.desc())
        .all()
    )

    # Query to get all campaigns
    campaigns = db.session.query(
        MissionCampaign
    ).all()  # Adjust if you need specific fields

    page_title = "Dashboard"
    return render_template(
        "home.html", guides=guides, campaigns=campaigns, page_title=page_title
    )


# ================================= MISSION PAPARAZZI ========================


@main.route("/update_mission_status/<string:mpc_unique_id>", methods=["POST"])
@login_required
def update_completed_mission_pap_status(mpc_unique_id):
    mission = MissionPaparazziCompleted.query.filter_by(
        mpc_unique_id=mpc_unique_id
    ).first_or_404()
    new_status = int(request.form.get("status"))
    mission.mpc_status = new_status
    db.session.commit()
    flash("Mission status updated!", "success")
    return redirect(url_for("main.completed_mission_paparazzi"))


@main.route("/completed_mission_paparazzi")
@login_required
def completed_mission_paparazzi():
    # Query all completed mission actions with user data
    completed_missions = MissionPaparazziCompleted.query.join(AppUser).all()

    # Pass the data to the template
    return render_template(
        "mission_paparazzi_completed.html", missions=completed_missions
    )


@main.route("/mission_paparazzi/delete", methods=["POST"])
@login_required
def delete_mission_paparazzi():
    # Get the mission ID from the form data
    id = request.form.get("id")

    if not id:
        return jsonify({"status": "error", "message": "Mission ID not provided"}), 400

    try:
        # Fetch the mission by ID
        mission = MissionPaparazzi.query.get(id)

        if not mission:
            return jsonify({"status": "error", "message": "Mission not found"}), 404

        # Check if the associated campaign is active
        campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Paparazzi"
        ).first()
        if campaign and campaign.mc_status:
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "Mission cannot be deleted because the campaign is active",
                    }
                ),
                403,
            )

        # Delete the mission from the database
        db.session.delete(mission)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Mission deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/mission_paparazzi")
@login_required  # Ensure the user is logged in
def mission_paparazzi():
    # Query to get all mission actions
    missions = MissionPaparazzi.query.order_by(MissionPaparazzi.mp_id.desc()).all()

    title = "Mission Paparazzi"
    page_title = "Mission Paparazzi"
    return render_template(
        "mission_paparazzi.html", page_title=page_title, title=title, missions=missions
    )


@main.route("/mission_paparazzi/add", methods=["POST"])
@login_required  # Assuming you want to restrict this to logged-in users
def add_mission_paparazzi():
    try:

        # Check if the associated campaign is active
        campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Paparazzi"
        ).first()
        if campaign and campaign.mc_status:
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "Mission cannot be added because the campaign is already active",
                    }
                ),
                403,
            )

        # Get form data
        mission_text = request.form.get("mission_text")
        mission_lat = request.form.get("mission_lat")
        mission_lng = request.form.get("mission_lng")
        mission_radius = request.form.get("mission_radius")
        mission_coins = request.form.get("mission_coins")

        # Validate the input
        if not mission_text or not mission_lat or not mission_lng or not mission_coins:
            return jsonify({"status": "error", "message": "All fields are required"})

        # Create a new MissionPaparazzi instance
        new_mission = MissionPaparazzi(
            mp_text=mission_text,
            mp_lat=mission_lat,
            mp_lng=mission_lng,
            mp_radius=mission_radius,
            mp_coins=int(mission_coins),
        )

        # Add to the database
        db.session.add(new_mission)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Mission added successfully"}), 200

    except Exception as e:
        # Handle any errors that may occur
        print(f"Error adding Mission: {str(e)}")
        db.session.rollback()  # Rollback in case of any errors
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "An error occurred while adding the mission",
                }
            ),
            500,
        )


# ================================= MISSION ACTION =========================


@main.route("/completed_mission_actions")
@login_required
def completed_mission_actions():
    # Query all completed mission actions with user data
    completed_missions = MissionActionsCompleted.query.join(AppUser).all()

    # Pass the data to the template
    return render_template("mission_action_completed.html", missions=completed_missions)


@main.route("/toggle_campaign_status/<int:campaign_id>", methods=["POST"])
@login_required
def toggle_campaign_status(campaign_id):
    campaign = MissionCampaign.query.get(campaign_id)
    if campaign:

        # Check if the campaign being toggled is "Mission Action" and is being deactivated
        if campaign.mc_campaign_type == "Mission Action" and campaign.mc_status:
            # Deactivate the campaign
            campaign.mc_status = False

            # Delete all missions from the MissionAction table
            MissionAction.query.delete()  # Deletes all rows in MissionAction table

            flash(
                "Campaign deactivated, and all associated missions have been deleted.",
                "warning",
            )

        else:
            # Toggle the campaign status
            campaign.mc_status = not campaign.mc_status
            status_message = "activated" if campaign.mc_status else "deactivated"
            flash(f"Campaign status {status_message} successfully!", "success")
        db.session.commit()
    else:
        flash("Campaign not found.", "danger")
    return redirect(url_for("main.home"))


@main.route("/mission_actions")
@login_required  # Ensure the user is logged in
def mission_actions():
    # Query to get all mission actions
    missions = MissionAction.query.order_by(MissionAction.ma_id.desc()).all()

    title = "Mission Action"
    page_title = "Mission Action"
    return render_template(
        "mission_action.html", missions=missions, page_title=page_title, title=title
    )


@main.route("/mission_actions/add", methods=["POST"])
@login_required  # Assuming you want to restrict this to logged-in users
def add_mission_action():
    try:

        # Check if the associated campaign is active
        campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Action"
        ).first()
        if campaign and campaign.mc_status:
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "Mission cannot be added because the campaign is already active",
                    }
                ),
                403,
            )

        # Get form data
        mission_text = request.form.get("mission_text")
        mission_url = request.form.get("mission_url")
        coins = request.form.get("mission_coins")

        # Validate the input (add more validation as needed)
        if not mission_text or not mission_url or not coins:
            return jsonify({"status": "error", "message": "All fields are required"})

        # Create a new MissionMCQ instance
        new = MissionAction(
            ma_text=mission_text,
            ma_url=mission_url,
            ma_coins=int(coins),  # Assuming coins is an integer
        )

        # Add to the database
        db.session.add(new)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Mission added successfully"}), 200

    except Exception as e:
        # Handle any errors that may occur
        print(f"Error adding Mission: {str(e)}")
        db.session.rollback()  # Rollback in case of any errors
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "An error occurred while adding the mission",
                }
            ),
            500,
        )


@main.route("/mission_actions/edit", methods=["POST"])
@login_required
def edit_mission_action():
    # Retrieve data from the request
    id = request.form.get("id")
    mission_text = request.form.get("mission_text")
    mission_url = request.form.get("mission_url")
    mission_coins = request.form.get("mission_coins")

    # Validate the input (add more validation as needed)
    if not mission_text or not mission_url or not mission_coins:
        return jsonify({"status": "error", "message": "All fields are required"})

    # Find the quiz entry by ID
    mission = MissionAction.query.get(id)

    if mission:

        # Check if the associated campaign is active
        campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Action"
        ).first()
        if campaign and campaign.mc_status:
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "Mission cannot be updated because the campaign is active",
                    }
                ),
                403,
            )

        # Update the mission entry with new data
        mission.ma_text = mission_text
        mission.ma_url = mission_url
        mission.ma_coins = int(mission_coins)

        # Commit the changes to the database
        db.session.commit()

        return (
            jsonify({"status": "ok", "message": "Mission updated successfully!"}),
            200,
        )
    else:
        return jsonify({"status": "warning", "message": "Mission not found."}), 404


@main.route("/mission_actions/delete", methods=["POST"])
@login_required
def delete_mission_action():
    # Get the mission ID from the form data
    id = request.form.get("id")

    if not id:
        return jsonify({"status": "error", "message": "Mission ID not provided"}), 400

    try:
        # Fetch the mission by ID
        mission = MissionAction.query.get(id)

        if not mission:
            return jsonify({"status": "error", "message": "Mission not found"}), 404

        # Check if the associated campaign is active
        campaign = MissionCampaign.query.filter_by(
            mc_campaign_type="Mission Action"
        ).first()
        if campaign and campaign.mc_status:
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "Mission cannot be deleted because the campaign is active",
                    }
                ),
                403,
            )

        # Delete the mission from the database
        db.session.delete(mission)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Mission deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"status": "error", "message": str(e)}), 500


# ================================= MISSION MCQ =========================
@main.route("/mission_mcqs")
@login_required  # Ensure the user is logged in
def mission_mcqs():
    # Query to get all quiz mcqs
    quizzes = MissionMCQ.query.order_by(MissionMCQ.q_id.desc()).all()

    title = "Quiz MCQs"
    page_title = "Quiz MCQs"
    return render_template(
        "mission_mcq.html", quizzes=quizzes, page_title=page_title, title=title
    )


@main.route("/mission_mcqs/add", methods=["POST"])
@login_required  # Assuming you want to restrict this to logged-in users
def add_mission_mcq():
    try:
        # Get form data
        question_text = request.form.get("question_text")
        option1 = request.form.get("option_1")
        option2 = request.form.get("option_2")
        option3 = request.form.get("option_3")
        option4 = request.form.get("option_4")
        correct_option = request.form.get("correct_option")
        coins = request.form.get("quiz_coins")

        # Validate the input (add more validation as needed)
        if (
            not question_text
            or not option1
            or not option2
            or not option3
            or not option4
            or not correct_option
            or not coins
        ):
            return jsonify({"status": "error", "message": "All fields are required"})

        # Create a new MissionMCQ instance
        new = MissionMCQ(
            q_question=question_text,
            q_option_1=option1,
            q_option_2=option2,
            q_option_3=option3,
            q_option_4=option4,
            q_correct_option=int(correct_option),
            q_coins=int(coins),  # Assuming coins is an integer
        )

        # Add to the database
        db.session.add(new)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Quiz added successfully"}), 200

    except Exception as e:
        # Handle any errors that may occur
        print(f"Error adding MissionMCQ: {str(e)}")
        db.session.rollback()  # Rollback in case of any errors
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "An error occurred while adding the quiz",
                }
            ),
            500,
        )


@main.route("/mission_mcqs/edit", methods=["POST"])
@login_required
def edit_mission_mcq():
    # Retrieve data from the request
    qid = request.form.get("qid")
    question_text = request.form.get("question_text")
    option_1 = request.form.get("option_1")
    option_2 = request.form.get("option_2")
    option_3 = request.form.get("option_3")
    option_4 = request.form.get("option_4")
    correct_option = request.form.get("correct_option")
    quiz_coins = request.form.get("quiz_coins")

    # Validate the input (add more validation as needed)
    if (
        not question_text
        or not option_1
        or not option_2
        or not option_3
        or not option_4
        or not correct_option
        or not quiz_coins
    ):
        return jsonify({"status": "error", "message": "All fields are required"})

    # Find the quiz entry by ID
    quiz = MissionMCQ.query.get(qid)

    if quiz:
        # Update the quiz entry with new data
        quiz.q_question = question_text
        quiz.q_option_1 = option_1
        quiz.q_option_2 = option_2
        quiz.q_option_3 = option_3
        quiz.q_option_4 = option_4
        quiz.q_correct_option = int(correct_option)
        quiz.q_coins = int(quiz_coins)

        # Commit the changes to the database
        db.session.commit()

        return jsonify({"status": "ok", "message": "Quiz updated successfully!"})
    else:
        return jsonify({"status": "warning", "message": "Quiz not found."})


@main.route("/mission_mcqs/delete", methods=["POST"])
@login_required
def delete_mission_mcq():
    # Get the quiz ID from the form data
    qid = request.form.get("qid")

    if not qid:
        return jsonify({"status": "error", "message": "Quiz ID not provided"}), 400

    try:
        # Fetch the quiz by ID
        quiz = MissionMCQ.query.get(qid)

        if not quiz:
            return jsonify({"status": "error", "message": "Quiz not found"}), 404

        # Delete the quiz from the database
        db.session.delete(quiz)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Quiz deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"status": "error", "message": str(e)}), 500


# ================================= EQUIVALENTS =========================
@main.route("/equivalents")
@login_required  # Ensure the user is logged in
def equivalents():
    # Query to get all equivalents
    equivalents = Equivalent.query.order_by(Equivalent.eq_id.desc()).all()

    title = "Equivalents"
    page_title = "Equivalent Items"
    return render_template(
        "equivalents.html", equivalents=equivalents, page_title=page_title, title=title
    )


@main.route("/equivalents_requests")
@login_required
def equivalents_requests():
    try:
         # Fetch equivalents requests data from the database, ordered by created_at (latest first)
        equivalents_requests = EquivalentRequest.query \
            .join(Equivalent) \
            .join(AppUser) \
            .order_by(EquivalentRequest.eqr_created_at.desc()) \
            .all()
        # print(json.dumps(equivalents_requests))

        return render_template(
            "equivalents_requests.html", equivalents_requests=equivalents_requests
        )
    except Exception as e:
        # Handle exceptions, e.g., log the error
        print(f"Error fetching equivalents requests: {str(e)}")
        return render_template("equivalents_requests.html", equivalents_requests=[])


@main.route("/update_equivalent_request", methods=["POST"])
@login_required
def update_equivalent_request():
    try:
        request_id = request.form.get("request_id")
        action = request.form.get("action")  # 'accept' or 'reject'
        print(request_id)
        equivalent_request = EquivalentRequest.query.get(request_id)

        if action == "accept":
            equivalent_request.eqr_accepted = 1
        elif action == "reject":
            equivalent_request.eqr_accepted = -1

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        # Handle exceptions, e.g., log the error
        print(f"Error updating equivalent request: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@main.route("/equivalents/add", methods=["POST"])
@login_required
def add_equivalent():
    try:
        # Get data from the request
        name = request.form.get("name")
        coins = request.form.get("coins")
        picture = request.files.get("picture")

        # Check if the name field is empty
        if not name or not coins or not picture:
            return jsonify({"status": "warning", "message": "All fields are required"})

        # Check if the name has at least 2 characters
        if len(name) < 2:
            return jsonify(
                {
                    "status": "warning",
                    "message": "Name must have at least two characters.",
                }
            )

        # Convert coins to int and check if it is at least 1
        try:
            coins = int(coins)
            if coins < 1:
                return jsonify(
                    {"status": "warning", "message": "Coins must be at least 1."}
                )
            if coins > 999:
                return jsonify(
                    {
                        "status": "warning",
                        "message": "Coins must not be greater than 999",
                    }
                )
        except ValueError:
            return jsonify(
                {"status": "warning", "message": "Coins must be a valid integer."}
            )

        # Check if the picture is a valid image and of correct format
        if not (
            picture
            and (picture.filename.endswith(".jpg") or picture.filename.endswith(".png"))
        ):
            return jsonify(
                {"status": "warning", "message": "Picture must be a JPG or PNG image."}
            )

        # Open the image file to check dimensions
        try:
            image = Image.open(picture)
            if image.format not in ["JPEG", "PNG", "JPG", "jpg", "jpeg", "png"]:
                return jsonify(
                    {
                        "status": "warning",
                        "message": "Image must be in JPG or PNG format.",
                    }
                )
            width, height = image.size
            if width != height:
                return jsonify(
                    {"status": "warning", "message": "Image must be square."}
                )
            if width > 500 or height > 500:
                return jsonify(
                    {
                        "status": "warning",
                        "message": "Image dimensions must not exceed 500x500 pixels.",
                    }
                )
        except Exception as e:
            return jsonify({"status": "warning", "message": "Invalid image file."})

        # Save the picture

        # Reset stream position to beginning
        picture.stream.seek(0)
        filename = FileUtils.generate_unique_filename(picture.filename)

        # Ensure the 'equivalents' folder exists
        equivalents_folder = os.path.join(
            current_app.config["UPLOAD_FOLDER"], "equivalents"
        )
        os.makedirs(equivalents_folder, exist_ok=True)

        picture_path = os.path.join(equivalents_folder, filename)
        picture.save(picture_path)

        # Insert the guide into the database
        new_equivalent = Equivalent(
            eq_name=name, eq_coins=int(coins), eq_picture=filename
        )
        db.session.add(new_equivalent)
        db.session.commit()

        return jsonify({"status": "ok", "message": "Equivalent Added Successfully"})

    except Exception as e:
        # print(e)
        return jsonify(
            {
                "status": "error",
                "message": "Cannot add data, please try again. Error: " + str(e),
            }
        )


# ================================= ALERTS =================================
@main.route("/alerts/")
@login_required
def get_alerts_with_user_info():
    # Query alerts with user information
    alerts_with_user_info = db.session.query(Alert, AppUser).join(AppUser).all()

    # Extract the relevant information from the query results
    result = []
    for alert, user in alerts_with_user_info:
        result.append(
            {
                "a_id": alert.a_id,
                "a_category": alert.a_category,
                "a_photo": alert.a_photo,
                "a_message": alert.a_message,
                "a_latitude": alert.a_latitude,
                "a_longitude": alert.a_longitude,
                "au_full_name": user.au_full_name,
                "au_email": user.au_email,
                "au_mobile_number": user.au_mobile_number,
                "au_id": user.au_id,
            }
        )

    # Render the template with the alerts data
    title = "Alerts"
    page_title = "Alerts"
    return render_template(
        "alerts.html", alerts=result, page_title=page_title, title=title
    )


#  ================================ CITIES =================================
@main.route("/cities/")
@login_required
def cities():
    # Query to get all guides with their point counts and settings
    cities = (
        db.session.query(
            Guide.g_id,
            Guide.g_title,
            db.func.count(Zone.z_id).label("point_count"),
            Guide.g_coins_for_first_alert,
            Guide.g_coins_for_confirm_alert,
            Guide.g_coins_for_close_alert,
        )
        .outerjoin(Zone, Zone.g_id == Guide.g_id)
        .group_by(
            Guide.g_id,
            Guide.g_coins_for_first_alert,
            Guide.g_coins_for_confirm_alert,
            Guide.g_coins_for_close_alert,
        )
        .order_by(Guide.g_id.desc())
        .all()
    )

    title = "Cities"
    page_title = "Cities"
    return render_template(
        "cities.html", cities=cities, page_title=page_title, title=title
    )


@main.route("/cities/add", methods=["POST"])
@login_required
def add_city():
    try:
        # Get data from the request
        title = request.form.get("title")

        # Check if the title field is empty
        if not title:
            return jsonify({"status": "warning", "message": "Both titles are required"})

        # Check if the title has at least 3 characters
        elif len(title) < 3:
            return jsonify(
                {
                    "status": "warning",
                    "message": "Title must have at least 3 characters.",
                }
            )

        # Validation passed, insert the guide into the database
        else:
            # Insert the guide into the database

            new_guide = Guide(
                g_title=title,
                g_coins_for_first_alert=100,
                g_coins_for_confirm_alert=50,
                g_coins_for_close_alert=30,
            )
            db.session.add(new_guide)
            db.session.commit()

            return jsonify({"status": "ok", "message": "City Added Successfully"})

    except Exception as e:
        # print(e)
        return jsonify(
            {
                "status": "error",
                "message": "Cannot add data, please try again " + str(e),
            }
        )


@main.route("/cities/edit", methods=["POST"])
@login_required
def edit_city():
    data = request.form
    title = data.get("gtitle")
    gid = data.get("gid")

    # Check if the title field is empty
    if not title:
        return jsonify(status="warning", message="Both titles are required")

    # Check if the title has at least 3 characters
    elif len(title) < 3:
        return jsonify(
            status="warning", message="Title must have at least 3 characters."
        )

    # Validation passed, update the guide in the database
    else:
        try:
            # Update the guide in the database
            guide = Guide.query.filter_by(g_id=gid).one()
            guide.g_title = title

            db.session.commit()

            return jsonify(status="ok", message="City Edited Successfully")

        except NoResultFound:
            return jsonify(status="error", message="City not found")

        except Exception as e:
            # Log the error for debugging
            print(e)
            db.session.rollback()

            return jsonify(status="error", message="Cannot edit data, please try again")


@main.route("/cities/delete", methods=["POST"])
@login_required
def delete_city():
    gid = request.form.get("gid")

    # Check if gid is provided
    if not gid:
        return jsonify(status="warning", message="Guide ID is required for deletion")

    try:
        # Find the guide by gid
        guide = Guide.query.filter_by(g_id=gid).one()

        # Delete the guide from the database
        db.session.delete(guide)
        db.session.commit()

        return jsonify(status="ok", message="City Deleted Successfully")

    except NoResultFound:
        return jsonify(status="error", message="City not found")

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status="error", message="Cannot delete data, please try again")


# ================================ CITY SETTINGS =========================
@main.route("/update_city_settings", methods=["POST"])
@login_required
def update_city_settings():
    try:
        # Get data from the request
        first_alert = int(request.form.get("first_alert"))
        confirm_alert = int(request.form.get("confirm_alert"))
        final_alert = int(request.form.get("final_alert"))
        g_id = int(request.form.get("gid"))

        # Check if the title field is empty
        if not first_alert or not confirm_alert or not final_alert:
            return jsonify({"status": "warning", "message": "All fields are required"})

        # Check if the title has at least 3 characters
        elif first_alert < 0 or confirm_alert < 0 or final_alert < 0:
            return jsonify(
                {"status": "warning", "message": "Coins values must be greater than 0"}
            )

        # Validation passed, update the guide settings in the database
        else:
            # Find the existing guide based on g_id
            existing_guide = Guide.query.get(g_id)

            if existing_guide:
                # Update the guide settings
                existing_guide.g_coins_for_first_alert = first_alert
                existing_guide.g_coins_for_confirm_alert = confirm_alert
                existing_guide.g_coins_for_close_alert = final_alert
                db.session.commit()
                return jsonify(
                    {"status": "ok", "message": "Settings Updated Successfully"}
                )
            else:
                return jsonify({"status": "error", "message": "Guide not found"})

    except Exception as e:
        print(e)
        return jsonify(
            {"status": "error", "message": "Cannot add data, please try again"}
        )


#  ================================ USERS =================================
@main.route("/users/")
@login_required
def users():

    # Query to get all users
    users = User.query.all()

    title = "Users"
    page_title = "Users"
    return render_template(
        "users.html", users=users, page_title=page_title, title=title
    )


@main.route("/users/add", methods=["POST"])
@login_required
def add_user():

    username = request.form.get("username")
    password = request.form.get("password")

    # Check if the fields are present
    if not username or not password:
        return jsonify({"status": "warning", "message": "All fields are required"})

    # Check length requirements
    if len(username) < 5:
        return jsonify(
            {
                "status": "warning",
                "message": "Username cannot be less than 5 characters.",
            }
        )

    if len(password) < 6:
        return jsonify(
            {
                "status": "warning",
                "message": "Password cannot be less than 6 characters.",
            }
        )

    # Hash the password
    hashed_password = hashlib.sha1(password.encode()).hexdigest()

    # Check if the username already exists
    existing_user = User.query.filter_by(u_username=username).first()

    if existing_user:
        return jsonify(
            {
                "status": "warning",
                "message": "Username already exists. Choose a different username.",
            }
        )

    # Create a new user
    new_user = User(u_username=username, u_password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "ok", "message": "User Added Successfully"})
    except Exception as e:
        return (
            jsonify(
                {"status": "error", "message": "Cannot add data, please try again"}
            ),
            500,
        )


#  ========================== ZONES  ===========================
@main.route("/zonesandroads/")
@login_required
def zones_and_roads():

    # Query all zones
    zones = Zone.query.join(Guide).order_by(Guide.g_id.desc()).all()

    # Query all roads
    roads = Road.query.join(Guide).order_by(Guide.g_id.desc()).all()

    cities = Guide.query.all()

    title = "Zones & Roads"
    page_title = "Zones & Roads"
    return render_template(
        "zones_and_roads.html",
        zones=zones,
        roads=roads,
        cities=cities,
        page_title=page_title,
        title=title,
    )


@main.route("/show_zone_points", methods=["POST"])
def show_zone_points():
    zid = request.form.get("zid")
    zone_points = ZonePoint.query.filter_by(z_id=zid).all()

    if zone_points:
        # Convert the SQLAlchemy objects to a list of dictionaries
        result = [
            {
                "zp_id": point.zp_id,
                "zp_lat": point.zp_lat,
                "zp_lng": point.zp_lng,
                "z_id": point.z_id,
            }
            for point in zone_points
        ]
        return jsonify({"status": "ok", "data": result})

    else:
        return jsonify({"status": "error", "message": "Points not found"})


@main.route("/add_zone", methods=["POST"])
@login_required
def add_zone():
    # Get data from the request
    gid = request.form.get("guide")
    zname = request.form.get("zname")

    # Check if gid is present and valid
    if gid is None or gid == "0":
        return jsonify({"status": "error", "message": "Please select a city"})

    # Check if zname is present and has at least 3 characters
    if zname is None or len(zname) < 3:
        return jsonify(
            {"status": "error", "message": "Zone name must have at least 3 characters"}
        )

    # Check if the file is present in the request
    if "zone_file" not in request.files:
        return jsonify({"status": "error", "message": "No file part"})

    # Get the uploaded file
    zone_file = request.files["zone_file"]

    # Check if the file is empty
    if zone_file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"})

    # Check if the file is allowed
    allowed_extensions = {"json"}
    if (
        "." not in zone_file.filename
        or zone_file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions
    ):
        return jsonify({"status": "error", "message": "Invalid file type"})

    # Set up the path for file upload
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save the uploaded file
    file_path = os.path.join(upload_folder, zone_file.filename)
    zone_file.save(file_path)

    # Check if the file already exists
    if Zone.query.filter_by(z_name=zname).first():
        os.remove(file_path)  # Delete the uploaded file
        return jsonify({"status": "error", "message": "Zone file already exists"})

    # Create a new zone
    new_zone = Zone(z_name=zname, g_id=gid)
    db.session.add(new_zone)
    db.session.commit()

    # Parse the JSON data from the uploaded file
    with open(file_path, "r") as json_file:
        try:
            json_data = json.load(json_file)
            coordinates = json_data["coordinates"]
            zone_id = new_zone.z_id

            # Initialize an array to store the data to be inserted into zone_points table
            zone_points_data = []

            for coord in coordinates:
                zp_lat = coord[1]
                zp_lng = coord[0]

                # Add the data to the array for insertion
                zone_points_data.append(
                    {
                        "zp_lat": zp_lat,
                        "zp_lng": zp_lng,
                        "z_id": zone_id,
                    }
                )

            # Insert the data into the zone_points table
            db.session.bulk_insert_mappings(ZonePoint, zone_points_data)
            db.session.commit()

            # Calculate centroid
            polygon = Polygon(coordinates)
            centroid = polygon.centroid
            # Save centroid in database
            new_zone.z_centroid_lat = centroid.y
            new_zone.z_centroid_lng = centroid.x
            db.session.commit()

            return jsonify(
                {"status": "ok", "message": "Zone and Zone Points Added Successfully"}
            )

        except json.JSONDecodeError:
            # Delete the zone if JSON decoding fails
            db.session.delete(new_zone)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({"status": "error", "message": "Invalid JSON file"})
        except Exception as e:
            # Delete the zone if an exception occurs
            db.session.delete(new_zone)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({"status": "error", "message": str(e)}), 500


@main.route("/delete_zone", methods=["POST"])
@login_required
def delete_zone():
    zid = request.form.get("zid")

    # Check if gid is provided
    if not zid:
        return jsonify(status="warning", message="Zone ID is required for deletion")

    try:
        # Find the guide by gid
        zone = Zone.query.filter_by(z_id=zid).one()

        # Delete the guide from the database
        db.session.delete(zone)
        db.session.commit()

        return jsonify(status="ok", message="Zone Deleted Successfully")

    except NoResultFound:
        return jsonify(status="error", message="Zone not found")

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status="error", message="Cannot delete data, please try again")


# ============================ ROADS =======================
@main.route("/show_road_points", methods=["POST"])
def show_road_points():
    rid = request.form.get("rid")
    road_points = RoadPoint.query.filter_by(r_id=rid).all()

    if road_points:
        # Convert the SQLAlchemy objects to a list of dictionaries
        result = [
            {
                "rp_id": point.rp_id,
                "rp_lat": point.rp_lat,
                "rp_lng": point.rp_lng,
                "r_id": point.r_id,
            }
            for point in road_points
        ]
        return jsonify({"status": "ok", "data": result})

    else:
        return jsonify({"status": "error", "message": "Points not found"})


@main.route("/add_road", methods=["POST"])
@login_required
def add_road():
    # Get data from the request
    gid = request.form.get("guide")
    rname = request.form.get("rname")

    # Check if gid is present and valid
    if gid is None or gid == "0":
        return jsonify({"status": "error", "message": "Please select a city"})

    # Check if zname is present and has at least 3 characters
    if rname is None or len(rname) < 3:
        return jsonify(
            {"status": "error", "message": "Road name must have at least 3 characters"}
        )

    # Check if the file is present in the request
    if "road_file" not in request.files:
        return jsonify({"status": "error", "message": "No file part"})

    # Get the uploaded file
    road_file = request.files["road_file"]

    # Check if the file is empty
    if road_file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"})

    # Check if the file is allowed
    allowed_extensions = {"json"}
    if (
        "." not in road_file.filename
        or road_file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions
    ):
        return jsonify({"status": "error", "message": "Invalid file type"})

    # Set up the path for file upload
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    # Save the uploaded file
    file_path = os.path.join(upload_folder, road_file.filename)
    road_file.save(file_path)

    # Check if the file already exists
    if Road.query.filter_by(r_name=rname).first():
        os.remove(file_path)  # Delete the uploaded file
        return jsonify({"status": "error", "message": "Road file already exists"})

    # Create a new road
    new_road = Road(r_name=rname, g_id=gid)
    db.session.add(new_road)
    db.session.commit()

    # Parse the JSON data from the uploaded file
    with open(file_path, "r") as json_file:
        try:
            json_data = json.load(json_file)
            coordinates = json_data["coordinates"]
            road_id = new_road.r_id

            # Initialize an array to store the data to be inserted into zone_points table
            road_points_data = []

            for coord in coordinates:
                rp_lat = coord[1]
                rp_lng = coord[0]

                # Add the data to the array for insertion
                road_points_data.append(
                    {
                        "rp_lat": rp_lat,
                        "rp_lng": rp_lng,
                        "r_id": road_id,
                    }
                )

            # Insert the data into the zone_points table
            db.session.bulk_insert_mappings(RoadPoint, road_points_data)
            db.session.commit()

            return jsonify(
                {"status": "ok", "message": "Road and Road Points Added Successfully"}
            )

        except json.JSONDecodeError:
            # Delete the zone if JSON decoding fails
            db.session.delete(new_road)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({"status": "error", "message": "Invalid JSON file"})
        except Exception as e:
            # Delete the zone if an exception occurs
            db.session.delete(new_road)
            db.session.commit()
            os.remove(file_path)  # Delete the uploaded file
            return jsonify({"status": "error", "message": str(e)})


@main.route("/delete_road", methods=["POST"])
@login_required
def delete_road():
    rid = request.form.get("rid")

    # Check if gid is provided
    if not rid:
        return jsonify(status="warning", message="Road ID is required for deletion")

    try:
        # Find the guide by gid
        road = Road.query.filter_by(r_id=rid).one()

        # Delete the guide from the database
        db.session.delete(road)
        db.session.commit()

        return jsonify(status="ok", message="Road Deleted Successfully")

    except NoResultFound:
        return jsonify(status="error", message="Road not found")

    except Exception as e:
        # Log the error for debugging
        print(e)
        db.session.rollback()

        return jsonify(status="error", message="Cannot delete data, please try again")
