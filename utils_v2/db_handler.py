from __future__ import annotations
import datetime
from typing import Any
import discord
from supabase import AsyncClient

from utils_v2.enums.status import FuncStatus
from utils_v2.enums.tables import TablesLeagues
from utils_v2.log_handler import LogHandler

from .enums import (
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
    ChallengeFailed,
    ChallengeUserColumn,
)


class DatabaseHandler:
    def __init__(self, log_handler: LogHandler, supabase_client: AsyncClient = None):
        self.log_handler = log_handler
        self.supabase_client = supabase_client

    async def get_discord_id(
        self, osu_username: str = None, discord_username: str = None
    ) -> int | None:
        log_context = "Unknown"
        try:
            # WARNING: Querying by discord_username is unreliable.
            # Users can change their Discord names, potentially
            # rendering database records stale. Always prefer
            # querying by osu_username or discord_id when possible.
            if discord_username:
                log_context = f"discord_username: {discord_username}"
                query = await self._id_from_discord(discord_username)
            else:
                log_context = f"osu_username: {osu_username}"
                query = await self._id_from_osu(osu_username)

            if not query.data:
                return None

            return query.data[0][DiscordOsuColumn.DISCORD_ID]

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_discord_id()",
                error,
                f"Lookup failed for {log_context}",
            )
            return None

    async def get_username(self, discord_id: int) -> str | None:
        try:
            # NOTE: We return the osu_username, not the discord_username.
            # The discord_username stored in the database can be outdated
            # (stale) because users can change it . The osu_username
            # is the stable identifier for this lookup as it's updated reguarly
            # in database (even better is discord_id which can't be changed)
            # But since Rivals Table doesn't have discord_id, this is the second
            # best choice
            query = await self._osu_from_id(discord_id)

            if not query.data:
                return None

            return query.data[0][DiscordOsuColumn.OSU_USERNAME]

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_username()",
                error,
                f"Lookup failed for discord_id: {discord_id}",
            )
            return None

    async def _id_from_osu(self, osu_username: str):
        return (
            await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
            .select(DiscordOsuColumn.DISCORD_ID)
            .eq(DiscordOsuColumn.OSU_USERNAME, osu_username)
            .execute()
        )

    async def _id_from_discord(self, discord_username: str):
        return (
            await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
            .select(DiscordOsuColumn.DISCORD_ID)
            .eq(DiscordOsuColumn.DISCORD_USERNAME, discord_username)
            .execute()
        )

    async def _osu_from_id(self, discord_id: int):
        return (
            await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
            .select(DiscordOsuColumn.OSU_USERNAME)
            .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
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

    async def add_points(self, discord_id: int, points: int) -> dict | bool:
        osu_uname = await self.get_username(discord_id)
        try:
            response = (
                await self.supabase_client.rpc(
                    "add_points", {"player": osu_uname, "given_points": points}
                )
                .single()
                .execute()
            )
            if response and response.data:
                return response.data
            else:
                raise Exception("RPC add_points returned empty data")
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.add_points()",
                error,
                f"Error adding {points} points for <@{discord_id}>.",
            )
            return False

    async def get_archived_points(
        self, season: int
    ) -> tuple[list[str], list[tuple[Any]]]:
        col_alias = f"points:season_{season}"

        try:
            response = (
                await self.supabase_client.table(TablesPoints.HISTORICAL_POINTS)
                .select(f"{HistoricalPointsColumn.OSU_USERNAME}, {col_alias}")
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

    async def _check_in_challenge_tble(self, discord_id: int, tble_type: str):
        query_eq = ".".join([TablesRivals.RIVALS, RivalsColumn.CHALLENGE_STATUS])
        query_selector = f"{TablesRivals.RIVALS}!inner(*)"

        try:
            response = (
                await self.supabase_client.table(tble_type)
                .select(query_selector, count="exact", head=True)
                .eq(ChallengeUserColumn.DISCORD_ID, discord_id)
                .eq(query_eq, ChallengeStatus.UNFINISHED)
                .execute()
            )
            if response and response.count:
                return response.count
            return 0
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler._check_in_challenge_tble()",
                error,
                f"The error occured for <@{discord_id}> in {tble_type.capitalize()} table",
            )
            return None

    async def get_active_challenge_count(self, discord_id: int):
        challenger_instances = await self._check_in_challenge_tble(
            discord_id, TablesRivals.CHALLENGER
        )
        challenged_instances = await self._check_in_challenge_tble(
            discord_id, TablesRivals.CHALLENGED
        )
        if challenged_instances is None or challenger_instances is None:
            return None
        return challenger_instances + challenged_instances

    async def validate_shared_league(self, discord_id: int, league: str):
        league = league.lower()
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select("*", count="exact", head=True)
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .eq(DiscordOsuColumn.LEAGUE, league)
                .execute()
            )
            # if response.count == 0, it still means false and we return false
            if response and response.count:
                return True
            return False
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler.validate_shared_league()",
                error,
                f"Error for <@{discord_id}> checking {league} League",
            )

    async def check_challenge_eligibility(self, challenger_id: int, challenged_id: int):
        challenger_uname = await self.get_username(challenger_id)
        challenged_uname = await self.get_username(challenged_id)

        if challenger_uname is None or challenged_uname is None:
            return ChallengeFailed.BAD_LINK

        try:
            history = await self._fetch_rivals_history(
                challenger_uname, challenged_uname
            )

            return self._validate_challenge_rules(history)

        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler.check_challenge_eligibility()",
                error,
                f"Error checking eligibility: {challenger_id} vs {challenged_id}",
            )
            return ChallengeFailed.FAILED

    async def _fetch_rivals_history(self, user_a: str, user_b: str) -> list:
        query_and1 = f"and({RivalsColumn.CHALLENGER}.eq.{user_a}, {RivalsColumn.CHALLENGED}.eq.{user_b})"
        query_and2 = f"and({RivalsColumn.CHALLENGER}.eq.{user_b}, {RivalsColumn.CHALLENGED}.eq.{user_a})"

        response = await (
            self.supabase_client.table(TablesRivals.RIVALS)
            .select("*")
            .or_(f"{query_and1}, {query_and2}")
            .order(RivalsColumn.ISSUED_AT, desc=True)
            .execute()
        )
        return response.data if response else []

    def _validate_challenge_rules(self, history: list):
        cutoff_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)

        for match in history:
            status = match.get(RivalsColumn.CHALLENGE_STATUS)

            raw_time = match.get(RivalsColumn.ISSUED_AT)
            issued_at = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))

            if status == ChallengeStatus.UNFINISHED:
                return ChallengeFailed.ONGOING

            if status == ChallengeStatus.PENDING:
                return ChallengeFailed.PENDING

            if issued_at > cutoff_time:
                return ChallengeFailed.TOO_EARLY

        return ChallengeFailed.GOOD

    async def log_rivals(
        self,
        challenger: discord.Member,
        challenged: discord.Member,
        for_pp: int,
        league: str,
    ):
        challenger_uname = await self.get_username(challenger.id)
        challenged_uname = await self.get_username(challenged.id)

        try:
            response = await self.supabase_client.rpc(
                "log_rivals",
                {
                    "challenger_uname": challenger_uname,
                    "challenged_uname": challenged_uname,
                    "for_pp": for_pp,
                    "league": league,
                },
            ).execute()

            if not response.data:
                raise Exception(
                    f"Error logging challenge: <@{challenger.id}> vs <@{challenged.id}>."
                )

            response2 = await self._log_to_challenge_tables(
                response.data,
                challenger,
                challenged,
                challenger_uname,
                challenged_uname,
            )

            if not response2:
                raise Exception(
                    f"Error logging challenge details: <@{challenger.id}> vs <@{challenged.id}>."
                )

            return response.data

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.log_rivals()",
                error,
                f"Error logging challenge: <@{challenger.id}> vs <@{challenged.id}>.",
            )
            return None

    async def _log_to_challenge_tables(
        self,
        challenge_id: str,
        challenger: discord.Member,
        challenged: discord.Member,
        challenger_ouname: str,
        challenged_ouname: str,
    ):
        challenger_duname = challenger.name
        challenged_duname = challenged.name

        try:
            response1 = await self.supabase_client.rpc(
                "log_to_challenge_table",
                {
                    "discord_username": challenger_duname,
                    "osu_username": challenger_ouname,
                    "discord_id": challenger.id,
                    "challenge_id": challenge_id,
                    "challenge_table": TablesRivals.CHALLENGER,
                },
            ).execute()

            if response1.data is not True:
                raise Exception(f"Error logging for challenger <@{challenger.id}>")

            response2 = await self.supabase_client.rpc(
                "log_to_challenge_table",
                {
                    "discord_username": challenged_duname,
                    "osu_username": challenged_ouname,
                    "discord_id": challenged.id,
                    "challenge_id": challenge_id,
                    "challenge_table": TablesRivals.CHALLENGED,
                },
            ).execute()

            if response2.data is not True:
                raise Exception(f"Error logging for challenged <@{challenged.id}>")

            return True

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler._log_to_challenge_tables()",
                error,
                f"Error logging challenge details: <@{challenger.id}> vs <@{challenged.id}>.",
            )
            return False

    async def revoke_challenge(self, challenge_id: int):
        try:
            await (
                self.supabase_client.table(TablesRivals.RIVALS)
                .update({RivalsColumn.CHALLENGE_STATUS: ChallengeStatus.REVOKED})
                .eq(RivalsColumn.CHALLENGE_ID, challenge_id)
                .execute()
            )
            return True
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.revoke_challenge()",
                error,
                f"Failed to revoke challenge, challenge_id : {challenge_id}",
            )
            return False

    async def accept_challenge(self, challange_id: int):
        try:
            response = await self.supabase_client.rpc(
                "accept_challenge", {"p_challenge_id": challange_id}
            ).execute()
            data = response.data
            if data:
                match_data = data if isinstance(data, dict) else data[0]
                challenger_id = match_data.get("out_challenger_id")
                challenged_id = match_data.get("out_challenged_id")
                for_pp = match_data.get("out_for_pp")
            else:
                raise Exception(f"Could not find challenge with id : {challange_id}")
            return [challenger_id, challenged_id, for_pp]
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.accept_challenge()",
                error,
                f"Failed to accept challenge, challenge_id : {challange_id}",
            )
            return None

    async def decline_challenge(self, challange_id: int):
        try:
            response = await self.supabase_client.rpc(
                "decline_challenge", {"p_challenge_id": challange_id}
            ).execute()
            data = response.data
            if data:
                match_data = data if isinstance(data, dict) else data[0]
                challenger_id = match_data.get("out_challenger_id")
                challenged_id = match_data.get("out_challenged_id")
                for_pp = match_data.get("out_for_pp")
            else:
                raise Exception(f"Could not find challenge with id : {challange_id}")
            return [challenger_id, challenged_id, for_pp]
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.decline_challenge()",
                error,
                f"Failed to decline challenge, challenge_id : {challange_id}",
            )
            return None

    async def store_msg_id(self, challenge_id: int, msg_id: int):
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.MESG_ID)
                .insert(
                    {
                        MessageIdColumn.MSG_ID: msg_id,
                        MessageIdColumn.CHALLENGE_ID: challenge_id,
                    }
                )
                .execute()
            )
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.store_msg_id()",
                error,
                f"Cannot store msg_id : {msg_id} as challenge_id : {challenge_id}",
            )

    async def get_current_season(self) -> int:
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.SEASONS)
                .select(SeasonColumn.SEASON)
                .eq(SeasonColumn.STATUS, SeasonStatus.ONGOING)
                .maybe_single()
                .execute()
            )
            if response and response.data:
                return response.data[SeasonColumn.SEASON]
            raise Exception(
                "Couldn't find any ongoing season. Please check the db if it doesn't sound right."
            )
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_current_season()",
                error,
                "Can't get stuff for current ongoing season.",
            )
            return None

    async def mark_current_archived(self, season: int) -> bool:
        try:
            response = await (
                self.supabase_client.table(TableMiscellaneous.SEASONS)
                .update({SeasonColumn.STATUS: SeasonStatus.ARCHIVED})
                .eq(SeasonColumn.SEASON, season)
                .eq(SeasonColumn.STATUS, SeasonStatus.ONGOING)
                .execute()
            )
            if not response.data:
                raise Exception(
                    f"No rows were updated when trying to mark season : {season} as archived."
                )
            return True
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.mark_current_archived()",
                error,
                f"Unable to mark season : {season} as {SeasonStatus.ARCHIVED}",
            )
            return False

    async def seasonal_point_update(self):
        error_marker = FuncStatus.GOOD
        try:
            for a_league in [league for league in TablesLeagues]:
                try:
                    await self.supabase_client.rpc(
                        "sync_table_pp", {"tbl_name": a_league}
                    ).execute()
                except Exception as error:
                    error_marker = FuncStatus.ERROR
                    self.log_handler.report_error(
                        "DatabaseHandler.seasonal_point_update()",
                        error,
                        f"Error syncing {a_league}, seasonal points for these players won't be updated",
                    )
                    continue
                try:
                    await self.supabase_client.rpc(
                        "award_seasonal_points", {"league_table_name": a_league}
                    ).execute()
                except Exception as error:
                    error_marker = FuncStatus.ERROR
                    self.log_handler.report_error(
                        "DatabaseHandler.seasonal_point_update()",
                        error,
                        f"Error syncing {a_league}, seasonal points for these players won't be updated",
                    )
                    continue
            return error_marker
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.seasonal_point_update()",
                error,
            )
            return FuncStatus.ERROR

    async def backup_seasonal_points(self, season_number):
        column_name = f"season_{season_number}"
        try:
            await self.supabase_client.rpc(
                "backup_historical_points", {"column_name": column_name}
            ).execute()
            return FuncStatus.GOOD
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.backup_seasonal_points()",
                error,
            )
            return FuncStatus.ERROR

    async def reset_seasonal_points(self):
        try:
            await self.supabase_client.rpc("reset_seasonal_points", {}).execute()
            return FuncStatus.GOOD
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.reset_seasonal_points()",
                error,
            )
            return FuncStatus.ERROR

    async def duplicate_table(self, league, season):
        new_table = f"{league}_{season}"
        try:
            await self.supabase_client.rpc(
                "duplicate_table", {"source_table": league, "new_table_name": new_table}
            ).execute()
            return FuncStatus.GOOD
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.duplicate_table()",
                error,
            )
            return FuncStatus.ERROR

    async def update_init_pp(self, league: str) -> None:
        try:
            await self.supabase_client.rpc(
                "update_init_pp", {"tbl_name": league}
            ).execute()
            return FuncStatus.GOOD
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.update_init_pp()",
                error,
            )
            return FuncStatus.ERROR

    async def update_leagues(self) -> list[dict[str, Any]] | None:
        datas = await self._fetch_mismatched_rows()
        if datas is None:
            return None

        players = []
        for data in datas:
            result = await self._process_single_transfer(data)
            if result:
                players.append(result)

        return players

    async def _fetch_mismatched_rows(self) -> list[dict[str, Any]] | None:
        try:
            response = await self.supabase_client.rpc(
                "get_mismatched_rows", {}
            ).execute()
            if response and response.data:
                return response.data
            return []
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler.update_leagues()",
                error,
                "Error at rpc function get_mismatched_rows()",
            )
            return None

    async def _process_single_transfer(
        self, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        uname = data[DiscordOsuColumn.DISCORD_USERNAME]
        league = data[DiscordOsuColumn.LEAGUE]
        future_league = data[DiscordOsuColumn.FUTURE_LEAGUE]
        discord_id = data[DiscordOsuColumn.DISCORD_ID]

        self.log_handler.report_info(
            f"Processing transfer: {uname} | {league} -> {future_league}",
            "Processing League Transfer",
        )

        if not await self._insert_into_new_league(data, future_league):
            return None

        if not await self._update_discord_osu_ref(league, future_league, discord_id):
            return None

        return {
            DiscordOsuColumn.DISCORD_USERNAME: uname,
            DiscordOsuColumn.FUTURE_LEAGUE: future_league,
            DiscordOsuColumn.LEAGUE: league,
            DiscordOsuColumn.DISCORD_ID: discord_id,
        }

    async def _insert_into_new_league(
        self, data: dict[str, Any], future_league: str
    ) -> bool:
        payload = {
            LeagueColumn.DISCORD_USERNAME: data[DiscordOsuColumn.DISCORD_USERNAME],
            LeagueColumn.OSU_USERNAME: data[DiscordOsuColumn.OSU_USERNAME],
            LeagueColumn.INITIAL_PP: data[DiscordOsuColumn.CURRENT_PP],
            LeagueColumn.CURRENT_PP: data[DiscordOsuColumn.CURRENT_PP],
            LeagueColumn.GLOBAL_RANK: data[DiscordOsuColumn.GLOBAL_RANK],
            LeagueColumn.II: data[DiscordOsuColumn.II],
            LeagueColumn.DISCORD_ID: data[DiscordOsuColumn.DISCORD_ID],
        }

        try:
            await self.supabase_client.table(future_league).insert([payload]).execute()
            return True
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler._insert_into_new_league()",
                error,
                f"Failed putting <@{data[DiscordOsuColumn.DISCORD_ID]}> into {future_league}",
            )
            return False

    async def _update_discord_osu_ref(
        self, old_league: str, future_league: str, discord_id: int
    ) -> bool:
        try:
            await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .update({DiscordOsuColumn.LEAGUE: future_league})
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            return True
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler._update_discord_osu_ref()",
                error,
                f"Failed updating <@{discord_id}> from {old_league} to {future_league}",
            )
            return False

    async def check_pending(self, challenger_id: int, challenged_id: int) -> int | None:
        challenger_uname = await self.get_username(challenger_id)
        challenged_uname = await self.get_username(challenged_id)

        if not challenger_uname or not challenged_uname:
            return None

        try:
            response = await (
                self.supabase_client.table(TablesRivals.RIVALS)
                .select(RivalsColumn.CHALLENGE_ID)
                .eq(RivalsColumn.CHALLENGER, challenger_uname)
                .eq(RivalsColumn.CHALLENGED, challenged_uname)
                .eq(RivalsColumn.CHALLENGE_STATUS, ChallengeStatus.PENDING)
                .maybe_single()
                .execute()
            )

            if response and response.data:
                return response.data[RivalsColumn.CHALLENGE_ID]

            return None

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.check_pending()", error
            )
            return None

    async def check_player_existence(self, discord_id: int) -> list[dict[str, Any]]:
        try:
            response = await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(f"{DiscordOsuColumn.POINTS, DiscordOsuColumn.SEASONAL_POINTS}")
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .single()
                .execute()
            )
            if response and response.data:
                return response.data
            return FuncStatus.EMPTY
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler.check_player_existence()",
                error,
                f"Failed to retrive player <@{discord_id}>",
            )
            return FuncStatus.ERROR

    async def remove_player(self, discord_id: int) -> bool:
        try:
            response = await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .delete()
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            # data was not deleted, so no response in response.data
            if not response.data:
                return False
            return True
        except Exception as error:
            self.log_handler.report_error(
                "DatabaseHandler.remove_player()",
                error,
                f"Error occured for <@{discord_id}>",
            )
            return False
