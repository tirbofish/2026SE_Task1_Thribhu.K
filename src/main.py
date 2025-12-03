from flask import Flask, jsonify, request
import user_management as dbHandler

app = Flask(__name__)


@app.route("/api/list", methods=["GET"])
def list():
    """Lists all the logs that have been created."""

    return jsonify(dbHandler.fetch_devlogs())


@app.route("/api/add", methods=["POST"])
def add():
    """Adds a log to the list"""

    try:
        data = request.get_json()
        id = dbHandler.add_log(data)
        return jsonify({"message": "Log successfully added", "id": f"{str(id)}"}), 201
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")
        return jsonify({"message": "Log failed to be added", "cause": f"{str(e)}"}), 400


@app.route("/api/remove/<int:log_id>", methods=["DELETE"])
def remove(log_id):
    try:
        row_count = dbHandler.remove_log(log_id)

        if row_count == 0:
            return jsonify({"message": "Log not found"}), 404

        return jsonify({"message": "Log successfully deleted", "id": log_id}), 200
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")
        return jsonify({"message": "Log failed to be deleted", "cause": str(e)}), 500


if __name__ == "__main__":
    dbHandler.prepare(app.logger)
    app.run(debug=True, host="0.0.0.0", port=5000)
