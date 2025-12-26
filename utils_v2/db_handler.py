from __future__ import annotations
from typing import Any, TYPE_CHECKING
from supabase import AsyncClient

from utils_v2 import (
    HistoricalPointsColumn,
    MessageIdColumn,
    RivalsColumn,
    SeasonColumn,
    SeasonStatus,
    LeagueColumn,
    TablesPoints,
    TablesRivals,
    ChallengeStatus,
    TableMiscellaneous,
    DiscordOsuColumn,
)

if TYPE_CHECKING:
    from bot import OsuArena


class DatabaseHandler:
    def __init__(self, bot: OsuArena, supabase_client: AsyncClient):
        self.bot = bot
        self.log_handler = self.bot.log_handler
        self.supabase_client = supabase_client

    async def get_discord_id(
        self, osu_username: str = None, discord_username: str = None
    ) -> int | None:
        uname_log = "Unknown"
        try:
            if discord_username:
                uname_log = f"discord_username: {discord_username}"
                query = await self.id_from_discord(discord_username)
            else:
                uname_log = f"Osu_uname: {osu_username}"
                query = await self.id_from_osu(osu_username)

            if not query.data:
                return None

            return query.data[0][DiscordOsuColumn.DISCORD_ID]

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_discord_id()",
                error,
                f"Lookup failed for {uname_log}",
            )
            return None

    async def id_from_osu(self, osu_username: str):
        return (
            await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
            .select(DiscordOsuColumn.DISCORD_ID)
            .eq(DiscordOsuColumn.OSU_USERNAME, osu_username)
            .execute()
        )

    async def id_from_discord(self, discord_username: str):
        return (
            await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
            .select(DiscordOsuColumn.DISCORD_ID)
            .eq(DiscordOsuColumn.DISCORD_USERNAME, discord_username)
            .execute()
        )

    async def get_msg_id(self, challenge_id: int) -> int | None:
        try:
            row = (
                await self.supabase_client.table(TableMiscellaneous.MESG_ID)
                .select(MessageIdColumn.MSG_ID)
                .eq(MessageIdColumn.CHALLENGE_ID, challenge_id)
                .execute()
            )

            if not row.data:
                return None

            return row.data[0][MessageIdColumn.MSG_ID]

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_msg_id()",
                error,
                f"Failed to retrieve Msg ID for challenge {challenge_id}",
            )
            return None

    async def top_play_detector(self) -> list[dict[str, Any]] | None:
        query_selector = [
            DiscordOsuColumn.DISCORD_ID,
            DiscordOsuColumn.OSU_USERNAME,
            DiscordOsuColumn.OSU_ID,
            DiscordOsuColumn.TOP_PLAY_ID,
        ]
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(", ".join(query_selector))
                .eq(DiscordOsuColumn.TOP_PLAY_ANNOUNCE, True)
                .execute()
            )
            return response.data if response.data else None
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.top_play_detector()", error
            )
            return None

    async def negate_top_play(self, discord_id: int) -> bool:
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .update({DiscordOsuColumn.TOP_PLAY_ANNOUNCE: False})
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            return True
        except Exception as e:
            await self.log_handler.report_error(
                "DatabaseHandler.negate_top_play()",
                e,
                f"Failed to negate top play for <@{discord_id}>",
            )
            return False

    async def new_player_detector(self) -> list[dict[str, Any]] | None:
        query_selector = [
            DiscordOsuColumn.DISCORD_ID,
            DiscordOsuColumn.LEAGUE,
            DiscordOsuColumn.OSU_ID,
            DiscordOsuColumn.OSU_USERNAME,
        ]
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(", ".join(query_selector))
                .eq(DiscordOsuColumn.NEW_PLAYER_ANNOUNCE, True)
                .execute()
            )
            return response.data if response.data else None
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.new_player_detector()", error
            )
            return None

    async def negate_new_player_announce(self, discord_id: int) -> bool:
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .update({DiscordOsuColumn.NEW_PLAYER_ANNOUNCE: False})
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            return True
        except Exception as e:
            await self.log_handler.report_error(
                "DatabaseHandler.negate_new_player_announce()",
                e,
                f"Failed to negate new player for <@{discord_id}>",
            )
            return False

    async def arrange_table(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[str], list[tuple[Any]]]:
        """Helper to format JSON response into Headers + Rows for Renderer."""
        if not data:
            return [], []
        headers = list(data[0].keys())
        rows = [tuple(row.get(h, 0) for h in headers) for row in data]
        return headers, rows

    async def get_current_league_table(
        self, league: str
    ) -> tuple[list[str], list[tuple[Any]]]:
        try:
            await self.supabase_client.rpc(
                "sync_table_pp", {"tbl_name": league}
            ).execute()
        except Exception as error:
            await self.log_handler.report_error(
                f"get_current_league_table({league})",
                error,
                "Failed to sync PP values.",
            )
            return [], []

        return await self._fetch_league_data(league)

    async def get_archived_league_table(
        self, league: str, season: int
    ) -> tuple[list[str], list[tuple[Any]]]:
        table_name = f"{league}_{season}"
        return await self._fetch_league_data(table_name)

    async def _fetch_league_data(
        self, table_name: str
    ) -> tuple[list[str], list[tuple[Any]]]:
        query_selector = ", ".join(
            [
                LeagueColumn.OSU_USERNAME,
                LeagueColumn.INITIAL_PP,
                LeagueColumn.CURRENT_PP,
                LeagueColumn.PP_CHANGE,
                LeagueColumn.PERCENTAGE_CHANGE,
                LeagueColumn.II,
            ]
        )
        try:
            response = (
                await self.supabase_client.table(table_name)
                .select(query_selector)
                .order(LeagueColumn.PP_CHANGE, desc=True)
                .execute()
            )
            if response and response.data:
                return await self.arrange_table(response.data)
            return [], []

        except Exception as error:
            await self.log_handler.report_error(
                f"DatabaseHandler._fetch_league_data({table_name})", error
            )
            return [], []

    async def get_rivals_table(self, status: str) -> tuple[list[str], list[tuple[Any]]]:
        try:
            await self.supabase_client.rpc("sync_rivals").execute()
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_rivals_table()",
                error,
                "Failed running postgres function : sync_rivals()",
            )
            return [], []

        if status == ChallengeStatus.UNFINISHED:
            query_selector = [
                RivalsColumn.CHALLENGER,
                RivalsColumn.CHALLENGED,
                RivalsColumn.CHALLENGER_STATS,
                RivalsColumn.CHALLENGED_STATS,
                RivalsColumn.FOR_PP,
            ]
        else:
            query_selector = [
                RivalsColumn.CHALLENGER,
                RivalsColumn.CHALLENGED,
                RivalsColumn.WINNER,
                RivalsColumn.FOR_PP,
            ]

        try:
            response = (
                await self.supabase_client.table(TablesRivals.RIVALS)
                .select(", ".join(query_selector))
                .eq(RivalsColumn.CHALLENGE_STATUS, status)
                .execute()
            )
            if response and response.data:
                return await self.arrange_table(response.data)
            return [], []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_rivals_table()", error
            )
            return [], []

    async def add_points(self, player: str, points: int) -> dict | bool:
        try:
            response = (
                await self.supabase_client.rpc(
                    "add_points", {"player": player, "given_points": points}
                )
                .single()
                .execute()
            )
            if response and response.data:
                return response.data
            else:
                raise Exception("RPC add_points returned empty data")
        except Exception as error:
            await self.log_handler.report_error("DatabaseHandler.add_points()", error)
            return False

    async def get_archived_points(
        self, season: int
    ) -> tuple[list[str], list[tuple[Any]]]:
        col_alias = f"points:season_{season}"

        try:
            response = (
                await self.supabase_client.table(TablesPoints.HISTORICAL_POINTS)
                .select(HistoricalPointsColumn.OSU_USERNAME, col_alias)
                .limit(15)
                .order(f"season_{season}", desc=True)
                .execute()
            )
            if response.data:
                return await self.arrange_table(response.data)
            return [], []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_archived_points()", error
            )
            return [], []

    async def get_current_points(
        self, point_type: str
    ) -> tuple[list[str], list[tuple[Any]]]:
        query_selector = [
            DiscordOsuColumn.OSU_USERNAME,
            DiscordOsuColumn.CURRENT_PP,
            point_type,
        ]
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(", ".join(query_selector))
                .limit(15)
                .order(point_type, desc=True)
                .execute()
            )
            if response.data:
                return await self.arrange_table(response.data)
            return [], []

        except Exception as e:
            await self.log_handler.report_error(
                "DatabaseHandler.get_current_points()", e
            )
            return [], []

    async def get_archived_season(self) -> list[int]:
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.SEASONS)
                .select(SeasonColumn.SEASON)
                .eq(SeasonColumn.STATUS, SeasonStatus.ARCHIVED)
                .execute()
            )
            if response and response.data:
                return [data[SeasonColumn.SEASON] for data in response.data]
            return []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_archived_season()", error
            )
            return []
