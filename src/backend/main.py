import endpoints
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
import db_handler as dbHandler
from dotenv import load_dotenv
from datetime import timedelta
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
jwt = JWTManager(app)

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

if __name__ == "__main__":
    load_dotenv()
    dbHandler.prepare(app.logger)
    
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")
    print()
    
    app.run(debug=True, host="0.0.0.0", port=5000)
