from shared import BLOCKLIST
from flask import Flask, jsonify
import endpoints
from flask import Flask, jsonify, request, render_template
from flask_jwt_extended import JWTManager
import db_handler as dbHandler
from dotenv import load_dotenv
from datetime import timedelta
from flask_cors import CORS
import os

# BEFORE COMING HERE REMEMBER THIS NOTE TO SELF YOU MADE:
#
# If you are running this on a code space, make sure the port is visible to the public (API).
# The frontend does not need to be public

app = Flask(__name__, template_folder='../../templates',
            static_folder='../../static')
CORS(app, supports_credentials=True)
jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return jti in BLOCKLIST


app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

endpoints.register_routes(app)


@app.route("/api/ping")
def ping():
    return jsonify("Pong!")


@app.route("/", methods=["GET"])
def index():
    return render_template("lost_dumbass.html")


if __name__ == "__main__":
    load_dotenv()
    dbHandler.prepare(app.logger)

    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(
            f"  {rule.rule} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")
    print()

    app.run(debug=True, host="0.0.0.0", port=5000)
