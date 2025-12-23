from asyncio.base_futures import _FINISHED
import discord
from discord.ext import commands
from typing import Any
from discord.ext.commands import Context
from supabase import AsyncClient
from utils.core_v2 import CHALLENGE_STATUS
from utils_v2 import ChallengeStatus, RivalsColumn
from utils_v2.enums.tables import TablesRivals
from utils_v2.enums.tables_internals import RivalsData


class Monitor(commands.cog, name="monitor"):
    def __init__(self, bot: commands.Bot, supabase_client: AsyncClient):
        self.bot = bot
        self.supabase_client = supabase_client
        self.error_handler = bot.error_handler

    async def check_end(self, row: RivalsColumn) -> tuple[str, str] | None:
        for_pp = row[RivalsColumn.FOR_PP]
        challenger_stats = row[RivalsColumn.CHALLENGER_STATS]
        challenged_stats = row[RivalsColumn.CHALLENGED_STATS]
        if challenger_stats >= for_pp:
            return (RivalsColumn.CHALLENGER, RivalsColumn.CHALLENGED)
        elif challenged_stats >= for_pp:
            return (RivalsColumn.CHALLENGED, RivalsColumn.CHALLENGER)
        else:
            return None

    async def monitor_rivals(self):
        rivals_table = self.get_rivals()
        for row in rivals_table:
            is_end = self.check_end(row)
            if is_end is None:
                continue
            else:
                winner, loser = is_end
                self.end_challenge(row, winner, loser)

    async def get_rivals(self) -> list[RivalsData]:
        REQ_COLUMNS = ", ".join(
            [
                RivalsColumn.CHALLENGER,
                RivalsColumn.CHALLENGED,
                RivalsColumn.CHALLENGE_ID,
                RivalsColumn.FOR_PP,
                RivalsColumn.CHALLENGER_STATS,
                RivalsColumn.CHALLENGED_STATS,
            ]
        )
        try:
            query = (
                await self.supabase_client.table(TablesRivals.RIVALS)
                .select(REQ_COLUMNS)
                .eq(RivalsColumn.CHALLENGE_STATUS, ChallengeStatus.PENDING)
                .execute()
            )
            return query.data if (query and query.data) else []
        except Exception as e:
            print(f"Exception fetching rivals: {e}")
            return []

    async def end_challenge(self, row: RivalsColumn, winner: str, loser: str) -> None:
        winner_uname = row[winner]
        loser_uname = row[loser]
        challenge_id = row[RivalsColumn.CHALLENGE_ID]
        try:
            await (
                self.supabase_client.table(TablesRivals.RIVALS)
                .update(
                    {
                        RivalsColumn.CHALLENGE_STATUS: ChallengeStatus.FINISHED,
                        RivalsColumn.WINNER: winner_uname,
                    }
                )
                .eq(RivalsColumn.CHALLENGE_ID, challenge_id)
                .execute()
            )
        except Exception as e:
            self.error_handler.report_error(
                "Monitor.end_challenge()",
                e,
                f"Failed updating Challenge Status for challenge_id{challenge_id}",
            )
