from flask import Flask
import sqlite3
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import db_handler as dbHandler
from shared import DB_PATH


def __register_routes(app: Flask):
    """Registers all the routes that are related to devlog manipulation"""

    @app.route("/api/projects", methods=["GET", "POST"])
    @jwt_required()
    def projects():
        """Project management
        
        GET: Lists all projects for the authenticated user.
        POST: Creates a new project.

        For POST, requires:
        - project_name: string (required)
        - repository_url: string (optional)
        - description: string (optional)

        Requires a JWT token
        """
        user_id = get_jwt_identity()

        if request.method == "GET":
            try:
                projects = dbHandler.fetch_projects(user_id)
                return jsonify(projects), 200
            except Exception as e:
                app.logger.error(f"Error fetching projects: {e}")
                return jsonify({"message": "Failed to fetch projects", "cause": str(e)}), 500
        
        elif request.method == "POST":
            try:
                data = request.form
                project_name = data.get("project_name")
                
                if not project_name:
                    return jsonify({"message": "project_name is required"}), 400
                
                repository_url = data.get("repository_url")
                description = data.get("description")
                
                project_id = dbHandler.create_project(
                    project_name=project_name,
                    user_id=user_id,
                    repository_url=repository_url,
                    description=description
                )
                
                return jsonify({
                    "message": "Project created successfully",
                    "project_id": project_id,
                    "project_name": project_name
                }), 201
            except Exception as e:
                app.logger.error(f"Error creating project: {e}")
                return jsonify({"message": "Failed to create project", "cause": str(e)}), 400

    @app.route("/api/<int:project_id>/logs", methods=["GET", "POST"])
    @jwt_required()
    def logs(project_id):
        """
        GET: Lists all the log entries for the authenticated user in a specific project.
        POST: Adds a log entry to a specific project
        
        POST Body fields:
        - start_time: datetime in Julian time or ISO format (when work started)
        - end_time: datetime in Julian time or ISO format (when work ended)
        - time_worked_minutes: integer (total minutes worked on this task)
        - developer_notes: the notes in markdown
        - log_timestamp: datetime (defaults to current timestamp if not provided) (optional)
        - related_commits: array of commits (e.g., ["abc123", "def456"]) (optional)

        Requires a JWT token
        """
        user_id = get_jwt_identity()
        
        if request.method == "POST":
            try:
                data = dict(request.form)
                data['project_id'] = project_id
                log_id = dbHandler.add_log(data, user_id)
                return jsonify({"message": "Log successfully added", "log_id": log_id}), 201
            except Exception as e:
                app.logger.error(f"Error occurred: {e}")
                return jsonify({"message": "Log failed to be added", "cause": str(e)}), 400
        else:
            try:
                logs = dbHandler.fetch_devlogs(user_id=user_id, project_id=project_id)
                return jsonify(logs), 200
            except Exception as e:
                app.logger.error(f"Error fetching logs: {e}")
                return jsonify({"message": "Failed to fetch logs", "cause": str(e)}), 500

    @app.route("/api/<int:project_id>/logs/<int:log_id>", methods=["GET"])
    @jwt_required()
    def fetch_log(project_id, log_id):
        """Fetches a specific log entry from a project"""
        user_id = get_jwt_identity()

        try:
            log = dbHandler.fetch_one_devlog(log_id, user_id)
            if log is None or log.get('project_id') != project_id:
                return jsonify({"message": f"Log [{log_id}] not found in project [{project_id}]"}), 404
            return jsonify(log), 200
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({"message": f"Failed to fetch log {log_id}", "cause": str(e)}), 500

    @app.route("/api/<int:project_id>/logs/<int:log_id>", methods=["PUT"])
    @jwt_required()
    def edit_log(project_id, log_id):
        """Allows you to edit a specific log in a project. 

        Items available to change:
        - start_time
        - end_time
        - time_worked_minutes 
        - developer_notes
        - related_commits (array of commit references)

        Requires a JWT token for authentication
        """
        user_id = get_jwt_identity()

        try:
            data = request.form

            existing_log = dbHandler.fetch_one_devlog(log_id, user_id)
            if not existing_log or existing_log.get('project_id') != project_id:
                return jsonify({"message": "Log not found in this project"}), 404

            row_count = dbHandler.update_log(log_id, data, user_id)

            if row_count == 0:
                return jsonify({"message": "Log not found or no changes made"}), 404

            return jsonify({
                "message": "Log successfully updated",
                "log_id": log_id
            }), 200
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({
                "message": "Log failed to be updated",
                "cause": str(e)
            }), 500

    @app.route("/api/<int:project_id>/logs/<int:log_id>", methods=["DELETE"])
    @jwt_required()
    def remove_log(project_id, log_id):
        """Removes the log entry from a project. User can only delete their own logs.

        Requires a JWT token
        """
        user_id = get_jwt_identity()

        try:
            existing_log = dbHandler.fetch_one_devlog(log_id, user_id)
            if not existing_log or existing_log.get('project_id') != project_id:
                return jsonify({"message": "Log not found in this project"}), 404

            row_count = dbHandler.remove_log(log_id, user_id)

            if row_count == 0:
                return jsonify({"message": "Log not found or not owned by user"}), 404

            return jsonify({"message": "Log successfully deleted", "log_id": log_id}), 200
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({"message": "Log failed to be deleted", "cause": str(e)}), 500
