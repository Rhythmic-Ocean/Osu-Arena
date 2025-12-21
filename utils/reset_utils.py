"""
Utilities for Season Resets and League Updates.

This module handles the logic for transitioning between seasons, including:
1. Resetting initial PP values for the new season.
2. Processing promotions and relegations (moving players between league tables).
"""

import logging
import discord
from typing import List, Dict, Any

from postgrest import Timeout
from .core_v2 import create_supabase, TABLE_MODES, LEAGUE_MODES
from .db_getter import get_pp, get_osu_uname
import discord.ui

"""
Functions in this module:
1. update_init_pp(league: str) -> None
2. update_leagues() -> List[Dict[str, Any]]
"""

logging.basicConfig(filename="reset_utils.log", level=logging.DEBUG, filemode="w")


class ResetConfirmView(discord.ui.View):
    def __init__(self, interaction=discord.Interaction):
        super().__init__(timeout=30)
        self.value = None
        self.original_user = interaction.user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            await interaction.response.send_message(
                "⛔ This is not your command!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Yes, Restart the season.", style=discord.ButtonStyle.green
    )
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel restart.", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


async def update_init_pp(league: str) -> None:
    """
    Updates the 'initial_pp' column for all users in a specific league table.

    Calls a Supabase RPC function ('update_init_pp') to snapshot the current
    PP as the starting point for the new season/period.

    Args:
        league (str): The name of the league table to update.
    """
    supabase = await create_supabase()
    try:
        await supabase.rpc("update_init_pp", {"tbl_name": league}).execute()
    except Exception as e:
        print(f"Error updating init pp: {e}")
        logging.error(f"Error updating init pp for {league}: {e}")


async def update_leagues() -> List[Dict[str, Any]]:
    """
    Processes promotions and relegations for all players.

    Iterates through the 'discord_osu' table. If a player's 'future_league'
    differs from their current 'league', it moves their data to the new
    league table and updates their status.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the players
                              who were successfully transferred.
    """
    supabase = await create_supabase()
    players = []

    try:
        query = (
            await supabase.table("discord_osu")
            .select("discord_username, discord_id, league, future_league")
            .execute()
        )
        datas = query.data

        for data in datas:
            league = data["league"]
            future_league = data["future_league"]
            u_id = data["discord_id"]
            uname = data["discord_username"]

            # Skip if no change is needed or if data is incomplete
            if league == future_league:
                continue
            if not league or not future_league:
                continue

            print(f"Processing transfer: {uname} | {league} -> {future_league}")

            osu_uname = await get_osu_uname(discord_uname=uname)
            pp = await get_pp(discord_username=uname)

            # Delete from old table (unless it's the 'Ranker' table, id 7)
            if league != TABLE_MODES[7]:
                await (
                    supabase.table(league)
                    .delete()
                    .eq("discord_username", uname)
                    .execute()
                )

            # Insert into new table
            await (
                supabase.table(future_league)
                .insert(
                    [
                        {
                            "discord_username": uname,
                            "osu_username": osu_uname,
                            "initial_pp": pp,
                        }
                    ]
                )
                .execute()
            )

            # Update the main reference table
            await (
                supabase.table("discord_osu")
                .update({"league": future_league})
                .eq("discord_username", uname)
                .execute()
            )

            players.append(
                {
                    "discord_username": uname,
                    "league_transferred": future_league,
                    "old_league": league,
                    "discord_id": u_id,
                }
            )

        return players

    except Exception as e:
        logging.error(f"Error updating leagues: {e}")
        return []


async def seasonal_point_update():
    seasonal_point_update_supabase = await create_supabase()
    try:
        for a_league in LEAGUE_MODES.values():
            try:
                await seasonal_point_update_supabase.rpc(
                    "sync_table_pp", {"tbl_name": a_league}
                ).execute()
            except Exception as e:
                print(f"Error sync leagues: {e}")
                continue
            await seasonal_point_update_supabase.rpc(
                "award_seasonal_points", {"league_table_name": a_league}
            ).execute()
            print(f"Updated this season's winner points for {a_league}.")
    except Exception as e:
        print(f"Error at function seasonal_point_update() : {e}")


async def reset_seasonal_points():
    seasonal_point_reset_supabase = await create_supabase()
    try:
        await seasonal_point_reset_supabase.rpc("reset_seasonal_points", {}).execute()
    except Exception as e:
        print(f"Something wrong at reset_seasonal_points() function {e}")


async def get_current_season():
    season_getter_supabase = await create_supabase()
    try:
        response = (
            await season_getter_supabase.table("seasons")
            .select("season")
            .eq("status", "Ongoing")
            .maybe_single()
            .execute()
        )
        if response.data:
            print(response.data["season"])
            return response.data["season"]

    except Exception as e:
        print(f"Error at get_current_season() function: {e}")
    return None


async def backup_seasonal_points(season_number):
    column_name = f"season_{season_number}"
    backup_supabase = await create_supabase()
    try:
        await backup_supabase.rpc(
            "backup_historical_points", {"column_name": column_name}
        ).execute()
    except Exception as e:
        print(f"Error at backup_historical_points() function : {e}")


async def mark_season_archived(season):
    marking_supabase = await create_supabase()
    try:
        response = (
            await marking_supabase.table("seasons")
            .update({"status": "Archived"})
            .eq("season", season)
            .execute()
        )
        if response.data:
            print(f"Season '{season}' successfully archived.")
            return True
        else:
            print(f"Warning: Season '{season}' not found, nothing archived.")
            return False
    except Exception as e:
        print(f"Error at mark_season_archived() fnc {e}")


async def duplicate_table(league, season):
    new_table = f"{league}_{season}"
    print(new_table)
    duplicating_supabase = await create_supabase()
    try:
        response = await duplicating_supabase.rpc(
            "duplicate_table", {"source_table": league, "new_table_name": new_table}
        ).execute()
        print(response)
        if response and response.data is True:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error at duplicate_table() function : {e}")
        return False
