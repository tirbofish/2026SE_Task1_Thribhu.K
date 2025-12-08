from flask import Flask
import sqlite3
from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt


def __register_routes(app: Flask):
    """Registers the routes that are related to authentication"""

    @app.route("/api/register", methods=["POST"])
    def register():
        """Registers a user and adds to the `users` database. 

        Requires the following body:
        - email: str
        - username: str
        - password: str
        - name: str
        """
        data = request.form
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        username = data.get("username")

        if not email or not password or not name:
            return jsonify({"message": "Name, email, and password are required"}), 400

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        try:
            conn = sqlite3.connect("databaseFiles/mono.db")
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO users (name, username, email, password_hash) VALUES (?, ?, ?, ?)",
                (name, username, email, password_hash.decode())
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

    @app.route("/api/whoami", methods=["GET"])
    @jwt_required()
    def whoami():
        """Returns the user information of your own user

        Requires for you to be already authenticated
        """
        user_id = get_jwt_identity()

        try:
            conn = sqlite3.connect("databaseFiles/mono.db")
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT id, name, email FROM users WHERE id = ?", (user_id,))
            user = cur.fetchone()
            conn.close()

            if not user:
                return jsonify({"message": "User not found"}), 404

            return jsonify({
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }), 200

        except Exception as e:
            app.logger.error(f"Error in whoami: {e}")
            return jsonify({"message": "Error fetching user info"}), 500
