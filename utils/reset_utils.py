"""
Utilities for Season Resets and League Updates.

This module handles the logic for transitioning between seasons, including:
1. Resetting initial PP values for the new season.
2. Processing promotions and relegations (moving players between league tables).
"""

import logging
from typing import List, Dict, Any
from .core_v2 import create_supabase, TABLE_MODES
from .db_getter import get_pp, get_osu_uname

"""
Functions in this module:
1. update_init_pp(league: str) -> None
2. update_leagues() -> List[Dict[str, Any]]
"""

logging.basicConfig(filename="reset_utils.log", level=logging.DEBUG, filemode='w')

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
        query = await supabase.table('discord_osu').select('discord_username, discord_id, league, future_league').execute()
        datas = query.data
        
        for data in datas:
            league = data['league']
            future_league = data['future_league']
            u_id = data['discord_id']
            uname = data['discord_username']

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
                await supabase.table(league).delete().eq('discord_username', uname).execute()
            
            # Insert into new table
            await supabase.table(future_league).insert([{
                'discord_username': uname,
                'osu_username': osu_uname,
                'initial_pp': pp
            }]).execute()
            
            # Update the main reference table
            await supabase.table('discord_osu').update({'league': future_league}).eq('discord_username', uname).execute()
            
            players.append({
                'discord_username': uname,
                'league_transferred': future_league,
                'old_league': league,
                'discord_id': u_id
            })
            
        return players

    except Exception as e:
        logging.error(f"Error updating leagues: {e}")
        return []