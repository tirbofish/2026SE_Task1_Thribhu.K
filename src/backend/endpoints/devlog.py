from flask import Flask
import sqlite3
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import db_handler as dbHandler
from shared import DB_PATH


def __register_routes(app: Flask):
    """Registers all the routes that are related to devlog manipulation"""

    @app.route("/api/list", methods=["GET"])
    @jwt_required()
    def list():
        """Lists all the logs that have been created.

        Requires a JWT token
        """

        user_id = get_jwt_identity()

        return jsonify(dbHandler.fetch_devlogs())

    @app.route("/api/add", methods=["POST"])
    @jwt_required()
    def add():
        """Adds a log to the list

        JSON submitted through body must include the following
        - time_user_logged in Unix Epoch
        - name of log
        - the description of the log
        The id of the user is provided with the JWT token. 

        Requires a JWT token
        """

        user_id = get_jwt_identity()

        try:
            data = request.form
            log_id = dbHandler.add_log(data, user_id)
            return jsonify({"message": "Log successfully added", "id": log_id}), 201
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({"message": "Log failed to be added", "cause": str(e)}), 400

    @app.route("/api/remove/<int:log_id>", methods=["DELETE"])
    @jwt_required()
    def remove(log_id):
        """Removes the log in the database with the api.

        Requires a JWT token
        """

        user_id = get_jwt_identity()

        try:
            row_count = dbHandler.remove_log(log_id)

            if row_count == 0:
                return jsonify({"message": "Log not found"}), 404

            return jsonify({"message": "Log successfully deleted", "id": log_id}), 200
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({"message": "Log failed to be deleted", "cause": str(e)}), 500

    @app.route("/api/fetch/<int:log_id>", methods=["GET"])
    @jwt_required()
    def fetch(log_id):
        """Fetches the devlog from the specified id"""

        try:
            log = dbHandler.fetch_one_devlog(log_id)
            if log is None:
                return jsonify({"message": f"Log [{log_id}] not found"}), 404
            return jsonify(log)
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({"message": f"Failed to fetch log {str(log_id)}", "cause": str(e)}), 500

    @app.route("/api/edit/<int:log_id>", methods=["PUT"])
    @jwt_required()
    def edit(log_id):
        """Allows you to edit a specific log. 

        Items available to change:
        - time_user_logged
        - name
        - description

        The API will not allow you to change the non-listed items. 

        Requires a JWT token for authentication
        """

        user_id = get_jwt_identity()

        try:
            data = request.form

            existing_log = dbHandler.fetch_one_devlog(log_id)
            if existing_log is None:
                return jsonify({"message": f"Log [{log_id}] not found"}), 404

            update_fields = []
            params = []

            if 'time_user_logged' in data:
                update_fields.append("time_user_logged = ?")
                params.append(data['time_user_logged'])

            if 'name' in data:
                update_fields.append("name = ?")
                params.append(data['name'])

            if 'description' in data:
                update_fields.append("description = ?")
                params.append(data['description'])

            if not update_fields:
                return jsonify({"message": "No fields provided to update"}), 400

            params.append(log_id)

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            query = f"UPDATE devlogs SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(query, params)

            conn.commit()
            row_count = cur.rowcount
            conn.close()

            if row_count == 0:
                return jsonify({"message": "Log not found or no changes made"}), 404

            return jsonify({
                "message": "Log successfully updated",
                "id": log_id
            }), 200
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({
                "message": "Log failed to be updated",
                "cause": str(e)
            }), 500
