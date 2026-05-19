import os
import secrets
import requests

from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "..", "templates"),
    static_folder=os.path.join(BASE_DIR, "..", "static")
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.permanent_session_lifetime = timedelta(days=30)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

API_ENDPOINT = "https://discord.com/api/v10"

AUTH_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = f"{API_ENDPOINT}/oauth2/token"
USER_URL = f"{API_ENDPOINT}/users/@me"
GUILDS_URL = f"{API_ENDPOINT}/users/@me/guilds"


def get_auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("dashboard"))

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
        f"&scope=identify%20guilds"
        f"&state={state}"
    )


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return "Invalid state", 400

    code = request.args.get("code")

    if not code:
        return "No code provided", 400

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

    token_data = token_response.json()

    if "access_token" not in token_data:
        return f"Discord token error: {token_data}", 400

    token = token_data["access_token"]

    user_response = requests.get(
        USER_URL,
        headers=get_auth_headers(token)
    )

    user = user_response.json()

    session.clear()
    session.permanent = True
    session["user"] = {
        "id": user.get("id"),
        "username": user.get("username"),
        "avatar": user.get("avatar"),
        "global_name": user.get("global_name")
    }
    session["access_token"] = token

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    token = session.get("access_token")

    if not user or not token:
        return redirect(url_for("login"))

    user_guilds_response = requests.get(
        GUILDS_URL,
        headers=get_auth_headers(token)
    )

    user_guilds_raw = user_guilds_response.json()

    bot_guilds_response = requests.get(
        GUILDS_URL,
        headers={
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}"
        }
    )

    bot_guilds_raw = bot_guilds_response.json()

    bot_guild_ids = {
        guild.get("id")
        for guild in bot_guilds_raw
    }

    guilds = []

    for guild in user_guilds_raw:
        guild_id = guild.get("id")

        if guild_id not in bot_guild_ids:
            continue

        icon_hash = guild.get("icon")

        if icon_hash:
            icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png"
        else:
            icon_url = None

        guilds.append({
            "id": guild_id,
            "name": guild.get("name"),
            "icon_url": icon_url
        })

    return render_template(
        "dashboard.html",
        user=user,
        guilds=guilds
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)