import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
import time

load_dotenv(dotenv_path="sec.env")

logging.basicConfig(filename="core_web.log", level=logging.DEBUG, filemode='w')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def search(username: str) -> dict | None:
    if not isinstance(username, str) or not username.strip():
        logging.error(f"{username} is not a valid username")
        return None
    try:
        response = supabase.table("discord_osu").select("osu_username, current_pp, league").eq("discord_username", username).limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        logging.error(f"Error searching web username: {e}")
    return None

def add_user(league, state, username: str, pp: int, g_rank: int, osu_id: int):
    try:
        supabase.table("discord_osu").insert({
            "discord_username": state,
            "osu_username": username,
            "current_pp": pp,
            "league": league,
            "global_rank": g_rank,
            "osu_id": osu_id
        }).execute()
    except Exception as e:
        logging.error(f"Error inserting into discord_osu table: {e}")


    try:
        supabase.table(league).insert({
            "discord_username": state,
            "osu_username": username,
            "initial_pp": pp,
            "current_pp": pp,
            "global_rank": g_rank
        }).execute()
    except Exception as e:
        logging.error(f"Error inserting in {league} table: {e}")


