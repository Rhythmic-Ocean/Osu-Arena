from flask import Flask
from supabase import Client, create_client
import osu
from osu import Scope, GameModeStr
import os
from dotenv import load_dotenv
from web import LEAGUE_MODES
from threading import Thread, Lock


load_dotenv(dotenv_path="sec.env")
update_lock = Lock()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

redirect_url = "http://127.0.0.1:8080"  # not used directly, fine to keep

OSU_CLIENT_ID = os.getenv("OSU_CLIENT2_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT2_SECRET")

osu_auth = osu.AuthHandler(OSU_CLIENT_ID, OSU_CLIENT_SECRET, Scope.identify())
client_updater = osu.Client.from_credentials(OSU_CLIENT_ID,
                                             OSU_CLIENT_SECRET,
                                             redirect_url,
                                             limit_per_minute=50)

app = Flask(__name__)


def get_pp(osu_username):
    if osu_username:
        try:
            user = client_updater.get_user(osu_username, GameModeStr.STANDARD)
            pp = round(user.statistics.pp)
            username = user.username
            global_rank = user.statistics.global_rank
            return username, global_rank, pp
        except Exception as e:
            print(f"Error fetching data for {osu_username}: {e}")
    return None


def update_pp():
    response = supabase.table("discord_osu").select("osu_id").execute()
    if not response.data:
        print("No users found in the discord_osu table.")
        return

    users = response.data
    for user in users:
        osu_id = user.get("osu_id")
        data = get_pp(osu_id)
        if data is not None:
            username, rank, pp = data
            league = "Unranked"
            for threshold, league_try in LEAGUE_MODES.items():
                if rank < threshold:
                    league = league_try
                    break
            try:
                supabase.table("discord_osu").update({
                    "current_pp": pp,
                    "osu_username": username,
                    "global_rank": rank,
                    "future_league": league
                }).eq("osu_id", osu_id).execute()
                print(f"{username}'s osu! pp: {pp}, rank: {rank} updated.")
            except Exception as e:
                print(f"Failed to update {osu_id}: {e}")


@app.route("/")
def index():
    return "Flask is running!"



@app.route("/update", methods=["GET"])
def handle_update():
    def run_update():
        with update_lock:
            update_pp()

    if update_lock.locked():
        return "Update already in progress.", 429  

    Thread(target=run_update).start()
    return "Update started in background.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
