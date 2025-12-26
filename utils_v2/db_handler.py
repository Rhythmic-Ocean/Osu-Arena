from __future__ import annotations
from typing import Any
from utils_v2 import TableMiscellaneous, DiscordOsuColumn
from utils_v2.enums.tables_internals import MessageIdColumn
from typing import TYPE_CHECKING
from supabase import AsyncClient

if TYPE_CHECKING:
    from bot import OsuArena


class DatabaseHandler:
    def __init__(self, bot: OsuArena, supabase_client: AsyncClient):
        self.bot = bot
        self.error_handler = self.bot.error_handler
        self.supabase_client = supabase_client

    async def get_discord_id(
        self, osu_username: str = None, discord_username: str = None
    ):
        uname = "Unknown"
        try:
            if not discord_username:
                uname = f"Osu_uname: {osu_username}"
                query = await self.id_from_osu(osu_username)
            else:
                uname = f"discord_username: {discord_username}"
                query = await self.id_from_discord(discord_username)

            if not query.data:
                raise ValueError(f"User not found in DB: {uname}")

            result = query.data[0][DiscordOsuColumn.DISCORD_ID]
            return result

        except Exception as error:
            await self.error_handler.report_error(
                "DatabaseGetter.get_discord_id()",
                error,
                f"Did not get a discord_id for {uname}",
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

    async def get_msg_id(self, challenge_id: int) -> int:
        try:
            # FIX 1: Use the correct attribute name 'supabase_client'
            row = (
                await self.supabase_client.table(TableMiscellaneous.MESG_ID)
                .select(MessageIdColumn.MSG_ID)
                .eq(MessageIdColumn.CHALLENGE_ID, challenge_id)
                .execute()
            )

            # FIX 2: Check if list is empty BEFORE accessing [0]
            if not row.data:
                # Raise error here so it jumps to the except block
                raise ValueError(f"Msg ID not found for challenge_id: {challenge_id}")

            result = row.data[0][MessageIdColumn.MSG_ID]
            return result

        except Exception as error:
            await self.error_handler.report_error(
                "DatabaseGetter.get_msg_id()",
                error,
                f"Failed to retrieve Msg ID for challenge {challenge_id}",
            )
            return None

    async def add_points(self, player, points):
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
                raise Exception("RPC function add_points() did not run properly!")
        except Exception as error:
            await self.error_handler.report_error(
                "DatabaseGetter.add_points()",
                error,
            )
        return False

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
            if response.data:
                return response.data
        except Exception as error:
            await self.error_handler.report_error(
                "DatabaseHandler.top_play_detector()", error
            )
        return None

    async def negate_top_play(self, discord_id) -> bool:
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .update({DiscordOsuColumn.TOP_PLAY_ANNOUNCE: False})
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            return True
        except Exception as e:
            self.error_handler.report_error(
                "DatabaseHandler.negate_top_play()",
                e,
                f"Failed to negate top play for <@{discord_id}>",
            )
            return False

    async def new_player_detector(self):
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
            if response and response.data:
                return response.data
        except Exception as error:
            self.error_handler.report_error(
                "DatabaseHandler.new_player_detector()",
                error,
            )
        return None

    async def negate_new_player_announce(self, discord_id):
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .update({DiscordOsuColumn.TOP_PLAY_ANNOUNCE: False})
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            return True
        except Exception as e:
            self.error_handler.report_error(
                "DatabaseHandler.negate_top_play()",
                e,
                f"Failed to negate top play for <@{discord_id}>",
            )
            return False
