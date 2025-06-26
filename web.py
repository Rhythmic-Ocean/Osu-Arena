from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import os
from osu import Client, AuthHandler, Scope
from itsdangerous import URLSafeSerializer
import logging
from core_web import search, add_user
import sys

app = Flask(__name__)

env_path = os.path.join(os.path.dirname(__file__), 'sec.env')
load_dotenv(dotenv_path=env_path)

logging.basicConfig(filename="web.log", level=logging.DEBUG ,filemode='w')

app.secret_key = os.getenv("FLASK_SECKEY")
SEC_KEY = os.getenv("SEC_KEY")
client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/" 
serializer = URLSafeSerializer(SEC_KEY)
auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

LEAGUE_MODES = {
    1000: "master",
    5000: "ranker",
    10000: "elite",
    20000: "diamond",
    50000: "platinum",
    100000: "gold",
    500000: "silver",
    sys.maxsize: "bronze",
}



@app.route("/")
def route():
    if "discord_username" in session:
        username = session["discord_username"]
        entry=  search(username)
        if entry: 
            uname = entry['osu_username'] 
            pp = entry['current_pp']
            league = entry['league']
            msg = "You already have a linked account, please contact spinneracc or Rhythmic_Ocean if you wanna link a different account or restart this session."
            return render_template("dashboard.html", username = uname, pp = pp, msg = msg, league = league)
    

    load = request.args.get("state")
    code = request.args.get("code")


    if load and code:
        try:
            data = serializer.loads(load)
            state = data["discord_username"]

        except Exception as e:
            logging.error(f"Error decrypting username: {e}")
            return "Invalid state, Please try again.",400
        

        entry =  search(state)
        if entry: 
            uname = entry['osu_username'] 
            pp = entry['current_pp']
            session["discord_username"] = state
            league = entry['league']
            msg = "You already have a linked account, please contact spinneracc or Rhythmic_Ocean if you wanna link a different account or restart this session."
            return render_template("dashboard.html", username = uname, pp = pp, msg = msg, league = league)
        

        else:
            auth.get_auth_token(code)
            client = Client(auth)
            mode = 'osu'
            user = client.get_own_data(mode)
            uname = user.username
            pp = round(user.statistics.pp)
            osu_id = user.id
            g_rank = user.statistics.global_rank

            for threshold, league_try in LEAGUE_MODES.items():
                   if g_rank < threshold:
                       add_user(league_try, state, uname, pp, g_rank, osu_id)
                       league = league_try

            msg = "You have been verified, you can safely exit this page."
            return render_template("dashboard.html", username = uname, pp = pp, msg = msg, league = league)
        
    return render_template("welcome.html")

if __name__ == "__main__":
    app.run(debug=True)