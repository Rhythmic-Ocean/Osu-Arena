import sys
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from quart import Quart
from supabase import create_async_client, AsyncClient
from osu import AsynchronousClient, GameModeStr, UserScoreType, SoloScore
import osu

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

BASE_DIR = Path(__file__).resolve().parent
dotenv_path = BASE_DIR / "local.env"
load_dotenv(dotenv_path=dotenv_path)

from load_env import ENV

app = Quart(__name__)
update_lock = asyncio.Lock()

# Global clients
supabase: AsyncClient = None
osu_client: AsynchronousClient = None


@app.before_serving
async def init_clients():
    global supabase, osu_client
    if supabase is None:
        supabase = await create_async_client(ENV.SUPABASE_URL, ENV.SUPABASE_KEY)
    if osu_client is None:
        osu_client = AsynchronousClient.from_credentials(
            int(ENV.OSU_CLIENT_ID), ENV.OSU_CLIENT_SECRET, ENV.REDIRECT_URL
        )


@app.after_serving
async def shutdown():
    pass


async def get_user_data(osu_id):
    if not osu_id:
        return None
    try:
        user = await osu_client.get_user(osu_id, GameModeStr.STANDARD)
        if not user or not user.statistics:
            return None

        pp = round(user.statistics.pp) if user.statistics.pp is not None else 0
        username = user.username
        global_rank = (
            user.statistics.global_rank
            if user.statistics.global_rank is not None
            else 0
        )
        secs_played = (
            user.statistics.play_time if user.statistics.play_time is not None else 0
        )
        hours_played = secs_played / 3600
        ii = get_ii(pp, hours_played)
        print(ii)
        return username, global_rank, pp, ii
    except Exception as e:
        print(f"Error fetching data for {osu_id}: {e}")
    return None


async def get_top_play(osu_id):
    if not osu_id:
        return None
    try:
        top_scores = await osu_client.get_user_scores(
            osu_id, UserScoreType.BEST, mode=GameModeStr.STANDARD, limit=1
        )
        if not top_scores:
            return None

        score = top_scores[0]
        # Previous version printed the type for debugging
        print(f"Type of 'score' is: {type(score)}")

        if isinstance(score, SoloScore):
            return (score.beatmapset.title, score.ended_at, score.pp, score.id)
        else:
            created_at = getattr(score, "created_at", getattr(score, "ended_at", None))
            return (score.beatmapset.title, created_at, score.pp, score.id)
    except Exception as e:
        print(f"Error fetching top play for {osu_id}: {e}")
    return None


def get_ii(pp, hours):
    if hours == 0:
        return 0
    numerator = -12 + 0.0781 * pp + 6.01e-6 * (pp**2)
    return round(numerator / hours, 2)


async def update_player_stats(user_record):
    osu_id = user_record.get("osu_id")
    current_top_play_id = user_record.get("top_play_id")
    current_top_play_pp = user_record.get("top_play_pp")
    current_pp = user_record.get("current_pp")
    current_ii = user_record.get("ii", 0)

    user_data_task = get_user_data(osu_id)
    top_play_task = get_top_play(osu_id)

    user_data, top_play_data = await asyncio.gather(user_data_task, top_play_task)

    updates = {}
    logs = []

    if user_data:
        username, rank, pp, ii = user_data
        if pp != current_pp or ii != current_ii:
            league = "Unranked"
            for threshold, league_try in LEAGUE_MODES.items():
                if rank < threshold:
                    league = league_try
                    break
            updates.update(
                {
                    "current_pp": pp,
                    "osu_username": username,
                    "global_rank": rank,
                    "future_league": league,
                    "ii": ii,
                }
            )
            logs.append(
                f"{username}'s osu! pp: {pp}, rank: {rank} updated. League: {league}"
            )
        else:
            logs.append(f"Same pp for {osu_id}")

    if top_play_data:
        title, date, p_points, score_id = top_play_data
        if score_id != current_top_play_id:
            formatted_date = date.isoformat() if date else None
            updates.update(
                {
                    "top_play_map": title,
                    "top_play_pp": int(p_points) if p_points else 0,
                    "top_play_date": formatted_date,
                    "top_play_id": score_id,
                    "prev_top_pp": current_top_play_pp,
                }
            )
            if current_top_play_id is not None:
                updates["top_play_announce"] = True

            logs.append(f"Updated for {osu_id}, with {title}  {p_points}")
        else:
            logs.append(f"Same top score for {osu_id}")

    if updates:
        try:
            await (
                supabase.table("discord_osu")
                .update(updates)
                .eq("osu_id", osu_id)
                .execute()
            )
        except Exception as e:
            print(f"Failed to update Supabase for {osu_id}: {e}")
            return

    # Print all logs after successful (or no-op) update
    for log in logs:
        print(log)


async def run_update_process():
    response = (
        await supabase.table("discord_osu")
        .select("osu_id, top_play_id, top_play_pp, current_pp, ii")
        .execute()
    )

    if not response.data:
        print("No users found.")
        return

    users = response.data
    # Limit concurrency to 10 users at a time to stay within rate limits
    semaphore = asyncio.Semaphore(10)

    async def sem_update(user):
        async with semaphore:
            await update_player_stats(user)

    await asyncio.gather(*(sem_update(user) for user in users))
    print("Update cycle completed.")


@app.route("/")
async def index():
    return "Quart is running!"


@app.route("/update", methods=["GET"])
async def handle_update():
    if update_lock.locked():
        return "Update already in progress.", 202

    async def run_in_background():
        async with update_lock:
            try:
                await run_update_process()
            except Exception as e:
                print(f"Update process failed: {e}")

    asyncio.create_task(run_in_background())
    return "Update started in background.", 200


if __name__ == "__main__":
    # Ensure clients are closed properly on exit would be good,
    # but for a script like this, OS cleanup is usually sufficient.
    app.run(host="0.0.0.0", port=8080)
