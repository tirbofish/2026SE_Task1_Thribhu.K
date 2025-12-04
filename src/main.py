import sqlite3
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import user_management as dbHandler
import bcrypt
from dotenv import load_dotenv
from datetime import timedelta

app = Flask(__name__)
jwt = JWTManager(app)

app.config['SECRET_KEY'] = 'your_strong_secret_key'
app.config["JWT_SECRET_KEY"] = 'your_jwt_secret_key'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

@app.route("/api/ping")
def ping():
    return jsonify("Pong!")

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
        
        conn = sqlite3.connect("databaseFiles/mono.db")
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

@app.route("/api/register", methods=["POST"])
def register():
    """Registers a user and adds to the `users` database. 
    
    Requires the following body:
    - email: str
    - password: str
    - name: str
    """
    data = request.form
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    
    if not email or not password or not name:
        return jsonify({"message": "Name, email, and password are required"}), 400
    
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    try:
        conn = sqlite3.connect("databaseFiles/mono.db")
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash.decode())
        )
        
        user_id = cur.lastrowid
        
        conn.commit()
        conn.close()
        
        access_token = create_access_token(
            identity=str(user_id),
            additional_claims={'email': email, 'name': name}
        )
        
        response = jsonify({
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "name": name,
                "email": email
            }
        })

        response.set_cookie(
            'access_token_cookie',
            access_token,
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=86400
        )
        
        return response, 201
        
    except sqlite3.IntegrityError:
        app.logger.error("Error: User already exists")
        return jsonify({"message": "User already exists"}), 400
    except Exception as e:
        app.logger.error(f"Error while creating user: {e}")
        return jsonify({"message": "Error while creating user", "cause": str(e)}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.form
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400
    
    try:
        conn = sqlite3.connect("databaseFiles/mono.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute(
            "SELECT id, password_hash, name FROM users WHERE email = ?",
            (email,)
        )
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        app.logger.error(f"Error while attempting to login: {e}")
        return jsonify({'message': 'Error while attempting to login', 'cause': str(e)})
    
    if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    token = create_access_token(
        identity=str(user['id']),
        additional_claims={'email': email, 'name': user['name']}
    )
    
    response = jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': email
        }
    })
    
    response.set_cookie(
        'access_token_cookie',
        token,
        httponly=True,
        secure=False,
        samesite='Lax',
        max_age=86400
    )
    
    return response, 200

if __name__ == "__main__":
    load_dotenv()
    dbHandler.prepare(app.logger)
    app.run(debug=True, host="0.0.0.0", port=5000)
