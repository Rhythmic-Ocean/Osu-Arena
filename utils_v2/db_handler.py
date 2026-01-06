"""
Every functionality that requires access to the database goes through this class.
Common class for both the website and the bot for database access
"""

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
    """Represents an interface for interacting with the PostgreSQL database via Supabase.

    This class handles data retrieval and formatting for operations across
    both the Discord bot and the web dashboard.

    Parameters
    -----------
    log_handler: :class:`LogHandler`
        The logger used for error handling and exception reporting.
        Typically, this should be an existing instance configured for
        either the bot or the web application.
    supabase_client: :class:`supabase.AsyncClient`
        The asynchronous client used to communicate with the Supabase API.
    """

    def __init__(self, log_handler: LogHandler, supabase_client: AsyncClient):
        self.log_handler = log_handler
        self.supabase_client = supabase_client

    async def get_discord_id(
        self, osu_username: str | None = None, discord_username: str | None = None
    ) -> int | None:
        """|coro|
        A coroutine to access a user's discord_id through their osu/discord username.
        Give only one of the two arguments at a time
        Accesses table : discord_osu

        Parameters
        -----------
        osu_username : class:`str`
            user's osu username

        discord_username : class:`str`
        user's discord username

        Returns
        -----------
        int | None
            The discord_id of the corresponding user if it exists
        """
        # WARNING: Querying by discord_username is unreliable.
        # Users can change their Discord names, potentially
        # rendering database records stale. Always prefer
        # querying by osu_username or discord_id when possible.
        log_context = "Unknown"
        try:
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
        """|coro|
        A coroutine to access a user's osu! username through their discord_id.
        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : class:`int`
            The user's unique Discord ID.

        Returns
        -----------
        str | None
            The osu! username of the corresponding user if it exists.
        """
        # NOTE: We return the osu_username, not the discord_username.
        # The discord_username stored in the database can be outdated
        # (stale) because users can change it (and it's not updated in the
        # database, after the intiial entry. The osu_username is the stable
        # identifier for this lookup as it's updated reguarly in database
        # (even better is discord_id which can't be changed).
        # But since Rivals Table doesn't have discord_id, this is the second
        # best choice
        try:
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

    async def get_msg_id(self, challenge_id: int) -> int | None:
        """|coro|
        A coroutine to access the message ID associated with a specific challenge.
        Accesses table : mesg_id

        Parameters
        -----------
        challenge_id : class:`int`
            The unique identifier of the challenge.
            Usually assigned when a new challenge is created in rivals table

        Returns
        -----------
        int | None
            The message ID if it exists, otherwise ``None``.
        """
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
        """|coro|
        Retrieves a list of users who have new top plays.

        This fetches the identification data (osu!/Discord IDs) for all users
        marked with ``top_play_announce = True`` in the database.

        The ``top_play_announce`` flag is set by the background worker in ``supabase.py``
        whenever a player achieves a new top play. This function detects those flags
        and retrieves the data for all such players.

        Accesses table : discord_osu

        Returns
        -----------
        list[dict[str, Any]] | None
            A list of user records containing ID and username fields,
            or ``None`` if no users are found or an error occurs.
        """
        # WARNING: It is strongly advised to access this data through
        # Monitor.monitor_top_plays() rather than calling this directly.
        # That method immediately resets 'top_play_announce' to False after
        # retrieval, preventing race conditions and duplicate announcements.
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
        """|coro|
        Resets the top play announcement flag for a user.

        This sets ``top_play_announce`` to ``False`` in the database, indicating
        that the pending top play has been successfully processed and announced.

        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : class:`int`
            The user's unique Discord ID.

        Returns
        -----------
        bool
            ``True`` if the update was successful, ``False`` otherwise.
        """
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
        """|coro|
        Retrieves a list of newly registered users waiting for an announcement.

        This fetches identification and league data for all users marked with
        ``new_player_announce = True`` in the database.

        The ``new_player_announce`` flag is set by the background worker in ``supabase.py``
        whenever a new player /links their account. This function detects those flags
        and retrieves the data for all such players.

        Accesses table : discord_osu

        Returns
        -----------
        list[dict[str, Any]] | None
            A list of user records containing ID, username, and league fields,
            or ``None`` if no users are found or an error occurs.
        """
        # WARNING: It is strongly advised to access this data through
        # Monitor.monitor_new_players() rather than calling this directly.
        # That method immediately resets 'new_player_announce' to False after
        # retrieval, preventing race conditions and duplicate announcements.
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
        """|coro|
        Resets the new player announcement flag for a user.

        This sets ``new_player_announce`` to ``False`` in the database, indicating
        that the new player arrival has been successfully processed and announced.

        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : class:`int`
            The user's unique Discord ID.

        Returns
        -----------
        bool
            ``True`` if the update was successful, ``False`` otherwise.
        """
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

    async def get_current_league_table(
        self, league: str
    ) -> tuple[list[str], list[tuple[Any]]]:
        """|coro|
        Retrieves the current standings for a specific league.

        This method first triggers a remote procedure call (``sync_table_pp``)
        to ensure all player performance points are up-to-date, and then
        fetches the sorted league data.

        Accesses table : f"{TablesLeagues.(any)}"

        Parameters
        -----------
        league : class:`str`
            The name of the league table to retrieve (e.g., "silver", "gold").

        Returns
        -----------
        tuple[list[str], list[tuple[Any]]]
            A tuple containing:
            1. A list of column headers (strings).
            2. A list of rows, where each row is a tuple of values.
            Returns ``([], [])`` if the synchronization or fetch fails.
        """
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
        """|coro|
        Retrieves historical standings for a specific past season.

        This constructs the archived table name (e.g., "silver_1") and fetches
        the data.

        Accesses table : f"{ArchivedTable.(any)}"

        Parameters
        -----------
        league : class:`str`
            The name of the league (e.g., "silver").
        season : class:`int`
            The season number to retrieve.

        Returns
        -----------
        tuple[list[str], list[tuple[Any]]]
            A tuple containing headers and row data for the archived season.
            Returns ``([], [])`` if the table does not exist.
        """
        table_name = f"{league}_{season}"
        return await self._fetch_league_data(table_name)

    async def get_rivals_table(self, status: str) -> tuple[list[str], list[tuple[Any]]]:
        """|coro|
        Retrieves the rivals table filtered by challenge status.

        This method first triggers a remote procedure call (``sync_rivals``)
        to ensure match statistics are up-to-date. The columns returned vary
        depending on whether the status is 'Unfinished' or 'Finished'.

        When passing the status it's recommended you pass it as an attribute of
        ChallengeStatus class.

        Accesses table : rivals

        Parameters
        -----------
        status : class:`str`
            The status to filter by (e.g., ``ChallengeStatus.UNFINISHED``).

        Returns
        -----------
        tuple[list[str], list[tuple[Any]]]
            A tuple containing headers and formatted row data.
            Returns ``([], [])`` on failure or if no data is found.
        """
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
                return await self._arrange_table(response.data)
            return [], []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_rivals_table()", error
            )
            return [], []

    async def add_points(
        self, points: int, discord_id: int = None, osu_uname=None
    ) -> dict | bool:
        """|coro|
        Adds points to a user's account via a database RPC function (`add_points`)

        You must provide either a ``discord_id`` (which will be resolved to a username)
        or the ``osu_username`` directly. Exactly one parameter required at a time.

        Accesses table : discord_osu

        Parameters
        -----------
        points : class:`int`
            The amount of points to add.
        discord_id : class:`int` | None
            The user's Discord ID.
        osu_username : class:`str` | None
            The user's osu! username.

        Returns
        -----------
        dict[str, Any] | bool
            The updated row data (as a dict) if successful, or ``False`` on failure.
        """
        # TODO: Update the 'add_points' PostgreSQL RPC to accept 'discord_id' directly.
        # While 'osu_username' is synchronized regularly, 'discord_id' is immutable
        # and provides a more robust identifier. This would also remove the need
        # for the intermediate username lookup in this function.
        if discord_id:
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

    async def get_current_points(
        self, point_type: str
    ) -> tuple[list[str], list[tuple[Any]]]:
        """|coro|
        Retrieves the top 15 players for (Univseral/ Seasonal) point category.

        This queries the discord_osu table to fetch rankings based on the
        given points-type column.

        Accesses table : discord_osu

        Parameters
        -----------
        point_type : class:`str`
            The database column name of the point type to retrieve.

        Returns
        -----------
        tuple[list[str], list[tuple[Any]]]
            A tuple containing headers and the top 15 rows of data.
            Returns ``([], [])`` if no data is found or on error.
        """
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
                return await self._arrange_table(response.data)
            return [], []

        except Exception as e:
            await self.log_handler.report_error(
                "DatabaseHandler.get_current_points()", e
            )
            return [], []

    async def get_archived_points(
        self, season: int
    ) -> tuple[list[str], list[tuple[Any]]]:
        """|coro|
        Retrieves the data for top 15 point scorers for a specific past season.

        This queries the historical points table, selecting the column
        corresponding to the requested season (e.g., ``season_3``) and aliasing
        it to ``points`` for formatting purposes.


        Accesses table : historical_points

        Parameters
        -----------
        season : class:`int`
            The season number to retrieve data for.

        Returns
        -----------
        tuple[list[str], list[tuple[Any]]]
            A tuple containing headers and the top 15 rows of data.
            Returns ``([], [])`` if the season data is missing or an error occurs.
        """
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
                return await self._arrange_table(response.data)
            return [], []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_archived_points()", error
            )
            return [], []

    async def get_archived_season(self) -> list[int]:
        """|coro|
        Retrieves a list of all season numbers that are currently archived.

        Accesses table : seasons

        Returns
        -----------
        list[int]
            A list of season integers (e.g., ``[1, 2, 3]``).
            Returns an empty list (``[]``) if no archived seasons are found or and error occurs.
        """
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

    async def get_active_challenge_count(self, discord_id: int) -> int | None:
        """|coro|
        Calculates the total number of active challenges for a specific user.

        This checks both the 'challenger' and 'challenged' columns to count
        how many Unfinished/ Pending challenges the user is currently involved in.

        Accesses tables = f"{TablesRivals.(any)}"

        Parameters
        -----------
        discord_id : class:`int`
            The user's unique Discord ID.

        Returns
        -----------
        int | None
            The total count of active challenges.
            Returns ``None`` if a database lookup fails 0 if not challenge for the player exists.
        """
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
        """|coro|
        Checks if a user belongs to a specific league.

        This performs a lightweight "head" query (counting rows without fetching data)
        to verify if the user exists in the specified league.

        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : class:`int`
            The user's unique Discord ID.
        league : class:`str`
            The name of the league to check (e.g., "gold").

        Returns
        -----------
        bool
            ``True`` if the user is in the specified league, ``False`` otherwise.
        """
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
            await self.log_handler.report_error(
                "DatabaseHandler.validate_shared_league()",
                error,
                f"Error for <@{discord_id}> checking {league} League",
            )

    async def check_challenge_eligibility(
        self, challenger_id: int, challenged_id: int
    ) -> ChallengeFailed:
        """|coro|
        Determines if a user is eligible to challenge another user based on their challenge history.

        This function acts as an orchestrator. It resolves Discord IDs to osu!
        usernames, fetches the match history between the two players, and passes
        that data to the rule validator.

        **Rule Checks:**
        1. Checks for any challenges between the pair within the last 24 hours.
        2. Checks for any currently unfinished or pending challenges.

        Internal calls: :meth:`get_username`, :meth:`_fetch_rivals_history`

        Parameters
        -----------
        challenger_id : :class:`int`
            The Discord ID of the user initiating the challenge.
        challenged_id : :class:`int`
            The Discord ID of the user receiving the challenge.

        Returns
        -----------
        :class:`ChallengeFailed`
            The status of the eligibility check:

            * ``ChallengeFailed.GOOD``: The users are eligible to challenge.
            * ``ChallengeFailed.PENDING``: A pending challenge already exists between the two.
            * ``ChallengeFailed.ONGOING``: An unfinished challenge exists between the two.
            * ``ChallengeFailed.TOO_EARLY``: A challenge (of any status) occurred within the last 24 hours.
            * ``ChallengeFailed.BAD_LINK``: One or both users are not linked to the system.
            * ``ChallengeFailed.FAILED``: An internal database error prevented the check.
        """
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
            await self.log_handler.report_error(
                "DatabaseHandler.check_challenge_eligibility()",
                error,
                f"Error checking eligibility: {challenger_id} vs {challenged_id}",
            )
            return ChallengeFailed.FAILED

    async def log_rivals(
        self,
        challenger: discord.Member,
        challenged: discord.Member,
        for_pp: int,
        league: str,
    ) -> dict[str, Any] | None:
        """|coro|
        Initiates and logs a new challenge match between two users.

        This method performs a two-step logging process:

        1. Calls the Supabase RPC ``log_rivals`` to create the primary match record in rivals table.
        2. Calls :meth:`_log_to_challenge_tables` to populate the auxillary tables challenged and challenger

        Internal calls: :meth:`get_username`, :meth:`_log_to_challenge_tables`

        Parameters
        -----------
        challenger : :class:`discord.Member`
            The Discord member object of the user initiating the challenge.
        challenged : :class:`discord.Member`
            The Discord member object of the user receiving the challenge.
        for_pp : :class:`int`
            The amount of points (PP) effectively wagered on this match.
        league : :class:`str`
            The identifier of the league this match belongs to (e.g., "gold").

        Returns
        -----------
        :class:`dict` | None
            The data returned by the database RPC if successful (usually containing the new Match ID).
            Returns ``None`` if an error occurs during the logging process.
        """
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

    async def accept_challenge(self, challange_id: int) -> list[int] | None:
        """|coro|
        Marks a specific challenge as accepted(Pending -> Unfinishd) in the rivals table.

        This calls the Supabase RPC ``accept_challenge``, which updates the match status
        as well as logs in the accepted date (now) and current pp as 'initial_pp'.
        It returns discord_id of the two rivals players as well as the number of pp they
        playing for, this will be used to later make announcement in the public discord
        channel.


        Parameters
        -----------
        challenge_id : :class:`int`
            The unique ID of the challenge to accept.

        Returns
        -----------
        :class:`list`[:class:`int`] | None
            A list containing ``[challenger_id, challenged_id, for_pp]`` if successful.
            Returns ``None`` if the challenge ID was not found or an error occurred.
        """
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

    async def decline_challenge(self, challange_id: int) -> list[int] | None:
        """|coro|
        Marks a specific challenge as declined (Pending -> Declined) in the rivals table.

        This calls the Supabase RPC ``decline_challenge``, which updates the match status
        to mark it as declined. Also updates the 'ended_at' column of rivals tables to log in
        the time right now. It returns the discord_id of the two rival players which will be
        used to notify in the public channel that this challenge was declined

        Parameters
        -----------
        challenge_id : :class:`int`
            The unique ID of the challenge to decline.

        Returns
        -----------
        :class:`list`[:class:`int`] | None
            A list containing ``[challenger_id, challenged_id, for_pp]`` if successful.
            Returns ``None`` if the challenge ID was not found or an error occurred.
        """
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

    async def revoke_challenge(self, challenge_id: int) -> bool:
        """|coro|
        Marks a specific challenge as revoked (Pending -> Revoked) in the rivals table.

        Unlike accept/decline, this method performs a direct table update on
        :attr:`~TablesRivals.RIVALS` rather than calling an RPC function. Usually
        called when some challenge becomes invalid due to internal error, or a
        challenger wants to revoke their pending challenge with someone.

        Accesses table : rivals

        Parameters
        -----------
        challenge_id : :class:`int`
            The unique ID of the challenge to revoke.

        Returns
        -----------
        :class:`bool`
            ``True`` if the update was successful, ``False`` otherwise.
        """
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

    async def store_msg_id(self, challenge_id: int, msg_id: int) -> None:
        """|coro|
        Links a Discord message ID to a specific challenge ID in the database.

        This is used to track the public challenge message so the bot can later
        update it or delete it if needed.

        Accesses table : msg_id

        Parameters
        -----------
        challenge_id : :class:`int`
            The unique ID of the challenge.
        msg_id : :class:`int`
            The Discord message ID of the notification/embed sent to the channel.
        """
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
        """|coro|
        Retrieves the season number of the currently ongoing season. Used for
        /season-reset command right now

        It queries the :attr:`~TableMiscellaneous.SEASONS` table for a row where
        the status is ``SeasonStatus.ONGOING``.

        Accesses table : seasons

        Returns
        -----------
        :class:`int` | None
            The current season number if found.
            Returns ``None`` if no ongoing season exists or if an error occurs.
        """
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

    async def mark_season_archived(self, season: int) -> bool:
        """|coro|
        Updates the status of a specific season from ONGOING to ARCHIVED.

        This is typically called at the end of a season (done with /season-reset)
        to lock it before starting a new one.

        Accesses table : seasons

        Parameters
        -----------
        season : :class:`int`
            The season number to archive.

        Returns
        -----------
        :class:`bool`
            ``True`` if the update was successful (rows were modified).
            ``False`` if the season was not found, was not ongoing, or an error occurred.
        """
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

    async def seasonal_point_update(self) -> FuncStatus:
        """|coro|
        Synchronizes and awards seasonal points for all leagues. Done during
        a season's end

        Iterates through every league table and performs two RPC calls per league:

        1. ``sync_table_pp``: Ensures current pp matches the latest osu! API data.
        2. ``award_seasonal_points``: Calculates and distributes points for the season during it's end

        If a league fails to update, the loop continues to the next one, but the
        function will return an error status at the end.

        Returns
        -----------
        :class:`FuncStatus`
            * ``FuncStatus.GOOD``: All leagues updated successfully.
            * ``FuncStatus.ERROR``: One or more leagues failed to update.
        """
        error_marker = FuncStatus.GOOD
        try:
            for a_league in [league for league in TablesLeagues]:
                try:
                    await self.supabase_client.rpc(
                        "sync_table_pp", {"tbl_name": a_league}
                    ).execute()
                except Exception as error:
                    error_marker = FuncStatus.ERROR
                    await self.log_handler.report_error(
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
                    await self.log_handler.report_error(
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

    async def backup_seasonal_points(self, season_number) -> FuncStatus:
        """|coro|
        Backs up the current seasonal points from discord_osu table to column in
        historical_points table.

        Calls the RPC ``backup_historical_points``, which copies the current points
        into a dynamic column named ``season_{number}``.

        Parameters
        -----------
        season_number : :class:`int`
            The season number to use for the column suffix (e.g., 4 for ``season_4``).

        Returns
        -----------
        :class:`FuncStatus`
            ``FuncStatus.GOOD`` if successful, ``FuncStatus.ERROR`` otherwise.
        """
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

    async def reset_seasonal_points(self) -> FuncStatus:
        """|coro|
        Resets the seasonal points for all users to zero. (Usually called at the
        end of the season)

        Calls the RPC ``reset_seasonal_points``. This is typically done immediately
        after backing up the points for the previous season.

        Accesses table : discord_osu

        Returns
        -----------
        :class:`FuncStatus`
            ``FuncStatus.GOOD`` if successful, ``FuncStatus.ERROR`` otherwise.
        """
        try:
            await self.supabase_client.rpc("reset_seasonal_points", {}).execute()
            return FuncStatus.GOOD
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.reset_seasonal_points()",
                error,
            )
            return FuncStatus.ERROR

    async def duplicate_table(self, league, season) -> FuncStatus:
        """|coro|
        Creates an archival copy of a league table for a specific season.

        Calls the RPC ``duplicate_table`` to copy the data from the active league
        table (e.g., "gold") to a new archival table (e.g., "gold_4").

        Parameters
        -----------
        league : :class:`str`
            The name of the league to backup (e.g., "gold").
        season : :class:`int`
            The season number to append to the new table name.

        Returns
        -----------
        :class:`FuncStatus`
            ``FuncStatus.GOOD`` if successful, ``FuncStatus.ERROR`` otherwise.
        """
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

    async def update_init_pp(self, league: str) -> FuncStatus:
        """|coro|
        Updates the 'initial_pp' value for all users in for the given league
        to the value in their corrsponding `current_pp` column in discord_osu
        table. This is done thru RPC function.


        Calls the RPC ``update_init_pp``. This sets the user's current PP as their
        starting PP for the new season or period.

        Parameters
        -----------
        league : :class:`str`
            The name of the league table to update.

        Returns
        -----------
        :class:`FuncStatus`
            ``FuncStatus.GOOD`` if successful, ``FuncStatus.ERROR`` otherwise.
        """
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
        """|coro|
        Identifies and processes users who need to be transferred between leagues.

        This process involves:
        1. Fetching mismatched rows (users whose PP no longer fits their current league).
        2. Processing each transfer individually via :meth:`_process_single_transfer`.

        Returns
        -----------
        :class:`list`[:class:`dict`[:class:`str`, :class:`Any`]] | None
            A list of player dictionaries representing successful transfers.
            Returns ``None`` if fetching mismatched rows failed.
        """
        datas = await self._fetch_mismatched_rows()
        if datas is None:
            return None

        players = []
        for data in datas:
            result = await self._process_single_transfer(data)
            if result:
                players.append(result)

        return players

    async def check_pending(self, challenger_id: int, challenged_id: int) -> int | None:
        """|coro|
        Checks if a pending challenge exists between two users. Used when someone Accepts
        a challenge. This function is called to verify that such challenge exists.

        This queries the :attr:`~TablesRivals.RIVALS` table for any row connecting
        these two users where the status is ``ChallengeStatus.PENDING``.

        Accesses table : rivals

        Internal calls: :meth:`get_username`

        Parameters
        -----------
        challenger_id : :class:`int`
            The Discord ID of the potential challenger.
        challenged_id : :class:`int`
            The Discord ID of the potential challenge recipient.

        Returns
        -----------
        :class:`int` | None
            The ``challenge_id`` if a pending challenge exists.
            Returns ``None`` if no pending challenge is found or an error occurs.
        """
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

    async def check_player_existence_for_points(
        self, discord_id: int
    ) -> list[dict[str, Any]]:
        """|coro|
        This function's is used when /point command is called and is used to
        verify if the given player exist in the database and report back their
        points if they do.

        Queries the main discord_osu table for the user's total and seasonal points.

        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : :class:`int`
            The Discord ID of the user to check.

        Returns
        -----------
        :class:`dict`[:class:`str`, :class:`Any`] | :class:`FuncStatus`
            A dictionary containing ``{'points': ..., 'seasonal_points': ...}`` if found.
            Returns ``FuncStatus.EMPTY`` if the user does not exist.
            Returns ``FuncStatus.ERROR`` if the database query fails.
        """
        # TODO: Refactor this funtion to make it do just one thing instead of two
        # stuffs half-ass
        try:
            response = await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(
                    f"{DiscordOsuColumn.POINTS}, {DiscordOsuColumn.SEASONAL_POINTS}"
                )
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .maybe_single()
                .execute()
            )
            if response and response.data:
                return response.data
            return FuncStatus.EMPTY
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.check_player_existence_for_points()",
                error,
                f"Failed to retrive player <@{discord_id}>",
            )
            return FuncStatus.ERROR

    async def remove_player(self, discord_id: int) -> bool:
        """|coro|
        Permanently deletes a player from the database.

        This removes the user's row from :attr:`~TableMiscellaneous.DISCORD_OSU`.

        Cascading deletion is enabled so once this function is called, the user's
        data is deleted from all table but rivals (and all their ongoing/ pending
        challenges form rivals tables are delete too, but that's done in a different
        function)

        Parameters
        -----------
        discord_id : :class:`int`
            The Discord ID of the user to remove.

        Returns
        -----------
        :class:`bool`
            ``True`` if the user was successfully deleted.
            ``False`` if the user was not found or an error occurred.
        """
        try:
            response = await (
                self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .delete()
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            # data was not deleted, so no response in response.data
            if not response.data:
                raise Exception(f"Failed to find <@{discord_id}>")

            return True
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.remove_player()",
                error,
                f"Error occured for <@{discord_id}>",
            )
            return False

    async def get_player(self, discord_id: int) -> dict[str, Any] | None | FuncStatus:
        """|coro|
        Retrieves a user's osu_username, initial_pp and their current_league
        based on their discord_id. This is to display them on /dashboard in the
        web.

        This is a two-step process:

        1. Fetches basic info (username, pp(this one's useless, wanna remove it but
        don't wanna break anything just in case), league) from the discord_osu table.
        2. Calls :meth:`_get_player_from_league` to fetch rank and stats from the
        specific league table (e.g., "gold" or "silver").

        Accesses tables : discord_osu , f"{TableLeague.(any)}"

        Parameters
        -----------
        discord_id : :class:`int`
            The Discord ID of the user to retrieve.

        Returns
        -----------
        :class:`dict`[:class:`str`, :class:`Any`] | None | :class:`FuncStatus`
            A dictionary containing the full player profile if successful.
            Returns ``None`` if the player is not found in the main table.
            Returns ``FuncStatus.ERROR`` if an internal error occurs.
        """
        query_selector = [
            DiscordOsuColumn.OSU_USERNAME,
            DiscordOsuColumn.CURRENT_PP,
            DiscordOsuColumn.LEAGUE,
        ]
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select(", ".join(query_selector))
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .maybe_single()
                .execute()
            )

            if response and response.data:
                return await self._get_player_from_league(
                    response.data[DiscordOsuColumn.LEAGUE],
                    discord_id,
                    response.data[DiscordOsuColumn.OSU_USERNAME],
                )

            return None

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_player()",
                error,
                f"Error checking player <@{discord_id}>",
            )
            return FuncStatus.ERROR

    async def check_if_player_exists(self, discord_id: int) -> bool:
        """|coro|
        Checks if a user is registered in the system.

        This performs a lightweight "head" query (fetching only the count, not the data)
        to the :attr:`~TableMiscellaneous.DISCORD_OSU` table to verify their existence.

        Accesses table : discord_osu

        Parameters
        -----------
        discord_id : :class:`int`
            The unique Discord ID to check.

        Returns
        -----------
        :class:`bool`
            ``True`` if the user exists in the database, ``False`` otherwise.
        """
        try:
            response = (
                await self.supabase_client.table(TableMiscellaneous.DISCORD_OSU)
                .select("*", count="exact", head=True)
                .eq(DiscordOsuColumn.DISCORD_ID, discord_id)
                .execute()
            )
            if response and response.count > 0:
                return True
            return False
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.check_if_player_exists()",
                error,
                f"Error checking for <@{discord_id}>.",
            )

    async def get_active_challenges(
        self, discord_id: int, osu_username: str
    ) -> list[dict[str, Any]] | FuncStatus:
        """|coro|
        Retrieves all active challenges (Pending or Unfinished) for a specific user.
        (This function is currently NOT in use anywhere, just here in case I make
        a functionality to have individual player's profiles)

        This checks both the "challenger" and "challenged" columns to find any
        involvement the user has in ongoing matches.

        Accessses tables : f"{TableRivals.(any)}"

        Parameters
        -----------
        discord_id : :class:`int`
            The Discord ID of the user (used primarily for error logging).
        osu_username : :class:`str`
            The user's osu! username (used for the database query).

        Returns
        -----------
        :class:`list`[:class:`dict`[:class:`str`, :class:`Any`]] | :class:`FuncStatus`
            A list of dictionary objects representing the active challenges.
            Returns an empty list ``[]`` if no active challenges are found.
            Returns ``FuncStatus.ERROR`` if the query fails.
        """
        # note: postgres syntax require double quotes around strings with spaces and these one can have spaces
        osu_username = f'"{osu_username}"'
        try:
            response = (
                await self.supabase_client.table(TablesRivals.RIVALS)
                .select(
                    f"{RivalsColumn.CHALLENGE_ID}, {RivalsColumn.CHALLENGED}, {RivalsColumn.CHALLENGER}"
                )
                .or_(
                    f"{RivalsColumn.CHALLENGED}.eq.{osu_username}, {RivalsColumn.CHALLENGER}.eq.{osu_username}"
                )
                .or_(
                    f"{RivalsColumn.CHALLENGE_STATUS}.eq.{ChallengeStatus.PENDING}, {RivalsColumn.CHALLENGE_STATUS}.eq.{ChallengeStatus.UNFINISHED}"
                )
                .execute()
            )
            if response and response.data:
                data = [item for item in response.data]
                return data
            return []
        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler.get_active_challenge()",
                error,
                f"Error retriving challenge for <@{discord_id}>",
            )
            return FuncStatus.ERROR

    # ------------------------------------------------------------------------------
    # Internal / Helper Methods
    # ------------------------------------------------------------------------------
    # NOTE: Do not use them unless you have to. Error handling is really inconsistent
    # in this functions. I've let some bubble up while others are handled in place.
    # So if you are gonna use them,

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

    async def _arrange_table(
        self, data: list[dict[str, Any]]
    ) -> tuple[list[str], list[tuple[Any]]]:
        if not data:
            return [], []
        headers = list(data[0].keys())
        rows = [tuple(row.get(h, 0) for h in headers) for row in data]
        return headers, rows

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
                return await self._arrange_table(response.data)
        except Exception as error:
            await self.log_handler.report_error(
                f"DatabaseHandler._fetch_league_data({table_name})", error
            )
            return [], []

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
            await self.log_handler.report_error(
                "DatabaseHandler._check_in_challenge_tble()",
                error,
                f"The error occured for <@{discord_id}> in {tble_type.capitalize()} table",
            )
            return None

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

    async def _fetch_mismatched_rows(self) -> list[dict[str, Any]] | None:
        try:
            response = await self.supabase_client.rpc(
                "get_mismatched_rows", {}
            ).execute()
            if response and response.data:
                return response.data
            return []
        except Exception as error:
            await self.log_handler.report_error(
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

        await self.log_handler.report_info(
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
            await self.log_handler.report_error(
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
            await self.log_handler.report_error(
                "DatabaseHandler._update_discord_osu_ref()",
                error,
                f"Failed updating <@{discord_id}> from {old_league} to {future_league}",
            )
            return False

    async def _get_player_from_league(
        self, league_table: str, discord_id: int, osu_username: str
    ) -> dict[str, Any] | FuncStatus:
        try:
            response = (
                await self.supabase_client.table(league_table)
                .select(LeagueColumn.INITIAL_PP)
                .eq(LeagueColumn.DISCORD_ID, discord_id)
                .maybe_single()
                .execute()
            )

            if response and response.data:
                return {
                    LeagueColumn.OSU_USERNAME: osu_username,
                    LeagueColumn.INITIAL_PP: response.data[LeagueColumn.INITIAL_PP],
                    DiscordOsuColumn.LEAGUE: league_table,
                }

            raise Exception(
                f"Data Integrity Error: User <@{discord_id}> exists in 'discord_osu' "
                f"but is missing from league table '{league_table}'."
            )

        except Exception as error:
            await self.log_handler.report_error(
                "DatabaseHandler._get_player_from_league()", error
            )
            return FuncStatus.ERROR
