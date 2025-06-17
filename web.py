from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, String, Column, Integer
from dotenv import load_dotenv
import os
from osu import Client, AuthHandler, Scope

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rt4d.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

load_dotenv(dotenv_path="sec.env")
app.secret_key = os.getenv("FLASK_SECKEY")

client_id = int(os.getenv("AUTH_ID"))
client_secret = os.getenv("AUTH_TOKEN")
redirect_url = "http://127.0.0.1:5000/"
state1 = "Rhythmic_Ocean"

auth = AuthHandler(client_id, client_secret, redirect_url, Scope.identify())

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    discord_username = db.Column(db.String(25), unique = True, nullable = True)
    osu_username = db.Column(db.String(25), unique = True, nullable = True)
    initial_pp = db.Column(db.Integer, unique = True, nullable = True)
    final_pp = db.Column(db.Integer, nullable = True)
    pp_change = db.Column(db.Integer, nullable = True)

@app.route("/")
def route():
    state = request.args.get("state")
    existing = User.query.filter_by(discord_username = state).first()
    if existing: 
        uname = existing.osu_username
        pp = existing.initial_pp
    else:
        code = request.args.get("code")
        auth.get_auth_token(code)
        client = Client(auth)
        mode = 'osu'
        user = client.get_own_data(mode)
        uname = user.username
        pp = round(user.statistics.pp)
        new_user = User(discord_username = state, osu_username = uname, initial_pp = pp, final_pp = None, pp_change = None)
        db.session.add(new_user)
        db.session.commit()
    return render_template("dashboard.html", username = uname, pp = pp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)