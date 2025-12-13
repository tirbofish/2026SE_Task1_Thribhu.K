from exceptions import UserSkillIssueException
from flask import Flask
from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import db_handler as dbHandler

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
        GET: Lists all the log entries for a user in a specific project.
        POST: Adds a log entry to a specific project
        
        GET 
        
        i recently added support for filtering like for searches:
            - start_time_gt, start_time_gte, start_time_lt, start_time_lte
            - end_time_gt, end_time_gte, end_time_lt, end_time_lte
            - time_worked_min, time_worked_max (integers)
            - log_timestamp_after, log_timestamp_before
            - username (exact match)
            - notes_contains (partial text search in developer_notes)
            
            Example: /api/2/logs?start_time_gt=2025-12-13 10:30:00&time_worked_min=30
        
        where _gte is 'greater than or equal' or '>=' (but the character is not used)
        
        POST body fields:
        - start_time: datetime in ISO 8601 format (YYYY-MM-DD HH:MM:SS) (when work started)
        - end_time: datetime in ISO 8601 format (YYYY-MM-DD HH:MM:SS) (when work ended)
        - time_worked_minutes: integer (total minutes worked on this task)
        - developer_notes: the notes in markdown
        - log_timestamp: datetime in ISO 8601 format (defaults to current timestamp if not provided) (optional)
        - related_commits: array of commits (e.g., ["abc123", "def456"]), either in json or just a standard array (optional)

        Requires a JWT token
        """
        user_id = get_jwt_identity()
        
        if request.method == "POST":
            try:
                from datetime import datetime
                
                project = dbHandler.fetch_projects()
                project_exists = any(p['project_id'] == project_id for p in project)
                if not project_exists:
                    raise UserSkillIssueException(f"Project with ID {project_id} does not exist")
                
                data = dict(request.form)
                data['project_id'] = project_id
                
                datetime_fields = ['start_time', 'end_time', 'log_timestamp']
                for field in datetime_fields:
                    if field in data and data[field]:
                        try:
                            datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            raise UserSkillIssueException(f"Field '{field}' must be in ISO 8601 format (YYYY-MM-DD HH:MM:SS)")
                
                log_id = dbHandler.add_log(data, user_id)
                return jsonify({"message": "Log successfully added", "log_id": log_id}), 201
            except UserSkillIssueException as e:
                app.logger.error(f"User error occurred: {e}")
                return jsonify({"message": "Log failed to be added", "cause": str(e)}), 400
            except Exception as e:
                app.logger.error(f"Error occurred: {e}")
                return jsonify({"message": "Log failed to be added", "cause": str(e)}), 500
        else:
            try:
                from filters import parse_log_filters
                filters = parse_log_filters()
                logs = dbHandler.fetch_devlogs(user_id=user_id, project_id=project_id, filters=filters)
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
        except UserSkillIssueException as e:
            app.logger.error(f"Error occurred: {e}")
            return jsonify({
                "message": "Log failed to be updated",
                "cause": str(e)
            }), 400
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
