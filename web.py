from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from osu import Client, AuthHandler, Scope

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rt4d.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

env_path = os.path.join(os.path.dirname(__file__), 'sec.env')
load_dotenv(dotenv_path=env_path)

app.secret_key = os.getenv("FLASK_SECKEY")

client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/" 

auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

class BaseUser(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key = True)
    discord_username = db.Column(db.String(25), nullable = True)
    osu_username = db.Column(db.String(25), nullable = True)
    initial_pp = db.Column(db.Integer, unique = True, nullable = True)
    final_pp = db.Column(db.Integer, nullable = True)
    pp_change = db.Column(db.Integer, nullable = True)


class Master(BaseUser):
    __tablename__ = 'Master'

class Ranker(BaseUser):
    __tablename__ = 'Ranker'

class Elite(BaseUser):
    __tablename__ = 'Elite'

class Diamond(BaseUser):
    __tablename__ = 'Diamond'

class Platinum(BaseUser):
    __tablename__ = 'Platinum'

class Gold(BaseUser):
    __tablename__ = 'Gold'

class Silver(BaseUser):
    __tablename__ = 'Silver'

class Bronze(BaseUser):
    __tablename__ = 'Bronze'

LEAGUE_MODELS = {
    1: Master,
    2: Ranker,
    3: Elite,
    4: Diamond,
    5: Platinum,
    6: Gold,
    7: Silver,
    8: Bronze
}

@app.route("/")
def route():
    state = request.args.get("state")
    existing = search(state)
    if existing: 
        for entry in existing:
            uname = entry['osu_username'] 
            pp = entry['pp']
            league = entry['league']
        msg = "You already have a linked account, please contact spinneracc or Rhythmic_Ocean if you wanna link a different account or restart this session."
        return render_template("dashboard.html", username = uname, pp = pp, msg = msg, league = league)
    else:
        code = request.args.get("code")
        auth.get_auth_token(code)
        client = Client(auth)
        mode = 'osu'
        user = client.get_own_data(mode)
        uname = user.username
        pp = round(user.statistics.pp)
        g_rank = user.statistics.global_rank
        if g_rank >= 500000:
            new_user = Bronze( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Bronze"
        elif g_rank >= 100000 and g_rank < 500000:
            new_user = Silver( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Silver"
        elif g_rank >= 50000 and g_rank < 100000:
            new_user = Gold( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Gold"
        elif g_rank >= 20000 and g_rank < 50000:
            new_user = Platinum( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None) 
            league = "Platinum"
        elif g_rank >= 10000 and g_rank < 20000:
            new_user = Diamond( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Diamond"
        elif g_rank >= 5000 and g_rank < 10000:
            new_user = Elite( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Elite"
        elif g_rank >= 1000 and g_rank < 5000:
            new_user = Ranker( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Ranker"
        elif g_rank < 1000:
            new_user = Master( discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
            league = "Master"
        db.session.add(new_user)
        db.session.commit()
        msg = "You have been verified, you can safely exit this page."
        return render_template("dashboard.html", username = uname, pp = pp, msg = msg, league = league)

def search(username):
    found=[]
    for league_number, league_class in LEAGUE_MODELS.items():
        data = league_class.query.filter_by(discord_username = username).first()
        if data:
            found.append({
                "league": league_class.__tablename__,
                "osu_username": data.osu_username,
                "pp": data.initial_pp
            })
    return found

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)