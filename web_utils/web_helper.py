from __future__ import annotations
import os
import logging
from dotenv import load_dotenv
from pydantic_core.core_schema import NoneSchema
from load_env import ENV
from typing import TYPE_CHECKING, Optional

import osu
from osu import AsynchronousClient, UserScoreType, SoloScore, Scope
from utils_v2 import InitExterns, LogHandler

load_dotenv(dotenv_path="sec.env")

logging.basicConfig(filename="core_web.log", level=logging.DEBUG, filemode="w")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if TYPE_CHECKING:
    from supabase import AsyncClient
    from osu import AsynchronousAuthHandler, AsynchronousClient

OSU_CLIENT_ID = os.getenv("OSU_CLIENT2_ID")
OSU_CLIENT_SECRET = os.getenv("OSU_CLIENT2_SECRET")
redirect_url = "http://127.0.0.1:8080"  # not used directly, fine to keep

osu_auth = osu.AuthHandler(OSU_CLIENT_ID, OSU_CLIENT_SECRET, Scope.identify())
client_updater = Client.from_credentials(
    OSU_CLIENT_ID, OSU_CLIENT_SECRET, redirect_url, limit_per_minute=50
)


class WebHelper:
    def __init__(self, log_handler):
        self.log_handler: LogHandler = log_handler
        self.osu_auth: Optional[AsynchronousAuthHandler] = None
        self.supabase_client: Optional[AsyncClient] = None
        self.osu_client: Optional[AsynchronousClient] = None

    @classmethod
    async def create(cls, log_handler) -> WebHelper:
        self = cls(log_handler)

        init_obj = InitExterns(log_handler)
        self.osu_auth = await init_obj.setup_osu_auth(
            ENV.AUTH_ID, ENV.AUTH_TOKEN, ENV.REDIRECT_URL
        )
        self.supabase_client = await init_obj.setup_supabase_client(
            ENV.SUPABASE_URL, ENV.SUPABASE_KEY
        )
        self.osu_client = await init_obj.setup_osu_client(
            ENV.OSU_CLIENT2_ID, ENV.OSU_CLIENT2_SECRET, ENV.CLIENT2_REDIRECT_URL
        )

        return self

    async def get_top_play(self, osu_id):
        if osu_id:
            try:
                top_scores = await self.osu_client.get_user_scores(
                    osu_id, UserScoreType.BEST, limit=1
                )
                for i, score in enumerate(top_scores):
                    print(f"Type of 'score' is: {type(score)}")
                    if isinstance(score, SoloScore):
                        return (score.beatmapset.title, score.ended_at, score.pp)
                    else:
                        return (score.beatmapset.title, score.created_at, score.pp)

            except Exception as e:
                print(f"{e}")
        return None


def search(username: str) -> dict | None:
    if not isinstance(username, str) or not username.strip():
        logging.error(f"{username} is not a valid username")
        return None
    try:
        resp = (
            supabase.table("discord_osu")
            .select("league")
            .eq("discord_username", username)
            .limit(1)
            .execute()
        )
        league = resp.data[0]["league"]
        response = (
            supabase.table(league)
            .select("osu_username", "initial_pp")
            .eq("discord_username", username)
            .limit(1)
            .execute()
        )
        if response.data and len(response.data) > 0:
            response.data[0]["league"] = league
            return response.data[0]
    except Exception as e:
        logging.error(f"Error searching web username: {e}")
    return None


def add_user(
    league, state, username: str, pp: int, g_rank: int, osu_id: int, state_id: int
) -> None:
    try:
        supabase.table("discord_osu").insert(
            {
                "discord_username": state,
                "osu_username": username,
                "current_pp": pp,
                "league": league,
                "future_league": league,
                "global_rank": g_rank,
                "osu_id": osu_id,
                "discord_id": state_id,
                "new_player_announce": True,
            }
        ).execute()
    except Exception as e:
        logging.error(f"Error inserting into discord_osu table: {e}")

    try:
        supabase.table(league).insert(
            {
                "discord_username": state,
                "osu_username": username,
                "initial_pp": pp,
                "current_pp": pp,
                "global_rank": g_rank,
            }
        ).execute()
    except Exception as e:
        logging.error(f"Error inserting in {league} table: {e}")
