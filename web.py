from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
import os
from osu import Client, AuthHandler, Scope
from itsdangerous import URLSafeSerializer
import logging
from core_web import search, add_user
import sys

app = Flask(__name__)

# --- Setup ---
env_path = os.path.join(os.path.dirname(__file__), "sec.env")
load_dotenv(dotenv_path=env_path)

logging.basicConfig(filename="web.log", level=logging.DEBUG, filemode="w")

app.secret_key = os.getenv("FLASK_SECKEY")
SEC_KEY = os.getenv("SEC_KEY")
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "https://rt4d-production.up.railway.app/"
serializer = URLSafeSerializer(SEC_KEY)
auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

LEAGUE_MODES = {
    1000: "master",
    3000: "elite",
    10000: "diamond",
    30000: "platinum",
    80000: "gold",
    150000: "silver",
    250000: "bronze",
    sys.maxsize: "novice",
}


@app.route("/")
def home():
    """
    Handles the Landing Page AND the OAuth Callback.
    """
    load = request.args.get("state")
    code = request.args.get("code")

    # --- 1. HANDLE OAUTH CALLBACK ---
    if load and code:
        # A. Decrypt State (Discord Info)
        try:
            data = serializer.loads(load)
            discord_name = data.get("user_name")
            discord_id = data.get("user_id")
        except Exception as e:
            logging.error(f"Error decrypting state: {e}")
            return "Invalid state. Please try again.", 400

        # B. Check if user is already in YOUR database
        try:
            entry = search(discord_name)
        except Exception as e:
            logging.error(f"Search error: {e}")
            entry = None

        if entry:
            # User exists: Load data into session
            session["user_data"] = {
                "username": entry["osu_username"],
                "pp": entry["initial_pp"],
                "league": entry["league"],
                "msg": "You already have a linked account. Contact spinneracc or Rhythmic_Ocean to change it.",
            }
            # CRITICAL FIX: Redirect to remove '?code=' from URL
            return redirect(url_for("dashboard"))

        else:
            # User is NEW: Finish OAuth with osu!
            try:
                auth.get_auth_token(code)
                client = Client(auth)
                user = client.get_own_data(mode="osu")
            except Exception as e:
                logging.error(f"OAuth failed: {e}")
                # This usually happens on refresh. Just redirect home to try again.
                return redirect(url_for("home"))

            # Process osu! data
            uname = user.username
            pp = round(user.statistics.pp)
            osu_id = user.id
            g_rank = user.statistics.global_rank
            league = "novice"

            for threshold, league_try in LEAGUE_MODES.items():
                if g_rank < threshold:
                    league = league_try
                    break

            # Save to Database
            add_user(league, discord_name, uname, pp, g_rank, osu_id, discord_id)

            # Save to Session
            session["user_data"] = {
                "username": uname,
                "pp": pp,
                "league": league,
                "msg": "You have been verified, you can safely exit this page.",
            }

            # CRITICAL FIX: Redirect to remove '?code=' from URL
            return redirect(url_for("dashboard"))

    # --- 2. CHECK EXISTING SESSION ---
    # If user just visits "/" but is already logged in
    if "user_data" in session:
        return redirect(url_for("dashboard"))

    # --- 3. SHOW LANDING PAGE ---
    return render_template("welcome.html")


@app.route("/dashboard")
def dashboard():
    """
    Displays the user info. Only accessible if logged in.
    """
    data = session.get("user_data")

    # If no session data, kick them back to home
    if not data:
        return redirect(url_for("home"))

    return render_template(
        "dashboard.html",
        username=data["username"],
        pp=data["pp"],
        msg=data["msg"],
        league=data["league"],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

