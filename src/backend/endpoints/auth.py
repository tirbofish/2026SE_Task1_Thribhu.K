from flask import Flask
import sqlite3
from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import bcrypt
import pyotp
import qrcode
import io
import base64
from shared import BLOCKLIST, DB_PATH


def __register_routes(app: Flask):
    """Registers the routes that are related to authentication"""

    @app.route("/api/register", methods=["POST"])
    def register():
        """Registers a user and adds to the `users` database. 

        Requires the following body:
        - email: str
        - username: str
        - password: str
        """
        data = request.form
        email = data.get("email")
        password = data.get("password")
        username = data.get("username")

        if not email or not password or not username:
            return jsonify({"message": "Email, username, and password are required"}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            cur.execute("SELECT user_id FROM users WHERE email = ? OR username = ?", (email, username))
            existing_user = cur.fetchone()
            
            if existing_user:
                return jsonify({"message": "User with this email or username already exists"}), 400
                
        except Exception as e:
            app.logger.error(f"Error checking existing user: {e}")
            return jsonify({"message": "Database error", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        totp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name='LoperLog')
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO users (username, email, password_hash, totp_secret) VALUES (?, ?, ?, ?)",
                (username, email, password_hash.decode(), totp_secret)
            )

            user_id = cur.lastrowid

            conn.commit()

            return jsonify({
                "message": "User created. 2FA verification is mandatory and requird.",
                "user_id": user_id,
                "totp_secret": totp_secret,
                "provisioning_uri": provisioning_uri,
                "qr_code": f"data:image/png;base64,{qr_code_base64}"
            }), 201

        except sqlite3.IntegrityError:
            app.logger.error("Error: User already exists")
            return jsonify({"message": "User already exists", "cause": "sqlite3 integrity err"}), 400
        except Exception as e:
            app.logger.error(f"Error while creating user: {e}")
            return jsonify({"message": "Error while creating user", "cause": str(e)}), 400
        finally:
            if conn:
                conn.close()

    @app.route("/api/register/verify_2fa", methods=["POST"])
    def verify_2fa_registration():
        """Verify 2FA code during registration and complete registration"""
        data = request.form
        user_id = data.get("user_id")
        totp_code = data.get("totp_code")

        if not user_id or not totp_code:
            return jsonify({"message": "user_id and totp_code are required"}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT user_id, username, email, totp_secret FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = cur.fetchone()

            if not user:
                return jsonify({"message": "User not found"}), 404

            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({"message": "Invalid 2FA code. Please check your authenticator app and try again."}), 401

            access_token = create_access_token(
                identity=str(user['user_id']),
                additional_claims={'email': user['email'], 'username': user['username']}
            )

            response = jsonify({
                "message": "2FA verified!",
                "user": {
                    "user_id": user['user_id'],
                    "username": user['username'],
                    "email": user['email']
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

            return response, 200

        except Exception as e:
            app.logger.error(f"Error verifying 2FA: {e}")
            return jsonify({"message": "Error verifying 2FA", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.form
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT user_id, username, password_hash, totp_secret FROM users WHERE email = ?",
                (email,)
            )
            user = cur.fetchone()
        except Exception as e:
            app.logger.error(f"Error while attempting to login: {e}")
            return jsonify({'message': 'Error while attempting to login', 'cause': str(e)}), 500
        finally:
            if conn:
                conn.close()

        if not user or not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return jsonify({'message': 'Invalid email or password'}), 401

        return jsonify({
            'message': 'Password correct, please enter 2FA code.',
            'user_id': user['user_id'],
            'requires_2fa': True
        }), 200

    @app.route("/api/login/verify_2fa", methods=["POST"])
    def verify_2fa_login():
        """Verify 2FA code during login and issue token"""
        data = request.form
        user_id = data.get("user_id")
        totp_code = data.get("totp_code")

        if not user_id or not totp_code:
            return jsonify({"message": "user_id and totp_code are required"}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT user_id, username, email, totp_secret FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = cur.fetchone()

            if not user:
                return jsonify({"message": "User not found"}), 404

            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({"message": "Invalid 2FA code"}), 401

            cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()

            token = create_access_token(
                identity=str(user['user_id']),
                additional_claims={'email': user['email'], 'username': user['username']}
            )

            response = jsonify({
                'message': 'Login successful',
                'user': {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'email': user['email']
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

        except Exception as e:
            app.logger.error(f"Error verifying 2FA login: {e}")
            return jsonify({"message": "Error verifying 2FA", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/whoami", methods=["GET"])
    @jwt_required()
    def whoami():
        """Returns the user information of your own user

        Requires for you to be already authenticated
        """
        user_id = get_jwt_identity()

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT user_id, username, email FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()

            if not user:
                return jsonify({"message": "User not found"}), 404

            return jsonify({
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"]
            }), 200

        except Exception as e:
            app.logger.error(f"Error in whoami: {e}")
            return jsonify({"message": "Error fetching user info"}), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/logout", methods=["POST"])
    @jwt_required()
    def logout():
        """Logs you out by setting the users JWT token onto a blocklist, forcing the 
        user to re-login"""
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        response = jsonify({"message": "Logout successful"})
        response.delete_cookie('access_token_cookie')
        return response, 200


    @app.route("/api/account/username", methods=["PUT"])
    @jwt_required()
    def update_username():
        """Update the authenticated user's username."""
        user_id = get_jwt_identity()
        data = request.form
        new_username = (data.get("username") or "").strip()

        if not new_username:
            return jsonify({"message": "username is required"}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            if not user:
                return jsonify({"message": "User not found"}), 404

            cur.execute(
                "SELECT user_id FROM users WHERE username = ? AND user_id != ?",
                (new_username, user_id)
            )
            if cur.fetchone():
                return jsonify({"message": "Username already in use"}), 400

            cur.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (new_username, user_id)
            )
            conn.commit()
            return jsonify({"message": "Username updated", "username": new_username}), 200

        except Exception as e:
            app.logger.error(f"Error updating username: {e}")
            return jsonify({"message": "Failed to update username", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()


    @app.route("/api/account/password", methods=["PUT"])
    @jwt_required()
    def update_password():
        """Update the authenticated user's password.

        Requires:
        - current_password
        - new_password
        - totp_code
        """
        user_id = get_jwt_identity()
        data = request.form
        current_password = data.get("current_password") or ""
        new_password = data.get("new_password") or ""
        totp_code = (data.get("totp_code") or "").strip()

        if not current_password or not new_password or not totp_code:
            return jsonify({"message": "current_password, new_password, and totp_code are required"}), 400

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT user_id, password_hash, totp_secret FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = cur.fetchone()

            if not user:
                return jsonify({"message": "User not found"}), 404

            totp = pyotp.TOTP(user["totp_secret"])
            if not totp.verify(totp_code, valid_window=1):
                return jsonify({"message": "Invalid 2FA code"}), 401

            if not bcrypt.checkpw(current_password.encode(), user["password_hash"].encode()):
                return jsonify({"message": "Current password is incorrect"}), 401

            password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE user_id = ?",
                (password_hash, user_id)
            )
            conn.commit()
            return jsonify({"message": "Password updated"}), 200

        except Exception as e:
            app.logger.error(f"Error updating password: {e}")
            return jsonify({"message": "Failed to update password", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()


    @app.route("/api/account", methods=["DELETE"])
    @jwt_required()
    def delete_account():
        """Delete the authenticated user's account."""
        user_id = get_jwt_identity()

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            if cur.rowcount == 0:
                return jsonify({"message": "User not found"}), 404

            conn.commit()

            # Revoke current token + attempt to clear cookie.
            try:
                jti = get_jwt()["jti"]
                BLOCKLIST.add(jti)
            except Exception:
                pass

            response = jsonify({"message": "Account deleted"})
            response.delete_cookie('access_token_cookie')
            return response, 200

        except Exception as e:
            app.logger.error(f"Error deleting account: {e}")
            return jsonify({"message": "Failed to delete account", "cause": str(e)}), 500
        finally:
            if conn:
                conn.close()