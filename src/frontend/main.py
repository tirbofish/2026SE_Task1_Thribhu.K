import os
from flask import Flask, render_template, redirect, url_for, request, session, make_response, send_file
import requests as req
import json

DEFAULT_API_ENDPOINT = "http://127.0.0.1:5000"
API_TIMEOUT_SECONDS = 8
ACCESS_COOKIE_NAME = "access_token_cookie"

app = Flask(
    __name__,
    template_folder='../../templates',
    static_folder='../../static'
)

app.secret_key = os.getenv("FRONTEND_SECRET_KEY", "dev-frontend-secret")


@app.route("/serviceWorker.js", methods=["GET"])
def service_worker():
    """Serve the service worker from the app root.

    Browsers restrict a service worker's max scope to its script directory unless
    Service-Worker-Allowed is set. Serving at '/serviceWorker.js' allows scope '/'.
    """
    static_root = os.path.abspath(app.static_folder)
    sw_path = os.path.join(static_root, "js", "serviceWorker.js")
    response = send_file(sw_path, mimetype="application/javascript", max_age=0)
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/favicon.ico", methods=["GET"])
def favicon():
    static_root = os.path.abspath(app.static_folder)
    icon_path = os.path.join(static_root, "images", "favicon.png")
    return send_file(icon_path, mimetype="image/png", max_age=86400)

@app.route("/privacy.html", methods=["GET"])
def privacy():
    return render_template("/privacy.html")

@app.template_filter('from_json')
def from_json_filter(value):
    """Parse a JSON string into a Python object"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return value


def _clean_endpoint(raw_endpoint: str | None) -> str:
    endpoint = (raw_endpoint or DEFAULT_API_ENDPOINT).strip()
    return endpoint[:-1] if endpoint.endswith('/') else endpoint


def _build_error_message(api_response):
    try:
        payload = api_response.json()
        if isinstance(payload, dict) and payload.get("message"):
            return payload["message"]
    except Exception as e:
        app.logger.error(f"Exception caught: {e}")
    return f"Request failed with status {api_response.status_code}"


@app.route("/")
def index():
    message = request.args.get("message")
    message_type = request.args.get("message_type", "info")
    return render_template("index.html", message=message, message_type=message_type)


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

def check_if_user_is_authenticated(api_endpoint, token):
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
            message="Unable to reach API",
            message_detail=str(exc),
            message_type="danger",
            projects=[]
        )

    if response.status_code != 200:
        return redirect(url_for("login"))
    else:
        return response.json()

@app.route("/dashboard", methods=["GET"])
def dashboard():
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    
    result = check_if_user_is_authenticated(api_endpoint, token)
    if not isinstance(result, dict):
        return result
    
    user_data = result
    
    projects = []
    try:
        projects_response = req.get(
            f"{api_endpoint}/api/projects",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if projects_response.status_code == 200:
            projects = projects_response.json()
    except req.RequestException as exc:
        return render_template(
            "dashboard.html",
            message="Unable to reach API",
            message_detail=str(exc),
            message_type="danger"
        )
    
    return render_template(
        "dashboard.html",
        username=user_data.get("username"),
        email=user_data.get("email"),
        user_id=user_data.get("user_id"),
        projects=projects
    )

@app.route("/projects/new", methods=["GET", "POST"])
def new_project():
    # copy from here for auth checking
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    
    result = check_if_user_is_authenticated(api_endpoint, token)
    if not isinstance(result, dict):
        return result
    
    user_data = result
    
    projects = []
    try:
        projects_response = req.get(
            f"{api_endpoint}/api/projects",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if projects_response.status_code == 200:
            projects = projects_response.json()
    except req.RequestException as exc:
        return render_template(
            "new_project.html",
            message="Unable to reach API",
            message_detail=str(exc),
            message_type="danger"
        )

    if not token:
        return redirect(url_for("login"))
    # end copy

    if request.method == "GET":
        return render_template(
            "new_project.html",
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects
        )

    project_name = (request.form.get("project_name") or "").strip()
    repository_url = (request.form.get("repository_url") or "").strip()
    description = (request.form.get("description") or "").strip()

    if not project_name:
        return render_template(
            "new_project.html",
            message="Project name is required",
            message_type="danger",
            project_name=project_name,
            repository_url=repository_url,
            description=description,
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects
        )

    try:
        response = req.post(
            f"{api_endpoint}/api/projects",
            data={
                "project_name": project_name,
                "repository_url": repository_url or None,
                "description": description or None
            },
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
    except req.RequestException as exc:
        return render_template(
            "new_project.html",
            message="Unable to reach API",
            message_detail=str(exc),
            message_type="danger"
        )

    if response.status_code not in (200, 201):
        return render_template(
            "new_project.html",
            message=_build_error_message(response),
            message_type="danger",
            project_name=project_name,
            repository_url=repository_url,
            description=description,
            
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects
        )

    try:
        result = response.json()
        project_id = result.get("project_id")
        if project_id:
            return redirect(url_for("project_info", project_id=project_id))
    except Exception as e:
        print(f"Exception as line 363 frontend/main.py: {e}")
    
    return redirect(url_for("dashboard"))

@app.route("/projects/<int:project_id>", methods=["GET", "POST"])
def project_info(project_id):
    # copy from here for auth checking
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    
    result = check_if_user_is_authenticated(api_endpoint, token)
    if not isinstance(result, dict):
        return result
    
    user_data = result
    
    projects = []
    try:
        projects_response = req.get(
            f"{api_endpoint}/api/projects",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if projects_response.status_code == 200:
            projects = projects_response.json()
    except req.RequestException:
        pass

    if not token:
        return redirect(url_for("login"))
    # end copy
    
    logs = []
    try:
        allowed_filter_keys = {
            "start_time_gt",
            "start_time_gte",
            "start_time_lt",
            "start_time_lte",
            "end_time_gt",
            "end_time_gte",
            "end_time_lt",
            "end_time_lte",
            "time_worked_min",
            "time_worked_max",
            "log_timestamp_after",
            "log_timestamp_before",
            "username",
            "notes_contains",
        }

        filters = {
            key: (request.args.get(key) or "").strip()
            for key in allowed_filter_keys
            if request.args.get(key) is not None and (request.args.get(key) or "").strip() != ""
        }

        search = (request.args.get("search") or "").strip()
        if search and "notes_contains" not in filters:
            filters["notes_contains"] = search

        after = filters.get("log_timestamp_after")
        if after and len(after) == 10 and after.count("-") == 2:
            filters["log_timestamp_after"] = f"{after} 00:00:00"
        before = filters.get("log_timestamp_before")
        if before and len(before) == 10 and before.count("-") == 2:
            filters["log_timestamp_before"] = f"{before} 23:59:59"

        project_request = req.get(
            f"{api_endpoint}/api/{project_id}/logs",
            params=filters,
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if project_request.status_code == 200:
            logs = project_request.json()
        else:
            return render_template(
                "devlog.html",
                message=f"Failed to fetch project logs: {_build_error_message(project_request)}"
            )
    except req.RequestException as exc:
        return render_template(
            "devlog.html",
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects,
            message="Unable to reach API",
            message_detail=str(exc)
        )
    
    if request.method == "GET":
        return render_template(
            "devlog.html",
            
            # populate the data
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects,
            logs=logs,
            project_id=project_id
        )
    else:
        return ""

@app.route("/projects/<int:project_id>/settings", methods=["GET", "POST"])
def project_settings(project_id):
    # copy from here for auth checking
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    
    result = check_if_user_is_authenticated(api_endpoint, token)
    if not isinstance(result, dict):
        return result
    
    user_data = result
    
    projects = []
    try:
        projects_response = req.get(
            f"{api_endpoint}/api/projects",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if projects_response.status_code == 200:
            projects = projects_response.json()
    except req.RequestException:
        pass

    if not token:
        return redirect(url_for("login"))
    # end copy
    
    project = next((p for p in projects if p.get('project_id') == project_id), None)

    if project is None:
        return render_template(
            "project_settings.html",
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects,
            project_id=project_id,
            message="Project not found, likely doesn't exist",
            message_type="danger",
            keyword='big and dangerous'
        )

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        if action == "update":
            project_name = (request.form.get("project_name") or "").strip()
            repository_url = request.form.get("repository_url")
            description = request.form.get("description")

            if not project_name:
                return render_template(
                    "project_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    project_id=project_id,
                    project=project,
                    project_name=project.get("project_name"),
                    message="Project name cannot be empty",
                    message_type="danger",
                )

            try:
                update_response = req.put(
                    f"{api_endpoint}/api/projects/{project_id}",
                    data={
                        "project_name": project_name,
                        "repository_url": repository_url if repository_url is not None else "",
                        "description": description if description is not None else "",
                    },
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
            except req.RequestException as exc:
                return render_template(
                    "project_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    project_id=project_id,
                    project=project,
                    project_name=project.get("project_name"),
                    message="Unable to reach API",
                    message_detail=str(exc),
                    message_type="danger",
                )

            if update_response.status_code != 200:
                return render_template(
                    "project_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    project_id=project_id,
                    project=project,
                    project_name=project.get("project_name"),
                    message=_build_error_message(update_response),
                    message_type="danger",
                )

            try:
                projects_response = req.get(
                    f"{api_endpoint}/api/projects",
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
                if projects_response.status_code == 200:
                    projects = projects_response.json()
            except req.RequestException:
                pass

            project = next((p for p in projects if p.get('project_id') == project_id), project)
            return render_template(
                "project_settings.html",
                username=user_data.get("username"),
                email=user_data.get("email"),
                user_id=user_data.get("user_id"),
                projects=projects,
                project_id=project_id,
                project=project,
                project_name=project.get("project_name") or project_name,
                message="Project updated",
                message_type="success",
            )

        if action == "delete":
            try:
                delete_response = req.delete(
                    f"{api_endpoint}/api/projects/{project_id}",
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
            except req.RequestException as exc:
                return render_template(
                    "project_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    project_id=project_id,
                    project=project,
                    project_name=project.get("project_name"),
                    message="Unable to reach API",
                    message_detail=str(exc),
                    message_type="danger",
                )

            if delete_response.status_code != 200:
                return render_template(
                    "project_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    project_id=project_id,
                    project=project,
                    project_name=project.get("project_name"),
                    message=_build_error_message(delete_response),
                    message_type="danger",
                )

            return redirect(url_for("dashboard"))

        return render_template(
            "project_settings.html",
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects,
            project_id=project_id,
            project=project,
            project_name=project.get("project_name"),
            message="Unknown action",
            message_type="danger",
        )
    
    return render_template(
        "project_settings.html",
        username=user_data.get("username"),
        email=user_data.get("email"),
        user_id=user_data.get("user_id"),
        projects=projects,
        project_id=project_id,
        project=project,
        project_name=project.get('project_name'),
    )

@app.route("/settings", methods=["GET", "POST"])
def user_settings():
    # copy from here for auth checking
    api_endpoint = session.get("api_endpoint", DEFAULT_API_ENDPOINT)
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    
    result = check_if_user_is_authenticated(api_endpoint, token)
    if not isinstance(result, dict):
        return result
    
    user_data = result
    
    projects = []
    try:
        projects_response = req.get(
            f"{api_endpoint}/api/projects",
            cookies={ACCESS_COOKIE_NAME: token},
            timeout=API_TIMEOUT_SECONDS
        )
        if projects_response.status_code == 200:
            projects = projects_response.json()
    except req.RequestException:
        pass

    if not token:
        return redirect(url_for("login"))
    # end copy
    
    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        if action == "update_username":
            new_username = (request.form.get("username") or "").strip()
            if not new_username:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="Username cannot be empty",
                    message_type="danger",
                )

            try:
                resp = req.put(
                    f"{api_endpoint}/api/account/username",
                    data={"username": new_username},
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
            except req.RequestException as exc:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="Unable to reach API",
                    message_detail=str(exc),
                    message_type="danger",
                )

            if resp.status_code != 200:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message=_build_error_message(resp),
                    message_type="danger",
                )

            user_data["username"] = new_username
            return render_template(
                "user_settings.html",
                username=new_username,
                email=user_data.get("email"),
                user_id=user_data.get("user_id"),
                projects=projects,
                message="Username updated",
                message_type="success",
            )

        if action == "update_password":
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_new_password") or ""
            totp_code = (request.form.get("totp_code") or "").strip()

            if not current_password or not new_password or not confirm_password or not totp_code:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="All password fields and 2FA code are required",
                    message_type="danger",
                )

            if new_password != confirm_password:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="New passwords do not match",
                    message_type="danger",
                )

            try:
                resp = req.put(
                    f"{api_endpoint}/api/account/password",
                    data={
                        "current_password": current_password,
                        "new_password": new_password,
                        "totp_code": totp_code,
                    },
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
            except req.RequestException as exc:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="Unable to reach API",
                    message_detail=str(exc),
                    message_type="danger",
                )

            if resp.status_code != 200:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message=_build_error_message(resp),
                    message_type="danger",
                )

            return render_template(
                "user_settings.html",
                username=user_data.get("username"),
                email=user_data.get("email"),
                user_id=user_data.get("user_id"),
                projects=projects,
                message="Password updated",
                message_type="success",
            )

        if action == "delete_user":
            try:
                resp = req.delete(
                    f"{api_endpoint}/api/account",
                    cookies={ACCESS_COOKIE_NAME: token},
                    timeout=API_TIMEOUT_SECONDS
                )
            except req.RequestException as exc:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message="Unable to reach API",
                    message_detail=str(exc),
                    message_type="danger",
                )

            if resp.status_code != 200:
                return render_template(
                    "user_settings.html",
                    username=user_data.get("username"),
                    email=user_data.get("email"),
                    user_id=user_data.get("user_id"),
                    projects=projects,
                    message=_build_error_message(resp),
                    message_type="danger",
                )

            session.pop("api_endpoint", None)
            redirect_response = make_response(
                redirect(url_for("login") + "?message=Account deleted&message_type=success")
            )
            redirect_response.set_cookie(ACCESS_COOKIE_NAME, "", max_age=0)
            return redirect_response

        return render_template(
            "user_settings.html",
            username=user_data.get("username"),
            email=user_data.get("email"),
            user_id=user_data.get("user_id"),
            projects=projects,
            message="Unknown action",
            message_type="danger",
        )

    return render_template(
        "user_settings.html",
        username=user_data.get("username"),
        email=user_data.get("email"),
        user_id=user_data.get("user_id"),
        projects=projects,
    )

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for("index") + "?message=Page not found&message_type=danger")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=4200)
