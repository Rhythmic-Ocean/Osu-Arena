from flask import Flask
from supabase import Client, create_client
import osu
from osu import Scope, GameModeStr, Client, UserScoreType, SoloScore
from osu.objects import LegacyScore
import os
from dotenv import load_dotenv
from web import LEAGUE_MODES
from threading import Thread, Lock
import pprint


load_dotenv(dotenv_path="sec.env")
update_lock = Lock()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

redirect_url = "http://127.0.0.1:8080"  # not used directly, fine to keep

OSU_CLIENT_ID = os.getenv("OSU_CLIENT2_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT2_SECRET")

client_updater = Client.from_credentials(OSU_CLIENT_ID,
                                             OSU_CLIENT_SECRET,
                                             redirect_url)

app = Flask(__name__)


def get_user_data(osu_id):
    if osu_id:
        try:
            user = client_updater.get_user(osu_id, GameModeStr.STANDARD)
            pp = round(user.statistics.pp)
            username = user.username
            global_rank = user.statistics.global_rank
            secs_played= user.statistics.play_time
            hours_played = secs_played/3600
            ii = get_ii(pp, hours_played)
            print(ii)
            return username, global_rank, pp, ii
        except Exception as e:
            print(f"Error fetching data for {osu_id}: {e}")
    return None

def get_top_play(osu_id):
    if osu_id:
        try:
            top_scores = client_updater.get_user_scores(osu_id, UserScoreType.BEST, limit=1)
            if not top_scores:
                return
            for i, score in enumerate(top_scores):
                print(f"Type of 'score' is: {type(score)}")
                if(isinstance(score, SoloScore)):
                    return (score.beatmapset.title, score.ended_at, score.pp, score.id)
                else:
                    return (score.beatmapset.title, score.created_at, score.pp, score.id)
                
        except Exception as e:
            print(f"{e}")
    return None


def get_ii(pp, hours):
    numerator = -12 + 0.0781 * pp + 6.01e-6 * (pp ** 2)
    if hours == 0:
        return 0
    ii = round(numerator / hours, 2)
    return ii


def update_scores(data, osu_id):
    username, rank, pp, ii = data
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
            "future_league": league,
            "ii" : ii,
        }).eq("osu_id", osu_id).execute()
        print(f"{username}'s osu! pp: {pp}, rank: {rank} updated. League: {league}")
    except Exception as e:
        print(f"Failed to update {osu_id}: {e}")


def update_top_plays(top_play_data, osu_id, announce_bool):
    title, date, p_points, score_id = top_play_data
    formatted_date = date.isoformat()
    update_payload = {
        "top_play_map":title,
        "top_play_pp": int(p_points) if p_points else 0,
        "top_play_date" : formatted_date,
        "top_play_id" : score_id,
    }

    if announce_bool:
        update_payload["top_play_announce"] = True
    try:
        supabase.table("discord_osu").update(update_payload).eq("osu_id", osu_id).execute()
        print(f"Updated for {osu_id}, with {title}  {p_points}")
    except Exception as e:
        print("\n----Error Summary----")
        print(f"Error at update_top_players {e}")




def update_player():
    response = supabase.table("discord_osu").select("osu_id, top_play_id, current_pp").execute()
    if not response.data:
        print("No users found in the discord_osu table.")
        return

    users = response.data

    for user in users:
        osu_id = user.get("osu_id")
        top_play_id = user.get("top_play_id")
        current_pp = user.get("current_pp")

        data = get_user_data(osu_id)
        top_play_data = get_top_play(osu_id)

        if data is not None:
            username, rank, pp, ii = data
            if current_pp != pp:
                update_scores(data, osu_id)
            else:
                print(f"Same pp for {osu_id}")

        if top_play_data is not None:
            title, date, p_points, score_id = top_play_data
            if score_id != top_play_id:
                if top_play_id == None:#first time player so no announcement
                    update_top_plays(top_play_data, osu_id, False)
                else:
                    update_top_plays(top_play_data, osu_id, True)
            else:
                print(f"Same top score for {osu_id}")





@app.route("/")
def index():
    return "Flask is running!"



@app.route("/update", methods=["GET"])
def handle_update():
    def run_update():
        with update_lock:
            update_player()

    if update_lock.locked():
        return "Update already in progress.", 429  

    Thread(target=run_update).start()
    return "Update started in background.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
