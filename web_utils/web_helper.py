from __future__ import annotations
import time

from load_env import ENV
from typing import Any, Optional
import sys

from osu import (
    AsynchronousClient,
    RequestException,
    UserScoreType,
    SoloScore,
    AsynchronousAuthHandler,
)
from supabase import AsyncClient
from utils_v2 import InitExterns, LogHandler
from utils_v2.db_handler import DatabaseHandler
from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables import TableMiscellaneous
from utils_v2.enums.tables_internals import DiscordOsuColumn, LeagueColumn

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


class WebHelper:
    def __init__(self, log_handler):
        self.log_handler: LogHandler = log_handler
        self.osu_auth: Optional[AsynchronousAuthHandler] = None
        self.supabase_client: Optional[AsyncClient] = None
        self.osu_client: Optional[AsynchronousClient] = None
        self.db_handler: DatabaseHandler = None

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
        self.osu_client = await init_obj.setup_osu_client(self.osu_auth)
        self.db_handler = DatabaseHandler(self.log_handler, self.supabase_client)

        return self

    async def get_top_play(self, osu_id) -> dict[str, Any]:
        if osu_id:
            try:
                top_scores = await self.osu_client.get_user_scores(
                    osu_id, UserScoreType.BEST, limit=1
                )
                for score in top_scores:
                    if isinstance(score, SoloScore):
                        return {
                            DiscordOsuColumn.TOP_PLAY_DATE: score.ended_at.isoformat(),
                            DiscordOsuColumn.TOP_PLAY_MAP: score.beatmapset.title,
                            DiscordOsuColumn.TOP_PLAY_PP: int(score.pp),
                            DiscordOsuColumn.TOP_PLAY_ID: int(score.id),
                        }
                    else:
                        return {
                            DiscordOsuColumn.TOP_PLAY_DATE: score.created_at.isoformat(),
                            DiscordOsuColumn.TOP_PLAY_MAP: score.beatmapset.title,
                            DiscordOsuColumn.TOP_PLAY_PP: int(score.pp),
                            DiscordOsuColumn.TOP_PLAY_ID: int(score.id),
                        }
                return FuncStatus.EMPTY
            except Exception as error:
                await self.log_handler.report_error(
                    "WebHelper.get_top_play()",
                    error,
                    f"Error getting top play for user with osu_id {osu_id}",
                )
            return FuncStatus.ERROR

    async def search_and_find(self, discord_id: int) -> dict | None:
        response = await self.db_handler.get_player(discord_id)
        return response

    async def check_discord_id(self, discord_id: Optional[int | str]) -> int:
        if not discord_id:
            error = Exception("Bad Request.")
            await self.log_handler.report_error(
                "WebHelper.search()", error, "Missing discord_id"
            )
            return FuncStatus.BAD_REQ
        try:
            discord_id = int(str(discord_id).strip())
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.search()", error, f"Malformed discord_id {discord_id}"
            )
            return FuncStatus.ERROR
        return discord_id

    async def get_osu_user(self, code: str, discord_id: int):
        try:
            try:
                await self.osu_auth.get_auth_token(code)

                client = AsynchronousClient(self.osu_auth)
            except RequestException as _:
                return FuncStatus.BAD_REQ

            user = await client.get_own_data(mode="osu")

            uname = user.username
            pp = round(user.statistics.pp)
            osu_id = user.id
            g_rank = user.statistics.global_rank
            secs_played = user.statistics.play_time
            hours_played = secs_played / 3600
            ii = self._get_ii(pp, hours_played)

            league = "novice"
            for threshold, league_try in LEAGUE_MODES.items():
                if g_rank < threshold:
                    league = league_try
                    break
            top_play_data = await self.get_top_play(user.id)
            player_data = {
                DiscordOsuColumn.OSU_USERNAME: uname,
                DiscordOsuColumn.CURRENT_PP: int(pp),
                DiscordOsuColumn.OSU_ID: osu_id,
                DiscordOsuColumn.LEAGUE: league,
                DiscordOsuColumn.GLOBAL_RANK: g_rank,
                DiscordOsuColumn.II: ii,
            }
            return {**player_data, **top_play_data}
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.get_osu_user()",
                error,
                f"Failed getting user data from osu! for user <@{discord_id}>",
            )
            return FuncStatus.ERROR

    @staticmethod
    def _get_ii(pp, hours):
        numerator = -12 + 0.0781 * pp + 6.01e-6 * (pp**2)
        if hours == 0:
            return 0
        ii = round(numerator / hours, 2)
        return ii

    async def add_user(self, player_data: dict[str, Any]) -> None:
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .insert(
                    {
                        DiscordOsuColumn.DISCORD_USERNAME: player_data[
                            DiscordOsuColumn.DISCORD_USERNAME
                        ],
                        DiscordOsuColumn.OSU_USERNAME: player_data[
                            DiscordOsuColumn.OSU_USERNAME
                        ],
                        DiscordOsuColumn.CURRENT_PP: player_data[
                            DiscordOsuColumn.CURRENT_PP
                        ],
                        DiscordOsuColumn.LEAGUE: player_data[DiscordOsuColumn.LEAGUE],
                        DiscordOsuColumn.FUTURE_LEAGUE: player_data[
                            DiscordOsuColumn.FUTURE_LEAGUE
                        ],
                        DiscordOsuColumn.GLOBAL_RANK: player_data[
                            DiscordOsuColumn.GLOBAL_RANK
                        ],
                        DiscordOsuColumn.OSU_ID: player_data[DiscordOsuColumn.OSU_ID],
                        DiscordOsuColumn.DISCORD_ID: player_data[
                            DiscordOsuColumn.DISCORD_ID
                        ],
                        DiscordOsuColumn.TOP_PLAY_DATE: player_data[
                            DiscordOsuColumn.TOP_PLAY_DATE
                        ],
                        DiscordOsuColumn.TOP_PLAY_MAP: player_data[
                            DiscordOsuColumn.TOP_PLAY_MAP
                        ],
                        DiscordOsuColumn.TOP_PLAY_PP: player_data[
                            DiscordOsuColumn.TOP_PLAY_PP
                        ],
                        DiscordOsuColumn.II: player_data[DiscordOsuColumn.II],
                        DiscordOsuColumn.NEW_PLAYER_ANNOUNCE: True,
                        DiscordOsuColumn.TOP_PLAY_ANNOUNCE: False,
                        DiscordOsuColumn.TOP_PLAY_ID: player_data[
                            DiscordOsuColumn.TOP_PLAY_ID
                        ],
                    }
                )
                .execute()
            )
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.add_user()",
                error,
                f"Error inserting new row in database table discord_osu for new player <@{player_data[DiscordOsuColumn.DISCORD_ID]}>",
            )
            return FuncStatus.ERROR

        try:
            await (
                self.supabase_client.table(player_data[DiscordOsuColumn.LEAGUE])
                .insert(
                    {
                        LeagueColumn.DISCORD_USERNAME: player_data[
                            DiscordOsuColumn.DISCORD_USERNAME
                        ],
                        LeagueColumn.OSU_USERNAME: player_data[
                            DiscordOsuColumn.OSU_USERNAME
                        ],
                        LeagueColumn.INITIAL_PP: player_data[
                            DiscordOsuColumn.CURRENT_PP
                        ],
                        LeagueColumn.CURRENT_PP: player_data[
                            DiscordOsuColumn.CURRENT_PP
                        ],
                        LeagueColumn.GLOBAL_RANK: player_data[
                            DiscordOsuColumn.GLOBAL_RANK
                        ],
                        LeagueColumn.DISCORD_ID: player_data[
                            DiscordOsuColumn.DISCORD_ID
                        ],
                        LeagueColumn.II: player_data[DiscordOsuColumn.II],
                    }
                )
                .execute()
            )
        except Exception as error:
            await self.log_handler.report_error
            (
                "WebHelper.add_user()",
                error,
                f"Error inserting new row in database table {player_data[DiscordOsuColumn.LEAGUE]} for new player <@{player_data[DiscordOsuColumn.DISCORD_ID]}>",
            )
            return FuncStatus.ERROR
        return FuncStatus.GOOD

    async def load_validity(self, discord_id: int, created_at: int):
        if not discord_id or not created_at:
            error = Exception("Didn't get any discord_id or created_at")
            await self.log_handler.report_error("WebHelper.load_validity()", error)
            return FuncStatus.BAD_REQ
        try:
            discord_id = int(str(discord_id).strip())
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.load_validity()",
                error,
                f"Malformed discord_id <@{discord_id}>",
            )
            return FuncStatus.ERROR

        try:
            created_at = int(str(created_at).strip())
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.load_validity()",
                error,
                f"Malformed created_at variable from url for <@{discord_id}>",
            )
            return FuncStatus.ERROR

        time_now = time.time()
        if time_now - created_at > 300:
            return FuncStatus.TOO_LATE
        return discord_id

    async def check_ouser_existence(self, osu_id: int):
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(DiscordOsuColumn.DISCORD_ID)
                .eq(DiscordOsuColumn.OSU_ID, osu_id)
                .maybe_single()
                .execute()
            )
            if response and response.data:
                return response.data[DiscordOsuColumn.DISCORD_ID]
            return None
        except Exception as error:
            await self.log_handler.report_error(
                "WebHelper.check_ouser_existence()",
                error,
                f"Error for user with osu_id {osu_id}",
            )
            return FuncStatus.ERROR
