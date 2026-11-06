from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.device import Device
from src.models.reading import Reading
from datetime import datetime

api_bp = Blueprint("api", __name__)

@api_bp.route("/v1/readings", methods=["POST"])
def post_reading():
    data = request.get_json()

    device_code = data.get("device_code")
    mac_address = data.get("mac_address")
    timestamp_str = data.get("timestamp")
    ticks = data.get("ticks")
    mm_per_tick = data.get("mm_per_tick")
    battery_mv = data.get("battery_mv")

    if not all([device_code, mac_address, timestamp_str, ticks is not None]):
        return jsonify({"error": "Missing required fields"}), 422

    device = Device.query.filter_by(device_code=device_code, mac_address=mac_address).first()
    if not device:
        return jsonify({"error": "Invalid device_code or mac_address"}), 401

    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        return jsonify({"error": "Invalid timestamp format"}), 422

    new_reading = Reading(
        device_id=device.id,
        timestamp=timestamp,
        ticks=ticks,
        mm_per_tick=mm_per_tick if mm_per_tick is not None else device.mm_per_tick_default,
        battery_mv=battery_mv
    )

    db.session.add(new_reading)
    db.session.commit()

    return jsonify({"status": "ok", "stored": True, "reading_id": new_reading.id}), 200

@api_bp.route("/healthz", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "PluvIFFAR API is healthy"}), 200


