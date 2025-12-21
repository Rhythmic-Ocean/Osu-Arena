"""
Database fetching utilities.

This module contains all functions responsible for fetching data from the
Supabase database. It handles data synchronization via RPC calls and retrieves
table data for leagues, player statistics, and challenge identifiers.

For database schema details, refer to `supabase_schema.txt` in the root directory.
"""

import supabase
from .core_v2 import TABLE_MODES, create_supabase, CHALLENGE_STATUS
from .archive_utils import get_historical_points
import logging
from typing import List, Tuple, Any

"""
Functions in this module:
1. get_table_data(leag: str, stat: str = None) -> Tuple[List[str], List[Tuple[str, ...]]]
2. get_pp(osu_username: str = None, discord_username: str = None) -> int | None
3. get_osu_uname(discord_uname: str) -> str | None
4. get_discord_id(osu_username: str) -> Any
5. get_msg_id(challenge_id: Any) -> Any
"""

logging.basicConfig(filename="db_getter.log", level=logging.DEBUG, filemode="w")


async def get_table_data(
    leag: str, stat: str = None
) -> Tuple[List[str], List[Tuple[str, ...]]]:
    """
    Retrieves table data for a specific league or the rivals list.

    This function fetches data from Supabase. It synchronizes the table data
    before fetching (using 'sync_rivals' or 'sync_table_pp' RPCs) to ensure
    stats are current.

    Args:
        leag (str): The name of the league (e.g., 'bronze', 'silver') or 'rivals'.
        stat (str, optional): The challenge status filter. Used primarily for
                              the 'rivals' table to distinguish between 'Unfinished'
                              and 'Finished' challenges.

    Returns:
        Tuple[List[str], List[Tuple[str, ...]]]: A tuple containing:
            - A list of column headers (List[str]).
            - A list of rows, where each row is a tuple of values (List[Tuple[str, ...]]).

        Example Return:
            (['Rank', 'Player', 'PP'], [(1, 'PlayerOne', 4500), (2, 'PlayerTwo', 4200)])

        Returns ([], []) on failure.

    Note:
        - The 'discord_osu' table is the only always-up-to-date table.
        - League tables are synced via RPC calls immediately before retrieval.
        - Historical tables are suffixed with season numbers (e.g., 'silver_1').
    """
    league = leag.lower()
    supabase = await create_supabase()

    if league == "rivals":
        try:
            await supabase.rpc("sync_rivals").execute()
        except Exception as e:
            print(f"Error syncing Rivals: {e}")
            return [], []

        try:
            if stat == CHALLENGE_STATUS[4]:
                response = (
                    await supabase.table(league)
                    .select("challenger, challenged, for_pp, winner, challenge_status")
                    .eq("challenge_status", CHALLENGE_STATUS[4])
                    .order("challenge_id", desc=False)
                    .execute()
                )
            else:
                response = (
                    await supabase.table(league)
                    .select(
                        "challenger, challenged, challenger_stats, challenged_stats, for_pp"
                    )
                    .eq("challenge_status", CHALLENGE_STATUS[3])
                    .order("challenge_id", desc=False)
                    .execute()
                )
        except Exception as e:
            print(f"Error show rivals: {e}")
            return [], []
    elif league == "points":
        response = await get_current_points(TABLE_MODES[11])
    elif league == "s_points":
        if not stat:
            response = await get_current_points(TABLE_MODES[12])
        else:
            response = await get_historical_points(stat)
    else:
        try:
            await supabase.rpc("sync_table_pp", {"tbl_name": league}).execute()
        except Exception as e:
            print(f"Error sync leagues: {e}")
            return [], []

        try:
            response = (
                await supabase.table(league)
                .select(
                    "osu_username, initial_pp, current_pp, pp_change, percentage_change, ii"
                )
                .order("pp_change", desc=True)
                .execute()
            )
        except Exception as e:
            print(f"Error at show league tables: {e}")
            return [], []

    if response.data:
        rows = response.data
        headers = list(rows[0].keys())
        row_tuples = [tuple(row.get(h, 0) for h in headers) for row in rows]
        return headers, row_tuples
    else:
        return [], []


async def get_pp(osu_username: str = None, discord_username: str = None) -> int | None:
    """
    Fetches the current PP (Performance Points) of a user.

    Can query by either osu! username or Discord username.

    Args:
        osu_username (str, optional): The user's osu! username.
        discord_username (str, optional): The user's Discord username.

    Returns:
        int | None: The user's current PP if found, otherwise None.
    """
    supabase = await create_supabase()

    if osu_username:
        try:
            response = (
                await supabase.table("discord_osu")
                .select("current_pp")
                .eq("osu_username", osu_username)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]["current_pp"]
            else:
                logging.warning(
                    f"[get_pp] No data found for osu_username: {osu_username}"
                )
                return None
        except Exception as e:
            logging.error(
                f"[get_pp] Error while fetching by osu_username ({osu_username}): {e}"
            )
            return None

    if discord_username:
        try:
            response = (
                await supabase.table("discord_osu")
                .select("current_pp")
                .eq("discord_username", discord_username)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]["current_pp"]
            else:
                logging.warning(
                    f"[get_pp] No data found for discord_username: {discord_username}"
                )
                return None
        except Exception as e:
            logging.error(
                f"[get_pp] Error while fetching by discord_username ({discord_username}): {e}"
            )
            return None

    logging.warning("[get_pp] No username provided.")
    return None


async def get_osu_uname(discord_uname: str) -> str | None:
    """
    Retrieves the osu! username corresponding to a given Discord username.

    Args:
        discord_uname (str): The Discord username to query.

    Returns:
        str | None: The osu! username if found, otherwise None.
    """
    supabase = await create_supabase()
    try:
        response = (
            await supabase.table("discord_osu")
            .select("osu_username")
            .eq("discord_username", discord_uname)
            .execute()
        )
        if response.data:
            return response.data[0]["osu_username"]
        else:
            return None
    except Exception as e:
        logging.error(f"Error at get_osu_uname: {e}")
        return None


async def get_discord_id(osu_username: str) -> Any:
    """
    Retrieves the Discord ID corresponding to a given osu! username.

    Args:
        osu_username (str): The osu! username to query.

    Returns:
        Any: The Discord ID (usually int or int-string) if found, otherwise None.
    """
    supabase = await create_supabase()
    try:
        query = (
            await supabase.table("discord_osu")
            .select("discord_id")
            .eq("osu_username", osu_username)
            .execute()
        )
        result = query.data[0]["discord_id"]
        return result
    except Exception as e:
        logging.error(f"Error at get_discord_id: {e}")
        print(f"Error at get_discord_id: {e}")
        return None


async def get_msg_id(challenge_id: Any) -> Any:
    """
    Retrieves the Discord message ID associated with a specific challenge.

    This ID is used to locate and update the challenge announcement message
    when the status changes.

    Args:
        challenge_id (Any): The unique identifier for the challenge.

    Returns:
        Any: The message ID if found, otherwise None.
    """
    supabase = await create_supabase()
    try:
        row = (
            await supabase.table("mesg_id")
            .select("msg_id")
            .eq("challenge_id", challenge_id)
            .execute()
        )
        result = row.data[0]["msg_id"]
        if result is None:
            return None
        print(result)
        return result
    except Exception as e:
        logging.error(f"Error at get msg id: {e}")
    return None


async def get_current_points(type: str):
    points_supabase = await create_supabase()
    try:
        if type == TABLE_MODES[12]:
            response = (
                await points_supabase.table("discord_osu")
                .select("osu_username,current_pp,seasonal_points")
                .limit(15)
                .order("seasonal_points", desc=True)
                .execute()
            )
        elif type == TABLE_MODES[11]:
            response = (
                await points_supabase.table("discord_osu")
                .select("osu_username,current_pp,points")
                .limit(15)
                .order("points", desc=True)
                .execute()
            )
        return response
    except Exception as e:
        print(f"Error at get_current_points(): {e}")
