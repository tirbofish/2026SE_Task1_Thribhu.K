import os
from flask import Flask, render_template, redirect, url_for, request, session, make_response
import requests as req

DEFAULT_API_ENDPOINT = "http://127.0.0.1:5000"
API_TIMEOUT_SECONDS = 8
ACCESS_COOKIE_NAME = "access_token_cookie"

app = Flask(
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)

app.secret_key = os.getenv("FRONTEND_SECRET_KEY", "dev-frontend-secret")


def _clean_endpoint(raw_endpoint: str | None) -> str:
    endpoint = (raw_endpoint or DEFAULT_API_ENDPOINT).strip()
    return endpoint[:-1] if endpoint.endswith('/') else endpoint


def _build_error_message(api_response):
    try:
        payload = api_response.json()
        if isinstance(payload, dict) and payload.get("message"):
            return payload["message"]
    except Exception:
        pass
    return f"Request failed with status {api_response.status_code}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)

    if request.method == "GET":
        redirect_message = request.args.get("message")
        redirect_message_type = request.args.get("message_type", "info")
        
        return render_template(
            "login.html", 
            api_endpoint=api_endpoint,
            redirect_message=redirect_message,
            redirect_message_type=redirect_message_type
        )

    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    api_endpoint = _clean_endpoint(request.form.get("apiEndpoint"))

    if not email or not password:
        return render_template(
            "login.html",
            message="Email and password are required",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    try:
        response = req.post(
            f"{api_endpoint}/api/login",
            data={"email": email, "password": password},
            timeout=API_TIMEOUT_SECONDS
        )
    except req.RequestException as exc:
        return render_template(
            "login.html",
            message=f"Unable to reach API: {exc}",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    if response.status_code != 200:
        return render_template(
            "login.html",
            message=_build_error_message(response),
            message_type="danger",
            api_endpoint=api_endpoint
        )

    token = response.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return render_template(
            "login.html",
            message="Login succeeded but token cookie missing in response",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    session["api_endpoint"] = api_endpoint

    redirect_response = make_response(
        redirect(url_for("dashboard")))
    redirect_response.set_cookie(
        ACCESS_COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=86400
    )
    return redirect_response


@app.route("/register", methods=["GET", "POST"])
def register():
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)

    if request.method == "GET":
        return render_template("register.html", api_endpoint=api_endpoint)

    name = (request.form.get("name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    api_endpoint = _clean_endpoint(request.form.get("apiEndpoint"))

    missing = [
        label for label, value in (
            ("name", name),
            ("username", username),
            ("email", email),
            ("password", password)
        ) if not value
    ]
    if missing:
        return render_template(
            "register.html",
            message=f"Missing required fields: {', '.join(missing)}",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    try:
        response = req.post(
            f"{api_endpoint}/api/register",
            data={
                "name": name,
                "username": username,
                "email": email,
                "password": password
            },
            timeout=API_TIMEOUT_SECONDS
        )
    except req.RequestException as exc:
        return render_template(
            "register.html",
            message=f"Unable to reach API: {exc}",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    if response.status_code not in (200, 201):
        return render_template(
            "register.html",
            message=_build_error_message(response),
            message_type="danger",
            api_endpoint=api_endpoint
        )

    token = response.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return render_template(
            "register.html",
            message="Registration succeeded but token cookie missing in response",
            message_type="danger",
            api_endpoint=api_endpoint
        )

    session["api_endpoint"] = api_endpoint

    redirect_response = make_response(
        redirect(url_for("dashboard")))
    redirect_response.set_cookie(
        ACCESS_COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=86400
    )
    return redirect_response

@app.route("/dashboard", methods=["GET"])
def dashboard():
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        return redirect(url_for("login"))

    try:
        response = req.get(
            f"{api_endpoint}/api/whoami",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
    except req.RequestException as exc:
        return render_template(
            "dashboard.html",
            message=f"Unable to reach API: {exc}",
            message_type="danger"
        )

    if response.status_code != 200:
        return redirect(url_for("login"))

    user_data = response.json()
    return render_template("dashboard.html", user=user_data)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=4200)
