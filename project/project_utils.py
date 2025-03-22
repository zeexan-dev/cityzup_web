import random
import string
import time
from . import db
from .models import (
    AlertClose,
    AlertConfirm,
    Guide,
    MissionPaparazziCompleted,
    Zone,
    Road,
    ZonePoint,
    RoadPoint,
    AppUser,
    Alert,
    Equivalent,
    EquivalentRequest,
    MissionActionsCompleted,
)


class FileUtils:
    @staticmethod
    def generate_unique_filename(filename):
        """
        Generate a unique filename using the current timestamp and a random string.

        :param filename: Original filename
        :return: Unique filename
        """
        # Generate a random string of fixed length
        random_str = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        # Extract the file extension
        ext = filename.rsplit(".", 1)[1].lower()
        # Create a unique filename using timestamp and random string
        unique_filename = f"{int(time.time())}_{random_str}.{ext}"
        return unique_filename


class PointsUtils:
    @staticmethod
    def calculate_user_points(user_id):
        """
        Calculate the total points for a user based on their alerts, confirmations, and closures.

        :param user_id: ID of the user
        :return: Total user points
        """
        points_for_alerts = 0
        points_for_confirmation = 0
        points_for_close = 0
        points_deducted = 0
        points_for_mission_action_completed = 0

        # Fetch all alerts for the user
        alerts = Alert.query.filter_by(au_id=user_id).all()
        for alert in alerts:
            # Add points based on the alert's points
            points_for_alerts += alert.a_points

        # Fetch all confirm alerts for the user
        confirmations = AlertConfirm.query.filter_by(au_id=user_id).all()
        for confirm in confirmations:
            # Add points based on the alert confirmation's points
            points_for_confirmation += confirm.acn_points

        # Fetch all close alerts for the user
        closures = AlertClose.query.filter_by(au_id=user_id).all()
        for close in closures:
            # Add points based on the alert closure's points
            points_for_close += close.acl_points

        # Fetch all mission action points for the user
        mission_action_points = (
            db.session.query(db.func.sum(MissionActionsCompleted.total_coins))
            .filter_by(au_id=user_id)
            .scalar()
            or 0
        )

        # Fetch all mission paparazzi points (only accepted ones)
        mission_paparazzi_points = (
            db.session.query(db.func.sum(MissionPaparazziCompleted.mpc_coins))
            .filter_by(au_id=user_id, mpc_status=1)
            .scalar()
            or 0
        )

        # Fetch all equivalent requests for the user where eqr_accepted is 0 or 1
        # 0 pending
        # 1 accepted
        equivalent_requests = (
            EquivalentRequest.query.filter_by(au_id=user_id)
            .filter(EquivalentRequest.eqr_accepted.in_([0, 1]))
            .all()
        )
        for request in equivalent_requests:
            # Deduct points based on the equivalent request's number of coins
            points_deducted += request.eqr_number_of_coins

        total_user_points = (
            points_for_alerts
            + points_for_confirmation
            + points_for_close
            + mission_action_points
            + mission_paparazzi_points
            - points_deducted
        )
        return total_user_points
