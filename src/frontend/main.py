from flask import Flask, render_template, redirect, url_for, request

app = Flask(__name__, 
    template_folder='../../templates',
    static_folder='../../static') 

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/login")
def login():
    return render_template("login.html")

@app.get("/register")
def register():
    return render_template("register.html")

@app.get("/auth-redirect")
def auth_redirect():
    user_name = request.args.get("name", "User")
    mode = request.args.get("mode", "login")
    return render_template("auth_redirect.html", user_name=user_name, mode=mode)

# ----------------- REDIRECTS -------------------------

@app.route("/index.<path:extension>")
def redirect_index(extension):
    return redirect(url_for('index'), code=301)

@app.route("/login.<path:extension>")
def redirect_login(extension):
    return redirect(url_for('login'), code=301)

@app.route("/register.<path:extension>")
def redirect_register(extension):
    return redirect(url_for('login'), code=301)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=4200)