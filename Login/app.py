import os
import secrets
import requests

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for, render_template

load_dotenv("../.env")

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

API_ENDPOINT = "https://discord.com/api/v10"

AUTH_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = f"{API_ENDPOINT}/oauth2/token"
USER_URL = f"{API_ENDPOINT}/users/@me"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    return redirect(
        f"{AUTH_URL}"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return "Invalid state"

    code = request.args.get("code")

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_response = requests.post(
        TOKEN_URL,
        data=data,
        headers=headers
    )

    token = token_response.json()["access_token"]

    user_response = requests.get(
        USER_URL,
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    user = user_response.json()
    session["user"] = user

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = session.get("user")

    if not user:
        return redirect(url_for("login"))

    return f"""
    <h1>Dashboard</h1>

    <p>Logged in as {user['username']}</p>

    <p>User ID: {user['id']}</p>

    <a href='/logout'>Logout</a>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)