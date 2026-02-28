from flask import request, jsonify

from flask_app.tasks import save_to_db_async

def regiter_routes(app):
    
    @app.post("/api/telemetry")
    def recieve_data():
        data = request.json

        save_to_db_async.delay(data["sensor_id"], data["temperature"])

        return jsonify({"status": "queued", "message": "Data recieving"}), 202